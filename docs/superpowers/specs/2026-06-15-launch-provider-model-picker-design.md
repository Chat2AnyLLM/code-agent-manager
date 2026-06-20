# `cam launch` Provider/Model Picker — Design

> Status: APPROVED — drafted 2026-06-15
> Author: jzhu + Claude
> Implements: a three-phase interactive picker for `cam launch`, plus
> `config_target` blocks for five additional tools (`crush`, `opencode`,
> `continue`, `gemini-cli`, `goose`).

## 1. Context

`cam launch` today writes the tool's native config file before exec'ing
(see [2026-06-15-launch-config-file-refactor-design.md](./2026-06-15-launch-config-file-refactor-design.md)).
The provider and model the writer uses are resolved silently:

- **Provider** (endpoint): the first enabled provider record in SQLite app state
  whose `supported_client` includes the chosen tool.
- **Model**: `endpoint.Models[0]`.
- Flags `--endpoint` / `--model` override either, but there is no
  interactive picker; the user can only see what was chosen via
  `--dry-run`.

The user's directive: **`cam launch` should let the user pick provider
and model interactively, then write that choice into the tool's config
file.** This is the natural complement to the config-file-write
refactor: today the file gets written automatically; with this design
the user actively chooses *what* gets written.

Separately, five tools currently lack a `config_target` block and
therefore launch without any config write. Online docs research
(2026-06-15) identified which of them are file-writable; this design
adds blocks for the writable ones.

## 2. Goal

After this ships:

1. `cam launch` (no args, TTY) presents a three-phase wizard:
   **tool → provider → model**. Enter advances; Esc steps back to the
   previous phase (no-op at phase 1); q/Ctrl+C aborts without writing.
2. CLI args skip phases the user has already pinned:
   - `cam launch <tool>` → skip phase 1.
   - `cam launch <tool> --endpoint X` → skip phases 1–2.
   - `cam launch <tool> -e X -m Y` → skip all three (today's
     behavior preserved).
3. The provider phase shows only endpoints whose `supported_client`
   includes the chosen tool.
4. The model phase shows `endpoint.Models` when non-empty. When empty,
   the wizard runs `endpoint.ListModelsCmd` with a 15-second timeout,
   caches results to `~/.cache/code-agent-manager/models/<endpointName>.json`
   with TTL = `common.cache_ttl_seconds` (default 86400), and shows the
   resulting list. On timeout/error/empty, the wizard offers a manual
   entry text field; Esc returns to provider selection.
5. Non-TTY launch falls back to today's auto-select (first matching
   endpoint, `endpoint.Models[0]`). Both decisions are printed to
   stderr so they are visible in scripts.
6. `tools/embed/tools.yaml` gains `config_target` blocks for `crush`,
   `opencode`, `continue`, `gemini-cli` (model-only), and `goose`
   (provider+model only). `copilot`, `ampcode`, `cursor-agent`, and
   `pi-coding-agent` are documented as out-of-scope here with the
   reason recorded in the spec (§7.3) — pi is omitted not because it
   isn't writable, but because its config spans two files and array
   semantics that warrant a follow-up.

## 3. Non-goals

- Persistent "last used" state across sessions. The on-disk tool
  config file *becomes* the de facto last-used state because the
  writer overwrites it on every launch.
- Refactoring `tools.WriteConfig`, `tools.ResolveLaunchEnv`,
  `tools.codexPostWrite`, or `internal/editorconfig`. The config-file
  refactor (commit `8a25841`) already did that work.
- Multi-select. Each phase picks exactly one value.
- Async / background model discovery. `list_models_cmd` runs
  synchronously in the wizard with a hard timeout.
- Reworking `cam install`, `cam doctor`, `cam config`, or
  `cam upgrade`.

## 4. Architecture

### 4.1 Package layout

