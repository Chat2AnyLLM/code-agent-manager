package cli_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

// seedEntity writes an entity directly into the store so tests don't depend on
// commands that are no longer exposed (like the old "add" subcommand).
func seedEntity(t *testing.T, kind entities.Kind, name, content, description string) {
	t.Helper()
	store := entities.NewStore(kind)
	if err := store.Put(entities.Entity{
		Name:        name,
		Content:     content,
		Description: description,
	}); err != nil {
		t.Fatalf("seedEntity: %v", err)
	}
}

// installEntityToApp installs an entity directly into an app directory for
// testing the list command's installed-scan behavior.
func installEntityToApp(t *testing.T, home string, kind entities.Kind, name, content, app string) {
	t.Helper()
	apps := entities.AppPathsFor(kind)
	dest, ok := apps[app]
	if !ok {
		t.Fatalf("unknown app %q for kind %s", app, kind)
	}
	resolved := os.ExpandEnv(strings.ReplaceAll(dest, "~", home))
	switch kind {
	case entities.KindPrompt, entities.KindInstruction:
		if err := os.MkdirAll(filepath.Dir(resolved), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(resolved, []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	case entities.KindSkill:
		dir := filepath.Join(resolved, name)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	case entities.KindAgent:
		dir := filepath.Join(resolved, name)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, "AGENT.md"), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	case entities.KindPlugin:
		dir := filepath.Join(resolved, name)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, "manifest.json"), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
}

// ============================================================================
// list — shows what's installed across code agents
// ============================================================================

// Empty agent dirs reports no installed skills.
func TestSkillListWhenEmpty(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "skill", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "No skills installed across agents") {
		t.Fatalf("missing empty state:\n%s", stdout)
	}
}

// List shows skills installed into agent directories.
func TestSkillListShowsInstalledSkills(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindSkill, "deep-research", "body", "claude")
	stdout, _, code := execute(t, "skill", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "deep-research") {
		t.Fatalf("list missing skill:\n%s", stdout)
	}
	if !strings.Contains(stdout, "claude") {
		t.Fatalf("list missing app name:\n%s", stdout)
	}
}

// List --app filters to a specific agent.
func TestSkillListFiltersByApp(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindSkill, "skill-a", "body", "claude")
	installEntityToApp(t, home, entities.KindSkill, "skill-b", "body", "codex")
	stdout, _, code := execute(t, "skill", "list", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "skill-a") {
		t.Fatalf("list missing claude skill:\n%s", stdout)
	}
	if strings.Contains(stdout, "skill-b") {
		t.Fatalf("list should not show codex skill when filtering by claude:\n%s", stdout)
	}
}

// List --app rejects unknown app names.
func TestSkillListRejectsUnknownApp(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "list", "--app", "ghostapp")
	if code == 0 {
		t.Fatal("expected non-zero exit for unknown app")
	}
	if !strings.Contains(stderr, "unknown app") {
		t.Fatalf("stderr missing guidance: %s", stderr)
	}
}

// List shows total count.
func TestSkillListShowsTotalCount(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindSkill, "s1", "body", "claude")
	installEntityToApp(t, home, entities.KindSkill, "s2", "body", "claude")
	stdout, _, code := execute(t, "skill", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Total:") {
		t.Fatalf("list missing total:\n%s", stdout)
	}
}

// ============================================================================
// search — search across configured repos
// ============================================================================

func TestSkillSearchFindsMatch(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindSkill, "deep-research", "content", "Deep research skill")
	seedEntity(t, entities.KindSkill, "code-review", "content", "Code review")
	stdout, _, code := execute(t, "skill", "search", "deep", "--local")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "deep-research") {
		t.Fatalf("search missing match:\n%s", stdout)
	}
	if strings.Contains(stdout, "code-review") {
		t.Fatalf("search should not include non-matching:\n%s", stdout)
	}
}

func TestSkillSearchNoResults(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindSkill, "deep-research", "content", "Deep research skill")
	stdout, _, code := execute(t, "skill", "search", "nonexistent", "--local")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "No skills found matching") {
		t.Fatalf("expected no-match message:\n%s", stdout)
	}
}

func TestSkillSearchMatchesDescription(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindSkill, "my-skill", "content", "Terraform infrastructure")
	stdout, _, code := execute(t, "skill", "search", "terraform", "--local")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "my-skill") {
		t.Fatalf("search should match on description:\n%s", stdout)
	}
}

