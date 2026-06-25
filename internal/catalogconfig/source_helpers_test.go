package catalogconfig

import "testing"

func TestParseGitHubRepoURL(t *testing.T) {
	cases := []struct {
		name   string
		raw    string
		owner  string
		repo   string
		branch string
		ok     bool
	}{
		{name: "plain", raw: "https://github.com/f/prompts.chat", owner: "f", repo: "prompts.chat", branch: "", ok: true},
		{name: "tree", raw: "https://github.com/owner/repo/tree/dev/prompts", owner: "owner", repo: "repo", branch: "dev", ok: true},
		{name: "git suffix", raw: "https://github.com/owner/repo.git", owner: "owner", repo: "repo", branch: "", ok: true},
		{name: "not github", raw: "https://example.com/owner/repo", ok: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := ParseGitHubRepoURL(tc.raw)
			if ok != tc.ok {
				t.Fatalf("ok = %v, want %v", ok, tc.ok)
			}
			if !ok {
				return
			}
			if got.Owner != tc.owner || got.Repo != tc.repo || got.Branch != tc.branch {
				t.Fatalf("repo = %#v", got)
			}
		})
	}
}

func TestSourceSlug(t *testing.T) {
	if got := SourceSlug("Prompts Chat"); got != "prompts_chat" {
		t.Fatalf("SourceSlug = %q", got)
	}
	if got := SourceSlug(" AI Boost: Awesome Prompts! "); got != "ai_boost_awesome_prompts" {
		t.Fatalf("SourceSlug punctuation = %q", got)
	}
}

func TestBlobURLAndRawURL(t *testing.T) {
	repo := GitHubRepo{Owner: "owner", Repo: "repo", Branch: "dev"}
	if got := repo.RawURL("prompts/a.txt"); got != "https://raw.githubusercontent.com/owner/repo/dev/prompts/a.txt" {
		t.Fatalf("RawURL = %q", got)
	}
	if got := repo.BlobURL("prompts/a.txt"); got != "https://github.com/owner/repo/blob/dev/prompts/a.txt" {
		t.Fatalf("BlobURL = %q", got)
	}
}

func TestCleanSourcePath(t *testing.T) {
	if got := CleanSourcePath("/prompts//"); got != "prompts" {
		t.Fatalf("CleanSourcePath = %q", got)
	}
	if got := CleanSourcePath(""); got != "" {
		t.Fatalf("CleanSourcePath empty = %q", got)
	}
}
