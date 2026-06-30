// Package repoconfig loads skill/agent/plugin repository definitions by
// walking every source declared in config.yaml's repositories.<kind>s.sources
// list, exactly mirroring the Python RepoConfigLoader:
//
//  1. Bundled JSON embedded in the binary — always loaded first as a fallback.
//  2. config.yaml sources (in order):
//     - type: local  → read the JSON file at the expanded path.
//     Local entries override everything already loaded (bundled + earlier).
//     - type: remote → fetch the JSON URL (with a disk cache governed by
//     cache.ttl_seconds).  Remote entries only fill gaps — they never
//     override keys already provided by a local source.
//
// The result is a merged map of RepoEntry values keyed by their JSON key
// (typically "owner/name" for skills/agents, or a slug for plugins).
package repoconfig

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/camconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/entities"
	"github.com/chat2anyllm/code-agent-manager/internal/fetching"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

//go:embed embed/skill_repos.json
var bundledSkillRepos []byte

//go:embed embed/agent_repos.json
var bundledAgentRepos []byte

//go:embed embed/plugin_repos.json
var bundledPluginRepos []byte

//go:embed embed/prompt_repos.json
var bundledPromptRepos []byte

//go:embed embed/instruction_repos.json
var bundledInstructionRepos []byte

// RepoEntry is a single repository definition.  Field names match the JSON
// keys used in the Python version so the same files work for both.
type RepoEntry struct {
	Owner       string   `json:"owner,omitempty"`
	Name        string   `json:"name,omitempty"`
	Branch      string   `json:"branch,omitempty"`
	Enabled     *bool    `json:"enabled,omitempty"`
	SkillsPath  string   `json:"skillsPath,omitempty"`
	AgentsPath  string   `json:"agentsPath,omitempty"`
	PluginPath  string   `json:"pluginPath,omitempty"`
	CatalogFile string   `json:"catalogFile,omitempty"`
	Exclude     []string `json:"exclude,omitempty"`

	// Plugin-specific fields.
	Description string   `json:"description,omitempty"`
	Type        string   `json:"type,omitempty"`
	RepoOwner   string   `json:"repoOwner,omitempty"`
	RepoName    string   `json:"repoName,omitempty"`
	RepoBranch  string   `json:"repoBranch,omitempty"`
	Aliases     []string `json:"aliases,omitempty"`
}

// IsEnabled returns true when the entry is enabled (default true).
func (r RepoEntry) IsEnabled() bool {
	if r.Enabled == nil {
		return true
	}
	return *r.Enabled
}

// EffectiveOwner returns the owner, preferring RepoOwner for plugin entries.
func (r RepoEntry) EffectiveOwner() string {
	if r.RepoOwner != "" {
		return r.RepoOwner
	}
	return r.Owner
}

// EffectiveName returns the repo name, preferring RepoName for plugin entries.
func (r RepoEntry) EffectiveName() string {
	if r.RepoName != "" {
		return r.RepoName
	}
	return r.Name
}

// EffectiveBranch returns the branch, defaulting to "main".
func (r RepoEntry) EffectiveBranch() string {
	if r.RepoBranch != "" {
		return r.RepoBranch
	}
	if r.Branch != "" {
		return r.Branch
	}
	return "main"
}

// RawFileURL builds a raw GitHub content URL for a repo entry and repo-relative file.
func (r RepoEntry) RawFileURL(baseURL, filePath string) string {
	owner := r.EffectiveOwner()
	repo := r.EffectiveName()
	if owner == "" || repo == "" {
		return ""
	}
	branch := r.EffectiveBranch()
	filePath = strings.Trim(strings.TrimSpace(filePath), "/")
	if filePath == "" {
		return ""
	}
	base := strings.TrimRight(baseURL, "/")
	return fmt.Sprintf("%s/%s/%s/%s/%s", base, url.PathEscape(owner), url.PathEscape(repo), url.PathEscape(branch), path.Clean(filePath))
}