```
internal/
├── cli/
│   ├── launch.go                  # MODIFY: replace tool-only menu + auto-select
│   ├── launch_wizard.go           # NEW: 3-phase bubbletea model
│   ├── launch_wizard_test.go      # NEW
│   ├── tool_menu.go               # REFACTOR: extract pickerStep helper
│   ├── tool_menu_test.go          # extend
│   └── cmd_launch_test.go         # extend
├── providers/
│   ├── providers.go               # unchanged signatures; add SupportingClients helper
│   ├── models.go                  # NEW: ResolveModels (static → list_models_cmd → cache)
│   └── models_test.go             # NEW
└── tools/
    └── embed/tools.yaml           # ADD: config_target for 5 tools
```

No new top-level packages. `internal/tools/configwriter.go`,
`internal/tools/launch.go`, and `internal/tools/codex_postwrite.go`
are not modified.

### 4.2 Layering

- `internal/cli/launch_wizard.go` depends on `internal/providers`
  (endpoint enumeration, `ResolveModels`) and `internal/tools`
  (registry, `LaunchNames`). It does **not** depend on
  `internal/tools/configwriter.go`. The wizard returns concrete
  strings; the existing config-write path handles the rest.
- `internal/providers/models.go` is a new sibling file in the
  providers package. It depends only on `os/exec`, `time`, `os`,
  `path/filepath`, `internal/pathutil`, and the existing `Endpoint`
  type. It does **not** know about tools or the CLI.
- `internal/cli/launch.go` orchestrates: parse flags → call wizard
  (or auto-resolve when non-TTY) → call `tools.WriteConfig` → call
  `tools.Run`.

### 4.3 Data flow

```
cli/launch.go RunE
  │
  ├── registry, err := tools.LoadDefault()
  ├── file, err     := providers.Load(state.providersPath)
  │
  ├── sel := resolveSelections(file, registry, args, flags, isTTY)
  │     // pinned fields: tool/endpoint/model from CLI flags
  │     // if isTTY && any unpinned: launchWizard(pinned, file, registry)
  │     // else: autoResolve(pinned, file, registry) + log to stderr
  │
  ├── apiKey := providers.ResolveAPIKey(sel.endpoint, os.Getenv)
  ├── if dryRun: tools.Plan + printDryRun; return
  ├── tools.WriteConfig(sel.tool, sel.endpoint, sel.epName, sel.model, apiKey)
  ├── launch := tools.ResolveLaunchEnv(sel.tool, sel.endpoint, sel.epName, sel.model)
  └── tools.Run(launch, toolArgs)
```

### 4.4 Wizard state machine

```
                 ┌──────────────┐
       (start)──>│ phasePickTool│──Enter──┐
                 └──────┬───────┘         │
                        ▲                 ▼
                        │ Esc       ┌──────────────────┐
                        │           │  phasePickEP     │──Enter──┐
                        └───────────┤  (filtered)      │         │
                                    └──────┬───────────┘         ▼
                                           ▲              ┌─────────────────┐
                                           │ Esc          │ phasePickModel  │──Enter─→ (done)
                                           │              │ list or manual  │
                                           └──────────────┤ entry on empty  │
                                                          └──────┬──────────┘
                                                                 │ Esc → phasePickEP
```

Phases pinned by CLI flag are skipped on entry. If a flag pins an
unknown value, the wizard returns an error before drawing — same as
today's flag validation.

## 5. `providers.ResolveModels`

```go
package providers

// ResolveModels returns the model list to present for endpoint ep,
// identified by epName. Priority:
//
//  1. ep.Models when non-empty → returned verbatim, no cache I/O.
//  2. ep.ListModelsCmd when non-empty → run with env vars
//     endpoint=ep.Endpoint and api_key=ResolveAPIKey(ep, getenv),
//     proxies stripped unless ep.KeepProxyConfig. 15s timeout.
//     stdout split on \n; empty lines dropped; result cached for
//     cacheTTL.
//  3. neither set → empty slice, nil error.
//
// On step-2 timeout or non-zero exit, returns ([], err). Callers
// (the wizard) treat err as a recoverable signal: offer manual entry
// or step back to provider selection.
//
// cacheDir defaults to pathutil.CacheDir()/models when empty.
func ResolveModels(ep Endpoint, epName string, cacheTTL time.Duration,
    cacheDir string, getenv func(string) string) ([]string, error)
```

