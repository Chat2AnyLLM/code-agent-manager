// Package providers contains provider data structures and helper functions
// shared by CAM's SQLite-backed provider store, launch flows, and doctor
// checks. Legacy providers.json migration lives elsewhere; production code
// should not treat JSON files as the active provider store.
package providers

import (
	"sort"
	"strings"
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

// ResolveAPIKeyEnv returns the environment-variable name that holds this
// endpoint's API key. When the endpoint sets APIKeyEnv explicitly that name is
// used; otherwise a stable name is derived from the endpoint name — e.g. the
// endpoint "omnillm" yields "OMNILLM_API_KEY". Tools that authenticate via an
// env var reference (codex's env_key) use this name.
func ResolveAPIKeyEnv(e Endpoint, endpointName string) string {
	if name := strings.TrimSpace(e.APIKeyEnv); name != "" {
		return name
	}
	return deriveAPIKeyEnvName(endpointName)
}

// deriveAPIKeyEnvName builds a valid env-var name from an endpoint name by
// upper-casing it, replacing any character that is not a letter or digit with
// an underscore, and appending "_API_KEY".
func deriveAPIKeyEnvName(endpointName string) string {
	var b strings.Builder
	for _, r := range strings.ToUpper(strings.TrimSpace(endpointName)) {
		switch {
		case r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
			b.WriteRune(r)
		default:
			b.WriteByte('_')
		}
	}
	name := b.String()
	if name == "" {
		return "API_KEY"
	}
	if name[0] >= '0' && name[0] <= '9' {
		name = "_" + name
	}
	return name + "_API_KEY"
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
