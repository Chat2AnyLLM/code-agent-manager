package entities_test

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

func TestStoreRoundTrip(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))

	store := entities.NewStore(entities.KindInstruction)
	if err := store.Put(entities.Entity{Name: "demo", Content: "Hello", Apps: []string{"claude"}}); err != nil {
		t.Fatalf("Put err = %v", err)
	}
	all, err := store.All()
	if err != nil {
		t.Fatalf("All err = %v", err)
	}
	if len(all) != 1 || all[0].Name != "demo" {
		t.Fatalf("All = %v", all)
	}
	got, err := store.Get("demo")
	if err != nil {
		t.Fatalf("Get err = %v", err)
	}
	if got.Content != "Hello" {
		t.Fatalf("content = %q", got.Content)
	}
	if got.Kind != entities.KindInstruction {
		t.Fatalf("kind = %q", got.Kind)
	}
	if got.UpdatedAt.IsZero() {
		t.Fatal("UpdatedAt should be set")
	}
	removed, err := store.Delete("demo")
	if err != nil || !removed {
		t.Fatalf("Delete = %v, %v", removed, err)
	}
	if all, _ := store.All(); len(all) != 0 {
		t.Fatalf("post-delete all = %v", all)
	}
}

func TestInstallPromptWritesFile(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	path, err := entities.InstallToApp(entities.Entity{Name: "demo", Content: "Hi"}, entities.KindInstruction, "claude")
	if err != nil {
		t.Fatalf("InstallToApp err = %v", err)
	}
	if path != filepath.Join(home, ".claude/CLAUDE.md") {
		t.Fatalf("path = %q", path)
	}
	data, _ := os.ReadFile(path)
	if string(data) != "Hi" {
		t.Fatalf("written content = %q", data)
	}
}

func TestInstallSkillCreatesDirectoryWithMarkdown(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	dir, err := entities.InstallToApp(entities.Entity{Name: "deep-research", Content: "skill body"}, entities.KindSkill, "claude")
	if err != nil {
		t.Fatalf("InstallToApp err = %v", err)
	}
	want := filepath.Join(home, ".claude/skills/deep-research")
	if dir != want {
		t.Fatalf("dir = %q, want %q", dir, want)
	}
	data, _ := os.ReadFile(filepath.Join(dir, "SKILL.md"))
	if string(data) != "skill body" {
		t.Fatalf("SKILL.md = %q", data)
	}
}

func TestUninstallSkillRemovesDirectory(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	if _, err := entities.InstallToApp(entities.Entity{Name: "demo", Content: "body"}, entities.KindSkill, "claude"); err != nil {
		t.Fatal(err)
	}
	_, removed, err := entities.UninstallFromApp("demo", entities.KindSkill, "claude")
	if err != nil {
		t.Fatalf("Uninstall err = %v", err)
	}
	if !removed {
		t.Fatal("expected removed=true")
	}
	if _, removed, _ := entities.UninstallFromApp("demo", entities.KindSkill, "claude"); removed {
		t.Fatal("second uninstall should not report removed=true")
	}
}

func TestSupportedAppsContainsExpectedSets(t *testing.T) {
	for _, kind := range []entities.Kind{entities.KindInstruction, entities.KindSkill, entities.KindAgent, entities.KindPlugin} {
		apps := entities.SupportedApps(kind)
		if len(apps) == 0 {
			t.Fatalf("kind %s should have apps", kind)
		}
		// claude should be supported across all kinds.
		found := false
		for _, a := range apps {
			if a == "claude" {
				found = true
			}
		}
		if !found {
			t.Fatalf("kind %s missing claude: %v", kind, apps)
		}
	}
}

