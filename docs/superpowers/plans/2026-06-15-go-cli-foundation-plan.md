# Go CLI Foundation — Implementation Plan

> Spec: `docs/superpowers/specs/2026-06-15-go-cli-foundation-design.md`
> Author: jzhu + Claude
> Date: 2026-06-15

## Phase 0 — Preparation

1. Add new dependencies and tidy modules.
2. Create the bundled assets directory.

```bash
go get github.com/fatih/color@latest
go get github.com/mattn/go-isatty@latest
go mod tidy
mkdir -p internal/camconfig/embed
cp code_assistant_manager/config.yaml internal/camconfig/embed/config.yaml
mkdir -p internal/doctor/embed
cp code_assistant_manager/tools.yaml internal/doctor/embed/tools.yaml
```

## Phase 1 — `internal/pathutil`

Create the shared helpers everyone else uses; no CLI churn.

- `Expand(path) string` — `~` and `~/` expansion using `os.UserHomeDir`.
- `ConfigDir() string` — honors `CAM_CONFIG_DIR`, else `~/.config/code-agent-manager`.
- `Home() string` — wraps `os.UserHomeDir` with fallback to `$HOME`.
- `Exists(path) bool` — `os.Stat` wrapper.
- Tests: table-driven for `Expand` (relative, absolute, `~`, `~/foo`), env override for `ConfigDir`.

## Phase 2 — `internal/ui`

Implement output before anything depending on `Reporter`.

- `Printer` struct, `New(out, err)` factory.
- Methods: `Header`, `Info`, `Pass`, `Warn`, `Fail`.
- Color detection: `isatty.IsTerminal` on `out`, off when `NO_COLOR != ""` or `TERM == "dumb"`.
- Tests: capture into `bytes.Buffer`, assert plain (no-ANSI) output.

## Phase 3 — `internal/envfile`

- `Find(custom, strict) (string, error)`.
- `Load(path) (map[string]string, error)` — stdlib parser.
- `ApplyToProcess(map)` — `os.Setenv` loop.
- Tests:
  - `Find` strict-custom missing → "" + error.
  - `Find` walk-upward to `.git` parent.
  - `Find` falls back to `~/.env` and `~/.config/code-agent-manager/.env`.
  - `Load` parses quoted values, comments, blank lines.
  - `Load` errors on malformed line.

## Phase 4 — `internal/providers`

- Types matching spec §5.1 with JSON tags.
- `Load`, `DefaultPath`, `DiscoverPath`, `IsEnabled`, `Clients`, `ResolveAPIKey`.
- Tests:
  - `Load` happy path with sample providers.json (use `code_assistant_manager/providers.json` text via testdata).
  - `Load` returns error on missing/malformed file.
  - `Clients` splits "claude,codex", strips whitespace, drops empties.
  - `IsEnabled` nil/true/false.
  - `ResolveAPIKey` via injected `env func(string) string`.

## Phase 5 — `internal/camconfig`

- Types matching spec §5.2.
- `Load`, `DefaultPath`, embed bundled config.yaml.
- Tests:
  - `Load` returns parsed user file when present.
  - `Load` falls back to bundled when path missing.
  - Cache directory `~` expansion via `pathutil.Expand`.

## Phase 6 — `internal/editorconfig`

This is the largest unit; build keypath first, then ToolConfig impls.

### 6a — `keypath`

- `Parse`, `Get`, `Set`, `Unset`, `Flatten`, `ParseScalar`.
- Tests: full table — dotted simple, dotted nested, TOML quoted segment, escaped quote, list index flattening, scalar coercion truth tables.

### 6b — `jsonToolConfig`

- `Load`, `LoadAll`, `Set`, `Unset` with JSON I/O.
- Round-trip test: create temp file, set a nested key, reload, assert value present.

### 6c — `tomlToolConfig`

- Same surface, codex only.
- Round-trip test using a quoted profile key.

### 6d — `Registry`

- `DefaultRegistry()` with all 13 entries from spec §5.4 table.
- `Get`, `Names`.
- Tests: registry contains exactly the 13 names; each entry has at least one user path; codex is TOML, others JSON.

## Phase 7 — `internal/doctor`

- `Reporter` interface, `Check` interface, `Result`, `Run`.
- 8 check implementations in `checks.go`.
- Embed `tools.yaml` for `ToolsAvailableCheck`.
- Tests:
  - Fake reporter records calls.
  - `InstallationCheck` with injected version.
  - `ConfigCheck` happy/missing/malformed.
  - `EnvCheck` with `t.TempDir` controlling `HOME`.
  - `EndpointFormatCheck` valid/invalid URLs.
  - `CacheCheck` synthesized files with fixed mtimes.
  - `GeminiAuthCheck` matrix: only `GEMINI_API_KEY`, only Vertex vars, partial Vertex, none.
  - `CopilotAuthCheck` set/unset.
  - `ToolsAvailableCheck` synthesized `PATH` with one available tool and one missing.

