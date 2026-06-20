package metadata

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInitCreatesTablesIdempotently(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	if err := s.Init(ctx); err != nil {
		t.Fatalf("first Init: %v", err)
	}
	if err := s.Init(ctx); err != nil {
		t.Fatalf("second Init: %v", err)
	}
}

func TestUpsertAndSearch(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	if err := s.Init(ctx); err != nil {
		t.Fatal(err)
	}

	item := Item{
		Kind:        "skill",
		Name:        "deep-research",
		Description: "Deep research harness for multi-source reports",
		RepoOwner:   "obra",
		RepoName:    "superpowers",
		RepoBranch:  "main",
		ItemPath:    "skills/deep-research",
		InstallKey:  "obra/superpowers:deep-research",
		TargetApps:  "claude,codex",
	}
	if err := s.UpsertItem(ctx, item); err != nil {
		t.Fatalf("UpsertItem: %v", err)
	}

	results, err := s.Search(ctx, SearchQuery{Query: "research"})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Name != "deep-research" {
		t.Fatalf("unexpected name: %s", results[0].Name)
	}
}

func TestSearchByKindFilter(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	if err := s.Init(ctx); err != nil {
		t.Fatal(err)
	}
	s.UpsertItem(ctx, Item{Kind: "skill", Name: "my-skill", InstallKey: "a/b:my-skill", Description: "a skill"})
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "my-agent", InstallKey: "a/b:my-agent", Description: "an agent"})

	results, _ := s.Search(ctx, SearchQuery{Query: "my", Kind: "skill"})
	if len(results) != 1 || results[0].Name != "my-skill" {
		t.Fatalf("kind filter failed: got %+v", results)
	}
}

// TestSearchAgentsRequiresAgentsFolder locks in the SubAgents-page rule: only
// markdown files beneath an `agents/` folder are subagents. Rows left by an
// older binary (commands/, docs/, README, …) must never surface in an agent
// search, even though they sit in the index with kind=agent.
func TestSearchAgentsRequiresAgentsFolder(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	if err := s.Init(ctx); err != nil {
		t.Fatal(err)
	}
	// A real subagent (under agents/) and several leaks that are not subagents.
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "security-auditor", ItemPath: "agents/security-auditor.md", InstallKey: "o/r:security-auditor", Description: "audits"})
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "nested", ItemPath: ".claude/agents/nested.md", InstallKey: "o/r:nested", Description: "nested"})
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "post", ItemPath: "commands/post.md", InstallKey: "o/r:post", Description: "a command"})
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "overview", ItemPath: "docs/overview.md", InstallKey: "o/r:overview", Description: "docs"})
	s.UpsertItem(ctx, Item{Kind: "agent", Name: "readme", ItemPath: "README.md", InstallKey: "o/r:readme", Description: "readme"})

	results, err := s.Search(ctx, SearchQuery{Query: "", Kind: "agent"})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	names := map[string]bool{}
	for _, r := range results {
		names[r.Name] = true
	}
	if len(results) != 2 || !names["security-auditor"] || !names["nested"] {
		t.Fatalf("expected only agents under agents/, got %+v", results)
	}
	if names["post"] || names["overview"] || names["readme"] {
		t.Fatalf("non-agent files leaked into agent search: %+v", names)
	}

	total, _ := s.Count(ctx, SearchQuery{Query: "", Kind: "agent"})
	if total != 2 {
		t.Fatalf("Count should match Search (2), got %d", total)
	}
}

func TestSearchNoMatchesReturnsEmptySlice(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	if err := s.Init(ctx); err != nil {
		t.Fatal(err)
	}
	if err := s.UpsertItem(ctx, Item{Kind: "skill", Name: "present", InstallKey: "a/b:present"}); err != nil {
		t.Fatalf("UpsertItem: %v", err)
	}

	results, err := s.Search(ctx, SearchQuery{Query: "missing", Kind: "skill"})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if results == nil {
		t.Fatal("expected non-nil empty slice for no matches")
	}
	if len(results) != 0 {
		t.Fatalf("expected 0 results, got %d", len(results))
	}
}

