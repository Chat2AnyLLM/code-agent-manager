package cli_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// `cam config list` lists the canonical CAM file paths plus each editor's
// per-app configs.  `CAM_CONFIG_DIR` must override the default so isolated
// tests can run without touching the user's real config.
func TestConfigListHonorsCAMConfigDir(t *testing.T) {
	dir := isolatedHome(t)
	t.Setenv("CAM_CONFIG_DIR", dir) // override default cfg subdir
	stdout, stderr, code := execute(t, "config", "list")
	if code != 0 {
		t.Fatalf("list exit = %d; stderr=%s", code, stderr)
	}
	for _, want := range []string{
		filepath.Join(dir, "cam.db"),
		filepath.Join(dir, "config.yaml"),
		"Editor configurations:",
	} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("list output missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

// `cam config validate` (with --config) loads the file and reports success.
func TestConfigValidateAcceptsValidYAML(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(cfg, []byte("repositories:\n  skills:\n    - local\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--config", cfg, "config", "validate")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Configuration is valid") {
		t.Fatalf("output missing success: %s", stdout)
	}
}

// Legacy CAM-config mode: `--config <file> config show` dumps the file as-is.
func TestConfigShowLegacyDumpsFile(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "config.yaml")
	content := "repositories:\n  skills:\n    - local\n"
	if err := os.WriteFile(cfg, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--config", cfg, "config", "show")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "repositories") {
		t.Fatalf("show output missing config text: %s", stdout)
	}
}

// Editor mode: `cam config show --app claude` lists keys from the editor's
// JSON config under an isolated HOME.
func TestConfigShowEditorModeFlattensKeys(t *testing.T) {
	home := isolatedHome(t)
	payload := map[string]any{
		"feature": map[string]any{"enabled": true, "threshold": 7},
	}
	raw, _ := json.MarshalIndent(payload, "", "  ")
	if err := os.WriteFile(filepath.Join(home, ".claude.json"), raw, 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, stderr, code := execute(t, "config", "show", "--app", "claude")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "claude.feature.enabled = true") {
		t.Fatalf("expected flattened key, got:\n%s", stdout)
	}
	if !strings.Contains(stdout, "claude.feature.threshold = 7") {
		t.Fatalf("expected int key, got:\n%s", stdout)
	}
}

// Legacy KEY=VALUE form against --config writes to that file.
func TestConfigSetLegacyKeyValueUpdatesFile(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(cfg, []byte("repositories:\n  skills: []\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--config", cfg, "config", "set", "repositories.cache_ttl_seconds=60")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Updated") {
		t.Fatalf("missing Updated: %s", stdout)
	}
	data, _ := os.ReadFile(cfg)
	if !strings.Contains(string(data), "cache_ttl_seconds: 60") {
		t.Fatalf("file did not get new key:\n%s", data)
	}
}

// Editor mode `set` round-trips through ParseScalar so booleans/ints persist
// as typed values.
func TestConfigSetEditorModePersistsTypedScalar(t *testing.T) {
	home := isolatedHome(t)
	_, _, code := execute(t, "config", "set", "--app", "claude", "feature.enabled", "true")
	if code != 0 {
		t.Fatalf("set exit = %d", code)
	}
	data, _ := os.ReadFile(filepath.Join(home, ".claude.json"))
	var got map[string]any
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatal(err)
	}
	feature, _ := got["feature"].(map[string]any)
	if feature["enabled"] != true {
		t.Fatalf("enabled value = %v", feature["enabled"])
	}
}

// `cam config unset` against a known editor key removes it; against a missing
// key it exits 0 with a "not found" notice (does not error).
func TestConfigUnsetEditorMode(t *testing.T) {
	home := isolatedHome(t)
	if _, _, code := execute(t, "config", "set", "--app", "claude", "foo.bar", "baz"); code != 0 {
		t.Fatalf("seed set exit = %d", code)
	}
	stdout, _, code := execute(t, "config", "unset", "--app", "claude", "foo.bar")
	if code != 0 {
		t.Fatalf("unset exit = %d", code)
	}
	if !strings.Contains(stdout, "Unset foo.bar") {
		t.Fatalf("missing unset confirmation: %s", stdout)
	}
	data, _ := os.ReadFile(filepath.Join(home, ".claude.json"))
	if strings.Contains(string(data), "\"bar\"") {
		t.Fatalf("file still has 'bar' leaf:\n%s", data)
	}

	// second unset should be a no-op success.
	stdout, _, code = execute(t, "config", "unset", "--app", "claude", "foo.bar")
	if code != 0 {
		t.Fatalf("second unset exit = %d", code)
	}
	if !strings.Contains(stdout, "Key not found") {
		t.Fatalf("expected Key not found: %s", stdout)
	}
}

// Unknown --app value errors out instead of silently writing to the wrong file.
func TestConfigSetRejectsUnknownApp(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "config", "set", "--app", "ghostly", "key", "value")
	if code == 0 {
		t.Fatal("expected non-zero exit on unknown --app")
	}
	if !strings.Contains(stderr, "Unknown app") {
		t.Fatalf("stderr missing unknown app: %s", stderr)
	}
}