// ============================================================================
// install — install into code agent
// ============================================================================

func TestSkillInstallCreatesSkillDirectoryWithMarkdown(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindSkill, "deep-research", "skill body", "")
	stdout, _, code := execute(t, "skill", "install", "deep-research", "--app", "claude")
	if code != 0 {
		t.Fatalf("install exit = %d", code)
	}
	wantDir := filepath.Join(home, ".claude", "skills", "deep-research")
	if !strings.Contains(stdout, wantDir) {
		t.Fatalf("install output missing dir:\n%s", stdout)
	}
	data, err := os.ReadFile(filepath.Join(wantDir, "SKILL.md"))
	if err != nil {
		t.Fatalf("SKILL.md missing: %v", err)
	}
	if string(data) != "skill body" {
		t.Fatalf("SKILL.md = %q", data)
	}
}

func TestSkillInstallWithoutAppErrors(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindSkill, "demo", "body", "")
	_, stderr, code := execute(t, "skill", "install", "demo")
	if code == 0 {
		t.Fatal("expected non-zero exit without --app")
	}
	if !strings.Contains(stderr, "--app is required") {
		t.Fatalf("stderr missing --app guidance: %s", stderr)
	}
}

// --all installs everything from the store.
func TestSkillInstallAll(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindSkill, "s1", "body1", "")
	seedEntity(t, entities.KindSkill, "s2", "body2", "")
	stdout, _, code := execute(t, "skill", "install", "--all", "--app", "claude")
	if code != 0 {
		t.Fatalf("install --all exit = %d", code)
	}
	if !strings.Contains(stdout, "Installed 2 skill(s)") {
		t.Fatalf("missing install count:\n%s", stdout)
	}
	// Verify files on disk.
	for _, name := range []string{"s1", "s2"} {
		if _, err := os.Stat(filepath.Join(home, ".claude", "skills", name, "SKILL.md")); err != nil {
			t.Fatalf("SKILL.md missing for %s: %v", name, err)
		}
	}
}

// --all with --force overwrites existing.
func TestSkillInstallAllForce(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindSkill, "s1", "new-body", "")
	installEntityToApp(t, home, entities.KindSkill, "s1", "old-body", "claude")
	stdout, _, code := execute(t, "skill", "install", "--all", "--app", "claude", "--force")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Installed 1 skill(s)") {
		t.Fatalf("missing install count:\n%s", stdout)
	}
	data, _ := os.ReadFile(filepath.Join(home, ".claude", "skills", "s1", "SKILL.md"))
	if string(data) != "new-body" {
		t.Fatalf("expected new-body, got %q", data)
	}
}

// Already installed without --force skips.
func TestSkillInstallSkipsExisting(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindSkill, "s1", "body", "")
	installEntityToApp(t, home, entities.KindSkill, "s1", "old-body", "claude")
	stdout, _, code := execute(t, "skill", "install", "s1", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "already installed") {
		t.Fatalf("expected skip message:\n%s", stdout)
	}
}

// --force overwrites existing.
func TestSkillInstallForceOverwrites(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindSkill, "s1", "new-body", "")
	installEntityToApp(t, home, entities.KindSkill, "s1", "old-body", "claude")
	stdout, _, code := execute(t, "skill", "install", "s1", "--app", "claude", "--force")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Installed s1") {
		t.Fatalf("expected install message:\n%s", stdout)
	}
	data, _ := os.ReadFile(filepath.Join(home, ".claude", "skills", "s1", "SKILL.md"))
	if string(data) != "new-body" {
		t.Fatalf("expected new-body, got %q", data)
	}
}

// ============================================================================
// update — dry-run mode
// ============================================================================

func TestSkillUpdateDryRun(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "skill", "update", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "[dry-run]") {
		t.Fatalf("expected dry-run label:\n%s", stdout)
	}
}

// ============================================================================
// install --from-local
// ============================================================================