// SubPath returns the sub-directory inside the repo where entities live
// (e.g. skillsPath or agentsPath).
func (r RepoEntry) SubPath(kind entities.Kind) string {
	switch kind {
	case entities.KindSkill:
		return r.SkillsPath
	case entities.KindAgent:
		return r.AgentsPath
	case entities.KindInstruction:
		return r.AgentsPath
	case entities.KindPlugin:
		return r.PluginPath
	}
	return ""
}

// ---------- loading ----------------------------------------------------------

// LoadAll returns all repo entries for the given kind by merging sources
// configured in config.yaml.  The loading order follows the Python
// RepoConfigLoader exactly:
//
//  1. Bundled JSON embedded in the binary (lowest priority, fallback).
//  2. Iterate every source in config.yaml repositories.<kind>s.sources:
//     - type: local  → read the JSON file at the expanded path.
//     Local entries override everything already loaded.
//     - type: remote → fetch the URL (with disk cache).
//     Remote entries only fill gaps — they do NOT override keys that
//     a local source already provided.
//
// If config.yaml has no sources or cannot be loaded, only the bundled
// entries are returned.
func LoadAll(kind entities.Kind) (map[string]RepoEntry, error) {
	if kind == entities.KindInstruction {
		if _, err := MigrateRepoConfigFiles(pathutil.ConfigDir()); err != nil {
			return nil, err
		}
	}
	merged := make(map[string]RepoEntry)

	// 1. Bundled defaults (lowest priority).
	bundled, err := loadBundled(kind)
	if err != nil {
		return nil, fmt.Errorf("repoconfig: bundled: %w", err)
	}
	for k, v := range bundled {
		merged[k] = v
	}

	// 2. Walk every source from config.yaml in declaration order.
	cfg, cfgErr := camconfig.Load("")
	if cfgErr == nil {
		repoKey := repoConfigKey(kind)
		if src, ok := cfg.Repositories[repoKey]; ok {
			for _, s := range src.Sources {
				switch s.Type {
				case "local":
					if s.Path == "" {
						continue
					}
					local, err := LoadLocalSource(s.Path)
					if err != nil || local == nil {
						continue
					}
					// Local sources override everything (same as Python's
					// repos.update(loaded)).
					for k, v := range local {
						merged[k] = v
					}

				case "remote":
					if s.URL == "" {
						continue
					}
					remote, err := loadRemoteWithCache(s.URL, kind, cfg.Cache)
					if err != nil {
						// Non-fatal: remote may be unavailable.
						continue
					}
					// Remote entries only fill gaps — don't override keys
					// already set by a local source (same as Python's
					// "if key not in repos: repos[key] = value").
					for k, v := range remote {
						if _, exists := merged[k]; !exists {
							merged[k] = v
						}
					}
				}
			}
		}
	}

	return merged, nil
}

// LoadEnabled is a convenience wrapper that filters out disabled entries.
func LoadEnabled(kind entities.Kind) (map[string]RepoEntry, error) {
	all, err := LoadAll(kind)
	if err != nil {
		return nil, err
	}
	for k, v := range all {
		if !v.IsEnabled() {
			delete(all, k)
		}
	}
	return all, nil
}

// ---------- per-source loaders -----------------------------------------------

func loadBundled(kind entities.Kind) (map[string]RepoEntry, error) {
	var raw []byte
	switch kind {
	case entities.KindSkill:
		raw = bundledSkillRepos
	case entities.KindAgent:
		raw = bundledAgentRepos
	case entities.KindPlugin:
		raw = bundledPluginRepos
	case entities.KindPrompt:
		raw = bundledPromptRepos
	case entities.KindInstruction:
		raw = bundledInstructionRepos
	default:
		// Unknown kinds return an empty map so config.yaml sources
		// can still be loaded.
		return make(map[string]RepoEntry), nil
	}
	return parseRepoJSON(raw)
}