func TestSearchPagination(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)
	// Insert 5 items.
	for i := range 5 {
		s.UpsertItem(ctx, Item{Kind: "skill", Name: fmt.Sprintf("page-skill-%d", i), InstallKey: fmt.Sprintf("a/b:page-%d", i)})
	}

	// Page 1: limit 2, offset 0 → 2 items.
	page1, _ := s.Search(ctx, SearchQuery{Query: "page-skill", Kind: "skill", Limit: 2, Offset: 0})
	if len(page1) != 2 {
		t.Fatalf("page1 expected 2 items, got %d", len(page1))
	}

	// Page 3: limit 2, offset 4 → 1 item (the last).
	page3, _ := s.Search(ctx, SearchQuery{Query: "page-skill", Kind: "skill", Limit: 2, Offset: 4})
	if len(page3) != 1 {
		t.Fatalf("page3 expected 1 item, got %d", len(page3))
	}

	// Count should be 5.
	count, _ := s.Count(ctx, SearchQuery{Query: "page-skill", Kind: "skill"})
	if count != 5 {
		t.Fatalf("count expected 5, got %d", count)
	}
}

// upsertSkill is a small helper for the dedup tests below.
func upsertSkill(t *testing.T, ctx context.Context, s *Store, name, owner, repo, installKey string) {
	t.Helper()
	if err := s.UpsertItem(ctx, Item{
		Kind:       "skill",
		Name:       name,
		RepoOwner:  owner,
		RepoName:   repo,
		InstallKey: installKey,
	}); err != nil {
		t.Fatalf("UpsertItem %s: %v", installKey, err)
	}
}

func TestSearchDeduplicatesByName(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)

	// Same name in two real repos: only one row should be returned.
	upsertSkill(t, ctx, s, "shared-skill", "davila7", "claude-code-templates", "davila7/claude-code-templates:shared-skill")
	upsertSkill(t, ctx, s, "shared-skill", "daymade", "claude-code-skills", "daymade/claude-code-skills:shared-skill")

	results, err := s.Search(ctx, SearchQuery{Query: "shared-skill", Kind: "skill"})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if len(results) != 1 {
		t.Fatalf("expected 1 deduplicated result, got %d: %+v", len(results), results)
	}
	total, _ := s.Count(ctx, SearchQuery{Query: "shared-skill", Kind: "skill"})
	if total != 1 {
		t.Fatalf("expected count 1 for deduplicated name, got %d", total)
	}
}

func TestSearchPrefersOfficialOverCatalogRepo(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)

	// A catalog/awesome-list repo must never be the chosen source when a real
	// copy exists. Here the official anthropics copy should win.
	upsertSkill(t, ctx, s, "xlsx", "anthropics", "skills", "anthropics/skills:xlsx")
	upsertSkill(t, ctx, s, "xlsx", "Chat2AnyLLM", "awesome-claude-skills", "Chat2AnyLLM/awesome-claude-skills:xlsx")

	results, _ := s.Search(ctx, SearchQuery{Query: "xlsx", Kind: "skill"})
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].RepoOwner != "anthropics" || results[0].RepoName != "skills" {
		t.Fatalf("expected canonical anthropics/skills, got %s/%s", results[0].RepoOwner, results[0].RepoName)
	}
}

func TestSearchPrefersNonCatalogRepoOverCatalogRepo(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)

	// Neither is official, but one is a catalog repo (awesome-*). The real repo wins.
	upsertSkill(t, ctx, s, "skill-creator", "daymade", "claude-code-skills", "daymade/claude-code-skills:skill-creator")
	upsertSkill(t, ctx, s, "skill-creator", "ComposioHQ", "awesome-claude-skills", "ComposioHQ/awesome-claude-skills:skill-creator")

	results, _ := s.Search(ctx, SearchQuery{Query: "skill-creator", Kind: "skill"})
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].RepoName == "awesome-claude-skills" {
		t.Fatalf("catalog repo must not be the chosen source, got %s/%s", results[0].RepoOwner, results[0].RepoName)
	}
}

