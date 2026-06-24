package prompts

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAwesomePromptsEmbedded_hasRequiredPromptFields(t *testing.T) {
	prompts, err := parseAwesomePrompts(awesomePromptsJSON)
	if err != nil {
		t.Fatalf("parseAwesomePrompts: %v", err)
	}
	if len(prompts) < 3 {
		t.Fatalf("expected at least 3 awesome prompts, got %d", len(prompts))
	}
	for _, p := range prompts {
		if strings.TrimSpace(p.Slug) == "" {
			t.Errorf("prompt with empty slug: %+v", p)
		}
		if strings.TrimSpace(p.Title) == "" {
			t.Errorf("prompt with empty title: %+v", p)
		}
		if strings.TrimSpace(p.Prompt) == "" {
			t.Errorf("prompt %q has empty content", p.Title)
		}
	}
}

func TestFetchAwesomePromptsLoadsConfigSources(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			w.Header().Set("Content-Type", "text/yaml")
			_, _ = w.Write([]byte(`sources:
  - name: Local Prompts
    type: local
    path: prompts/
  - name: Prompts Chat
    type: github
    url: https://github.com/f/prompts.chat
    format: csv
    file_path: prompts.csv
`))
		case "/repos/Chat2AnyLLM/awesome-prompts/git/trees/master":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"tree":[{"path":"prompts/local.yaml","type":"blob","size":80}],"truncated":false}`))
		case "/Chat2AnyLLM/awesome-prompts/master/prompts/local.yaml":
			_, _ = w.Write([]byte("slug: local\ntitle: Local Prompt\ndescription: Local description\nprompt: Use local prompt\ntags: [local]\ncategory: local-cat\nauthor: tester\n"))
		case "/f/prompts.chat/main/prompts.csv":
			_, _ = w.Write([]byte("title,prompt,description,category,tags,author\nCSV Prompt,Use csv prompt,CSV description,csv-cat,one;two,csv-author\n"))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	svc.repoRawBaseURL = server.URL
	svc.githubAPIBaseURL = server.URL + "/repos"

	got, err := svc.FetchAwesomePrompts(ctx)
	if err != nil {
		t.Fatalf("FetchAwesomePrompts: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 prompts, got %d: %#v", len(got), got)
	}
	if got[0].Title != "Local Prompt" || got[0].Prompt != "Use local prompt" {
		t.Fatalf("unexpected local prompt: %#v", got[0])
	}
	if got[1].Title != "CSV Prompt" || got[1].Prompt != "Use csv prompt" || got[1].Author != "csv-author" {
		t.Fatalf("unexpected csv prompt: %#v", got[1])
	}
}

func TestFetchAwesomePromptsDoesNotUseDistFallback(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			_, _ = w.Write([]byte("output:\n  dir: dist\n  formats: [json]\nsources: []\n"))
		case "/dist/prompts.json":
			t.Fatalf("dist/prompts.json should not be fetched")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	_, err := svc.FetchAwesomePrompts(ctx)
	if err == nil || !strings.Contains(err.Error(), "no prompts loaded") {
		t.Fatalf("expected no prompts loaded error, got %v", err)
	}
}

func TestSyncAllUsesAwesomePromptsConfigYaml(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			w.Header().Set("Content-Type", "text/yaml")
			_, _ = w.Write([]byte(`sources:
  - name: Local Prompts
    type: local
    path: prompts/
`))
		case "/repos/Chat2AnyLLM/awesome-prompts/git/trees/master":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"tree":[{"path":"prompts/configured.yaml","type":"blob","size":100}],"truncated":false}`))
		case "/Chat2AnyLLM/awesome-prompts/master/prompts/configured.yaml":
			_, _ = w.Write([]byte("slug: configured\ntitle: Configured Prompt\ndescription: Configured description\nprompt: Use configured source\ntags: [configured]\ncategory: repo-config\nauthor: tester\n"))
		case "/dist/prompts.json":
			t.Fatalf("dist/prompts.json should not be fetched")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	svc.repoRawBaseURL = server.URL
	svc.githubAPIBaseURL = server.URL + "/repos"

	n, err := svc.SyncAll(ctx)
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 prompt synced, got %d", n)
	}
	stored, err := svc.store.ListPrompts(ctx, "awesome_prompts", "")
	if err != nil {
		t.Fatalf("ListPrompts: %v", err)
	}
	if len(stored) != 1 || stored[0].Title != "Configured Prompt" {
		t.Fatalf("expected configured prompt, got %+v", stored)
	}
}

