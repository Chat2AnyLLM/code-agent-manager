// Package entities provides the shared data model for CAM's "managed
// entities" — prompts, skills, agents, and plugins.
//
// Each entity type has the same lifecycle: a JSON manifest store under
// ~/.config/code-agent-manager/<kind>s.json holds metadata, and per-tool
// install paths receive the rendered content (Markdown for prompts/skills,
// directories for agents, plugin manifests for plugins).
//
// Sub-projects #5–#8 add command surfaces over this package; the unified
// model keeps the binary small and avoids the per-handler subclass hierarchy
// from Python.
package entities

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// Kind identifies the entity category.
type Kind string

const (
	// KindPrompt is the legacy name for instructions, kept so that
	// metadata and CLI packages that still reference it can compile.
	// It is NOT used inside this package; use KindInstruction instead.
	KindPrompt Kind = "prompt"

	KindInstruction Kind = "instruction"
	KindSkill       Kind = "skill"
	KindAgent       Kind = "agent"
	KindPlugin      Kind = "plugin"
)

// Entity is the canonical representation stored on disk.
type Entity struct {
	Kind        Kind           `json:"kind"`
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Content     string         `json:"content,omitempty"`
	Path        string         `json:"path,omitempty"`
	Repo        *RepoRef       `json:"repo,omitempty"`
	Apps        []string       `json:"apps,omitempty"`
	Tags        []string       `json:"tags,omitempty"`
	Metadata    map[string]any `json:"metadata,omitempty"`
	UpdatedAt   time.Time      `json:"updated_at"`
}

// RepoRef points at the upstream source for fetched entities.
type RepoRef struct {
	Owner  string `json:"owner"`
	Name   string `json:"name"`
	Branch string `json:"branch,omitempty"`
	Path   string `json:"path,omitempty"`
}

// Store persists Entity records as JSON.  Each kind gets its own file so they
// can be migrated independently.
type Store struct {
	dir  string
	kind Kind
}

// NewStore constructs a Store rooted at ~/.config/code-agent-manager
// (overridable via CAM_CONFIG_DIR).
func NewStore(kind Kind) *Store {
	return &Store{dir: pathutil.ConfigDir(), kind: kind}
}

// Path returns the on-disk JSON path for the store.
func (s *Store) Path() string {
	return filepath.Join(s.dir, string(s.kind)+"s.json")
}

// All returns every entity in the store sorted by name.
func (s *Store) All() ([]Entity, error) {
	if err := s.migrateIfInstruction(); err != nil {
		return nil, err
	}
	data := map[string]Entity{}
	raw, err := os.ReadFile(s.Path())
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("entities: read %s: %w", s.Path(), err)
	}
	if len(raw) == 0 {
		return nil, nil
	}
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, fmt.Errorf("entities: parse %s: %w", s.Path(), err)
	}
	out := make([]Entity, 0, len(data))
	for _, e := range data {
		out = append(out, e)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out, nil
}

// Get returns an entity by name.
func (s *Store) Get(name string) (Entity, error) {
	all, err := s.All()
	if err != nil {
		return Entity{}, err
	}
	for _, e := range all {
		if e.Name == name {
			return e, nil
		}
	}
	return Entity{}, fmt.Errorf("entities: %s %q not found", s.kind, name)
}

// Put writes (creates or replaces) an entity.
func (s *Store) Put(entity Entity) error {
	if entity.Name == "" {
		return fmt.Errorf("entities: name is required")
	}
	entity.Kind = s.kind
	entity.UpdatedAt = time.Now().UTC()
	all := map[string]Entity{}
	if existing, err := s.All(); err == nil {
		for _, e := range existing {
			all[e.Name] = e
		}
	}
	all[entity.Name] = entity
	return s.write(all)
}

// Delete removes an entity and reports whether it existed.
func (s *Store) Delete(name string) (bool, error) {
	all, err := s.allMap()
	if err != nil {
		return false, err
	}
	if _, ok := all[name]; !ok {
		return false, nil
	}
	delete(all, name)
	if err := s.write(all); err != nil {
		return false, err
	}
	return true, nil
}

func (s *Store) allMap() (map[string]Entity, error) {
	if err := s.migrateIfInstruction(); err != nil {
		return nil, err
	}
	out := map[string]Entity{}
	raw, err := os.ReadFile(s.Path())
	if err != nil {
		if os.IsNotExist(err) {
			return out, nil
		}
		return nil, err
	}
	if len(raw) == 0 {
		return out, nil
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *Store) write(all map[string]Entity) error {
	if err := os.MkdirAll(s.dir, 0o755); err != nil {
		return fmt.Errorf("entities: mkdir %s: %w", s.dir, err)
	}
	data, err := json.MarshalIndent(all, "", "  ")
	if err != nil {
		return fmt.Errorf("entities: marshal: %w", err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(s.Path(), data, 0o600); err != nil {
		return fmt.Errorf("entities: write %s: %w", s.Path(), err)
	}
	return nil
}

func (s *Store) migrateIfInstruction() error {
	if s.kind != KindInstruction {
		return nil
	}
	return MigrateEntityStorage()
}

// MigrateEntityStorage migrates legacy prompt entities to instruction storage
// idempotently. It reads prompts.json, converts each entity's Kind from
// "prompt" to "instruction", and writes them to instructions.json. The
// prompts.json file is left untouched. If instructions.json already exists or
// prompts.json does not exist, no migration is performed.
func MigrateEntityStorage() error {
	dir := pathutil.ConfigDir()
	oldPath := filepath.Join(dir, "prompts.json")
	newPath := filepath.Join(dir, "instructions.json")

	if _, err := os.Stat(newPath); err == nil {
		return nil
	}

	raw, err := os.ReadFile(oldPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("entities: read %s: %w", oldPath, err)
	}
	if len(raw) == 0 {
		return nil
	}

	entitiesByName := map[string]Entity{}
	if err := json.Unmarshal(raw, &entitiesByName); err != nil {
		return fmt.Errorf("entities: parse %s: %w", oldPath, err)
	}
	for name, entity := range entitiesByName {
		entity.Kind = KindInstruction
		entitiesByName[name] = entity
	}

	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("entities: mkdir %s: %w", dir, err)
	}
	data, err := json.MarshalIndent(entitiesByName, "", "  ")
	if err != nil {
		return fmt.Errorf("entities: marshal migrated instructions: %w", err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(newPath, data, 0o600); err != nil {
		return fmt.Errorf("entities: write %s: %w", newPath, err)
	}
	return nil
}