func TestSearchPagedWithInstalledApps(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	s := NewStore(filepath.Join(dir, "cam.db"))
	svc := NewService(s)
	s.Init(ctx)
	s.UpsertItem(ctx, Item{Kind: "skill", Name: "paged-installed", InstallKey: "a/b:paged-installed"})

	// Simulate install to claude by creating the directory.
	claudeDir := filepath.Join(dir, ".claude", "skills", "paged-installed")
	os.MkdirAll(claudeDir, 0o755)

	resp, err := svc.SearchPaged(ctx, SearchQuery{Query: "paged", Kind: "skill"})
	if err != nil {
		t.Fatalf("SearchPaged: %v", err)
	}
	if resp.Total != 1 {
		t.Fatalf("total expected 1, got %d", resp.Total)
	}
	if len(resp.Items) != 1 {
		t.Fatalf("items expected 1, got %d", len(resp.Items))
	}
	apps := resp.Items[0].InstalledApps
	found := false
	for _, a := range apps {
		if a == "claude" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected claude in installed apps, got %v", apps)
	}
}

func TestGetItem(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)
	s.UpsertItem(ctx, Item{Kind: "skill", Name: "test-skill", InstallKey: "a/b:test-skill"})

	item, err := s.GetItem(ctx, "skill", "a/b:test-skill")
	if err != nil {
		t.Fatalf("GetItem: %v", err)
	}
	if item.Name != "test-skill" {
		t.Fatalf("unexpected name: %s", item.Name)
	}
}

func TestMarkInstalled(t *testing.T) {
	ctx := context.Background()
	s := NewStore(filepath.Join(t.TempDir(), "cam.db"))
	s.Init(ctx)
	s.UpsertItem(ctx, Item{Kind: "skill", Name: "x", InstallKey: "a/b:x"})

	if err := s.MarkInstalled(ctx, "skill", "a/b:x", "claude"); err != nil {
		t.Fatalf("MarkInstalled: %v", err)
	}
	item, _ := s.GetItem(ctx, "skill", "a/b:x")
	if !item.Installed {
		t.Fatal("expected installed=true")
	}
	if item.InstalledTargets != "claude" {
		t.Fatalf("unexpected targets: %s", item.InstalledTargets)
	}
}

