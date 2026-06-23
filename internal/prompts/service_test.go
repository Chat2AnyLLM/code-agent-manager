package prompts

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAwesomePromptsEmbedded_hasRequiredPromptFields(t *testing.T) {
	// Given
	svc := NewService()

	// When
	prompts, err := svc.FetchAwesomePrompts(context.Background())

	// Then
	if err != nil {
		t.Fatalf("FetchAwesomePrompts: %v", err)
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

func TestSyncAll_storesAwesomePrompts_whenRemoteUnavailable(t *testing.T) {
	// Given
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	svc := NewService()
	svc.sourceURL = "http://127.0.0.1:1/prompts.json"

	// When
	n, err := svc.SyncAll(ctx)

	// Then
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	if n != 3 {
		t.Fatalf("expected 3 prompts synced, got %d", n)
	}

	count, err := svc.store.CountPrompts(ctx, "awesome_prompts", "")
	if err != nil {
		t.Fatalf("CountPrompts: %v", err)
	}
	if count != 3 {
		t.Fatalf("expected 3 awesome prompts stored, got %d", count)
	}
}

func TestSyncAll_mapsRemoteAwesomePromptsFields(t *testing.T) {
	// Given
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

	// When
	n, err := svc.SyncAll(ctx)

	// Then
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
	// Given
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	svc := NewService()
	svc.sourceURL = "http://127.0.0.1:1/prompts.json"
	for _, source := range []string{"claude", "prompts_chat", "promptingguide"} {
		if err := svc.store.UpsertPrompt(ctx, &Prompt{Source: source, SourceURL: source + "://old", Title: "old", Content: "old"}); err != nil {
			t.Fatalf("UpsertPrompt(%s): %v", source, err)
		}
	}

	// When
	_, err := svc.SyncAll(ctx)

	// Then
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
