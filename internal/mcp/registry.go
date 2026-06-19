// Package mcp manages the Model Context Protocol server catalog and wires
// servers into per-tool config files.
//
// The package embeds the bundled mcpm-style server schemas at compile time so
// `cam mcp server list/search/show` work out of the box.  Per-client config
// writers live in client.go and dispatch on tool name.
package mcp

import (
	"embed"
	"encoding/json"
	"fmt"
	"io/fs"
	"sort"
	"strings"
)

//go:embed all:registry/servers
var bundledRegistry embed.FS

// ServerSchema mirrors the bundled mcpm-style JSON files.
type ServerSchema struct {
	Name          string                       `json:"name"`
	DisplayName   string                       `json:"display_name"`
	Description   string                       `json:"description"`
	Repository    Repository                   `json:"repository"`
	Homepage      string                       `json:"homepage"`
	Author        Author                       `json:"author"`
	License       string                       `json:"license"`
	Categories    []string                     `json:"categories"`
	Tags          []string                     `json:"tags"`
	Installations map[string]InstallationEntry `json:"installations"`
	Arguments     map[string]any               `json:"arguments,omitempty"`
}

type Repository struct {
	Type string `json:"type"`
	URL  string `json:"url"`
}

type Author struct {
	Name string `json:"name"`
}

// InstallationEntry describes one way to run the server.
type InstallationEntry struct {
	Type    string            `json:"type"`
	Command string            `json:"command"`
	Args    []string          `json:"args"`
	Env     map[string]string `json:"env,omitempty"`
	URL     string            `json:"url,omitempty"`
	Headers map[string]string `json:"headers,omitempty"`
}

// Registry exposes lookups against the bundled MCP server catalog.
type Registry struct {
	schemas map[string]ServerSchema
}

// LoadBundledRegistry parses every embedded JSON schema into a Registry.  The
// load fails fast on the first malformed file so binary-time validation
// surfaces drift between Python and Go.
func LoadBundledRegistry() (*Registry, error) {
	out := map[string]ServerSchema{}
	err := fs.WalkDir(bundledRegistry, "registry/servers", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(path, ".json") {
			return nil
		}
		data, err := bundledRegistry.ReadFile(path)
		if err != nil {
			return err
		}
		var schema ServerSchema
		if err := json.Unmarshal(data, &schema); err != nil {
			return fmt.Errorf("mcp: parse %s: %w", path, err)
		}
		if schema.Name == "" {
			return fmt.Errorf("mcp: schema missing name in %s", path)
		}
		out[schema.Name] = schema
		return nil
	})
	if err != nil {
		return nil, err
	}
	return &Registry{schemas: out}, nil
}

// Get looks up a server by name.
func (r *Registry) Get(name string) (ServerSchema, bool) {
	s, ok := r.schemas[name]
	return s, ok
}

// Names returns the registered server names in alphabetical order.
func (r *Registry) Names() []string {
	names := make([]string, 0, len(r.schemas))
	for n := range r.schemas {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// All returns every registered schema, sorted by name. Unlike Search it returns
// the full catalog when no query is supplied (Search returns nil for an empty
// query), which is what the registry browser needs to list all discovered servers.
func (r *Registry) All() []ServerSchema {
	out := make([]ServerSchema, 0, len(r.schemas))
	for _, name := range r.Names() {
		out = append(out, r.schemas[name])
	}
	return out
}

// Search returns all schemas whose name, display name, description, tags or
// categories contain the query (case-insensitive).
func (r *Registry) Search(query string) []ServerSchema {
	q := strings.ToLower(strings.TrimSpace(query))
	if q == "" {
		return nil
	}
	out := []ServerSchema{}
	for _, name := range r.Names() {
		s := r.schemas[name]
		if matchesQuery(s, q) {
			out = append(out, s)
		}
	}
	return out
}

func matchesQuery(s ServerSchema, q string) bool {
	if strings.Contains(strings.ToLower(s.Name), q) {
		return true
	}
	if strings.Contains(strings.ToLower(s.DisplayName), q) {
		return true
	}
	if strings.Contains(strings.ToLower(s.Description), q) {
		return true
	}
	for _, t := range s.Tags {
		if strings.Contains(strings.ToLower(t), q) {
			return true
		}
	}
	for _, c := range s.Categories {
		if strings.Contains(strings.ToLower(c), q) {
			return true
		}
	}
	return false
}

// PreferredInstallation returns the best installation method for the schema.
// Order matches the Python implementation: docker, uvx, npm, python, custom.
func (s ServerSchema) PreferredInstallation() (string, InstallationEntry, bool) {
	for _, key := range []string{"docker", "uvx", "npm", "python", "custom"} {
		if entry, ok := s.Installations[key]; ok {
			return key, entry, true
		}
	}
	for key, entry := range s.Installations {
		return key, entry, true
	}
	return "", InstallationEntry{}, false
}
