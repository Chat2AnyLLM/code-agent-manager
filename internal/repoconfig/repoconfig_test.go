package repoconfig

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

func TestBundledSkillReposDoNotIncludeChat2AnyLLMCatalog(t *testing.T) {
	repos, err := loadBundled(entities.KindSkill)
	if err != nil {
		t.Fatalf("loadBundled(skill): %v", err)
	}
	if _, ok := repos["Chat2AnyLLM/awesome-claude-skills"]; ok {
		t.Fatal("bundled skill repos must not include the Chat2AnyLLM catalog; load awesome-repo-configs instead")
	}
}

func TestBundledAgentReposDoNotIncludeChat2AnyLLMCatalog(t *testing.T) {
	repos, err := loadBundled(entities.KindAgent)
	if err != nil {
		t.Fatalf("loadBundled(agent): %v", err)
	}
	if _, ok := repos["Chat2AnyLLM/awesome-claude-agents"]; ok {
		t.Fatal("bundled agent repos must not include the Chat2AnyLLM catalog; load awesome-repo-configs instead")
	}
}

func TestBundledPluginReposDoNotIncludeChat2AnyLLMCatalog(t *testing.T) {
	repos, err := loadBundled(entities.KindPlugin)
	if err != nil {
		t.Fatalf("loadBundled(plugin): %v", err)
	}
	if _, ok := repos["chat2anyllm-awesome-claude-plugins"]; ok {
		t.Fatal("bundled plugin repos must not include the Chat2AnyLLM catalog; load awesome-repo-configs instead")
	}
}

func TestBundledPromptReposDoNotIncludeDirectAwesomePrompts(t *testing.T) {
	repos, err := loadBundled(entities.KindPrompt)
	if err != nil {
		t.Fatalf("loadBundled(prompt): %v", err)
	}
	if _, ok := repos["Chat2AnyLLM/awesome-prompts"]; ok {
		t.Fatal("bundled prompt repos must not include direct awesome-prompts; load awesome-repo-configs first")
	}
}