func TestInstructionPathUserLevel(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	path, err := entities.InstructionPath("claude", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	want := filepath.Join(home, ".claude/CLAUDE.md")
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathUserLevelGemini(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	path, err := entities.InstructionPath("gemini", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	want := filepath.Join(home, ".gemini/GEMINI.md")
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathUserLevelCodex(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	path, err := entities.InstructionPath("codex", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	want := filepath.Join(home, ".codex/AGENTS.md")
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathUserLevelCopilot(t *testing.T) {
	// Copilot supports user-level via ~/.copilot/copilot-instructions.md.
	home := t.TempDir()
	t.Setenv("HOME", home)
	path, err := entities.InstructionPath("copilot", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := filepath.Join(home, ".copilot", "copilot-instructions.md")
	if path != expected {
		t.Fatalf("expected %s, got %s", expected, path)
	}
}

func TestInstructionPathProjectLevel(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	projDir := t.TempDir()

	path, err := entities.InstructionPath("claude", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/CLAUDE.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathProjectLevelGemini(t *testing.T) {
	projDir := t.TempDir()

	path, err := entities.InstructionPath("gemini", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/GEMINI.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathProjectLevelCopilot(t *testing.T) {
	projDir := t.TempDir()

	path, err := entities.InstructionPath("copilot", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/.github/copilot-instructions.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathProjectLevelCodex(t *testing.T) {
	projDir := t.TempDir()

	path, err := entities.InstructionPath("codex", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstructionPath err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/AGENTS.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
}

func TestInstructionPathUnsupportedApp(t *testing.T) {
	_, err := entities.InstructionPath("nonexistent", entities.InstallLevelUser, "")
	if err == nil {
		t.Fatal("expected error for unsupported app")
	}
}

func TestInstructionPathUnsupportedLevel(t *testing.T) {
	_, err := entities.InstructionPath("claude", "system", "")
	if err == nil {
		t.Fatal("expected error for unsupported level")
	}
}

func TestInstructionPathProjectLevelMissingDir(t *testing.T) {
	_, err := entities.InstructionPath("claude", entities.InstallLevelProject, "")
	if err == nil {
		t.Fatal("expected error for missing project dir")
	}
}

func TestInstructionPathProjectLevelNonexistentDir(t *testing.T) {
	_, err := entities.InstructionPath("claude", entities.InstallLevelProject, "/nonexistent/path")
	if err == nil {
		t.Fatal("expected error for nonexistent project dir")
	}
}

func TestInstructionPathProjectLevelFileNotDir(t *testing.T) {
	f := t.TempDir()
	filePath := filepath.Join(f, "somefile.txt")
	if err := os.WriteFile(filePath, []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	_, err := entities.InstructionPath("claude", entities.InstallLevelProject, filePath)
	if err == nil {
		t.Fatal("expected error when project dir is a file, not a directory")
	}
}

func TestInstallInstructionUserLevel(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	path, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "my instruction"}, "claude", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("InstallInstruction err = %v", err)
	}
	want := filepath.Join(home, ".claude/CLAUDE.md")
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
	data, _ := os.ReadFile(path)
	if string(data) != "my instruction" {
		t.Fatalf("content = %q", data)
	}
}

func TestInstallInstructionProjectLevel(t *testing.T) {
	projDir := t.TempDir()
	t.Setenv("HOME", t.TempDir())

	path, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "project instruction"}, "claude", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstallInstruction err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/CLAUDE.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
	data, _ := os.ReadFile(path)
	if string(data) != "project instruction" {
		t.Fatalf("content = %q", data)
	}
}

func TestInstallInstructionCopilotProjectLevel(t *testing.T) {
	projDir := t.TempDir()
	t.Setenv("HOME", t.TempDir())

	path, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "copilot instructions"}, "copilot", entities.InstallLevelProject, projDir)
	if err != nil {
		t.Fatalf("InstallInstruction err = %v", err)
	}
	absProj, _ := filepath.Abs(projDir)
	want := absProj + "/.github/copilot-instructions.md"
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
	data, _ := os.ReadFile(path)
	if string(data) != "copilot instructions" {
		t.Fatalf("content = %q", data)
	}
}

func TestInstallInstructionUnsupportedApp(t *testing.T) {
	_, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "x"}, "unknown", entities.InstallLevelUser, "")
	if err == nil {
		t.Fatal("expected error for unsupported app")
	}
}

func TestInstallInstructionUnsupportedLevel(t *testing.T) {
	_, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "x"}, "claude", entities.InstallLevelProject, "")
	if err == nil {
		t.Fatal("expected error for missing project dir")
	}
}

func TestUninstallInstructionUserLevel(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	// Install first
	path, err := entities.InstallInstruction(entities.Entity{Name: "test", Content: "content"}, "claude", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatal(err)
	}
	if !pathutilExists(path) {
		t.Fatal("file should exist after install")
	}
	// Uninstall
	resolved, removed, err := entities.UninstallInstruction("test", "claude", entities.InstallLevelUser, "")
	if err != nil {
		t.Fatalf("UninstallInstruction err = %v", err)
	}
	if resolved != path {
		t.Fatalf("resolved = %q, want %q", resolved, path)
	}
	// Instructions are app-wide files, not removed on uninstall
	if removed {
		t.Fatal("expected removed=false for instruction files")
	}
}

func TestInstructionAppsList(t *testing.T) {
	apps := entities.InstructionApps()
	if len(apps) == 0 {
		t.Fatal("expected non-empty instruction apps list")
	}
	found := false
	for _, a := range apps {
		if a == "claude" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected claude in instruction apps")
	}
}

func TestInstructionAppLevels(t *testing.T) {
	// Claude supports both user and project
	levels := entities.InstructionAppLevels("claude")
	if len(levels) != 2 {
		t.Fatalf("expected 2 levels for claude, got %d", len(levels))
	}
	// Copilot supports both user and project
	levels = entities.InstructionAppLevels("copilot")
	if len(levels) != 2 {
		t.Fatalf("expected 2 levels for copilot, got %v", levels)
	}
	// Unknown app
	levels = entities.InstructionAppLevels("unknown")
	if levels != nil {
		t.Fatal("expected nil for unknown app")
	}
}

func TestAppPathsForInstruction(t *testing.T) {
	// AppPathsFor should return promptApps when called with KindInstruction
	paths := entities.AppPathsFor(entities.KindInstruction)
	if paths == nil {
		t.Fatal("AppPathsFor(KindInstruction) should not return nil")
	}
	if _, ok := paths["claude"]; !ok {
		t.Fatal("AppPathsFor(KindInstruction) should contain claude")
	}
}

func TestMigrateEntityStorageIdempotent(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	cfgDir := filepath.Join(home, "cfg")
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	legacy := `{"old-prompt":{"kind":"prompt","name":"old-prompt","content":"legacy"}}`
	if err := os.WriteFile(filepath.Join(cfgDir, "prompts.json"), []byte(legacy), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := entities.MigrateEntityStorage(); err != nil {
		t.Fatalf("MigrateEntityStorage: %v", err)
	}
	if err := entities.MigrateEntityStorage(); err != nil {
		t.Fatalf("second MigrateEntityStorage: %v", err)
	}
	data, err := os.ReadFile(filepath.Join(cfgDir, "instructions.json"))
	if err != nil {
		t.Fatalf("read instructions.json: %v", err)
	}
	parsed := map[string]entities.Entity{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("parse instructions.json: %v", err)
	}
	if got := parsed["old-prompt"].Kind; got != entities.KindInstruction {
		t.Fatalf("kind = %q, want %q", got, entities.KindInstruction)
	}
	if _, err := os.Stat(filepath.Join(cfgDir, "prompts.json")); err != nil {
		t.Fatalf("prompts.json should remain: %v", err)
	}
}

func TestInstructionStoreAllMigratesLegacyPromptStorage(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	cfgDir := filepath.Join(home, "cfg")
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	legacy := `{"legacy":{"kind":"prompt","name":"legacy","content":"body"}}`
	if err := os.WriteFile(filepath.Join(cfgDir, "prompts.json"), []byte(legacy), 0o644); err != nil {
		t.Fatal(err)
	}

	items, err := entities.NewStore(entities.KindInstruction).All()
	if err != nil {
		t.Fatalf("All: %v", err)
	}
	if len(items) != 1 || items[0].Name != "legacy" || items[0].Kind != entities.KindInstruction {
		t.Fatalf("items = %+v", items)
	}
}

func TestMigrateEntityStorageNoFileDoesNothing(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	if err := entities.MigrateEntityStorage(); err != nil {
		t.Fatalf("MigrateEntityStorage: %v", err)
	}
}

func TestMigrateEntityStoragePrefersExistingInstructionFile(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	cfgDir := filepath.Join(home, "cfg")
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	existing := `{"existing":{"kind":"instruction","name":"existing"}}`
	if err := os.WriteFile(filepath.Join(cfgDir, "instructions.json"), []byte(existing), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(cfgDir, "prompts.json"), []byte(`{}`), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := entities.MigrateEntityStorage(); err != nil {
		t.Fatalf("MigrateEntityStorage: %v", err)
	}
	data, err := os.ReadFile(filepath.Join(cfgDir, "instructions.json"))
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != existing {
		t.Fatalf("instructions.json was modified: got %q, want %q", data, existing)
	}
}

// pathutilExists is a helper to check file existence
func pathutilExists(path string) bool {
	_, err := os.Stat(path)
	return !errors.Is(err, os.ErrNotExist)
}
