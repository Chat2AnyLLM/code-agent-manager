package metadata

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func TestSearchPagedFallsBackToOnlineSkillSearchAndPersists(t *testing.T) {
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/search/code":
			query := r.URL.Query().Get("q")
			if !strings.Contains(query, "filename:SKILL.md") {
				t.Fatalf("unexpected GitHub search query: %s", query)
			}
			_ = json.NewEncoder(w).Encode(map[string]any{
				"items": []map[string]any{
					{
						"name": "SKILL.md",
						"path": "skills/online-research/SKILL.md",
						"repository": map[string]any{
							"full_name":        "octo/skillbox",
							"stargazers_count": 25,
						},
					},
				},
			})
		case r.URL.Path == "/octo/skillbox/main/skills/online-research/SKILL.md":
			_, _ = w.Write([]byte("---\nname: online-research\ndescription: Online research from GitHub\n---\n"))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	oldGitHubBaseURL := githubBaseURL
	oldGitHubRawBaseURL := githubRawBaseURL
	githubBaseURL = server.URL
	githubRawBaseURL = server.URL
	t.Cleanup(func() {
		githubBaseURL = oldGitHubBaseURL
		githubRawBaseURL = oldGitHubRawBaseURL
	})

	store := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	svc := NewService(store)
	resp, err := svc.SearchPaged(ctx, SearchQuery{Kind: "skill", Query: "online research", Limit: 10})
	if err != nil {
		t.Fatalf("SearchPaged: %v", err)
	}
	if resp.Total != 1 || len(resp.Items) != 1 {
		t.Fatalf("expected one online result, got total=%d items=%d", resp.Total, len(resp.Items))
	}
	item := resp.Items[0]
	if item.Name != "online-research" || item.Description != "Online research from GitHub" {
		t.Fatalf("unexpected online item: %+v", item)
	}
	if item.InstallKey != "octo/skillbox:online-research" {
		t.Fatalf("unexpected install key: %s", item.InstallKey)
	}

	stored, err := store.GetItem(ctx, "skill", "octo/skillbox:online-research")
	if err != nil {
		t.Fatalf("GetItem persisted online hit: %v", err)
	}
	if stored.ItemPath != "skills/online-research" {
		t.Fatalf("unexpected stored item path: %q", stored.ItemPath)
	}

	githubBaseURL = "http://127.0.0.1:1"
	githubRawBaseURL = "http://127.0.0.1:1"
	cached, err := svc.SearchPaged(ctx, SearchQuery{Kind: "skill", Query: "online research", Limit: 10})
	if err != nil {
		t.Fatalf("cached SearchPaged should not need GitHub: %v", err)
	}
	if cached.Total != 1 || len(cached.Items) != 1 {
		t.Fatalf("expected cached result after online persist, got total=%d items=%d", cached.Total, len(cached.Items))
	}
}

func TestOnlineSkillSearchRejectsInvalidPaths(t *testing.T) {
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"items": []map[string]any{
				{
					"name":       "SKILL.md",
					"path":       ".hidden/bad/SKILL.md",
					"repository": map[string]any{"full_name": "octo/bad"},
				},
			},
		})
	}))
	defer server.Close()

	oldGitHubBaseURL := githubBaseURL
	oldGitHubRawBaseURL := githubRawBaseURL
	githubBaseURL = server.URL
	githubRawBaseURL = server.URL
	t.Cleanup(func() {
		githubBaseURL = oldGitHubBaseURL
		githubRawBaseURL = oldGitHubRawBaseURL
	})

	store := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	svc := NewService(store)
	resp, err := svc.SearchPaged(ctx, SearchQuery{Kind: "skill", Query: "bad", Limit: 10})
	if err != nil {
		t.Fatalf("SearchPaged: %v", err)
	}
	if resp.Total != 0 || len(resp.Items) != 0 {
		t.Fatalf("invalid online path should not be persisted: %+v", resp)
	}
}
