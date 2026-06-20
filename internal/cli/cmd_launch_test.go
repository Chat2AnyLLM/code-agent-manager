package cli_test

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// `cam launch` with no args prints the Bubble Tea menu rendered as plain text
// (no TTY in tests) so users running scripts can see what they would have
// picked interactively.
func TestLaunchWithoutToolShowsBubbleTeaMenu(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "launch")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	for _, want := range []string{"Manage tools", "claude", "Use ↑/↓ or j/k", "Enter to select"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("menu missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

// `cam launch <bin> --dry-run -- args...` prints the resolved env so users can
// confirm what would be exec'd.  The endpoint picker selects the first enabled
// provider that supports the client.
func TestLaunchKnownToolDryRunPrintsResolvedPlan(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "test", "https://example.com", "claude,codex", "model-a", "CAM_LAUNCH_KEY")
	t.Setenv("CAM_LAUNCH_KEY", "secret")

	stdout, stderr, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run", "--", "--print")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	for _, want := range []string{"Tool: claude", "Endpoint: https://example.com", "Model: model-a", "Args: --print"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("dry-run missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

// Unknown binaries are rejected with a clear "Unknown tool" message.
func TestLaunchRejectsUnknownTool(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "launch", "not-a-tool")
	if code == 0 {
		t.Fatalf("exit = 0; stdout=%s", stdout)
	}
	if !strings.Contains(stderr, "Unknown tool") {
		t.Fatalf("stderr missing Unknown tool: %s", stderr)
	}
}

// --endpoint selects a specific named endpoint even when others would also
// match the tool's supported_client.
func TestLaunchExplicitEndpointSelectsByName(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "first", "https://first.example.com", "claude", "a", "")
	seedProvider(t, storePath, "second", "https://second.example.com", "claude", "b", "")
	stdout, _, code := execute(t, "--store", storePath, "launch", "claude", "--endpoint", "second", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "https://second.example.com") {
		t.Fatalf("expected second endpoint, got:\n%s", stdout)
	}
}

// --model overrides the auto-selected model.
func TestLaunchExplicitModelOverridesAuto(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "e", "https://x", "claude", "auto-model,other", "")
	stdout, _, code := execute(t, "--store", storePath, "launch", "claude", "--model", "other", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Model: other") {
		t.Fatalf("expected other model, got:\n%s", stdout)
	}
}

// When no endpoint matches the requested tool, launch errors out instead of
// exec'ing with empty env vars.
func TestLaunchFailsWithoutMatchingEndpoint(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "launch", "claude")
	if code == 0 {
		t.Fatal("expected non-zero exit")
	}
	if !strings.Contains(stderr, "no provider supports tool") {
		t.Fatalf("stderr missing missing-provider message: %s", stderr)
	}
}

// `cam l` alias accepts the same args.
func TestLaunchAliasL(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "e", "https://x", "claude", "m", "")
	stdout, _, code := execute(t, "--store", storePath, "l", "claude", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Tool: claude") {
		t.Fatalf("alias l output unexpected:\n%s", stdout)
	}
}

// --dry-run prints the planned config writes for a tool that has a
// config_target block (claude).
func TestLaunchDryRunPrintsConfigPlan(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "litellm", "https://api.test", "claude", "claude-sonnet-4", "CAM_LAUNCH_DRY_KEY")
	t.Setenv("CAM_LAUNCH_DRY_KEY", "sk-secret-1234")
	stdout, _, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d\nstdout:\n%s", code, stdout)
	}
	if !strings.Contains(stdout, "Config writes (") {
		t.Fatalf("output missing Config writes section:\n%s", stdout)
	}
	if !strings.Contains(stdout, "env.ANTHROPIC_BASE_URL") {
		t.Fatalf("output missing ANTHROPIC_BASE_URL plan line:\n%s", stdout)
	}
	// API key should be masked, not present in cleartext.
	if strings.Contains(stdout, "sk-secret-1234") {
		t.Fatalf("API key leaked in dry-run output:\n%s", stdout)
	}
}

// --dry-run must not write the tool's config file to disk.
func TestLaunchDryRunDoesNotTouchDisk(t *testing.T) {
	home := isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "litellm", "https://api.test", "claude", "claude-sonnet-4", "CAM_LAUNCH_DRY_KEY2")
	t.Setenv("CAM_LAUNCH_DRY_KEY2", "x")
	target := filepath.Join(home, ".claude", "settings.json")
	if _, code, _ := func() (string, int, error) {
		stdout, _, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run")
		return stdout, code, nil
	}(); code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if _, err := os.Stat(target); !os.IsNotExist(err) {
		t.Errorf("dry-run wrote file %s (err = %v)", target, err)
	}
}

// Auto-select reports both endpoint and model on stderr so scripts can
// see which provider/model CAM picked.
func TestLaunchAutoSelectLogsToStderr(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "only", "https://x", "claude", "m1", "")
	_, stderr, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stderr, "[cam] auto-selected endpoint: only") {
		t.Errorf("missing endpoint log in stderr: %s", stderr)
	}
	if !strings.Contains(stderr, "[cam] auto-selected model: m1") {
		t.Errorf("missing model log in stderr: %s", stderr)
	}
}

// In auto mode, when an endpoint has list_models_cmd but no static
// list, CAM runs the discovery command and picks the first model.
func TestLaunchAutoSelectInvokesListModelsCmd(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")

	seedProvider(t, storePath, "dyn", "https://x", "claude", "", "")
	// Update the provider to set list_models_cmd
	cmd := "printf 'one\\ntwo\\n'"
	if runtime.GOOS == "windows" {
		cmd = "Write-Output 'one','two'"
	}
	if _, _, code := execute(t, "--store", storePath, "provider", "update", "dyn", "--list-models-cmd", cmd); code != 0 {
		t.Fatalf("seed list-models-cmd failed")
	}
	stdout, stderr, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Model: one") {
		t.Fatalf("expected first discovered model in dry-run, got:\n%s", stdout)
	}
}

func TestLaunchAutoSelectUsesFetchedModelsBeforeStaticFallback(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")

	seedProvider(t, storePath, "only", "https://x", "claude", "static-a", "")

	stdout, stderr, code := execute(t, "--store", storePath, "launch", "claude", "--dry-run")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Model: static-a") {
		t.Fatalf("expected first static model in dry-run, got:\n%s", stdout)
	}
}

func TestLaunchPinnedEndpointUnsupportedForTool(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "qwenonly", "https://x", "qwen", "m", "")
	_, stderr, code := execute(t, "--store", storePath, "launch", "claude", "--endpoint", "qwenonly")
	if code == 0 {
		t.Fatalf("expected non-zero exit")
	}
	if !strings.Contains(stderr, "does not support tool") {
		t.Fatalf("stderr missing unsupported-client message: %s", stderr)
	}
}
