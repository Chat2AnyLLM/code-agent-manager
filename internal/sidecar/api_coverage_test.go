package sidecar

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/desktop"
)

func newAPITestHandler(t *testing.T) http.Handler {
	t.Helper()
	dir := t.TempDir()
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	t.Setenv("CAM_CONFIG_DIR", dir)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))
	dbPath := filepath.Join(dir, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	server := New(Options{Version: "test"})
	server.services = desktop.NewServices("test", dbPath)
	return server.Handler()
}

func apiRequest(t *testing.T, handler http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func requireStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status=%d want=%d body=%s", rec.Code, want, rec.Body.String())
	}
}

func TestSidecarProviderModelsEndpointDiscoversModels(t *testing.T) {
	modelsAPI := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/models" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"api-model-a"},{"id":"api-model-b"}]}`))
	}))
	defer modelsAPI.Close()

	handler := newAPITestHandler(t)
	rec := apiRequest(t, handler, http.MethodPost, "/api/providers", `{"name":"local","endpoint":"`+modelsAPI.URL+`","models":["configured-model"],"enabled":true}`)
	requireStatus(t, rec, http.StatusOK)

	rec = apiRequest(t, handler, http.MethodGet, "/api/providers/local/models", "")
	requireStatus(t, rec, http.StatusOK)
	var models []string
	if err := json.Unmarshal(rec.Body.Bytes(), &models); err != nil {
		t.Fatalf("decode models: %v", err)
	}
	for _, want := range []string{"api-model-a", "api-model-b", "configured-model"} {
		if !containsModel(models, want) {
			t.Fatalf("models=%v missing %q", models, want)
		}
	}

	rec = apiRequest(t, handler, http.MethodPost, "/api/providers/local/models", "")
	requireStatus(t, rec, http.StatusMethodNotAllowed)
}

func TestSidecarCoreAPIRoutes(t *testing.T) {
	handler := newAPITestHandler(t)

	routes := []struct {
		name   string
		method string
		path   string
		body   string
		status int
	}{
		{"version", http.MethodGet, "/api/app/version", "", http.StatusOK},
		{"provider create", http.MethodPost, "/api/providers", `{"name":"local","endpoint":"http://127.0.0.1:1","models":["m1"],"clients":["claude"],"enabled":true}`, http.StatusOK},
		{"provider list", http.MethodGet, "/api/providers", "", http.StatusOK},
		{"provider show", http.MethodGet, "/api/providers/local", "", http.StatusOK},
		{"provider patch", http.MethodPatch, "/api/providers/local", `{"models":["m2"]}`, http.StatusOK},
		{"provider disable", http.MethodPost, "/api/providers/local/disable", "", http.StatusOK},
		{"provider enable", http.MethodPost, "/api/providers/local/enable", "", http.StatusOK},
		{"tools list", http.MethodGet, "/api/tools", "", http.StatusOK},
		{"tool install dry-run", http.MethodPost, "/api/tools/codex/install", `{"dryRun":true}`, http.StatusOK},
		{"tool upgrade dry-run", http.MethodPost, "/api/tools/codex/upgrade", `{"dryRun":true}`, http.StatusOK},
		{"mcp clients", http.MethodGet, "/api/mcp/clients", "", http.StatusOK},
		{"mcp registry", http.MethodGet, "/api/mcp/registry", "", http.StatusOK},
		{"mcp install validation", http.MethodPost, "/api/mcp/install", `{"server":"github"}`, http.StatusBadRequest},
		{"mcp uninstall validation", http.MethodPost, "/api/mcp/uninstall", `{"server":"github"}`, http.StatusBadRequest},
		{"entities list", http.MethodGet, "/api/entities?kind=skill", "", http.StatusOK},
		{"entities uninstall validation", http.MethodPost, "/api/entities/uninstall", `{}`, http.StatusBadRequest},
		{"config files", http.MethodGet, "/api/config/files", "", http.StatusOK},
		{"doctor checks", http.MethodGet, "/api/doctor/checks", "", http.StatusOK},
		{"launch dry-run", http.MethodPost, "/api/launch/dry-run", `{"tool":"claude","provider":"local","model":"m2"}`, http.StatusOK},
		{"launch apply", http.MethodPost, "/api/launch/apply", `{"tool":"claude","provider":"local","model":"m2"}`, http.StatusOK},
		{"prompts create", http.MethodPost, "/api/prompts", `{"source":"test","source_url":"test://1","category":"coding","title":"Prompt","content":"Do it"}`, http.StatusCreated},
		{"prompts list", http.MethodGet, "/api/prompts", "", http.StatusOK},
		{"prompts search", http.MethodGet, "/api/prompts/search?q=Prompt", "", http.StatusOK},
		{"prompts sources", http.MethodGet, "/api/prompts/sources", "", http.StatusOK},
		{"prompts sync claude", http.MethodPost, "/api/prompts/sync", `{"source":"claude"}`, http.StatusOK},
		{"provider delete", http.MethodDelete, "/api/providers/local", "", http.StatusOK},
	}

	for _, route := range routes {
		t.Run(route.name, func(t *testing.T) {
			rec := apiRequest(t, handler, route.method, route.path, route.body)
			requireStatus(t, rec, route.status)
			if route.status < 400 && strings.TrimSpace(rec.Body.String()) == "" {
				t.Fatalf("expected response body for %s %s", route.method, route.path)
			}
		})
	}
}

func containsModel(models []string, want string) bool {
	for _, model := range models {
		if model == want {
			return true
		}
	}
	return false
}