## Phase 8 — `internal/cli` refactor

### 8a — Split files

Move existing code without behavior changes:

- `commands.go` → split into `launch.go`, `lifecycle.go`. Keep `knownTools`/`isKnownTool`/`runToolMenu`/`isTerminal`/`titleASCII` in `launch.go` since they're only used there.
- `config.go` → split into `config_cmd.go` (the actual config subcommand wiring) and `management.go` (the generic agent/prompt/skill/plugin placeholder). Move JSON store helpers to `management.go`.
- Delete old `commands.go`/`config.go` if fully drained.

### 8b — `global.go`

- `globalState` extends with `endpoints`, `debug`.
- Persistent flags wired on root: `--config`, `--providers`, `--store`, `--endpoints`, `--debug/-d`.
- `errEndpointsHandled` sentinel.
- PersistentPreRunE: configures logging when `debug`; if `endpoints != ""`, prints via `providers.Load(state.providersPath)`, returns sentinel.

### 8c — `app.go` updates

- `App.Run`: existing error handling, plus sentinel translation:

  ```go
  if err := cmd.Execute(); err != nil {
      if errors.Is(err, errEndpointsHandled) {
          return 0
      }
      fmt.Fprintln(a.stderr, err.Error())
      return 1
  }
  ```

### 8d — `version.go`, `completion.go`

- `version.go`: extract version command and aliases (existing logic).
- `completion.go`: replace hand-rolled output with Cobra generators. Banner `# code-agent-manager <shell> completion` prefix keeps existing test assertions green.

### 8e — `doctor.go`

- Build check list from spec §5.5.
- Wrap `ui.Printer` as `Reporter`.
- **Backwards-compat block**: emit the existing one-line summary at the top:

  ```text
  Providers: <N>
  - <name>: <endpoint>
    Environment: <ENV> set|missing
  ```

  This satisfies `TestDoctorValidatesProvidersConfigAndEnv` without rewriting it.
- Then run the 8 native Go checks below.

### 8f — `config_cmd.go`

- `cam config list` — iterate registry + CAM config files.
- `cam config validate` — load providers.json + config.yaml.
- `cam config show` — `--app`, `--scope`.
- `cam config set` — `--app`, `--scope`; accept `KEY=VALUE` single-arg or `KEY VALUE` two-arg.
- `cam config unset` — `--app`, `--scope`.

### 8g — Test updates

- `TestConfigListShowValidateSetUnset` is updated:
  - `set` and `unset` calls switch to use a temp HOME plus a JSON-backed registered editor (`--app claude`, `--scope user`).
  - The test still asserts on success messages (`Updated`, `Removed`).
  - The existing assertion about `Configuration is valid` for `config validate` and the `repositories` substring for `config show` work against the new behavior because: validate reads `--config` (camconfig); show ALSO supports `--config` for a CAM yaml fallback when `--app` is not provided. To preserve, we keep a two-mode `show`: when `--app` not given AND a `--config` path exists, dump that file's contents (legacy behavior).
- New tests added in `cli/`:
  - `--endpoints` short-circuit prints expected lines and exits 0.
  - `--debug` does not affect output (smoke test).
  - `cam config show --app claude --scope user` round-trips a temp HOME.
  - `cam completion bash` output contains `bash completion` (Cobra banner).

## Phase 9 — Verification

Per CLAUDE.md "find all files with `find` and run them one by one":

```bash
go vet ./...
gofmt -s -l cmd internal | tee /tmp/gofmt-diff && test ! -s /tmp/gofmt-diff
mapfile -t TESTFILES < <(find . -path ./code_assistant_manager -prune -o -name '*_test.go' -print | sort)
declare -A PKGS=()
for f in "${TESTFILES[@]}"; do
  dir=$(dirname "$f")
  PKGS[$dir]=1
done
for d in "${!PKGS[@]}"; do
  go test -count=1 "$d"
done
go test -race -count=1 ./...
```

Then per CLAUDE.md:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed   # only if backup exists
```

## Phase 10 — Wrap-up

Hand control back to the user. No git commit until they approve.

## Build order

1. Phase 0 (deps + bundled assets)
2. Phase 1–7 in parallel-friendly order: `pathutil` → `ui` → `envfile` / `providers` / `camconfig` (independent) → `editorconfig` → `doctor`
3. Phase 8 (cli refactor) after all packages compile and pass tests
4. Phase 9 verification
5. Phase 10 stop

Each phase ends with `go build ./...` + `go test ./<package>` passing before moving on.