func TestInitMigratesPromptToInstructionIdempotent(t *testing.T) {
	ctx := context.Background()
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	s := NewStore(dbPath)
	db, err := s.open()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, schemaSQL); err != nil {
		t.Fatalf("init schema: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO metadata_sources(kind, source_key, owner, repo) VALUES('prompt', 'legacy/source', 'owner', 'repo')`)
	if err != nil {
		t.Fatalf("insert source: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO metadata_items(kind, name, install_key) VALUES('prompt', 'legacy-prompt', 'legacy/source:legacy-prompt')`)
	if err != nil {
		t.Fatalf("insert item: %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	if err := s.Init(ctx); err != nil {
		t.Fatalf("migrating Init: %v", err)
	}
	if err := s.Init(ctx); err != nil {
		t.Fatalf("second migrating Init: %v", err)
	}

	db, err = sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	for _, table := range []string{"metadata_sources", "metadata_items"} {
		var prompts int
		if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM `+table+` WHERE kind = 'prompt'`).Scan(&prompts); err != nil {
			t.Fatalf("count prompts in %s: %v", table, err)
		}
		if prompts != 0 {
			t.Fatalf("%s still has %d prompt rows", table, prompts)
		}
		var instructions int
		if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM `+table+` WHERE kind = 'instruction'`).Scan(&instructions); err != nil {
			t.Fatalf("count instructions in %s: %v", table, err)
		}
		if instructions != 1 {
			t.Fatalf("%s instruction rows = %d, want 1", table, instructions)
		}
	}
	var migrations int
	if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM migration_meta WHERE id = 'prompt_to_instruction'`).Scan(&migrations); err != nil {
		t.Fatalf("count migration rows: %v", err)
	}
	if migrations != 1 {
		t.Fatalf("migration rows = %d, want 1", migrations)
	}
}

func TestRefreshFromLocalRepoFiles(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	s := NewStore(dbPath)

	cfgDir := filepath.Join(dir, "config")
	os.MkdirAll(cfgDir, 0o755)

	skillRepos := map[string]any{
		"obra/superpowers": map[string]any{
			"owner":      "obra",
			"name":       "superpowers",
			"branch":     "main",
			"enabled":    true,
			"skillsPath": "skills",
		},
	}
	raw, _ := json.MarshalIndent(skillRepos, "", "  ")
	os.WriteFile(filepath.Join(cfgDir, "skill_repos.json"), raw, 0o644)

	agentRepos := map[string]any{
		"iannuttall/claude-agents": map[string]any{
			"owner":      "iannuttall",
			"name":       "claude-agents",
			"branch":     "main",
			"enabled":    true,
			"agentsPath": "agents",
		},
	}
	raw2, _ := json.MarshalIndent(agentRepos, "", "  ")
	os.WriteFile(filepath.Join(cfgDir, "agent_repos.json"), raw2, 0o644)

	svc := NewService(s)
	summary, err := svc.RefreshFromFiles(ctx, cfgDir)
	if err != nil {
		t.Fatalf("RefreshFromFiles: %v", err)
	}
	if summary.SourcesScanned != 2 {
		t.Fatalf("expected 2 sources scanned, got %d", summary.SourcesScanned)
	}
	if summary.ItemsAdded < 2 {
		t.Fatalf("expected at least 2 items, got %d added", summary.ItemsAdded)
	}

	results, err := s.Search(ctx, SearchQuery{Query: "superpowers"})
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if len(results) == 0 {
		t.Fatal("expected search results for 'superpowers'")
	}
}

// fakeFetcher writes a synthetic repo tree instead of downloading from GitHub,
// so refresh tests are fast and deterministic. Every repo gets the same shape:
// one SKILL.md, one agent .md, one instruction .md, and one plugin.json.
type fakeFetcher struct{}

func (fakeFetcher) Fetch(owner, repo, branch, dest string) (string, error) {
	root := filepath.Join(dest, repo+"-"+branch)
	files := map[string]string{
		filepath.Join("skills", repo+"-skill", "SKILL.md"):    "---\nname: " + repo + "-skill\ndescription: A skill from " + repo + "\n---\n",
		filepath.Join("agents", repo+"-agent.md"):             "---\nname: " + repo + "-agent\ndescription: An agent\n---\n",
		filepath.Join("instructions", repo+"-instruction.md"): "---\nname: " + repo + "-instruction\ndescription: An instruction\n---\n",
		filepath.Join(repo+"-plugin", "plugin.json"):          `{"name":"` + repo + `-plugin","description":"A plugin"}`,
	}
	for rel, content := range files {
		p := filepath.Join(root, rel)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			return "", err
		}
		if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
			return "", err
		}
	}
	return root, nil
}

func TestRefreshAll(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))
	s := NewStore(filepath.Join(dir, "cam.db"))

	svc := NewService(s).WithFetcher(fakeFetcher{})
	summary, err := svc.RefreshAll(ctx)
	if err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	if summary.ItemsAdded == 0 {
		t.Fatal("expected resources discovered from repos")
	}

	// Every kind, including instructions, should be represented.
	for _, kind := range []string{"skill", "agent", "instruction", "plugin"} {
		results, _ := s.Search(ctx, SearchQuery{Query: "", Kind: kind})
		if len(results) == 0 {
			t.Fatalf("expected %s results after refresh", kind)
		}
		// Items are individual resources, not repos: install_key has a ":name" suffix.
		if kind == "skill" && !strings.Contains(results[0].InstallKey, ":") {
			t.Fatalf("expected resource-level install_key, got %q", results[0].InstallKey)
		}
	}
}

// catalogFakeFetcher writes generated catalog files instead of installable manifests.
type catalogFakeFetcher struct{}

func (catalogFakeFetcher) Fetch(owner, repo, branch, dest string) (string, error) {
	root := filepath.Join(dest, repo+"-"+branch)
	files := map[string]string{}
	switch repo {
	case "skill-catalog":
		files["FULL-SKILLS.md"] = "| Skill | Description |\n| --- | --- |\n| catalog-skill-a | First catalog skill |\n| catalog-skill-b | Second catalog skill |\n"
	case "plugin-catalog":
		files["README.md"] = "| Plugin | Description |\n| --- | --- |\n| catalog-plugin-a | First catalog plugin |\n| catalog-plugin-b | Second catalog plugin |\n"
	}
	for rel, content := range files {
		p := filepath.Join(root, rel)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			return "", err
		}
		if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
			return "", err
		}
	}
	if err := os.MkdirAll(root, 0o755); err != nil {
		return "", err
	}
	return root, nil
}

func TestRefreshAllDiscoversCatalogFallback(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_CONFIG_DIR", dir)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))

	writeFile(t, filepath.Join(dir, "config.yaml"), `repositories:
  skills:
    sources:
      - type: local
        path: `+filepath.ToSlash(filepath.Join(dir, "skill_repos.json"))+`
  plugins:
    sources:
      - type: local
        path: `+filepath.ToSlash(filepath.Join(dir, "plugin_repos.json"))+`
cache:
  enabled: false
  directory: `+filepath.ToSlash(filepath.Join(dir, "cache"))+`
  ttl_seconds: 3600
`)
	writeFile(t, filepath.Join(dir, "skill_repos.json"), `{
  "example/skill-catalog": {"owner":"example","name":"skill-catalog","branch":"main","enabled":true}
}`)
	writeFile(t, filepath.Join(dir, "plugin_repos.json"), `{
  "plugin-catalog": {"repoOwner":"example","repoName":"plugin-catalog","repoBranch":"main","enabled":true,"catalogFile":"README.md"}
}`)

	s := NewStore(filepath.Join(dir, "cam.db"))
	svc := NewService(s).WithFetcher(catalogFakeFetcher{})
	summary, err := svc.RefreshAll(ctx)
	if err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	if summary.ItemsAdded != 4 {
		t.Fatalf("expected 4 catalog items added, got %d (summary=%+v)", summary.ItemsAdded, summary)
	}

	skillResp, err := svc.SearchPaged(ctx, SearchQuery{Kind: "skill", Query: "catalog-skill", Limit: 10})
	if err != nil {
		t.Fatalf("SearchPaged skills: %v", err)
	}
	if skillResp.Total != 2 || len(skillResp.Items) != 2 {
		t.Fatalf("expected 2 catalog skills, got total=%d items=%d", skillResp.Total, len(skillResp.Items))
	}
	if skillResp.Items[0].ItemPath != "FULL-SKILLS.md" {
		t.Fatalf("expected catalog item path, got %q", skillResp.Items[0].ItemPath)
	}

	pluginResp, err := svc.SearchPaged(ctx, SearchQuery{Kind: "plugin", Query: "catalog-plugin", Limit: 10})
	if err != nil {
		t.Fatalf("SearchPaged plugins: %v", err)
	}
	if pluginResp.Total != 2 || len(pluginResp.Items) != 2 {
		t.Fatalf("expected 2 catalog plugins, got total=%d items=%d", pluginResp.Total, len(pluginResp.Items))
	}
}

func TestRefreshAllPreservesInstalledStatus(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))
	s := NewStore(filepath.Join(dir, "cam.db"))
	svc := NewService(s).WithFetcher(fakeFetcher{})

	if _, err := svc.RefreshAll(ctx); err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	skills, _ := s.Search(ctx, SearchQuery{Query: "", Kind: "skill", Limit: 1})
	if len(skills) == 0 {
		t.Fatal("no skills indexed")
	}
	key := skills[0].InstallKey
	if err := s.MarkInstalled(ctx, "skill", key, "claude"); err != nil {
		t.Fatalf("MarkInstalled: %v", err)
	}

	// A second refresh must not wipe the installed flag.
	if _, err := svc.RefreshAll(ctx); err != nil {
		t.Fatalf("second RefreshAll: %v", err)
	}
	item, _ := s.GetItem(ctx, "skill", key)
	if !item.Installed {
		t.Fatal("expected installed flag to survive refresh")
	}
}

func TestInstallItem(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	s := NewStore(filepath.Join(dir, "cam.db"))
	svc := NewService(s)

	s.Init(ctx)
	s.UpsertItem(ctx, Item{
		Kind:       "skill",
		Name:       "test-install-skill",
		InstallKey: "test/repo:test-install-skill",
		RepoOwner:  "test",
		RepoName:   "repo",
		RepoBranch: "main",
		ItemPath:   "skills",
		TargetApps: "claude",
	})

	err := svc.Install(ctx, "skill", "test/repo:test-install-skill", "claude")
	if err != nil {
		t.Fatalf("Install: %v", err)
	}

	item, _ := s.GetItem(ctx, "skill", "test/repo:test-install-skill")
	if !item.Installed {
		t.Fatal("expected installed=true after Install")
	}
}
