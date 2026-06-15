package cli_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// `cam provider list` on a fresh machine emits a friendly "no providers"
// message and does NOT crash because providers.json is missing.
func TestProviderListEmptyAutoCreatesNothing(t *testing.T) {
	home := isolatedHome(t)
	stdout, stderr, code := execute(t, "provider", "list")
	if code != 0 {
		t.Fatalf("list exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "No providers configured") {
		t.Fatalf("expected friendly empty message, got: %s", stdout)
	}
	// LoadOrInit must not touch disk on its own.
	cfgPath := filepath.Join(home, "cfg", "providers.json")
	if _, err := os.Stat(cfgPath); !os.IsNotExist(err) {
		t.Fatalf("expected providers.json to remain missing, got err=%v", err)
	}
}

// `cam provider init` writes the empty skeleton with 0600 permissions and
// is idempotent on a second call.
func TestProviderInitCreatesEmptyFile(t *testing.T) {
	home := isolatedHome(t)
	cfgPath := filepath.Join(home, "cfg", "providers.json")

	stdout, _, code := execute(t, "provider", "init")
	if code != 0 {
		t.Fatalf("init exit = %d", code)
	}
	if !strings.Contains(stdout, "Created empty providers.json") {
		t.Fatalf("expected 'Created' notice, got: %s", stdout)
	}
	info, err := os.Stat(cfgPath)
	if err != nil {
		t.Fatalf("stat err = %v", err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Fatalf("perm = %o, want 0o600", perm)
	}

	data, _ := os.ReadFile(cfgPath)
	parsed := map[string]any{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("parse err = %v", err)
	}
	if _, ok := parsed["endpoints"]; !ok {
		t.Fatalf("file missing 'endpoints' key: %s", data)
	}

	stdout, _, code = execute(t, "provider", "init")
	if code != 0 {
		t.Fatalf("second init exit = %d", code)
	}
	if !strings.Contains(stdout, "already exists") {
		t.Fatalf("expected idempotent notice, got: %s", stdout)
	}
}

// End-to-end: `cam provider add` on a fresh machine creates providers.json
// AND writes the new endpoint in one go (auto-create on first mutation).
func TestProviderAddOnFreshMachineCreatesFile(t *testing.T) {
	home := isolatedHome(t)
	cfgPath := filepath.Join(home, "cfg", "providers.json")

	stdout, stderr, code := execute(t,
		"provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--api-key-env", "ALPHA_KEY",
		"--client", "claude,codex",
		"--model", "m1,m2",
		"--description", "test provider",
	)
	if code != 0 {
		t.Fatalf("add exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Created") {
		t.Fatalf("expected 'Created' notice on first run, got: %s", stdout)
	}
	if !strings.Contains(stdout, `Added provider "alpha"`) {
		t.Fatalf("expected 'Added provider' notice, got: %s", stdout)
	}

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		t.Fatalf("read err = %v", err)
	}
	var parsed struct {
		Endpoints map[string]map[string]any `json:"endpoints"`
	}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("parse err = %v", err)
	}
	got, ok := parsed.Endpoints["alpha"]
	if !ok {
		t.Fatalf("alpha not present in file: %s", data)
	}
	if got["endpoint"] != "https://alpha.example" {
		t.Fatalf("endpoint = %v", got["endpoint"])
	}
	if got["supported_client"] != "claude,codex" {
		t.Fatalf("supported_client = %v", got["supported_client"])
	}
}

func TestProviderAddRejectsDuplicate(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed add failed")
	}
	_, stderr, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a")
	if code == 0 {
		t.Fatal("expected non-zero exit on duplicate")
	}
	if !strings.Contains(stderr, "already exists") {
		t.Fatalf("stderr missing duplicate notice: %s", stderr)
	}
}

func TestProviderAddRequiresEndpoint(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add", "alpha")
	if code == 0 {
		t.Fatal("expected error when --endpoint missing")
	}
	// In non-TTY, the wizard path returns a terminal-required error.
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}

func TestProviderAddNoArgsNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add")
	if code == 0 {
		t.Fatal("expected non-zero exit when add has no args in non-TTY")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
	if !strings.Contains(stderr, "--endpoint") {
		t.Fatalf("stderr missing flag hint: %s", stderr)
	}
}

func TestProviderAddNameOnlyNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add", "myapi")
	if code == 0 {
		t.Fatal("expected non-zero exit")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}

func TestProviderUpdateNoFlagsNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	_, stderr, code := execute(t, "provider", "update", "alpha")
	if code == 0 {
		t.Fatal("expected non-zero exit when update has no flags in non-TTY")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}

func TestProviderAddWithAllFlagsStillWorks(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t,
		"provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--api-key-env", "ALPHA_KEY",
	)
	if code != 0 {
		t.Fatalf("add exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, `Added provider "alpha"`) {
		t.Fatalf("expected added notice: %s", stdout)
	}
}

func TestProviderUpdateWithFlagsStillWorks(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, stderr, code := execute(t, "provider", "update", "alpha",
		"--description", "updated desc")
	if code != 0 {
		t.Fatalf("update exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, `Updated provider "alpha"`) {
		t.Fatalf("expected updated notice: %s", stdout)
	}
}

// `cam provider list` after add prints a table with the right columns.
func TestProviderListPopulatedTable(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--client", "claude",
	); code != 0 {
		t.Fatal("seed add failed")
	}
	if _, _, code := execute(t, "provider", "add", "beta",
		"--endpoint", "https://beta.example",
		"--client", "codex",
		"--disabled",
	); code != 0 {
		t.Fatal("seed add failed")
	}
	stdout, _, code := execute(t, "provider", "list")
	if code != 0 {
		t.Fatalf("list exit = %d", code)
	}
	for _, want := range []string{"NAME", "ENDPOINT", "CLIENTS", "ENABLED", "alpha", "beta", "yes", "no"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("table missing %q\noutput:\n%s", want, stdout)
		}
	}
}

func TestProviderListJSON(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
	); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, _, code := execute(t, "provider", "list", "--json")
	if code != 0 {
		t.Fatalf("list --json exit = %d", code)
	}
	var got map[string]map[string]any
	if err := json.Unmarshal([]byte(stdout), &got); err != nil {
		t.Fatalf("json parse err = %v; raw: %s", err, stdout)
	}
	if _, ok := got["alpha"]; !ok {
		t.Fatalf("alpha missing in JSON: %s", stdout)
	}
}

func TestProviderListEnabledOnlyFiltersDisabled(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	if _, _, code := execute(t, "provider", "add", "beta", "--endpoint", "https://b", "--disabled"); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, _, code := execute(t, "provider", "list", "--enabled-only")
	if code != 0 {
		t.Fatalf("list exit = %d", code)
	}
	if !strings.Contains(stdout, "alpha") {
		t.Fatal("expected alpha in output")
	}
	if strings.Contains(stdout, "beta") {
		t.Fatalf("expected beta filtered out, got: %s", stdout)
	}
}

// `show` prints masked API key by default; `--reveal-key` reveals it.
func TestProviderShowMasksKeyByDefault(t *testing.T) {
	isolatedHome(t)
	t.Setenv("ALPHA_KEY", "sk-1234567890abcdef")
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--api-key-env", "ALPHA_KEY",
	); code != 0 {
		t.Fatal("seed failed")
	}

	stdout, _, code := execute(t, "provider", "show", "alpha")
	if code != 0 {
		t.Fatalf("show exit = %d", code)
	}
	if strings.Contains(stdout, "sk-1234567890abcdef") {
		t.Fatal("show output leaked raw API key")
	}
	if !strings.Contains(stdout, "sk-1") {
		t.Fatalf("expected masked prefix, got: %s", stdout)
	}

	stdout, _, code = execute(t, "provider", "show", "alpha", "--reveal-key")
	if code != 0 {
		t.Fatalf("show --reveal-key exit = %d", code)
	}
	if !strings.Contains(stdout, "sk-1234567890abcdef") {
		t.Fatalf("expected raw key revealed, got: %s", stdout)
	}
}

