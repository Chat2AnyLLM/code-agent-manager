// Package providers loads and queries providers.json, the file that holds the
// CAM endpoint catalog.
//
// Endpoints describe a remote LLM provider (URL, API key environment variable,
// available models, the list of clients it supports).  CAM consumes these
// records when launching tools, running doctor, and showing the --endpoints
// summary.
package providers

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// File mirrors the top-level structure of providers.json.
type File struct {
	Common    map[string]any      `json:"common"`
	Endpoints map[string]Endpoint `json:"endpoints"`
}

// Endpoint describes a single provider entry.
//
// Enabled is a pointer so a missing key is treated as the default ("true"),
// matching the Python implementation.
type Endpoint struct {
	Endpoint string `json:"endpoint"`
	// APIKey is the literal API key value stored directly with the provider.
	// It takes precedence over APIKeyEnv when set. Storing the key here lets
	// the desktop app and CLI write it into agent config files without
	// relying on an environment variable being present in the process.
	APIKey          string `json:"api_key"`
	APIKeyEnv       string `json:"api_key_env"`
	SupportedClient string `json:"supported_client"`
	// ListModelsCmd is deprecated. CAM now fetches /v1/models directly and
	// combines the fetched IDs with Models. This field remains as a fallback
	// for older provider configs.
	ListModelsCmd   string   `json:"list_models_cmd"`
	Models          []string `json:"list_of_models"`
	KeepProxyConfig bool     `json:"keep_proxy_config"`
	UseProxy        bool     `json:"use_proxy"`
	Enabled         *bool    `json:"enabled,omitempty"`
	Description     string   `json:"description"`
}

// DefaultPath returns the canonical providers.json location under CAM's config
// directory.
func DefaultPath() string {
	return filepath.Join(pathutil.ConfigDir(), "providers.json")
}

// DiscoverPath returns the first providers.json that exists across the
// canonical search locations.  It mirrors Python's discovery chain: the user's
// config directory, the current working directory, and the user's home.
func DiscoverPath() string {
	for _, candidate := range []string{
		DefaultPath(),
		filepath.Join(mustGetwd(), "providers.json"),
		filepath.Join(pathutil.Home(), "providers.json"),
	} {
		if pathutil.Exists(candidate) {
			return candidate
		}
	}
	return DefaultPath()
}

func mustGetwd() string {
	if dir, err := os.Getwd(); err == nil {
		return dir
	}
	return "."
}

// Load returns the parsed providers.json at path.  When path is empty the
// discovery chain is used.  Missing files surface os.ErrNotExist; malformed
// JSON surfaces a descriptive error.
func Load(path string) (File, error) {
	if path == "" {
		path = DiscoverPath()
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return File{}, fmt.Errorf("providers: read %s: %w", path, err)
	}
	var file File
	if err := json.Unmarshal(data, &file); err != nil {
		return File{}, fmt.Errorf("providers: parse %s: %w", path, err)
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]Endpoint{}
	}
	return file, nil
}

// SortedNames returns the endpoint names sorted for deterministic output.
func (f File) SortedNames() []string {
	names := make([]string, 0, len(f.Endpoints))
	for name := range f.Endpoints {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// IsEnabled reports whether the endpoint participates in tool launches.  A nil
// Enabled field is treated as "true" to match Python.
func (e Endpoint) IsEnabled() bool {
	if e.Enabled == nil {
		return true
	}
	return *e.Enabled
}

// Clients returns the supported_client field split into a normalized slice.
func (e Endpoint) Clients() []string {
	if e.SupportedClient == "" {
		return nil
	}
	parts := strings.Split(e.SupportedClient, ",")
	out := make([]string, 0, len(parts))
	for _, raw := range parts {
		client := strings.TrimSpace(raw)
		if client != "" {
			out = append(out, client)
		}
	}
	return out
}

// SupportsClient reports whether the endpoint advertises the given client.
func (e Endpoint) SupportsClient(client string) bool {
	target := strings.TrimSpace(client)
	for _, c := range e.Clients() {
		if c == target {
			return true
		}
	}
	return false
}

// ResolveAPIKey resolves the endpoint's API key. A literal key stored on the
// endpoint (APIKey) wins; otherwise the value is read from the environment
// variable named by APIKeyEnv via the supplied env lookup function. Returns an
// empty string when neither is set. Callers should inject os.Getenv (or a test
// stub) so this stays pure and easy to fake.
func ResolveAPIKey(e Endpoint, env func(string) string) string {
	if strings.TrimSpace(e.APIKey) != "" {
		return e.APIKey
	}
	if e.APIKeyEnv == "" || env == nil {
		return ""
	}
	return env(e.APIKeyEnv)
}

// MaskedAPIKey returns a redacted form suitable for display.
func MaskedAPIKey(key string) string {
	if key == "" {
		return ""
	}
	if len(key) <= 8 {
		return strings.Repeat("*", len(key))
	}
	return key[:4] + strings.Repeat("*", len(key)-8) + key[len(key)-4:]
}