// makeLocalSkillDir creates a temp directory with SKILL.md files for testing.
func makeLocalSkillDir(t *testing.T, skills map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for name, content := range skills {
		skillDir := filepath.Join(dir, name)
		if err := os.MkdirAll(skillDir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func TestSkillInstallFromLocalSingleSkill(t *testing.T) {
	home := isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{"my-local-skill": "local body"})
	stdout, _, code := execute(t, "skill", "install", localDir, "--from-local", "--app", "claude")
	if code != 0 {
		t.Fatalf("install --from-local exit = %d", code)
	}
	if !strings.Contains(stdout, "my-local-skill") {
		t.Fatalf("missing skill name:\n%s", stdout)
	}
	data, err := os.ReadFile(filepath.Join(home, ".claude", "skills", "my-local-skill", "SKILL.md"))
	if err != nil {
		t.Fatalf("SKILL.md missing: %v", err)
	}
	if string(data) != "local body" {
		t.Fatalf("SKILL.md = %q", data)
	}
}

func TestSkillInstallFromLocalMultipleSkills(t *testing.T) {
	home := isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{
		"skill-a": "body-a",
		"skill-b": "body-b",
	})
	stdout, _, code := execute(t, "skill", "install", localDir, "--from-local", "--all", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "2 skill(s) installed to claude") {
		t.Fatalf("missing count:\n%s", stdout)
	}
	for _, name := range []string{"skill-a", "skill-b"} {
		if _, err := os.Stat(filepath.Join(home, ".claude", "skills", name, "SKILL.md")); err != nil {
			t.Fatalf("missing %s: %v", name, err)
		}
	}
}

func TestSkillInstallFromLocalRequiresDir(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "install", "--from-local", "--app", "claude")
	if code == 0 {
		t.Fatal("expected error without path")
	}
	if !strings.Contains(stderr, "--from-local requires") {
		t.Fatalf("stderr: %s", stderr)
	}
}

func TestSkillInstallFromLocalEmptyDir(t *testing.T) {
	isolatedHome(t)
	emptyDir := t.TempDir()
	stdout, _, code := execute(t, "skill", "install", emptyDir, "--from-local", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "No skills found") {
		t.Fatalf("expected empty message:\n%s", stdout)
	}
}

func TestSkillInstallFromLocalSkipsExisting(t *testing.T) {
	home := isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{"existing-skill": "new-body"})
	installEntityToApp(t, home, entities.KindSkill, "existing-skill", "old-body", "claude")
	stdout, _, code := execute(t, "skill", "install", localDir, "--from-local", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Skipping existing-skill") {
		t.Fatalf("expected skip message:\n%s", stdout)
	}
}

func TestSkillInstallFromLocalForceOverwrites(t *testing.T) {
	home := isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{"existing-skill": "new-body"})
	installEntityToApp(t, home, entities.KindSkill, "existing-skill", "old-body", "claude")
	stdout, _, code := execute(t, "skill", "install", localDir, "--from-local", "--app", "claude", "--force")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "1 skill(s) installed to claude") {
		t.Fatalf("missing count:\n%s", stdout)
	}
	data, _ := os.ReadFile(filepath.Join(home, ".claude", "skills", "existing-skill", "SKILL.md"))
	if string(data) != "new-body" {
		t.Fatalf("expected new-body, got %q", data)
	}
}

// Specifying a skill name with --from-local installs just that one.
func TestSkillInstallFromLocalByName(t *testing.T) {
	home := isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{
		"skill-a": "body-a",
		"skill-b": "body-b",
	})
	stdout, _, code := execute(t, "skill", "install", localDir, "skill-a", "--from-local", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "skill-a") {
		t.Fatalf("missing skill-a:\n%s", stdout)
	}
	// skill-b should NOT be installed.
	if _, err := os.Stat(filepath.Join(home, ".claude", "skills", "skill-b")); err == nil {
		t.Fatal("skill-b should not be installed")
	}
}

// Without --all or name, multiple skills errors (non-interactive).
func TestSkillInstallFromLocalMultipleWithoutAllListsThem(t *testing.T) {
	isolatedHome(t)
	localDir := makeLocalSkillDir(t, map[string]string{
		"skill-a": "body-a",
		"skill-b": "body-b",
	})
	_, _, code := execute(t, "skill", "install", localDir, "--from-local", "--app", "claude")
	if code == 0 {
		t.Fatal("expected error without --all or name")
	}
	// Non-interactive should fail asking to specify name or --all.
}

// ============================================================================
// install --from-github (flag validation only, no network)
// ============================================================================