func TestProviderShowMissingProvider(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "show", "ghost")
	if code == 0 {
		t.Fatal("expected error on missing provider")
	}
	if !strings.Contains(stderr, "not found") {
		t.Fatalf("stderr missing 'not found': %s", stderr)
	}
}

// Update changes only the fields supplied; others remain untouched.
func TestProviderUpdateSparsePatch(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--api-key-env", "OLD",
		"--description", "v1",
	); code != 0 {
		t.Fatal("seed failed")
	}
	if _, stderr, code := execute(t, "provider", "update", "alpha",
		"--description", "v2",
	); code != 0 {
		t.Fatalf("update exit = %d; stderr=%s", code, stderr)
	}

	stdout, _, code := execute(t, "provider", "show", "alpha")
	if code != 0 {
		t.Fatalf("show exit = %d", code)
	}
	if !strings.Contains(stdout, `"description": "v2"`) {
		t.Fatalf("description not updated: %s", stdout)
	}
	if !strings.Contains(stdout, `"api_key_env": "OLD"`) {
		t.Fatalf("api_key_env clobbered when not specified: %s", stdout)
	}
	if !strings.Contains(stdout, `"endpoint": "https://alpha.example"`) {
		t.Fatalf("endpoint clobbered when not specified: %s", stdout)
	}
}

// `update --client +droid` appends without replacing.
func TestProviderUpdateAddRemoveReplaceClients(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--client", "claude,codex",
	); code != 0 {
		t.Fatal("seed failed")
	}

	if _, _, code := execute(t, "provider", "update", "alpha", "--client", "+droid"); code != 0 {
		t.Fatal("add client failed")
	}
	if _, _, code := execute(t, "provider", "update", "alpha", "--client", "-codex"); code != 0 {
		t.Fatal("remove client failed")
	}

	stdout, _, _ := execute(t, "provider", "show", "alpha")
	if !strings.Contains(stdout, `"supported_client": "claude,droid"`) {
		t.Fatalf("client list wrong: %s", stdout)
	}

	if _, _, code := execute(t, "provider", "update", "alpha", "--client", "=gemini"); code != 0 {
		t.Fatal("replace client failed")
	}
	stdout, _, _ = execute(t, "provider", "show", "alpha")
	if !strings.Contains(stdout, `"supported_client": "gemini"`) {
		t.Fatalf("client list after replace wrong: %s", stdout)
	}
}

func TestProviderUpdateMissingProvider(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "update", "ghost", "--description", "x")
	if code == 0 {
		t.Fatal("expected error on missing provider")
	}
	if !strings.Contains(stderr, "not found") {
		t.Fatalf("stderr missing 'not found': %s", stderr)
	}
}

// `remove --yes` deletes without prompting.
func TestProviderRemoveYes(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, _, code := execute(t, "provider", "remove", "alpha", "--yes")
	if code != 0 {
		t.Fatalf("remove exit = %d", code)
	}
	if !strings.Contains(stdout, `Removed provider "alpha"`) {
		t.Fatalf("missing removed notice: %s", stdout)
	}
	listOut, _, _ := execute(t, "provider", "list")
	if strings.Contains(listOut, "alpha") {
		t.Fatalf("alpha still present: %s", listOut)
	}
}

func TestProviderRemoveMissing(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "remove", "ghost", "--yes")
	if code == 0 {
		t.Fatal("expected error on missing provider")
	}
	if !strings.Contains(stderr, "not found") {
		t.Fatalf("stderr missing 'not found': %s", stderr)
	}
}

func TestProviderRemoveWithoutYesNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	_, stderr, code := execute(t, "provider", "remove", "alpha")
	if code == 0 {
		t.Fatal("expected error when no --yes and stdin is non-tty")
	}
	if !strings.Contains(stderr, "--yes") {
		t.Fatalf("stderr missing --yes hint: %s", stderr)
	}
}

// `enable` / `disable` flip the field and persist.
func TestProviderEnableDisableRoundTrip(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	if _, _, code := execute(t, "provider", "disable", "alpha"); code != 0 {
		t.Fatal("disable failed")
	}
	stdout, _, _ := execute(t, "provider", "show", "alpha")
	if !strings.Contains(stdout, `"enabled": false`) {
		t.Fatalf("expected enabled=false, got: %s", stdout)
	}
	if _, _, code := execute(t, "provider", "enable", "alpha"); code != 0 {
		t.Fatal("enable failed")
	}
	stdout, _, _ = execute(t, "provider", "show", "alpha")
	if !strings.Contains(stdout, `"enabled": true`) {
		t.Fatalf("expected enabled=true, got: %s", stdout)
	}
}

func TestProviderEnableMissing(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "enable", "ghost")
	if code == 0 {
		t.Fatal("expected error")
	}
	if !strings.Contains(stderr, "not found") {
		t.Fatalf("stderr missing 'not found': %s", stderr)
	}
}

// `rename` moves a key; refuses to overwrite an existing one.
func TestProviderRenameHappy(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha", "--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	if _, stderr, code := execute(t, "provider", "rename", "alpha", "beta"); code != 0 {
		t.Fatalf("rename exit = %d; stderr=%s", code, stderr)
	}
	stdout, _, _ := execute(t, "provider", "list")
	if strings.Contains(stdout, "alpha") {
		t.Fatalf("alpha still present: %s", stdout)
	}
	if !strings.Contains(stdout, "beta") {
		t.Fatalf("beta missing: %s", stdout)
	}
}

func TestProviderRenameRejectsOverwrite(t *testing.T) {
	isolatedHome(t)
	for _, n := range []string{"alpha", "beta"} {
		if _, _, code := execute(t, "provider", "add", n, "--endpoint", "https://x"); code != 0 {
			t.Fatalf("seed %s failed", n)
		}
	}
	_, stderr, code := execute(t, "provider", "rename", "alpha", "beta")
	if code == 0 {
		t.Fatal("expected error on overwrite")
	}
	if !strings.Contains(stderr, "already exists") {
		t.Fatalf("stderr missing already exists: %s", stderr)
	}
}

// --use-proxy and --keep-proxy-config persist as booleans.
func TestProviderAddBooleanFlagsPersist(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--use-proxy",
		"--keep-proxy-config",
	); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, _, _ := execute(t, "provider", "show", "alpha")
	if !strings.Contains(stdout, `"use_proxy": true`) {
		t.Fatalf("use_proxy not persisted: %s", stdout)
	}
	if !strings.Contains(stdout, `"keep_proxy_config": true`) {
		t.Fatalf("keep_proxy_config not persisted: %s", stdout)
	}
}

// Make sure the --providers flag override works (writes to non-default path).
func TestProviderRespectsProvidersFlag(t *testing.T) {
	isolatedHome(t)
	dir := t.TempDir()
	custom := filepath.Join(dir, "custom-providers.json")

	if _, _, code := execute(t,
		"--providers", custom,
		"provider", "add", "alpha", "--endpoint", "https://a",
	); code != 0 {
		t.Fatal("add failed")
	}
	if _, err := os.Stat(custom); err != nil {
		t.Fatalf("expected custom file written, err=%v", err)
	}
	stdout, _, _ := execute(t, "--providers", custom, "provider", "list")
	if !strings.Contains(stdout, "alpha") {
		t.Fatalf("alpha not visible via custom path: %s", stdout)
	}
}