// LoadLocalSource reads a JSON repo file from the given path, expanding ~.
// Used for both config.yaml local sources and direct path lookups.
func LoadLocalSource(path string) (map[string]RepoEntry, error) {
	resolved := pathutil.Expand(path)
	data, err := os.ReadFile(resolved)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	return parseRepoJSON(data)
}

func loadRemoteWithCache(url string, kind entities.Kind, cache camconfig.CacheConfig) (map[string]RepoEntry, error) {
	if cache.Enabled {
		if cached, err := loadFromCache(url, kind, cache); err == nil && cached != nil {
			return cached, nil
		}
	}

	client := fetching.New()
	tmp, err := os.CreateTemp("", "cam-repocfg-*.json")
	if err != nil {
		return nil, err
	}
	tmpPath := tmp.Name()
	tmp.Close()
	defer os.Remove(tmpPath)

	if err := client.FetchFile(url, tmpPath); err != nil {
		return nil, err
	}

	data, err := os.ReadFile(tmpPath)
	if err != nil {
		return nil, err
	}

	repos, err := parseRepoJSON(data)
	if err != nil {
		return nil, err
	}

	if cache.Enabled {
		_ = saveToCache(url, kind, cache, data)
	}

	return repos, nil
}

// ---------- disk cache -------------------------------------------------------

func cacheFilePath(url string, kind entities.Kind, cache camconfig.CacheConfig) string {
	safe := strings.ReplaceAll(url, "https://", "")
	safe = strings.ReplaceAll(safe, "http://", "")
	safe = strings.ReplaceAll(safe, "/", "_")
	safe = strings.ReplaceAll(safe, ":", "_")
	return filepath.Join(cache.Directory, fmt.Sprintf("%s_%s.json", kind, safe))
}

func loadFromCache(url string, kind entities.Kind, cache camconfig.CacheConfig) (map[string]RepoEntry, error) {
	path := cacheFilePath(url, kind, cache)
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	age := time.Since(info.ModTime())
	if age > time.Duration(cache.TTLSeconds)*time.Second {
		return nil, fmt.Errorf("cache expired")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return parseRepoJSON(data)
}

func saveToCache(url string, kind entities.Kind, cache camconfig.CacheConfig, data []byte) error {
	path := cacheFilePath(url, kind, cache)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

// ---------- JSON parsing -----------------------------------------------------

func parseRepoJSON(data []byte) (map[string]RepoEntry, error) {
	var out map[string]RepoEntry
	if err := json.Unmarshal(data, &out); err != nil {
		return nil, fmt.Errorf("repoconfig: parse: %w", err)
	}
	return out, nil
}

func repoConfigKey(kind entities.Kind) string {
	if kind == entities.KindInstruction {
		return "instructions"
	}
	return string(kind) + "s" // "skills", "agents", "plugins"
}

// MigrateRepoConfigFiles migrates legacy prompt_repos.json files to the
// canonical instruction_repos.json name. If instruction_repos.json already
// exists, it is preferred and prompt_repos.json is left untouched. If only
// prompt_repos.json exists, its repository entries are copied as-is because repo
// config entries do not store an entity kind.
func MigrateRepoConfigFiles(cfgDir string) (bool, error) {
	oldPath := filepath.Join(cfgDir, "prompt_repos.json")
	newPath := filepath.Join(cfgDir, "instruction_repos.json")

	if fileExists(newPath) {
		return false, nil
	}

	data, err := os.ReadFile(oldPath)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, fmt.Errorf("repoconfig: read %s: %w", oldPath, err)
	}
	if _, err := parseRepoJSON(data); err != nil {
		return false, err
	}
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		return false, fmt.Errorf("repoconfig: mkdir %s: %w", cfgDir, err)
	}
	if err := os.WriteFile(newPath, data, 0o644); err != nil {
		return false, fmt.Errorf("repoconfig: write %s: %w", newPath, err)
	}
	return true, nil
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