Cache layout:

```
~/.cache/code-agent-manager/models/<epName>.json
  { "models": ["claude-sonnet-4", "claude-haiku-4"],
    "fetched_at": "2026-06-15T10:23:04Z" }
```

On a cache hit younger than `cacheTTL`, return the cached models
without spawning the command. On staleness or read error, fall back to
spawning. Successful spawns overwrite the cache file atomically
(write `<file>.tmp.<pid>`, fsync, rename; mode 0600, parent dir 0700).

## 6. Wizard model

`internal/cli/launch_wizard.go` defines:

```go
type launchSelection struct {
    Tool         tools.Tool
    EndpointName string
    Endpoint     providers.Endpoint
    Model        string
}

type wizardInput struct {
    Pinned        launchSelection  // any field empty = needs to be picked
    Providers     providers.File
    Registry      *tools.Registry
    ResolveModels func(ep providers.Endpoint, epName string) ([]string, error)
    // ResolveModels is the bound form of providers.ResolveModels
    // (ttl + cacheDir + getenv captured). Tests inject a fake.
}

// runLaunchWizard runs the bubbletea program and returns the user's
// selection. When the user aborts (q/Ctrl+C), cancelled is true and
// err is nil. When a pinned value is invalid, err is set and the
// program never starts.
func runLaunchWizard(out io.Writer, in wizardInput) (sel launchSelection, cancelled bool, err error)
```

### 6.1 `pickerStep` helper

`tool_menu.go` is refactored to expose `pickerStep`, a small struct
that owns one list of strings + filter + cursor. The wizard composes
three of these. The pre-existing standalone tool-only menu is removed
(the wizard subsumes it).

```go
type pickerStep struct {
    title   string
    items   []string
    cursor  int
    filter  string
}

func (s pickerStep) view() string
func (s *pickerStep) update(msg tea.KeyMsg) (advanced, back, aborted bool)
```

`advanced` is set on Enter (when filtered set non-empty), `back` on
Esc, `aborted` on q/Ctrl+C.

### 6.2 Model phase with manual entry

When the resolved model list is empty (`ResolveModels` returned
`([], err)` or `([], nil)`), the phase enters **manual entry**: a
single-line textinput pre-filled with empty content. Esc returns to
provider phase; Enter accepts whatever was typed (must be
non-empty after `strings.TrimSpace`).

When the list is non-empty, the phase is a normal `pickerStep`. Type
any character to filter; backspace deletes; Enter selects.

### 6.3 Auto-select fallback

When `isTTY(stdin) == false` (piped, scripted, CI), the wizard is not
launched. Instead `autoResolve` runs:

```go
func autoResolve(pinned launchSelection, file providers.File,
    registry *tools.Registry, getenv func(string) string,
    stderr io.Writer) (launchSelection, error)
```

1. If `pinned.Tool.Name == ""`, that is an error: non-interactive
   launch with no tool name is meaningless.
2. If `pinned.EndpointName == ""`, pick the first
   `file.SortedNames()` entry that is enabled and supports
   `pinned.Tool.LaunchCommand()`. Log `[cam] auto-selected endpoint:
   <name>` to stderr. If no endpoint matches, return an error naming
   the tool and pointing at `supported_client`.
3. If `pinned.Model == ""`, pick `pinned.Endpoint.Models[0]` when
   non-empty and log `[cam] auto-selected model: <model>` to stderr.
   When `Models` is empty in auto mode, return an error (no
   `list_models_cmd` fallback — interactive selection is required
   for dynamic discovery by design).

## 7. `tools.yaml` changes

### 7.1 New `config_target` blocks

