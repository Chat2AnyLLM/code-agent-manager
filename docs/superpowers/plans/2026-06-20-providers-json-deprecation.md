# providers.json Deprecation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `providers.json` as an active provider storage/input and make SQLite the only provider source of truth.

**Architecture:** `internal/appapi.ProviderAPI` becomes the provider boundary that rejects deprecated JSON paths, deletes the canonical default JSON file, and reads/writes provider records only through `appstate.Store`. Installer and docs stop creating/restoring provider JSON files. Tests prove JSON is not imported, default JSON is deleted, `--providers` is removed, and existing SQLite-backed provider flows still work.

**Tech Stack:** Go, Cobra CLI, SQLite appstate via `modernc.org/sqlite`, Bash installer tests/verification.

---

### Task 1: Make ProviderAPI SQLite-only

**Files:**
- Modify: `internal/appapi/providers.go`
- Modify: `internal/appapi/providers_test.go`

- [ ] **Step 1: Add failing tests for no import and default JSON deletion**

Add tests in `internal/appapi/providers_test.go`:

```go
func TestProviderAPIDoesNotImportProvidersJSON(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	jsonPath := filepath.Join(dir, "providers.json")
	if err := providers.Save(jsonPath, providers.File{Endpoints: map[string]providers.Endpoint{
		"legacy": {Endpoint: "https://legacy.example", Models: []string{"legacy-model"}},
	}}); err != nil {
		t.Fatalf("save providers json: %v", err)
	}
	api := ProviderAPI{DBPath: filepath.Join(dir, "cam.db")}
	listed, err := api.List(ctx)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(listed) != 0 {
		t.Fatalf("providers.json should not be imported, got %+v", listed)
	}
}

func TestProviderAPIInitDeletesDefaultProvidersJSON(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	jsonPath := filepath.Join(dir, "providers.json")
	if err := providers.Save(jsonPath, providers.File{Endpoints: map[string]providers.Endpoint{
		"legacy": {Endpoint: "https://legacy.example"},
	}}); err != nil {
		t.Fatalf("save providers json: %v", err)
	}
	api := ProviderAPI{DBPath: filepath.Join(dir, "cam.db")}
	if _, err := api.Init(ctx); err != nil {
		t.Fatalf("Init: %v", err)
	}
	if _, err := os.Stat(jsonPath); !os.IsNotExist(err) {
		t.Fatalf("providers.json should be deleted, stat err=%v", err)
	}
}

func TestProviderFlagRemoved(t *testing.T) {
	_, stderr, code := execute(t, "--providers", filepath.Join(t.TempDir(), "providers.json"), "provider", "list")
	if code == 0 || !strings.Contains(stderr, "unknown flag: --providers") {
		t.Fatalf("expected unknown --providers flag, code=%d stderr=%s", code, stderr)
	}
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `go test ./internal/appapi -run 'TestProviderAPI(DoesNotImport|InitDeletes|Rejects)' -count=1`

Expected: failure before implementation because current code imports JSON or still exposes `--providers`.

- [ ] **Step 3: Implement SQLite-only ProviderAPI helper**

In `internal/appapi/providers.go`, add:

```go
func (api ProviderAPI) cleanupDefaultProvidersJSON() error {
	path := filepath.Join(pathutil.ConfigDir(), "providers.json")
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove deprecated providers.json %s: %w", path, err)
	}
	return nil
}

