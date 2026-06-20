package cli_test

import (
	"path/filepath"
	"strings"
	"testing"
)

// `cam doctor` always runs to completion (exit 0) and prints both the legacy
// "Providers: N" summary block and the new per-section structured checks.
// We seed providers via the SQLite store and an env var so the summary picks them up.
func TestDoctorPrintsProviderSummaryAndAllSections(t *testing.T) {
	home := isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "test-endpoint", "https://example.com/v1", "claude,codex", "model-a", "CAM_DOCTOR_KEY")
	t.Setenv("CAM_DOCTOR_KEY", "secret")
	_ = home // ensure HOME is honored when doctor walks ~/.env etc

	stdout, stderr, code := execute(t, "--store", storePath, "doctor")
	if code != 0 {
		t.Fatalf("doctor exit = %d; stderr=%s", code, stderr)
	}
	for _, want := range []string{
		"Providers: 1",
		"test-endpoint",
		"Environment: CAM_DOCTOR_KEY set",
		"Installation Check",
		"Configuration Check",
		"Environment File Check",
		"Endpoint Format Check",
		"Cache Check",
		"Gemini / Vertex Authentication Check",
		"GitHub Copilot Authentication Check",
		"Tool Installation Check",
	} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("doctor missing %q\nstdout:\n%s", want, stdout)
		}
	}
}

// --verbose enables the supported-clients line beneath each provider in the
// legacy block.
func TestDoctorVerboseShowsSupportedClients(t *testing.T) {
	isolatedHome(t)
	storePath := filepath.Join(t.TempDir(), "store.db")
	seedProvider(t, storePath, "test", "https://x", "claude,codex", "", "")
	stdout, _, code := execute(t, "--store", storePath, "doctor", "--verbose")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "Supported clients: claude, codex") {
		t.Fatalf("verbose output missing supported clients line:\n%s", stdout)
	}
}

// When no providers are configured, doctor must still run all checks
// — it just notes the store is empty under the Configuration Check section.
func TestDoctorWithMissingProvidersStillRunsChecks(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "doctor")
	if code != 0 {
		t.Fatalf("exit = %d (doctor should always succeed without InstallationCheck failure)", code)
	}
	if !strings.Contains(stdout, "Installation Check") {
		t.Fatalf("missing installation check section:\n%s", stdout)
	}
	if !strings.Contains(stdout, "Providers in store: 0") {
		t.Fatalf("missing zero-provider note:\n%s", stdout)
	}
}

// `cam d` alias works.
func TestDoctorAliasWorks(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "d")
	if code != 0 {
		t.Fatalf("d exit = %d", code)
	}
	if !strings.Contains(stdout, "Installation Check") {
		t.Fatalf("d alias missing checks:\n%s", stdout)
	}
}
