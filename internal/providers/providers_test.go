package providers_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func writeProviders(t *testing.T, payload any) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestLegacyTestHelperLoadsHappyPath(t *testing.T) {
	path := writeProviders(t, map[string]any{
		"common": map[string]any{"http_proxy": ""},
		"endpoints": map[string]any{
			"alpha": map[string]any{
				"endpoint":         "https://alpha.example.com",
				"api_key_env":      "ALPHA_KEY",
				"supported_client": "claude,codex",
				"list_of_models":   []string{"m1", "m2"},
			},
			"beta": map[string]any{
				"endpoint":         "https://beta.example.com",
				"supported_client": "gemini",
				"enabled":          false,
			},
		},
	})

	got, err := loadLegacyFileForTest(path)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	if want := []string{"alpha", "beta"}; !reflect.DeepEqual(got.SortedNames(), want) {
		t.Fatalf("SortedNames = %v, want %v", got.SortedNames(), want)
	}
	alpha := got.Endpoints["alpha"]
	if alpha.Endpoint != "https://alpha.example.com" {
		t.Fatalf("alpha.Endpoint = %q", alpha.Endpoint)
	}
	if !alpha.IsEnabled() {
		t.Fatal("alpha should default to enabled")
	}
	beta := got.Endpoints["beta"]
	if beta.IsEnabled() {
		t.Fatal("beta should be disabled when enabled: false")
	}
}

func TestLegacyTestHelperMissingFile(t *testing.T) {
	if _, err := loadLegacyFileForTest(filepath.Join(t.TempDir(), "missing.json")); err == nil {
		t.Fatal("expected error on missing file")
	}
}

func TestLegacyTestHelperMalformedJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")
	if err := os.WriteFile(path, []byte("not-json"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := loadLegacyFileForTest(path); err == nil {
		t.Fatal("expected error on malformed JSON")
	}
}

func TestClientsSplittingAndTrimming(t *testing.T) {
	tests := []struct {
		raw  string
		want []string
	}{
		{raw: "", want: nil},
		{raw: "claude", want: []string{"claude"}},
		{raw: "claude,codex", want: []string{"claude", "codex"}},
		{raw: " claude , codex ", want: []string{"claude", "codex"}},
		{raw: "claude,,codex", want: []string{"claude", "codex"}},
	}
	for _, tc := range tests {
		tc := tc
		t.Run(tc.raw, func(t *testing.T) {
			t.Parallel()
			ep := providers.Endpoint{SupportedClient: tc.raw}
			got := ep.Clients()
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("Clients() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestSupportsClient(t *testing.T) {
	ep := providers.Endpoint{SupportedClient: "claude,codex"}
	if !ep.SupportsClient("codex") {
		t.Fatal("SupportsClient(codex) = false, want true")
	}
	if ep.SupportsClient("gemini") {
		t.Fatal("SupportsClient(gemini) = true, want false")
	}
}

func TestResolveAPIKey(t *testing.T) {
	ep := providers.Endpoint{APIKeyEnv: "FOO"}
	env := map[string]string{"FOO": "secret"}
	got := providers.ResolveAPIKey(ep, func(k string) string { return env[k] })
	if got != "secret" {
		t.Fatalf("ResolveAPIKey = %q, want secret", got)
	}

	empty := providers.ResolveAPIKey(providers.Endpoint{}, func(string) string { return "x" })
	if empty != "" {
		t.Fatalf("ResolveAPIKey on empty APIKeyEnv = %q, want \"\"", empty)
	}
}

func TestMaskedAPIKey(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"", ""},
		{"short", "*****"},
		{"abcdefgh", "********"},
		{"abcdefghij", "abcd**ghij"},
		{"sk-1234567890abcdef", "sk-1***********cdef"},
	}
	for _, tc := range tests {
		tc := tc
		t.Run(tc.in, func(t *testing.T) {
			t.Parallel()
			if got := providers.MaskedAPIKey(tc.in); got != tc.want {
				t.Fatalf("MaskedAPIKey(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func loadLegacyFileForTest(path string) (providers.File, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return providers.File{}, err
	}
	var file providers.File
	if err := json.Unmarshal(data, &file); err != nil {
		return providers.File{}, err
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]providers.Endpoint{}
	}
	return file, nil
}
