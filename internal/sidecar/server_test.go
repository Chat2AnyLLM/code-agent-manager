package sidecar

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/desktop"
)

func TestSidecarRequiresToken(t *testing.T) {
	server := New(Options{Version: "test", Token: "secret"})
	server.services = desktop.NewServices("test", t.TempDir()+"/cam.db")
	req := httptest.NewRequest(http.MethodGet, "/api/app/version", nil)
	rec := httptest.NewRecorder()

	server.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
}

func TestSidecarVersion(t *testing.T) {
	server := New(Options{Version: "test-version", Token: "secret"})
	server.services = desktop.NewServices("test-version", t.TempDir()+"/cam.db")
	req := httptest.NewRequest(http.MethodGet, "/api/app/version", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec := httptest.NewRecorder()

	server.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", rec.Code, rec.Body.String())
	}
	payload := map[string]string{}
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("json: %v", err)
	}
	if payload["version"] != "test-version" {
		t.Fatalf("version = %q", payload["version"])
	}
}

func TestSidecarProviderLifecycle(t *testing.T) {
	server := New(Options{Version: "test", Token: "secret"})
	server.services = desktop.NewServices("test", t.TempDir()+"/cam.db")
	handler := server.Handler()

	body := bytes.NewBufferString(`{"name":"local","endpoint":"http://localhost:4000/v1","supportedClient":"claude","models":["m1"],"enabled":true}`)
	req := httptest.NewRequest(http.MethodPost, "/api/providers", body)
	req.Header.Set("Authorization", "Bearer secret")
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("add status=%d body=%s", rec.Code, rec.Body.String())
	}

	req = httptest.NewRequest(http.MethodGet, "/api/providers", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec = httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status=%d body=%s", rec.Code, rec.Body.String())
	}
	var listed []map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &listed); err != nil {
		t.Fatalf("list json: %v", err)
	}
	if len(listed) != 1 || listed[0]["name"] != "local" {
		t.Fatalf("listed = %+v", listed)
	}

	req = httptest.NewRequest(http.MethodPost, "/api/providers/local/disable", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec = httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("disable status=%d body=%s", rec.Code, rec.Body.String())
	}

	req = httptest.NewRequest(http.MethodDelete, "/api/providers/local", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec = httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("delete status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestSidecarUsesDefaultStorePath(t *testing.T) {
	server := New(Options{Version: "test", Token: "secret"})
	req := httptest.NewRequest(http.MethodGet, "/api/providers", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec := httptest.NewRecorder()

	server.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", rec.Code, rec.Body.String())
	}
}

func TestSidecarMCPRegistry(t *testing.T) {
	server := New(Options{Version: "test", Token: "secret"})
	handler := server.Handler()

	// Listing the registry returns the discovered servers as JSON.
	req := httptest.NewRequest(http.MethodGet, "/api/mcp/registry", nil)
	req.Header.Set("Authorization", "Bearer secret")
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("registry status=%d body=%s", rec.Code, rec.Body.String())
	}
	var items []map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &items); err != nil {
		t.Fatalf("registry json: %v", err)
	}
	if len(items) == 0 {
		t.Fatal("expected discovered registry servers")
	}

	// Installing into no clients is rejected with a 400.
	req = httptest.NewRequest(http.MethodPost, "/api/mcp/install", bytes.NewBufferString(`{"server":"github"}`))
	req.Header.Set("Authorization", "Bearer secret")
	rec = httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("install status=%d body=%s, want 400", rec.Code, rec.Body.String())
	}
}
