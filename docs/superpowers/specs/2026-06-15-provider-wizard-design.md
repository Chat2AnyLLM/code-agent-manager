# Provider Wizard — Interactive Add/Update for `cam provider`

**Date:** 2026-06-15
**Status:** Draft

## Summary

Add a guided Bubble Tea wizard to `cam provider add` and `cam provider update`
so that running either command without flags launches a step-by-step interactive
TUI. Flag-based usage remains fully backward compatible. Non-TTY contexts error
with a helpful message instead of hanging.

## Motivation

Today every provider field must be specified via CLI flags. For new users or
infrequent edits, remembering `--endpoint`, `--api-key-env`, `--client`, etc.
is friction. The launch command already has a polished Bubble Tea wizard; the
provider command should match that quality.

## Design

### Trigger Behavior

**`cam provider add`:**

| Invocation | Behavior |
|---|---|
| `cam provider add myapi --endpoint URL ...` | Flag-only (today's path, unchanged) |
| `cam provider add myapi` (no `--endpoint`) | TTY: wizard from step 2 (name pre-set). Non-TTY: error |
| `cam provider add` (no args) | TTY: wizard from step 1. Non-TTY: error |

**`cam provider update NAME`:**

| Invocation | Behavior |
|---|---|
| `cam provider update myapi --endpoint URL` | Flag-only (today's path, unchanged) |
| `cam provider update myapi` (no flags changed) | TTY: wizard, all fields pre-populated. Non-TTY: error |

The name argument is still required for `update` — you must specify which
provider to edit.

**All other subcommands** (`list`, `show`, `remove`, `enable`, `disable`,
`rename`, `init`) are unchanged.

### Wizard Steps

The wizard walks through 10 steps in order. Two component types handle all
fields:

| # | Field | Type | Required | Notes |
|---|---|---|---|---|
| 1 | Name | textInput | yes (add only) | Skipped on update. Validated: non-empty, no duplicates |
| 2 | Endpoint URL | textInput | yes | Non-empty required |
| 3 | API Key Env | textInput | no | Env var name, not the key itself |
| 4 | Supported Clients | textInput | no | Comma-separated (e.g. `claude,aider`) |
| 5 | Models | textInput | no | Comma-separated |
| 6 | List Models Cmd | textInput | no | Shell command for dynamic discovery |
| 7 | Description | textInput | no | Human-readable |
| 8 | Use Proxy | boolPicker | no | yes/no, defaults to no |
| 9 | Keep Proxy Config | boolPicker | no | yes/no, defaults to no |
| 10 | Enabled | boolPicker | no | yes/no, defaults to yes |

### Navigation

- **Enter** — advance to next step (validates required fields first)
- **Esc** — go back to previous step
- **Esc at first step** — abort wizard
- **Ctrl+C** — abort wizard from anywhere
- **Abort** — nothing saved, prints "Aborted."

### Update Mode Pre-population

When launched from `update`, each step shows the current value:

- Text steps: `[current value]` shown as placeholder. Enter on empty input
  keeps the current value. Typing replaces it entirely.
- Bool pickers: cursor pre-set to the current value (`yes` or `no`).

### Non-TTY Handling

Both `add` and `update` detect non-TTY stdin before launching the wizard. If
stdin is not a terminal, the command returns an error:

```
Error: interactive wizard requires a terminal; use flags instead:
  cam provider add NAME --endpoint URL [--api-key-env VAR] ...
```

This mirrors the existing pattern in `providerRemoveCommand`.

## New Components

### `textInputStep` (`internal/cli/text_input_step.go`)

A reusable text input component matching the `pickerStep` interface contract:

```go
type textInputStep struct {
    title       string
    prompt      string
    value       string
    placeholder string   // shown when value is empty (e.g. "[current value]")
    required    bool
    hint        string
    errMsg      string   // validation error, cleared on next keystroke
}
```

Methods:
- `update(key tea.KeyMsg) pickerAction` — handles typing, backspace, Enter
  (advance if valid), Esc (back), Ctrl+C (abort)
- `view() string` — renders title, prompt with cursor, error message if any,
  hint footer
- `selected() string` — returns the current value (or placeholder if empty and
  not required)

### `providerWizardModel` (`internal/cli/provider_wizard.go`)

A `tea.Model` following the same architecture as `launchWizardModel`:

```go
type providerWizardPhase int

const (
    wizPhaseName providerWizardPhase = iota
    wizPhaseEndpoint
    wizPhaseAPIKeyEnv
    wizPhaseClients
    wizPhaseModels
    wizPhaseListModelsCmd
    wizPhaseDescription
    wizPhaseUseProxy
    wizPhaseKeepProxy
    wizPhaseEnabled
    wizPhaseDone
)

type providerWizardModel struct {
    mode       wizardMode  // add or update
    phase      providerWizardPhase
    startPhase providerWizardPhase  // first phase (skip name on update)
    
    // Steps
    nameStep        textInputStep
    endpointStep    textInputStep
    apiKeyEnvStep   textInputStep
    clientsStep     textInputStep
    modelsStep      textInputStep
    listModelsCmdStep textInputStep
    descriptionStep textInputStep
    useProxyStep    pickerStep
    keepProxyStep   pickerStep
    enabledStep     pickerStep
    
    // Result
    result  wizardResult
    aborted bool
    
    // For duplicate name checking (add mode)
    existingNames map[string]bool
}
```

### `runProviderWizard` (entry point)

```go
func runProviderWizard(
    out io.Writer,
    mode wizardMode,
    existing *providers.Endpoint, // nil for add
    existingName string,          // "" for add
    existingNames []string,       // for duplicate checking
) (name string, ep providers.Endpoint, cancelled bool, err error)
```

- Checks TTY, returns error if non-interactive
- Constructs the model, runs `tea.NewProgram`
- Returns the completed provider name + endpoint, or cancelled=true

## Integration Changes

### `provider_cmd.go`

**`providerAddCommand`:**
- Change `Args: cobra.ExactArgs(1)` to `Args: cobra.RangeArgs(0, 1)`
- In `RunE`: if name is missing or `--endpoint` not set, call
  `runProviderWizard` in add mode. On success, use the returned name + endpoint
  to call `providers.Add` + `providers.Save` (same save path as today).

**`providerUpdateCommand`:**
- In `RunE`: if no flags were explicitly changed (check via
  checking whether any of the `addOrUpdateFlags` local flags were explicitly
  `Changed()` — same approach as the existing sparse-patch logic), call
  `runProviderWizard` in update mode with the existing endpoint pre-loaded. On
  success, replace the endpoint wholesale and save.

## File Layout

**New files:**
- `internal/cli/text_input_step.go`
- `internal/cli/text_input_step_test.go`
- `internal/cli/provider_wizard.go`
- `internal/cli/provider_wizard_test.go`

**Modified files:**
- `internal/cli/provider_cmd.go`
- `internal/cli/cmd_provider_test.go`

## Testing

### `textInputStep` unit tests
- Key sequence: type "hello" + Enter → advance, value = "hello"
- Key sequence: Esc → back action
- Key sequence: Ctrl+C → abort action
- Required field: Enter on empty → no advance, errMsg set
- Backspace: removes last character
- Placeholder: empty + Enter on non-required → returns placeholder value

### `providerWizardModel` unit tests
- Full add flow: send key sequences for all 10 steps → verify result struct
- Full update flow: pre-populated, Enter through all → verify values unchanged
- Update flow with edits: pre-populated, type new endpoint, Enter rest → verify
  endpoint changed, others preserved
- Back navigation: advance 3 steps, Esc twice, verify phase
- Abort: Ctrl+C at step 3 → aborted=true
- Duplicate name: type existing name + Enter → errMsg, no advance

### Integration tests (cmd_provider_test.go)
- `add` with no args, non-TTY stdin → error message about flags
- `update` with no flags, non-TTY stdin → error message about flags
- `add` with all flags → flag-only path (existing tests, unchanged)
- `update` with flags → flag-only path (existing tests, unchanged)

## Backward Compatibility

- All existing flag-based invocations behave identically
- Non-TTY callers (scripts, CI) see clear error messages directing them to flags
- The `--yes` flag on `remove` is unaffected
- Provider records are now persisted in SQLite app state; this note is historical
- No new dependencies (Bubble Tea is already imported)

## Not In Scope

- Dashboard/manager TUI for browsing providers
- Interactive `remove` with provider picker
- Model discovery integration in the wizard (deferred — users can type models
  or set `list_models_cmd` and discover later via `cam launch`)
