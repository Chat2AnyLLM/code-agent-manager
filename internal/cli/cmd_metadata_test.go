package cli_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/metadata"
)

// seedMetadataDB populates the metadata index directly so CLI search/install
// tests don't depend on live GitHub downloads.
func seedMetadataDB(t *testing.T, dbPath string) {
	t.Helper()
	ctx := context.Background()
	store := metadata.NewStore(dbPath)
	if err := store.Init(ctx); err != nil {
		t.Fatalf("init metadata store: %v", err)
	}
	items := []metadata.Item{
		{Kind: "skill", Name: "superpowers", Description: "Skill bundle", RepoOwner: "obra", RepoName: "superpowers", RepoBranch: "main", InstallKey: "obra/superpowers:superpowers", TargetApps: "claude,codex"},
		{Kind: "agent", Name: "code-reviewer", Description: "Reviews code", RepoOwner: "iannuttall", RepoName: "claude-agents", RepoBranch: "main", InstallKey: "iannuttall/claude-agents:code-reviewer", TargetApps: "claude"},
	}
	for _, it := range items {
		if err := store.UpsertItem(ctx, it); err != nil {
			t.Fatalf("seed upsert: %v", err)
		}
	}
}

func TestMetadataRefreshCommand(t *testing.T) {
	if testing.Short() || os.Getenv("CAM_RUN_LIVE_TESTS") != "1" {
		t.Skip("refresh performs live network downloads; set CAM_RUN_LIVE_TESTS=1 to run")
	}
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	t.Setenv("CAM_DB_PATH", filepath.Join(home, "cam.db"))
	t.Setenv("CAM_CACHE_DIR", filepath.Join(home, "cache"))

	stdout, _, code := execute(t, "metadata", "refresh")
	if code != 0 {
		t.Fatalf("exit %d: %s", code, stdout)
	}
	if !strings.Contains(stdout, "Refreshed metadata") {
		t.Fatalf("unexpected output:\n%s", stdout)
	}
}

func TestMetadataSearchCommand(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	dbPath := filepath.Join(home, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	seedMetadataDB(t, dbPath)

	stdout, _, code := execute(t, "metadata", "search", "superpowers")
	if code != 0 {
		t.Fatalf("exit %d: %s", code, stdout)
	}
	if !strings.Contains(stdout, "superpowers") {
		t.Fatalf("expected 'superpowers' in output:\n%s", stdout)
	}
}

func TestMetadataSearchNoResults(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	t.Setenv("CAM_DB_PATH", filepath.Join(home, "cam.db"))

	stdout, _, code := execute(t, "metadata", "search", "zzz-nonexistent-xyz")
	if code != 0 {
		t.Fatalf("exit %d: %s", code, stdout)
	}
	if !strings.Contains(stdout, "No results") {
		t.Fatalf("expected 'No results' in output:\n%s", stdout)
	}
}

func TestMetadataInstallCommand(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	dbPath := filepath.Join(home, "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	seedMetadataDB(t, dbPath)

	stdout, _, code := execute(t, "metadata", "install", "obra/superpowers:superpowers", "--target", "claude")
	if code != 0 {
		t.Fatalf("exit %d: %s", code, stdout)
	}
	if !strings.Contains(stdout, "Installed") {
		t.Fatalf("unexpected output:\n%s", stdout)
	}
}
