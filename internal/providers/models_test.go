package providers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestResolveModels_CombinesAPIDiscoveryWithStaticList(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/models" {
			t.Fatalf("path = %q, want /v1/models", r.URL.Path)
		}
		for _, key := range []string{
			"return_wildcard_routes",
			"include_model_access_groups",
			"only_model_access_groups",
			"include_metadata",
		} {
			if got := r.URL.Query().Get(key); got != "false" {
				t.Fatalf("query %s = %q, want false", key, got)
			}
		}
		if got := r.Header.Get("Authorization"); got != "Bearer secret-123" {
			t.Fatalf("Authorization = %q, want bearer token", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"api-a"},{"id":"static-b"},{"id":"api-c"}]}`))
	}))
	defer server.Close()

	t.Setenv("CAM_TEST_KEY", "secret-123")
	ep := Endpoint{
		Endpoint:  server.URL,
		APIKeyEnv: "CAM_TEST_KEY",
		Models:    []string{"static-b", "static-d"},
	}

	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"api-a", "static-b", "api-c", "static-d"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
}

func TestResolveModels_FetchesModelsEndpointBeforeDeprecatedCommand(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/models" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"root-model"}]}`))
	}))
	defer server.Close()

	got, err := ResolveModels(
		Endpoint{
			Endpoint:      server.URL,
			ListModelsCmd: "echo deprecated-command-should-not-run >&2; exit 5",
		},
		"ep",
		time.Hour,
		t.TempDir(),
		os.Getenv,
	)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !equalSlices(got, []string{"root-model"}) {
		t.Fatalf("models = %v, want [root-model]", got)
	}
}

func TestResolveModels_IgnoresDeprecatedListModelsCmdFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
	}))
	defer server.Close()

	got, err := ResolveModels(
		Endpoint{
			Endpoint:      server.URL,
			ListModelsCmd: "echo jq error >&2; exit 5",
		},
		"ep",
		time.Hour,
		t.TempDir(),
		os.Getenv,
	)
	if err != nil {
		t.Fatalf("deprecated list_models_cmd failure should not surface: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("models = %v, want empty list", got)
	}
}

func TestResolveModels_CacheDoesNotRetainRemovedStaticModels(t *testing.T) {
	cacheDir := t.TempDir()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"api-a"}]}`))
	}))
	defer server.Close()

	ep := Endpoint{
		Endpoint: server.URL,
		Models:   []string{"static-old"},
	}
	if _, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv); err != nil {
		t.Fatalf("first resolve: %v", err)
	}

	ep.Models = []string{"static-new"}
	got, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv)
	if err != nil {
		t.Fatalf("second resolve: %v", err)
	}
	want := []string{"api-a", "static-new"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
}

func TestResolveModels_IgnoresAPICacheWriteFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"api-a"}]}`))
	}))
	defer server.Close()

	cacheDir := filepath.Join(t.TempDir(), "cache-as-file")
	if err := os.WriteFile(cacheDir, []byte("not a directory"), 0o600); err != nil {
		t.Fatal(err)
	}

	got, err := ResolveModels(
		Endpoint{Endpoint: server.URL},
		"ep",
		time.Hour,
		cacheDir,
		os.Getenv,
	)
	if err != nil {
		t.Fatalf("cache write failure should not fail model discovery: %v", err)
	}
	if !equalSlices(got, []string{"api-a"}) {
		t.Fatalf("models = %v, want [api-a]", got)
	}
}

func TestResolveModels_IgnoresCommandCacheWriteFailure(t *testing.T) {
	cacheDir := filepath.Join(t.TempDir(), "cache-as-file")
	if err := os.WriteFile(cacheDir, []byte("not a directory"), 0o600); err != nil {
		t.Fatal(err)
	}

	got, err := ResolveModels(
		Endpoint{ListModelsCmd: "printf 'cmd-a\\n'"},
		"ep",
		time.Hour,
		cacheDir,
		os.Getenv,
	)
	if err != nil {
		t.Fatalf("cache write failure should not fail command discovery: %v", err)
	}
	if !equalSlices(got, []string{"cmd-a"}) {
		t.Fatalf("models = %v, want [cmd-a]", got)
	}
}

func TestResolveModels_FallsBackToStaticListWhenAPIDiscoveryFails(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, "boom", http.StatusBadGateway)
	}))
	defer server.Close()

	ep := Endpoint{
		Endpoint: server.URL,
		Models:   []string{"static-a", "static-b"},
	}

	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"static-a", "static-b"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
}

func TestResolveModels_FallsBackToDeprecatedListModelsCmd(t *testing.T) {
	ep := Endpoint{
		Endpoint:      "http://127.0.0.1:1",
		ListModelsCmd: "printf 'cmd-a\\ncmd-b\\n'",
	}

	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"cmd-a", "cmd-b"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
}
func TestResolveModels_StaticList(t *testing.T) {
	ep := Endpoint{Models: []string{"m1", "m2"}, ListModelsCmd: "echo never"}
	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 2 || got[0] != "m1" || got[1] != "m2" {
		t.Fatalf("expected static list, got %v", got)
	}
}