```yaml
crush:
  config_target:
    path: ~/.config/crush/crush.json
    format: json
    upsert:
      providers.{endpoint_name}.type: "openai-compat"
      providers.{endpoint_name}.base_url: "{endpoint}"
      providers.{endpoint_name}.api_key: "{api_key}"
      providers.{endpoint_name}.models[+].id: "{selected_model}"

opencode:
  config_target:
    path: ~/.config/opencode/opencode.json
    format: json
    upsert:
      provider.{endpoint_name}.npm: "@ai-sdk/openai-compatible"
      provider.{endpoint_name}.name: "{endpoint_name}"
      provider.{endpoint_name}.options.baseURL: "{endpoint}"
      provider.{endpoint_name}.options.apiKey: "{api_key}"
      model: "{endpoint_name}/{selected_model}"

continue:
  config_target:
    path: ~/.continue/config.yaml
    format: yaml
    upsert:
      schema: "v1"
      models[name={endpoint_name}/{selected_model}].name: "{endpoint_name}/{selected_model}"
      models[name={endpoint_name}/{selected_model}].provider: "openai"
      models[name={endpoint_name}/{selected_model}].model: "{selected_model}"
      models[name={endpoint_name}/{selected_model}].apiBase: "{endpoint}"
      models[name={endpoint_name}/{selected_model}].apiKey: "{api_key}"

gemini-cli:
  # endpoint/auth are env-var only per Gemini CLI docs; only model.name
  # is file-configurable, so this block writes the model only.
  config_target:
    path: ~/.gemini/settings.json
    format: json
    upsert:
      model.name: "{selected_model}"

goose:
  # GOOSE_PROVIDER and GOOSE_MODEL are writable in config.yaml; custom
  # base_url and api_key are env-var only per Goose docs.
  config_target:
    path: ~/.config/goose/config.yaml
    format: yaml
    upsert:
      GOOSE_PROVIDER: "{endpoint_name}"
      GOOSE_MODEL: "{selected_model}"
```

### 7.2 Tools left without `config_target`

| Tool | Why no `config_target` |
|------|--------------------------|
| copilot-api | No file-configurable endpoint/model. Auth via `GH_TOKEN`/`GITHUB_TOKEN`; model is the runtime `/model` command. |
| ampcode | No custom endpoint configurable. `AMP_API_KEY` env-var only; modes (`smart`/`rush`) are runtime. |
| cursor-agent | No file-configurable endpoint/model. `CURSOR_API_KEY` env + `--endpoint`/`--model` flags only. |
| pi-coding-agent | Two-file write (settings.json + models.json) + array semantics that warrant a follow-up. Deferred. |

These four still launch via `cam launch`; the wizard still picks
their provider and model (provider for filtering; model is informational
since their CLIs ignore it). No on-disk write happens for them — the
writer is a no-op when `ConfigTarget == nil`.

## 8. `launch.go` changes

```go
// internal/cli/launch.go (sketch)

selections, err := resolveSelections(
    file, registry, args, endpointName, modelName,
    cmd.OutOrStdout(), cmd.ErrOrStderr(),
)
if err != nil {
    return err
}
if selections.cancelled {
    return nil
}
tool := selections.Tool
endpoint := selections.Endpoint
epName := selections.EndpointName
model := selections.Model

apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)

if dryRun { … }                                       // unchanged

if _, werr := tools.WriteConfig(tool, endpoint, epName, model, apiKey); werr != nil {
    return fmt.Errorf("launch: write %s config: %w", tool.Name, werr)
}
launch := tools.ResolveLaunchEnv(tool, endpoint, epName, model)
code, err := tools.Run(launch, toolArgs)
```

`resolveEndpoint` and the standalone `runToolMenu` from today are
deleted; the wizard subsumes both.

## 9. Testing

### 9.1 `internal/providers/models_test.go`

| Test | Asserts |
|---|---|
| `TestResolveModels_StaticList`             | Non-empty `Models` returned verbatim; no exec, no cache I/O. |
| `TestResolveModels_DynamicCacheHit`        | Fresh cache file returned without exec. |
| `TestResolveModels_DynamicCacheMiss`       | Exec runs, cache file written, models parsed from stdout. |
| `TestResolveModels_DynamicStale`           | Stale cache → re-exec, cache overwritten. |
| `TestResolveModels_Timeout`                | Command that sleeps past timeout returns err containing "timeout". |
| `TestResolveModels_NonZeroExit`            | err contains exit code; no cache write. |
| `TestResolveModels_EmptyStdout`            | err `errEmptyModelList`; no cache write. |
| `TestResolveModels_NeitherStaticNorCmd`    | Returns `([], nil)`. |
| `TestResolveModels_StripsProxies`          | When `KeepProxyConfig=false`, env passed to cmd has no `http_proxy`/`HTTPS_PROXY`/etc. |
| `TestResolveModels_KeepsProxies`           | When `KeepProxyConfig=true`, proxies passed through. |

