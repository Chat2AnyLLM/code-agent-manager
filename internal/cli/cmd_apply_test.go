package cli_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// `cam apply <tool> -e <ep> -m <model>` writes the provider's config into the
// agent's native config file (~/.claude/settings.json) WITHOUT launching it.
// This is the cc-switch "switch" operation. HOME is isolated so the write
// lands in a temp dir and never touches the developer's real config.
func TestApplyWritesConfigWithoutLaunching(t *testing.T) {
	home := isolatedHome(t)
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"litellm":{"endpoint":"https://api.test","api_key_env":"CAM_APPLY_KEY","supported_client":"claude","list_of_models":["claude-sonnet-4"]}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_APPLY_KEY", "sk-secret-1234")

	stdout, stderr, code := execute(t, "--providers", providersFile, "apply", "claude", "--endpoint", "litellm", "--model", "claude-sonnet-4")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}

	// Reports what it did. The tool's registry name is "claude-code"; "claude"
	// is its CLI command.
	for _, want := range []string{"Applied claude-code", "provider: litellm", "model: claude-sonnet-4"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("output missing %q\nstdout:\n%s", want, stdout)
		}
	}

	// Actually wrote the config file with the resolved values.
	target := filepath.Join(home, ".claude", "settings.json")
	data, err := os.ReadFile(target)
	if err != nil {
		t.Fatalf("settings.json not written: %v", err)
	}
	body := string(data)
	for _, want := range []string{"ANTHROPIC_BASE_URL", "https://api.test", "claude-sonnet-4"} {
		if !strings.Contains(body, want) {
			t.Errorf("settings.json missing %q\n%s", want, body)
		}
	}
	// The cleartext API key must be written (it is a real config write, not a
	// dry-run), but it must never appear in stdout/stderr.
	if strings.Contains(stdout+stderr, "sk-secret-1234") {
		t.Errorf("API key leaked in apply output:\n%s", stdout+stderr)
	}
}

// `cam apply` rejects unknown tools with the same message as `cam launch`.
func TestApplyRejectsUnknownTool(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "apply", "not-a-tool")
	if code == 0 {
		t.Fatal("expected non-zero exit")
	}
	if !strings.Contains(stderr, "Unknown tool") {
		t.Fatalf("stderr missing Unknown tool: %s", stderr)
	}
}

// `cam ap` alias accepts the same args.
func TestApplyAliasAp(t *testing.T) {
	home := isolatedHome(t)
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"e":{"endpoint":"https://x","supported_client":"claude","list_of_models":["m"]}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--providers", providersFile, "ap", "claude")
	if code != 0 {
		t.Fatal("expected zero exit")
	}
	if !strings.Contains(stdout, "Applied claude-code") {
		t.Fatalf("alias ap output unexpected:\n%s", stdout)
	}
	// And the file really was written.
	if _, err := os.Stat(filepath.Join(home, ".claude", "settings.json")); err != nil {
		t.Errorf("settings.json not written via alias: %v", err)
	}
}
