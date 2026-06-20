// Shared test harness for the CLI package.  Per-command tests live in
// cmd_<name>_test.go files; this file only holds the small driver every test
// uses to run the App against a captured stdout/stderr.
package cli_test

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/cli"
)

// execute runs the App once with the given args and returns the captured
// streams + exit code.  Tests share this helper so changes to App.Run flow
// only need to be applied in one place.
func execute(t *testing.T, args ...string) (stdout string, stderr string, code int) {
	t.Helper()
	var out, err bytes.Buffer
	app := cli.New(cli.Options{
		Version: "test-version",
		Stdout:  &out,
		Stderr:  &err,
		Stdin:   &bytes.Buffer{},
	})
	code = app.Run(args)
	return out.String(), err.String(), code
}

// writeTempFile creates a file inside a t.TempDir with the given content and
// returns its absolute path.  Used by `add`-style command tests that need a
// file path for the `-f` flag.
func writeTempFile(t *testing.T, content string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "in")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

// isolatedHome rewires HOME and CAM_CONFIG_DIR to a fresh tempdir so commands
// that write to ~/ touch nothing outside the test.
func isolatedHome(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(dir, "cfg"))
	return dir
}

// seedProvider seeds a single provider into the SQLite store at storePath
// by running `cam provider add` via execute().
func seedProvider(t *testing.T, storePath, name, endpoint, client, models, apiKeyEnv string) {
	t.Helper()
	args := []string{"--store", storePath, "provider", "add", name, "--endpoint", endpoint}
	if client != "" {
		args = append(args, "--client", client)
	}
	if models != "" {
		args = append(args, "--model", models)
	}
	if apiKeyEnv != "" {
		args = append(args, "--api-key-env", apiKeyEnv)
	}
	stdout, stderr, code := execute(t, args...)
	if code != 0 {
		t.Fatalf("seed provider %s: exit=%d stderr=%s stdout=%s", name, code, stderr, stdout)
	}
}