func (api ProviderAPI) prepareProviderStore(ctx context.Context) (appstate.Store, error) {
	store := api.store()
	if err := store.Init(ctx); err != nil {
		return appstate.Store{}, err
	}
	if err := api.cleanupDefaultProvidersJSON(); err != nil {
		return appstate.Store{}, err
	}
	return store, nil
}
```

- [ ] **Step 4: Replace ImportProvidersJSON calls**

Update `Init`, `File`, `Show`, and `ResolveModels` to call `prepareProviderStore(ctx)` and remove all `ImportProvidersJSON` calls.

- [ ] **Step 5: Run appapi tests**

Run: `go test ./internal/appapi -count=1`

Expected: PASS.

### Task 2: Remove legacy appstate import behavior

**Files:**
- Modify: `internal/appstate/store.go`
- Modify: `internal/appstate/store_test.go`

- [ ] **Step 1: Replace import test with no-import compatibility test**

Replace `TestImportProvidersJSON` with a test that asserts the method is absent or unused by API paths. If keeping the function for compile compatibility, mark it deprecated no-op and test it does not import.

- [ ] **Step 2: Make ImportProvidersJSON a no-op or remove it**

Preferred: remove `ImportProvidersJSON` and `providerspkgLoad` if no callers remain. If compile callers remain, change it to:

```go
// Deprecated: providers.json is no longer read. This method is a no-op.
func (s Store) ImportProvidersJSON(ctx context.Context, path string) error {
	return nil
}
```

- [ ] **Step 3: Run appstate tests**

Run: `go test ./internal/appstate -count=1`

Expected: PASS.

### Task 3: Deprecate CLI/provider JSON path usage

**Files:**
- Modify: `internal/cli/global.go`
- Modify: `internal/cli/provider_cmd.go`
- Modify: `internal/cli/cmd_provider_test.go`
- Modify: `internal/cli/cmd_config_test.go` if it references providers path behavior

- [ ] **Step 1: Add failing CLI test**

Add to `internal/cli/cmd_provider_test.go`:

```go
func TestProviderFlagIsDeprecated(t *testing.T) {
	path := filepath.Join(t.TempDir(), "providers.json")
	_, stderr, code := execute(t, "--providers", path, "provider", "list")
	if code == 0 {
		t.Fatal("expected --providers to fail")
	}
	if !strings.Contains(stderr, "providers.json is deprecated") {
		t.Fatalf("missing deprecation guidance: %s", stderr)
	}
}
```

- [ ] **Step 2: Update providerAPI path handling**

Remove `resolveProvidersPath` and the `providersPath` field from CLI state. Provider commands should construct `appapi.ProviderAPI{DBPath: state.storePath}` when `--store` is set, or an empty `ProviderAPI{}` for the default SQLite path.

- [ ] **Step 3: Update root flag help**

Remove the root `--providers` flag entirely:

```go
// no --providers flag; providers are stored in SQLite
```

- [ ] **Step 4: Run CLI provider tests**

Run: `go test ./internal/cli -run 'TestProvider|TestEndpoints' -count=1`

Expected: PASS.

### Task 4: Stop installer/docs from creating providers.json

**Files:**
- Modify: `install.sh`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `.specify/memory/constitution.md` if it repeats reinstall restore command

- [ ] **Step 1: Remove install creation logic**

In `install.sh`, delete the block that copies `providers.json` or `providers.json.example` into `$CONFIG_DIR/providers.json`. Leave config.yaml and `.env` creation unchanged.

- [ ] **Step 2: Update docs**

Remove `cp providers.json.example ~/.config/code-agent-manager/providers.json` from README quick start. Replace with a SQLite-backed provider command example such as:

```bash
cam provider add local --endpoint http://localhost:4000/v1 --client claude,codex --model claude-opus-4-8
```

Remove providers.json restore/create instructions from project instructions/docs that are part of the repo.

- [ ] **Step 3: Run shell syntax check**

Run: `bash -n install.sh`

Expected: PASS.

### Task 5: Final verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run Go tests by package using find**

Run:

```bash
find . -path './.claude' -prune -o -name '*_test.go' -printf '%h\n' | sort -u | while read -r dir; do
  go test -timeout 120s "./${dir#./}"
done
```

Expected: every package exits 0.

- [ ] **Step 2: Run frontend tests/build if frontend files changed**

Run:

```bash
npm --prefix frontend run test:run
npm --prefix frontend run build
```

Expected: both exit 0.

- [ ] **Step 3: Run reinstall sequence without providers restore**

Run:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
```

Expected: install exits 0 and does not create `~/.config/code-agent-manager/providers.json`.

- [ ] **Step 4: Verify providers.json is absent after install**

Run:

```bash
test ! -f ~/.config/code-agent-manager/providers.json
```

Expected: exit 0.