func TestSkillInstallFromGitHubRequiresArg(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "install", "--from-github", "--app", "claude")
	if code == 0 {
		t.Fatal("expected error without repo arg")
	}
	if !strings.Contains(stderr, "--from-github requires") {
		t.Fatalf("stderr: %s", stderr)
	}
}

func TestSkillInstallFromGitHubRejectsInvalidRepo(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "install", "notarepo", "--from-github", "--app", "claude")
	if code == 0 {
		t.Fatal("expected error for invalid repo format")
	}
	if !strings.Contains(stderr, "invalid repository") {
		t.Fatalf("stderr: %s", stderr)
	}
}

func TestSkillInstallFromLocalAndFromGitHubConflict(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "install", "foo/bar", "--from-local", "--from-github", "--app", "claude")
	if code == 0 {
		t.Fatal("expected error with both flags")
	}
	if !strings.Contains(stderr, "cannot be used together") {
		t.Fatalf("stderr: %s", stderr)
	}
}

// ============================================================================
// search --local (flag parsing, no network)
// ============================================================================

func TestSkillSearchHelpShowsFlags(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "skill", "search", "--help")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "--local") {
		t.Fatalf("help missing --local flag:\n%s", stdout)
	}
	if !strings.Contains(stdout, "--owner") {
		t.Fatalf("help missing --owner flag:\n%s", stdout)
	}
	if !strings.Contains(stdout, "--limit") {
		t.Fatalf("help missing --limit flag:\n%s", stdout)
	}
	if !strings.Contains(stdout, "GitHub") {
		t.Fatalf("help should mention GitHub:\n%s", stdout)
	}
}

// --local skips GitHub and only searches local store + configured repos.
func TestSkillSearchLocalOnly(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindSkill, "my-terraform-skill", "content", "Terraform module builder")
	stdout, _, code := execute(t, "skill", "search", "terraform", "--local")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "my-terraform-skill") {
		t.Fatalf("search should find local match:\n%s", stdout)
	}
	// Should NOT contain GitHub results header.
	if strings.Contains(stdout, "Showing") && strings.Contains(stdout, "REPOSITORY") {
		t.Fatalf("--local should skip GitHub search:\n%s", stdout)
	}
}

// ============================================================================
// alias
// ============================================================================

func TestSkillAliasS(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "s", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "No skills installed across agents") {
		t.Fatalf("alias output: %s", stdout)
	}
}

// ============================================================================
// uninstall
// ============================================================================

func TestSkillUninstallRemovesInstalled(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindSkill, "my-skill", "body", "claude")
	// Verify it's there.
	skillDir := filepath.Join(home, ".claude", "skills", "my-skill")
	if _, err := os.Stat(skillDir); err != nil {
		t.Fatalf("skill not installed: %v", err)
	}
	stdout, _, code := execute(t, "skill", "uninstall", "my-skill", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Removed my-skill") {
		t.Fatalf("missing removal message:\n%s", stdout)
	}
	// Verify it's gone.
	if _, err := os.Stat(skillDir); !os.IsNotExist(err) {
		t.Fatal("skill directory should have been removed")
	}
}

func TestSkillUninstallNotFoundReports(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "skill", "uninstall", "no-such-skill", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "not found") {
		t.Fatalf("expected not-found message:\n%s", stdout)
	}
}

func TestSkillUninstallWithoutAppErrors(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "skill", "uninstall", "demo")
	if code == 0 {
		t.Fatal("expected non-zero exit without --app in non-interactive mode")
	}
	if !strings.Contains(stderr, "--app is required") {
		t.Fatalf("stderr missing --app guidance: %s", stderr)
	}
}

func TestPluginUninstallRemovesInstalled(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindPlugin, "my-plugin", `{"name":"test"}`, "claude")
	pluginDir := filepath.Join(home, ".claude", "plugins", "my-plugin")
	if _, err := os.Stat(pluginDir); err != nil {
		t.Fatalf("plugin not installed: %v", err)
	}
	stdout, _, code := execute(t, "plugin", "uninstall", "my-plugin", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Removed my-plugin") {
		t.Fatalf("missing removal message:\n%s", stdout)
	}
	if _, err := os.Stat(pluginDir); !os.IsNotExist(err) {
		t.Fatal("plugin directory should have been removed")
	}
}
