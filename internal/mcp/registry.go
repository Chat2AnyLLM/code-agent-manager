// Package mcp manages the Model Context Protocol server catalog and wires
// servers into per-tool config files.
//
// The package loads mcpm-style server schemas from configured catalog sources.
// Per-client config writers live in client.go and dispatch on tool name.
package mcp

import (
	"encoding/json"
	"sort"
	"strings"
)

// ServerSchema mirrors the mcpm-style JSON files.
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

func (a *Author) UnmarshalJSON(data []byte) error {
	var object struct {
		Name string `json:"name"`
	}
	if err := json.Unmarshal(data, &object); err == nil {
		a.Name = object.Name
		return nil
	}

	var name string
	if err := json.Unmarshal(data, &name); err != nil {
		return err
	}
	a.Name = name
	return nil
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

// Registry exposes lookups against the MCP server catalog.
type Registry struct {
	schemas map[string]ServerSchema
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