func TestLoadEnabledUsesConfiguredSourcesWithoutBundledCatalogs(t *testing.T) {
	cfgDir := t.TempDir()
	reposPath := filepath.Join(cfgDir, "skill_repos.json")
	if err := os.WriteFile(reposPath, []byte(`{"real/skill-repo":{"owner":"real","name":"skill-repo","branch":"main","enabled":true}}`), 0o644); err != nil {
		t.Fatal(err)
	}
	config := "repositories:\n  skills:\n    sources:\n      - type: local\n        path: " + filepath.ToSlash(reposPath) + "\ncache:\n  enabled: false\n"
	if err := os.WriteFile(filepath.Join(cfgDir, "config.yaml"), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_CONFIG_DIR", cfgDir)

	repos, err := LoadEnabled(entities.KindSkill)
	if err != nil {
		t.Fatalf("LoadEnabled(skill): %v", err)
	}
	if _, ok := repos["real/skill-repo"]; !ok {
		t.Fatalf("expected configured repo in result: %+v", repos)
	}
	if _, ok := repos["Chat2AnyLLM/awesome-claude-skills"]; ok {
		t.Fatal("did not expect Chat2AnyLLM catalog fallback when using configured sources")
	}
}

func TestRepoEntryRawFileURL(t *testing.T) {
	entry := RepoEntry{Owner: "Chat2AnyLLM", Name: "awesome-prompts", Branch: "master"}
	got := entry.RawFileURL("https://raw.example", "dist/prompts.json")
	want := "https://raw.example/Chat2AnyLLM/awesome-prompts/master/dist/prompts.json"
	if got != want {
		t.Fatalf("RawFileURL = %q, want %q", got, want)
	}
}

func TestRepoEntryIsEnabled(t *testing.T) {
	trueVal := true
	falseVal := false

	tests := []struct {
		name     string
		entry    RepoEntry
		expected bool
	}{
		{"nil defaults true", RepoEntry{}, true},
		{"explicit true", RepoEntry{Enabled: &trueVal}, true},
		{"explicit false", RepoEntry{Enabled: &falseVal}, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.entry.IsEnabled(); got != tt.expected {
				t.Errorf("IsEnabled() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestRepoEntryEffectiveOwnerName(t *testing.T) {
	// Standard entry.
	r := RepoEntry{Owner: "alice", Name: "my-repo"}
	if r.EffectiveOwner() != "alice" {
		t.Errorf("EffectiveOwner() = %q", r.EffectiveOwner())
	}
	if r.EffectiveName() != "my-repo" {
		t.Errorf("EffectiveName() = %q", r.EffectiveName())
	}

	// Plugin-style entry prefers RepoOwner/RepoName.
	p := RepoEntry{Owner: "alice", Name: "old", RepoOwner: "bob", RepoName: "new-repo"}
	if p.EffectiveOwner() != "bob" {
		t.Errorf("EffectiveOwner() = %q, want bob", p.EffectiveOwner())
	}
	if p.EffectiveName() != "new-repo" {
		t.Errorf("EffectiveName() = %q, want new-repo", p.EffectiveName())
	}
}

func TestRepoEntryEffectiveBranch(t *testing.T) {
	tests := []struct {
		name     string
		entry    RepoEntry
		expected string
	}{
		{"default main", RepoEntry{}, "main"},
		{"branch set", RepoEntry{Branch: "develop"}, "develop"},
		{"repoBranch preferred", RepoEntry{Branch: "develop", RepoBranch: "release"}, "release"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.entry.EffectiveBranch(); got != tt.expected {
				t.Errorf("EffectiveBranch() = %q, want %q", got, tt.expected)
			}
		})
	}
}

func TestRepoEntrySubPath(t *testing.T) {
	r := RepoEntry{SkillsPath: "skills", AgentsPath: "agents", PluginPath: "plugins"}
	if r.SubPath(entities.KindSkill) != "skills" {
		t.Errorf("SubPath(skill) = %q", r.SubPath(entities.KindSkill))
	}
	if r.SubPath(entities.KindAgent) != "agents" {
		t.Errorf("SubPath(agent) = %q", r.SubPath(entities.KindAgent))
	}
	if r.SubPath(entities.KindPlugin) != "plugins" {
		t.Errorf("SubPath(plugin) = %q", r.SubPath(entities.KindPlugin))
	}
}

func TestParseRepoJSON(t *testing.T) {
	input := `{
		"my-org/my-repo": {
			"owner": "my-org",
			"name": "my-repo",
			"branch": "main",
			"enabled": true
		}
	}`
	repos, err := parseRepoJSON([]byte(input))
	if err != nil {
		t.Fatalf("parseRepoJSON: %v", err)
	}
	if len(repos) != 1 {
		t.Fatalf("expected 1 repo, got %d", len(repos))
	}
	r := repos["my-org/my-repo"]
	if r.Owner != "my-org" || r.Name != "my-repo" {
		t.Errorf("unexpected owner/name: %q/%q", r.Owner, r.Name)
	}
	if r.CatalogFile != "" {
		t.Errorf("unexpected catalog file: %q", r.CatalogFile)
	}
}

func TestParseRepoJSONCatalogFile(t *testing.T) {
	input := `{
		"my-org/catalog": {
			"owner": "my-org",
			"name": "catalog",
			"branch": "main",
			"enabled": true,
			"catalogFile": "FULL-SKILLS.md"
		}
	}`
	repos, err := parseRepoJSON([]byte(input))
	if err != nil {
		t.Fatalf("parseRepoJSON: %v", err)
	}
	if got := repos["my-org/catalog"].CatalogFile; got != "FULL-SKILLS.md" {
		t.Fatalf("CatalogFile = %q, want FULL-SKILLS.md", got)
	}
}

func TestLoadLocalSource(t *testing.T) {
	// Create a temporary config dir with a skill_repos.json.
	tmpDir := t.TempDir()

	data := map[string]RepoEntry{
		"test/repo": {
			Owner:  "test",
			Name:   "repo",
			Branch: "main",
		},
	}
	raw, _ := json.MarshalIndent(data, "", "  ")
	path := filepath.Join(tmpDir, "skill_repos.json")
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}

	repos, err := LoadLocalSource(path)
	if err != nil {
		t.Fatalf("loadLocalSource: %v", err)
	}
	if len(repos) != 1 {
		t.Fatalf("expected 1 repo, got %d", len(repos))
	}
	if _, ok := repos["test/repo"]; !ok {
		t.Error("expected test/repo in loaded repos")
	}
}

func TestLoadLocalSourceMissing(t *testing.T) {
	repos, err := LoadLocalSource("/nonexistent/path/repos.json")
	if err != nil {
		t.Fatalf("loadLocalSource: %v", err)
	}
	if repos != nil {
		t.Errorf("expected nil for missing file, got %v", repos)
	}
}

func TestLoadLocalSourceExpandsTilde(t *testing.T) {
	// Create a temp file and refer to it via ~ expansion.
	tmpDir := t.TempDir()
	data := map[string]RepoEntry{
		"tilde/test": {Owner: "tilde", Name: "test", Branch: "main"},
	}
	raw, _ := json.MarshalIndent(data, "", "  ")
	path := filepath.Join(tmpDir, "repos.json")
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}

	// loadLocalSource should handle absolute paths fine.
	repos, err := LoadLocalSource(path)
	if err != nil {
		t.Fatalf("loadLocalSource: %v", err)
	}
	if _, ok := repos["tilde/test"]; !ok {
		t.Error("expected tilde/test in loaded repos")
	}
}

func TestLoadEnabledFilters(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", tmpDir)

	falseVal := false
	data := map[string]RepoEntry{
		"enabled/repo": {
			Owner:  "enabled",
			Name:   "repo",
			Branch: "main",
		},
		"disabled/repo": {
			Owner:   "disabled",
			Name:    "repo",
			Branch:  "main",
			Enabled: &falseVal,
		},
	}
	raw, _ := json.MarshalIndent(data, "", "  ")
	reposPath := filepath.Join(tmpDir, "agent_repos.json")
	if err := os.WriteFile(reposPath, raw, 0o644); err != nil {
		t.Fatal(err)
	}

	// Write a config.yaml that points to the local repos file.
	configYAML := fmt.Sprintf(`repositories:
  agents:
    sources:
      - type: local
        path: %s
cache:
  enabled: false
  directory: %s/cache
  ttl_seconds: 3600
`, reposPath, tmpDir)
	if err := os.WriteFile(filepath.Join(tmpDir, "config.yaml"), []byte(configYAML), 0o644); err != nil {
		t.Fatal(err)
	}

	repos, err := LoadEnabled(entities.KindAgent)
	if err != nil {
		t.Fatalf("LoadEnabled: %v", err)
	}
	if _, ok := repos["disabled/repo"]; ok {
		t.Error("disabled/repo should have been filtered out")
	}
	// enabled/repo should be present (from local source in config.yaml).
	if _, ok := repos["enabled/repo"]; !ok {
		t.Error("enabled/repo should be present")
	}
}

func TestRepoConfigKey(t *testing.T) {
	tests := []struct {
		kind     entities.Kind
		expected string
	}{
		{entities.KindSkill, "skills"},
		{entities.KindAgent, "agents"},
		{entities.KindPlugin, "plugins"},
		{entities.KindInstruction, "instructions"},
	}
	for _, tt := range tests {
		if got := repoConfigKey(tt.kind); got != tt.expected {
			t.Errorf("repoConfigKey(%s) = %q, want %q", tt.kind, got, tt.expected)
		}
	}
}

func TestBundledInstructionRepos(t *testing.T) {
	repos, err := loadBundled(entities.KindInstruction)
	if err != nil {
		t.Fatalf("loadBundled(instruction): %v", err)
	}
	if len(repos) == 0 {
		t.Fatal("expected bundled instruction repos")
	}
	if _, ok := repos["anthropics/claude-code"]; !ok {
		t.Fatal("expected anthropics/claude-code in bundled instruction repos")
	}
}

func TestMigrateRepoConfigFilesCreatesInstructionFile(t *testing.T) {
	dir := t.TempDir()
	promptData := `{"test/repo": {"owner": "test", "name": "repo", "enabled": true}}`
	if err := os.WriteFile(filepath.Join(dir, "prompt_repos.json"), []byte(promptData), 0o644); err != nil {
		t.Fatal(err)
	}
	updated, err := MigrateRepoConfigFiles(dir)
	if err != nil {
		t.Fatalf("MigrateRepoConfigFiles: %v", err)
	}
	if !updated {
		t.Fatal("expected updated=true")
	}
	if _, err := os.Stat(filepath.Join(dir, "instruction_repos.json")); err != nil {
		t.Fatalf("instruction_repos.json should exist: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "prompt_repos.json")); err != nil {
		t.Fatalf("prompt_repos.json should remain: %v", err)
	}
}

func TestMigrateRepoConfigFilesPrefersExistingInstructionFile(t *testing.T) {
	dir := t.TempDir()
	instructionData := `{"new/repo": {"owner": "new", "name": "repo"}}`
	promptData := `{"old/repo": {"owner": "old", "name": "repo"}}`
	if err := os.WriteFile(filepath.Join(dir, "instruction_repos.json"), []byte(instructionData), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "prompt_repos.json"), []byte(promptData), 0o644); err != nil {
		t.Fatal(err)
	}
	updated, err := MigrateRepoConfigFiles(dir)
	if err != nil {
		t.Fatalf("MigrateRepoConfigFiles: %v", err)
	}
	if updated {
		t.Fatal("expected updated=false when instruction file exists")
	}
	data, err := os.ReadFile(filepath.Join(dir, "instruction_repos.json"))
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != instructionData {
		t.Fatalf("instruction_repos.json changed: got %q, want %q", data, instructionData)
	}
}

func TestMigrateRepoConfigFilesNoFileDoesNothing(t *testing.T) {
	updated, err := MigrateRepoConfigFiles(t.TempDir())
	if err != nil {
		t.Fatalf("MigrateRepoConfigFiles: %v", err)
	}
	if updated {
		t.Fatal("expected updated=false when no files exist")
	}
}
