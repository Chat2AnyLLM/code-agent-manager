package cli_test

import (
	"os"
	"path/filepath"
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"test":{"endpoint":"https://example.com","api_key_env":"CAM_LAUNCH_KEY","list_of_models":["model-a"],"supported_client":"claude,codex"}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_LAUNCH_KEY", "secret")

	stdout, stderr, code := execute(t, "--providers", providersFile, "launch", "claude", "--dry-run", "--", "--print")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{
		"first": {"endpoint":"https://first.example.com","supported_client":"claude","list_of_models":["a"]},
		"second":{"endpoint":"https://second.example.com","supported_client":"claude","list_of_models":["b"]}
	}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--providers", providersFile, "launch", "claude", "--endpoint", "second", "--dry-run")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"e":{"endpoint":"https://x","supported_client":"claude","list_of_models":["auto-model","other"]}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--providers", providersFile, "launch", "claude", "--model", "other", "--dry-run")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	if err := os.WriteFile(providersFile, []byte(`{"endpoints":{}}`), 0o600); err != nil {
		t.Fatal(err)
	}
	_, stderr, code := execute(t, "--providers", providersFile, "launch", "claude")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	if err := os.WriteFile(providersFile, []byte(`{"endpoints":{"e":{"endpoint":"https://x","supported_client":"claude","list_of_models":["m"]}}}`), 0o600); err != nil {
		t.Fatal(err)
	}
	stdout, _, code := execute(t, "--providers", providersFile, "l", "claude", "--dry-run")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"litellm":{"endpoint":"https://api.test","api_key_env":"CAM_LAUNCH_DRY_KEY","supported_client":"claude","list_of_models":["claude-sonnet-4"]}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_LAUNCH_DRY_KEY", "sk-secret-1234")
	stdout, _, code := execute(t, "--providers", providersFile, "launch", "claude", "--dry-run")
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
	providersFile := filepath.Join(t.TempDir(), "providers.json")
	payload := `{"endpoints":{"litellm":{"endpoint":"https://api.test","api_key_env":"CAM_LAUNCH_DRY_KEY2","supported_client":"claude","list_of_models":["claude-sonnet-4"]}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_LAUNCH_DRY_KEY2", "x")
	target := filepath.Join(home, ".claude", "settings.json")
	if _, code, _ := func() (string, int, error) {
		stdout, _, code := execute(t, "--providers", providersFile, "launch", "claude", "--dry-run")
		return stdout, code, nil
	}(); code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if _, err := os.Stat(target); !os.IsNotExist(err) {
		t.Errorf("dry-run wrote file %s (err = %v)", target, err)
	}
}
