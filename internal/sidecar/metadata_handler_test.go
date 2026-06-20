package sidecar

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/metadata"
)

// seedMetadata populates the metadata index directly so search/pagination tests
// do not depend on live GitHub downloads.
func seedMetadata(t *testing.T, dbPath string, n int) {
	t.Helper()
	ctx := context.Background()
	store := metadata.NewStore(dbPath)
	if err := store.Init(ctx); err != nil {
		t.Fatalf("init store: %v", err)
	}
	for i := range n {
		kind := "skill"
		itemPath := "skills/seed/SKILL.md"
		if i%2 == 0 {
			kind = "agent"
			itemPath = "agents/seed.md"
		}
		if err := store.UpsertItem(ctx, metadata.Item{
			Kind:        kind,
			Name:        kindName(kind, i),
			Description: "seeded item",
			RepoOwner:   "seed",
			RepoName:    "repo",
			RepoBranch:  "main",
			ItemPath:    itemPath,
			InstallKey:  kind + "-seed-" + itoa(i),
			TargetApps:  "claude,codex",
		}); err != nil {
			t.Fatalf("seed upsert: %v", err)
		}
	}
}

func kindName(kind string, i int) string { return kind + "-seed-" + itoa(i) }

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var b []byte
	for i > 0 {
		b = append([]byte{byte('0' + i%10)}, b...)
		i /= 10
	}
	return string(b)
}

func TestMetadataRefreshEndpointWiring(t *testing.T) {
	if testing.Short() || os.Getenv("CAM_RUN_LIVE_TESTS") != "1" {
		t.Skip("refresh performs live network downloads; set CAM_RUN_LIVE_TESTS=1 to run")
	}
	dir := t.TempDir()
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	// The refresh endpoint performs live network fetches; here we only assert the
	// route is wired and returns a well-formed RefreshSummary (200). Network
	// failures still yield 200 with FailedSources populated, so this is stable.
	req := httptest.NewRequest(http.MethodPost, "/api/metadata/refresh", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("refresh: status %d, body %s", w.Code, w.Body.String())
	}
	var summary metadata.RefreshSummary
	if err := json.NewDecoder(w.Body).Decode(&summary); err != nil {
		t.Fatalf("decode: %v", err)
	}
}

func TestMetadataSearchEndpoint(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	seedMetadata(t, dbPath, 3)

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/search?q=seed", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("search: status %d, body %s", w.Code, w.Body.String())
	}

	var resp metadata.SearchResponse
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Items) == 0 {
		t.Fatal("expected at least one search result")
	}
	if resp.Total == 0 {
		t.Fatal("expected total > 0")
	}
}

func TestMetadataSearchPagination(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	seedMetadata(t, dbPath, 12)

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/search?q=seed&limit=5&offset=0", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("search: status %d, body %s", w.Code, w.Body.String())
	}
	var resp metadata.SearchResponse
	json.NewDecoder(w.Body).Decode(&resp)
	if len(resp.Items) != 5 {
		t.Fatalf("page1 expected 5 items, got %d", len(resp.Items))
	}
	if resp.Total != 12 {
		t.Fatalf("expected total 12, got %d", resp.Total)
	}
}

func TestMetadataSearchWithTypeFilter(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	seedMetadata(t, dbPath, 6)

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/search?q=seed&type=agent", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("search: status %d, body %s", w.Code, w.Body.String())
	}

	var resp metadata.SearchResponse
	json.NewDecoder(w.Body).Decode(&resp)
	if len(resp.Items) == 0 {
		t.Fatal("expected agent results")
	}
	for _, r := range resp.Items {
		if r.Kind != "agent" {
			t.Fatalf("expected kind=agent, got %s", r.Kind)
		}
	}
}

func TestMetadataTargetsEndpoint(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/targets?kind=skill", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("targets: status %d, body %s", w.Code, w.Body.String())
	}

	var targets []string
	if err := json.NewDecoder(w.Body).Decode(&targets); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(targets) == 0 {
		t.Fatal("expected at least one target agent for skills")
	}
	hasClaude := false
	for _, tg := range targets {
		if tg == "claude" {
			hasClaude = true
		}
	}
	if !hasClaude {
		t.Fatalf("expected claude in skill targets, got %v", targets)
	}
}

func TestMetadataTargetsDefaultsToInstruction(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/targets", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("targets: status %d, body %s", w.Code, w.Body.String())
	}
	var targets []string
	if err := json.NewDecoder(w.Body).Decode(&targets); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(targets) == 0 {
		t.Fatal("expected instruction targets")
	}
}