func TestResolveModels_StaticListIsCopy(t *testing.T) {
	ep := Endpoint{Models: []string{"m1", "m2"}}
	got, _ := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	got[0] = "mutated"
	if ep.Models[0] != "m1" {
		t.Fatalf("ResolveModels returned a shared slice; backing array mutated")
	}
}

func TestResolveModels_NeitherStaticNorCmd(t *testing.T) {
	got, err := ResolveModels(Endpoint{}, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("expected empty, got %v", got)
	}
}

func TestResolveModels_DynamicCacheMiss(t *testing.T) {
	cacheDir := t.TempDir()
	ep := Endpoint{ListModelsCmd: "printf 'alpha\\nbeta\\n'"}
	got, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"alpha", "beta"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
	// Cache file written.
	raw, err := os.ReadFile(filepath.Join(cacheDir, "ep.json"))
	if err != nil {
		t.Fatalf("cache not written: %v", err)
	}
	var entry cacheEntry
	if err := json.Unmarshal(raw, &entry); err != nil {
		t.Fatalf("cache parse: %v", err)
	}
	if !equalSlices(entry.Models, want) {
		t.Fatalf("cached models = %v, want %v", entry.Models, want)
	}
	if entry.FetchedAt.IsZero() {
		t.Fatalf("cached FetchedAt is zero")
	}
}

func TestResolveModels_DynamicCacheHit(t *testing.T) {
	cacheDir := t.TempDir()
	cachePath := filepath.Join(cacheDir, "ep.json")
	entry := cacheEntry{Models: []string{"cached-m"}, FetchedAt: time.Now()}
	payload, _ := json.Marshal(entry)
	if err := os.WriteFile(cachePath, payload, 0o600); err != nil {
		t.Fatal(err)
	}
	// Command would fail if run; cache hit must short-circuit.
	ep := Endpoint{ListModelsCmd: "exit 7"}
	got, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv)
	if err != nil {
		t.Fatalf("cache hit should not invoke cmd: %v", err)
	}
	if len(got) != 1 || got[0] != "cached-m" {
		t.Fatalf("expected cached models, got %v", got)
	}
}

func TestResolveModels_DynamicStale(t *testing.T) {
	cacheDir := t.TempDir()
	cachePath := filepath.Join(cacheDir, "ep.json")
	stale := cacheEntry{Models: []string{"old"}, FetchedAt: time.Now().Add(-2 * time.Hour)}
	payload, _ := json.Marshal(stale)
	_ = os.WriteFile(cachePath, payload, 0o600)

	ep := Endpoint{ListModelsCmd: "echo fresh"}
	got, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0] != "fresh" {
		t.Fatalf("expected fresh exec, got %v", got)
	}
}

func TestResolveModels_DeprecatedCommandNonZeroExitReturnsEmpty(t *testing.T) {
	cacheDir := t.TempDir()
	ep := Endpoint{ListModelsCmd: "exit 3"}
	got, err := ResolveModels(ep, "ep", time.Hour, cacheDir, os.Getenv)
	if err != nil {
		t.Fatalf("deprecated command failure should not surface: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("models = %v, want empty list", got)
	}
	if _, statErr := os.Stat(filepath.Join(cacheDir, "ep.json")); statErr == nil {
		t.Fatalf("cache should not be written on failure")
	}
}

func TestResolveModels_DeprecatedCommandEmptyStdoutReturnsEmpty(t *testing.T) {
	ep := Endpoint{ListModelsCmd: "true"} // no output, exit 0
	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatalf("deprecated command empty output should not surface: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("models = %v, want empty list", got)
	}
}

func TestResolveModels_StripsProxiesByDefault(t *testing.T) {
	t.Setenv("http_proxy", "should-be-stripped")
	t.Setenv("HTTPS_PROXY", "should-be-stripped")
	ep := Endpoint{ListModelsCmd: `printf '%s\n%s\n' "${http_proxy:-EMPTY}" "${HTTPS_PROXY:-EMPTY}"`}
	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatal(err)
	}
	for _, line := range got {
		if line != "EMPTY" {
			t.Fatalf("proxy leaked into discovery env: %v", got)
		}
	}
}

func TestResolveModels_KeepsProxiesWhenRequested(t *testing.T) {
	t.Setenv("http_proxy", "kept-value")
	ep := Endpoint{
		ListModelsCmd:   `printf '%s\n' "${http_proxy:-EMPTY}"`,
		KeepProxyConfig: true,
	}
	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0] != "kept-value" {
		t.Fatalf("expected proxy to pass through, got %v", got)
	}
}

func TestResolveModels_ExposesEndpointAndApiKey(t *testing.T) {
	t.Setenv("CAM_TEST_KEY", "secret-123")
	ep := Endpoint{
		Endpoint:      "https://x.example",
		APIKeyEnv:     "CAM_TEST_KEY",
		ListModelsCmd: `printf '%s\n%s\n' "$endpoint" "$api_key"`,
	}
	got, err := ResolveModels(ep, "ep", time.Hour, t.TempDir(), os.Getenv)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"https://x.example", "secret-123"}
	if !equalSlices(got, want) {
		t.Fatalf("models = %v, want %v", got, want)
	}
}

func equalSlices(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
