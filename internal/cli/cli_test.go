package cli_test

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/cli"
)

func execute(t *testing.T, args ...string) (stdout string, stderr string, code int) {
	t.Helper()
	var out, err bytes.Buffer
	app := cli.New(cli.Options{
		Version: "test-version",
		Stdout:  &out,
		Stderr:  &err,
	})
	code = app.Run(args)
	return out.String(), err.String(), code
}

func TestRootHelpShowsCommandSurfaceAndAliases(t *testing.T) {
	stdout, stderr, code := execute(t, "--help")
	if code != 0 {
		t.Fatalf("exit code = %d, want 0; stderr=%s", code, stderr)
	}

	for _, want := range []string{
		"Code Assistant Manager",
		"launch", "l",
		"doctor", "d",
		"agent", "ag",
		"prompt", "p",
		"skill", "s",
		"plugin", "pl",
		"mcp", "m",
		"upgrade", "u",
		"install", "i",
		"uninstall", "un",
		"config", "cf",
		"completion", "comp", "c",
		"version", "v",
	} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("root help missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

func TestVersionCommandAndAlias(t *testing.T) {
	for _, args := range [][]string{{"version"}, {"v"}, {"--version"}} {
		stdout, stderr, code := execute(t, args...)
		if code != 0 {
			t.Fatalf("%v exit code = %d, want 0; stderr=%s", args, code, stderr)
		}
		if strings.TrimSpace(stdout) != "test-version" {
			t.Fatalf("%v stdout = %q, want test-version", args, stdout)
		}
	}
}

func TestCompletionCommandSupportsAliasesAndShells(t *testing.T) {
	for _, tc := range []struct {
		name string
		args []string
		want string
	}{
		{name: "bash", args: []string{"completion", "bash"}, want: "bash completion"},
		{name: "zsh alias", args: []string{"comp", "zsh"}, want: "zsh completion"},
		{name: "fish short alias", args: []string{"c", "fish"}, want: "fish completion"},
		{name: "powershell", args: []string{"completion", "powershell"}, want: "powershell completion"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			stdout, stderr, code := execute(t, tc.args...)
			if code != 0 {
				t.Fatalf("exit code = %d, want 0; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, tc.want) {
				t.Fatalf("stdout missing %q\nstdout:\n%s", tc.want, stdout)
			}
		})
	}
}

func TestCompletionRejectsUnsupportedShell(t *testing.T) {
	stdout, stderr, code := execute(t, "completion", "nushell")
	if code == 0 {
		t.Fatalf("exit code = 0, want non-zero; stdout=%s", stdout)
	}
	if !strings.Contains(stderr, "Unsupported shell") {
		t.Fatalf("stderr missing unsupported shell message: %s", stderr)
	}
}

func TestCommandAliasesShowHelp(t *testing.T) {
	for _, command := range []string{"l", "d", "ag", "p", "s", "pl", "m", "u", "i", "un", "cf"} {
		t.Run(command, func(t *testing.T) {
			stdout, stderr, code := execute(t, command, "--help")
			if code != 0 {
				t.Fatalf("exit code = %d, want 0; stderr=%s", code, stderr)
			}
			if strings.TrimSpace(stdout) == "" {
				t.Fatalf("expected help output for %s", command)
			}
		})
	}
}

func TestConfigListShowValidateSetUnset(t *testing.T) {
	dir := t.TempDir()
	configFile := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(configFile, []byte("repositories:\n  skills:\n    - local\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	stdout, stderr, code := execute(t, "--config", configFile, "config", "validate")
	if code != 0 {
		t.Fatalf("validate exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Configuration is valid") {
		t.Fatalf("validate output missing success: %s", stdout)
	}

	stdout, stderr, code = execute(t, "--config", configFile, "config", "show")
	if code != 0 {
		t.Fatalf("show exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "repositories") {
		t.Fatalf("show output missing config content: %s", stdout)
	}

	stdout, stderr, code = execute(t, "--config", configFile, "config", "set", "repositories.cache_ttl_seconds=60")
	if code != 0 {
		t.Fatalf("set exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Updated") {
		t.Fatalf("set output missing update message: %s", stdout)
	}

	stdout, stderr, code = execute(t, "--config", configFile, "config", "unset", "repositories.cache_ttl_seconds")
	if code != 0 {
		t.Fatalf("unset exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Removed") {
		t.Fatalf("unset output missing remove message: %s", stdout)
	}

	stdout, stderr, code = execute(t, "config", "list")
	if code != 0 {
		t.Fatalf("list exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, ".config/code-agent-manager/providers.json") {
		t.Fatalf("list output missing providers path: %s", stdout)
	}
}

func TestConfigListHonorsCAMConfigDir(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)

	stdout, stderr, code := execute(t, "config", "list")
	if code != 0 {
		t.Fatalf("list exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, filepath.Join(dir, "providers.json")) {
		t.Fatalf("list output missing CAM_CONFIG_DIR providers path: %s", stdout)
	}
	if !strings.Contains(stdout, filepath.Join(dir, "config.yaml")) {
		t.Fatalf("list output missing CAM_CONFIG_DIR config path: %s", stdout)
	}
}

func TestDoctorValidatesProvidersConfigAndEnv(t *testing.T) {
	dir := t.TempDir()
	providersFile := filepath.Join(dir, "providers.json")
	payload := map[string]any{
		"common": map[string]any{"cache_ttl_seconds": 60},
		"endpoints": map[string]any{
			"test-endpoint": map[string]any{
				"endpoint":         "https://example.com/v1",
				"api_key_env":      "CAM_TEST_API_KEY",
				"list_of_models":   []string{"model-a"},
				"supported_client": "claude,codex",
			},
		},
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(providersFile, data, 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_TEST_API_KEY", "secret")

	stdout, stderr, code := execute(t, "--providers", providersFile, "doctor")
	if code != 0 {
		t.Fatalf("doctor exit code = %d, want 0; stderr=%s", code, stderr)
	}
	for _, want := range []string{"Providers: 1", "test-endpoint", "Environment: CAM_TEST_API_KEY set"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("doctor output missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

func TestLaunchKnownToolPrintsResolvedEnvironment(t *testing.T) {
	dir := t.TempDir()
	providersFile := filepath.Join(dir, "providers.json")
	payload := `{"endpoints":{"test":{"endpoint":"https://example.com","api_key_env":"CAM_TEST_KEY","list_of_models":["model-a"],"supported_client":"claude,codex"}}}`
	if err := os.WriteFile(providersFile, []byte(payload), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CAM_TEST_KEY", "secret")

	stdout, stderr, code := execute(t, "--providers", providersFile, "launch", "claude", "--dry-run", "--", "--print")
	if code != 0 {
		t.Fatalf("launch exit code = %d, want 0; stderr=%s", code, stderr)
	}
	for _, want := range []string{"Tool: claude", "Endpoint: https://example.com", "Model: model-a", "Args: --print"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("launch output missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

func TestLaunchRejectsUnknownTool(t *testing.T) {
	stdout, stderr, code := execute(t, "launch", "not-a-tool")
	if code == 0 {
		t.Fatalf("exit code = 0, want non-zero; stdout=%s", stdout)
	}
	if !strings.Contains(stderr, "Unknown tool") {
		t.Fatalf("stderr missing unknown tool: %s", stderr)
	}
}

func TestManagementCommandsHaveWorkingListInstallRemoveFlow(t *testing.T) {
	dir := t.TempDir()
	for _, group := range []string{"agent", "prompt", "skill", "plugin"} {
		t.Run(group, func(t *testing.T) {
			store := filepath.Join(dir, group+"s.json")
			stdout, stderr, code := execute(t, "--store", store, group, "list")
			if code != 0 {
				t.Fatalf("list exit code = %d, want 0; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, "No "+group+"s installed") {
				t.Fatalf("empty list output unexpected: %s", stdout)
			}

			stdout, stderr, code = execute(t, "--store", store, group, "install", "example")
			if code != 0 {
				t.Fatalf("install exit code = %d, want 0; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, "Installed example") {
				t.Fatalf("install output unexpected: %s", stdout)
			}

			stdout, stderr, code = execute(t, "--store", store, group, "list")
			if code != 0 || !strings.Contains(stdout, "example") {
				t.Fatalf("list after install code=%d stdout=%s stderr=%s", code, stdout, stderr)
			}

			stdout, stderr, code = execute(t, "--store", store, group, "remove", "example")
			if code != 0 || !strings.Contains(stdout, "Removed example") {
				t.Fatalf("remove code=%d stdout=%s stderr=%s", code, stdout, stderr)
			}
		})
	}
}

func TestMCPServerAddListRemoveFlow(t *testing.T) {
	store := filepath.Join(t.TempDir(), "mcp.json")
	stdout, stderr, code := execute(t, "--store", store, "mcp", "add", "context7", "--command", "npx", "--arg", "-y", "--arg", "@upstash/context7-mcp")
	if code != 0 {
		t.Fatalf("add exit code = %d, want 0; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Added context7") {
		t.Fatalf("add output unexpected: %s", stdout)
	}

	stdout, stderr, code = execute(t, "--store", store, "mcp", "list")
	if code != 0 || !strings.Contains(stdout, "context7") || !strings.Contains(stdout, "npx") {
		t.Fatalf("list code=%d stdout=%s stderr=%s", code, stdout, stderr)
	}

	stdout, stderr, code = execute(t, "--store", store, "mcp", "remove", "context7")
	if code != 0 || !strings.Contains(stdout, "Removed context7") {
		t.Fatalf("remove code=%d stdout=%s stderr=%s", code, stdout, stderr)
	}
}

func TestUpgradeInstallUninstallDryRun(t *testing.T) {
	for _, tc := range []struct {
		args []string
		want string
	}{
		{args: []string{"upgrade", "claude", "--dry-run"}, want: "Would upgrade claude"},
		{args: []string{"u", "all", "--dry-run"}, want: "Would upgrade all"},
		{args: []string{"install", "codex", "--dry-run"}, want: "Would install codex"},
		{args: []string{"i", "all", "--dry-run"}, want: "Would install all"},
		{args: []string{"uninstall", "gemini", "--dry-run"}, want: "Would uninstall gemini"},
		{args: []string{"un", "all", "--dry-run"}, want: "Would uninstall all"},
	} {
		t.Run(strings.Join(tc.args, " "), func(t *testing.T) {
			stdout, stderr, code := execute(t, tc.args...)
			if code != 0 {
				t.Fatalf("exit code = %d, want 0; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, tc.want) {
				t.Fatalf("stdout missing %q\nstdout:%s", tc.want, stdout)
			}
		})
	}
}