func TestMetadataSearchRejectsPromptType(t *testing.T) {
	srv := New(Options{Version: "test"})
	req := httptest.NewRequest(http.MethodGet, "/api/metadata/search?type=prompt", nil)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest || !strings.Contains(w.Body.String(), "instruction") {
		t.Fatalf("expected prompt rename error, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataTargetsRejectsPromptKind(t *testing.T) {
	srv := New(Options{Version: "test"})
	req := httptest.NewRequest(http.MethodGet, "/api/metadata/targets?kind=prompt", nil)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest || !strings.Contains(w.Body.String(), "instruction") {
		t.Fatalf("expected prompt rename error, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataDetailRejectsPromptKind(t *testing.T) {
	srv := New(Options{Version: "test"})
	req := httptest.NewRequest(http.MethodGet, "/api/metadata/detail?kind=prompt&install_key=o/r:name", nil)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest || !strings.Contains(w.Body.String(), "instruction") {
		t.Fatalf("expected prompt rename error, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataInstallRejectsPromptKind(t *testing.T) {
	srv := New(Options{Version: "test"})
	body := strings.NewReader(`{"kind":"prompt","install_key":"o/r:name","target_apps":["claude"]}`)
	req := httptest.NewRequest(http.MethodPost, "/api/metadata/install", body)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest || !strings.Contains(w.Body.String(), "instruction") {
		t.Fatalf("expected prompt rename error, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataInstallInstructionRejectsMissingProjectDir(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))

	srv := New(Options{Version: "test"})
	body := strings.NewReader(`{"kind":"instruction","install_key":"o/r:name","target_apps":["claude"],"level":"project"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/metadata/install", body)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest || !strings.Contains(w.Body.String(), "project_dir") {
		t.Fatalf("expected 400 with project_dir error, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataInstallNonInstructionIgnoresLevel(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))
	ctx := context.Background()
	store := metadata.NewStore(filepath.Join(dir, "cam.db"))
	if err := store.Init(ctx); err != nil {
		t.Fatal(err)
	}
	if err := store.UpsertItem(ctx, metadata.Item{Kind: "skill", Name: "test-skill", InstallKey: "o/r:test-skill", RepoOwner: "o", RepoName: "r", ItemPath: "skills/test-skill/SKILL.md", TargetApps: "claude"}); err != nil {
		t.Fatal(err)
	}

	srv := New(Options{Version: "test"})
	body := strings.NewReader(`{"kind":"skill","install_key":"o/r:test-skill","target_apps":["claude"],"level":"project"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/metadata/install", body)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusOK && strings.Contains(w.Body.String(), "project_dir") {
		t.Fatalf("level/project_dir should be ignored for non-instruction kinds, got status %d body %s", w.Code, w.Body.String())
	}
}

func TestMetadataInstallAcceptsUserLevelByDefault(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))
	ctx := context.Background()
	store := metadata.NewStore(filepath.Join(dir, "cam.db"))
	if err := store.Init(ctx); err != nil {
		t.Fatal(err)
	}
	if err := store.UpsertItem(ctx, metadata.Item{Kind: "instruction", Name: "test-instruction", InstallKey: "o/r:test-instruction", RepoOwner: "o", RepoName: "r", ItemPath: "instructions/test-instruction.md", TargetApps: "claude"}); err != nil {
		t.Fatal(err)
	}

	srv := New(Options{Version: "test"})
	body := strings.NewReader(`{"kind":"instruction","install_key":"o/r:test-instruction","target_apps":["claude"]}`)
	req := httptest.NewRequest(http.MethodPost, "/api/metadata/install", body)
	w := httptest.NewRecorder()
	srv.Handler().ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 with default user-level, got status %d body %s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "user") {
		t.Fatalf("expected level=user in response, got %s", w.Body.String())
	}
}

// TestMetadataDetailEndpoint verifies the detail route returns the indexed item
// for a seeded install key. The manifest fetch hits the network and is allowed
// to fail (Content empty); we assert only on the indexed metadata and status so
// the test stays deterministic offline.
func TestMetadataDetailEndpoint(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))
	seedMetadata(t, dbPath, 2)

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/detail?kind=agent&install_key=agent-seed-0", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("detail: status %d, body %s", w.Code, w.Body.String())
	}
	var detail metadata.ItemDetail
	if err := json.NewDecoder(w.Body).Decode(&detail); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if detail.Item.InstallKey != "agent-seed-0" {
		t.Fatalf("expected install_key agent-seed-0, got %q", detail.Item.InstallKey)
	}
	if detail.Item.Kind != "agent" {
		t.Fatalf("expected kind agent, got %q", detail.Item.Kind)
	}
}

// TestMetadataDetailEndpointRequiresParams verifies the detail route rejects
// requests missing the kind or install_key query parameters.
func TestMetadataDetailEndpointRequiresParams(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_DB_PATH", filepath.Join(dir, "cam.db"))

	srv := New(Options{Version: "test"})
	handler := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "/api/metadata/detail?kind=agent", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing install_key, got %d", w.Code)
	}
}