func TestSyncAllUsesExplicitAwesomePromptsURLOverride(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/default/prompts.json" {
			t.Fatalf("unexpected path %q", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"version":"1.0.0","prompts":[{"slug":"configured","title":"Configured Prompt","description":"Configured description","prompt":"Use configured source","tags":["configured"],"category":"repo-config","author":"tester","variables":[]}]}`))
	}))
	defer server.Close()
	svc := NewService()
	svc.sourceURL = server.URL + "/default/prompts.json"
	svc.preferSourceURLDirect = true

	n, err := svc.SyncAll(ctx)
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 prompt synced, got %d", n)
	}
	stored, err := svc.store.ListPrompts(ctx, "awesome_prompts", "")
	if err != nil {
		t.Fatalf("ListPrompts: %v", err)
	}
	if len(stored) != 1 || stored[0].Title != "Configured Prompt" {
		t.Fatalf("expected configured prompt, got %+v", stored)
	}
}

func TestSyncAllReturnsErrorWhenConfigUnavailable(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	svc := NewService()
	svc.configURL = "http://127.0.0.1:1/config.yaml"

	_, err := svc.SyncAll(ctx)
	if err == nil {
		t.Fatal("expected config fetch error")
	}
}

func TestSyncAll_mapsRemoteAwesomePromptsFields(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"version":"1.0.0","prompts":[{"slug":"custom","title":"Custom Prompt","description":"Custom description","prompt":"Do custom work","tags":["one","two"],"category":"custom-category","author":"tester","variables":[]}]}`))
	}))
	defer server.Close()
	svc := NewService()
	svc.sourceURL = server.URL
	svc.preferSourceURLDirect = true

	n, err := svc.SyncAll(ctx)
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 prompt synced, got %d", n)
	}
	stored, err := svc.store.ListPrompts(ctx, "awesome_prompts", "")
	if err != nil {
		t.Fatalf("ListPrompts: %v", err)
	}
	if len(stored) != 1 {
		t.Fatalf("expected 1 stored prompt, got %d", len(stored))
	}
	p := stored[0]
	if p.SourceURL != "https://github.com/Chat2AnyLLM/awesome-prompts/blob/master/prompts/custom.yaml" {
		t.Fatalf("SourceURL = %q", p.SourceURL)
	}
	if p.Title != "Custom Prompt" || p.Description != "Custom description" || p.Content != "Do custom work" || p.Tags != "one, two" || p.Category != "custom-category" || p.Author != "tester" {
		t.Fatalf("unexpected prompt mapping: %+v", p)
	}
}

func TestSyncAll_removesRetiredPromptSources(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"version":"1.0.0","prompts":[{"slug":"current","title":"Current Prompt","prompt":"Use current prompt"}]}`))
	}))
	defer server.Close()
	svc := NewService()
	svc.sourceURL = server.URL
	svc.preferSourceURLDirect = true
	for _, source := range []string{"claude", "prompts_chat", "promptingguide"} {
		if err := svc.store.UpsertPrompt(ctx, &Prompt{Source: source, SourceURL: source + "://old", Title: "old", Content: "old"}); err != nil {
			t.Fatalf("UpsertPrompt(%s): %v", source, err)
		}
	}

	_, err := svc.SyncAll(ctx)
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	for _, source := range []string{"claude", "prompts_chat", "promptingguide"} {
		count, err := svc.store.CountPrompts(ctx, source, "")
		if err != nil {
			t.Fatalf("CountPrompts(%s): %v", source, err)
		}
		if count != 0 {
			t.Fatalf("expected retired source %s removed, got %d", source, count)
		}
	}
}