### 9.2 `internal/cli/launch_wizard_test.go`

| Test | Asserts |
|---|---|
| `TestWizard_AllUnpinned_HappyPath`         | Pick tool → endpoint → model; selection returned. |
| `TestWizard_PinnedTool_SkipsPhase1`        | Phase 1 not shown; wizard starts at endpoint. |
| `TestWizard_PinnedToolAndEndpoint`         | Starts at model phase. |
| `TestWizard_AllPinned_NoTUI`               | `runLaunchWizard` returns immediately without starting bubbletea. |
| `TestWizard_PinnedInvalidTool`             | err `unknown tool: foo`; no TUI. |
| `TestWizard_PinnedUnsupportedEndpoint`     | err mentions endpoint and tool. |
| `TestWizard_EndpointFiltersByClient`       | Only endpoints whose `supported_client` includes the chosen tool's CLI command are listed. |
| `TestWizard_NoMatchingEndpoint`            | err with hint pointing at `supported_client`. |
| `TestWizard_ModelListEmpty_ManualEntry`    | `ResolveModels` returns `[]` → manual entry text input shown; typed value returned. |
| `TestWizard_ModelListEmpty_ManualEntryEsc` | Esc from manual entry returns to endpoint phase. |
| `TestWizard_EscFromPhase1_NoOp`            | Esc at tool phase keeps the wizard there. |
| `TestWizard_QuitAtAnyPhase`                | q/Ctrl+C at any phase returns cancelled=true. |

### 9.3 `internal/cli/cmd_launch_test.go` (extend)

| Test | Asserts |
|---|---|
| `TestLaunch_NonTTY_AutoSelect`             | No TTY, no flags → picks first matching endpoint + Models[0], logs both to stderr, then launches stub. |
| `TestLaunch_NonTTY_NoTool_Errors`          | No TTY, no positional tool, no flags → returns error. |
| `TestLaunch_PinnedFlagsLaunchImmediately`  | `cam launch claude -e X -m Y` does not start TUI; existing behavior preserved. |
| `TestLaunch_DryRunStillWorks`              | `--dry-run` path is unchanged. |

Tests for the existing config-write golden table
(`configwriter_per_tool_test.go`) are extended by 5 new sub-tests
covering `crush`, `opencode`, `continue`, `gemini-cli`, `goose`.

### 9.4 Existing tests touched

- `internal/cli/tool_menu_test.go` — adapt to refactored `pickerStep`.
- `internal/cli/cmd_launch_test.go` — remove the test that asserts the
  old tool-only menu behavior; replace with the new wizard tests
  above.
- `internal/cli/cmd_doctor_test.go` and `internal/providers/providers_test.go`
  — unchanged.

## 10. Migration & rollback

- **Migration.** None. Existing `cam launch <tool>` invocations
  continue to work; the only behavior change is the addition of the
  TUI wizard when called without `-e`/`-m`. Existing scripts that
  rely on auto-select get an extra stderr log line (`[cam]
  auto-selected …`) but no functional change.
- **CHANGELOG.** New entry: "`cam launch` now prompts for provider and
  model when stdin is a TTY and the flags are not set. Non-TTY
  behavior is unchanged. Five additional tools (crush, opencode,
  continue, gemini-cli, goose) now write their native config files on
  launch."
- **Rollback.** Revert the commit. The new tools' config files on
  disk are harmless leftovers — they were going to be written
  eventually anyway.

## 11. Open issues (none)

All decisions captured. The `pi-coding-agent` two-file split is
deferred to a follow-up spec; the four explicitly-unwritable tools
(copilot, ampcode, cursor-agent, plus pi's deferral) are documented
in §7.2.
