# `cam provider` — Interactive Mode for Provider Subcommands

**Date:** 2026-06-15
**Status:** Design approved, ready for implementation plan
**Related:** [`2026-06-15-cam-provider-management-design.md`](./2026-06-15-cam-provider-management-design.md)

## Goal

Add an interactive mode to every mutating `cam provider` subcommand
(`add`, `update`, `remove`, `enable`, `disable`, `rename`) so users can
manage provider records without memorising flags, while keeping every
existing flag-based invocation byte-for-byte compatible for scripting
and CI use.

This spec is additive to the previous
`cam-provider-management` spec — that spec explicitly listed
"Interactive wizard / TUI for `add`" as out-of-scope. We are now
delivering that.

## Scripting Contract (must hold)

The non-interactive contract is the first invariant; interactivity is
layered on top.

| Invocation | TTY | Non-TTY (script/CI) |
| --- | --- | --- |
| `cam provider add NAME --endpoint URL --api-key-env FOO --client claude` | Non-interactive (today's behaviour) | Non-interactive |
| `cam provider add NAME --endpoint URL` (partial flags) | Wizard prompts for missing fields, endpoint pre-filled | Non-interactive with defaults for omitted optional fields |
| `cam provider add NAME` (bare) | Full wizard | Error: required flag missing, suggests TTY |
| `cam provider remove NAME --yes` | Removes without prompting | Removes without prompting |
| `cam provider remove` (bare) | Picker + confirm | Error |
| `cam provider list`, `show`, `init` | Non-interactive | Non-interactive |

**Key invariants:**
- Whenever all *required* flags are present, no prompts fire — TTY or
  not. Today's CI scripts keep working unchanged.
- A wizard only activates when *required input is missing* AND
  `stdin`+`stdout` are both TTYs.
- `CAM_NO_INTERACTIVE=1` forces non-interactive even on a TTY, so
  scripts that source `.env` get deterministic behaviour.

## Scope

**In scope:**
- Multi-step wizard for `add` (full guided flow).
- Field-picker editor for `update`.
- Picker + confirmation for `remove`, `enable`, `disable`, `rename`.
- Mixed mode: flags pre-fill the wizard; only missing fields are
  prompted.
- TTY detection with hard-error fallback for non-interactive
  environments.

**Out of scope:**
- `list`, `show`, `init` — read-only, no change.
- A top-level bare `cam provider` menu — rejected; one entry style.
- Editing the `common` block (proxies, `cache_ttl`).
- Network-side validation (URL reachability, key resolution) —
  `cam doctor` already covers that.
- Migrating the existing `cam launch` wizard to a different UI library.

## Architecture

### New files

```
internal/cli/
  provider_cmd.go            (modified — adds wizard dispatch on missing flags)
  provider_wizard.go         (new — bubbletea model orchestrating add/update wizard)
  provider_wizard_test.go    (new)
  picker_multi.go            (new — multiSelectStep + confirmStep)
  picker_multi_test.go       (new)
  picker_input.go            (new — textInputStep extracted from launch_wizard.go)
  picker_input_test.go       (new)
```

### Reusable sub-components

All three new components live under `internal/cli/` because they are
private to the CLI layer. They are bubbletea sub-models — not
`tea.Model`s themselves — following the established `pickerStep`
pattern in `tool_menu.go`.

**`textInputStep`** — single-line text input.

```go
type textInputStep struct {
    title       string
    placeholder string
    value       string         // initial / running value
    validator   func(string) error
    err         error          // last validation error, shown above input
    hint        string
}
```

Lifted from the inline `manualEntry` code in `launch_wizard.go` so
both the launch and provider wizards share the same input primitive.
Re-renders with the error message above the input when the validator
rejects; the typed value is preserved so the user can edit-in-place.

**`multiSelectStep`** — checkbox list.

```go
type multiSelectStep struct {
    title    string
    items    []string
    selected map[int]bool
    cursor   int
    filter   string           // type-to-filter like pickerStep
    hint     string
    minOne   bool              // if true, Enter is rejected when nothing is selected
}
```

Keys: ↑/↓ move, Space toggle, Enter confirm, type to filter, Esc back,
q abort. Returns `[]string` of items in the original order.

**`confirmStep`** — y/N prompt with explicit default.

```go
type confirmStep struct {
    prompt   string
    defaultY bool      // true = "[Y/n]", false = "[y/N]"
}
```

Returns `bool`. Enter respects the default; explicit y/n overrides.

### `providerWizardModel`

Top-level bubbletea model. Like `launchWizardModel`, it owns a `phase`
enum and switches the active sub-step. Phases are skipped when the
corresponding field was pinned by a CLI flag.

```go
type providerWizardModel struct {
    mode     wizardMode               // add | update | remove | rename | enable | disable
    file     providers.File           // loaded once at start, mutated only after confirm
    registry *tools.Registry          // for client multi-select
    pinned   providerPinned           // flag-pre-filled values

    phase     providerWizardPhase
    nameStep  textInputStep
    pickerSt  pickerStep               // for "pick existing provider"
    endpointStep textInputStep
    apiKeyStep   textInputStep
    clientsStep  multiSelectStep
    modelsModeStep pickerStep          // static | dynamic | skip
    modelsListStep multiSelectStep
    modelsCmdStep  textInputStep
    useProxyStep   pickerStep
    keepProxyStep  pickerStep
    descStep       textInputStep
    fieldMenuStep  multiSelectStep    // for update: which fields to edit
    listOpStep     pickerStep          // replace | add | remove (for list-field edits)
    reviewConfirm  confirmStep         // final save confirm

    result   wizardResult            // populated when phase==phaseDone
    aborted  bool
}
```

The wizard never writes to disk itself. It returns a
`wizardResult` value containing the intended mutation
(`Add(name, ep)`, `Update(name, patch)`, `Remove(name)`, etc.).
`provider_cmd.go` applies that result via the existing `providers.*`
functions and calls `providers.Save`. This keeps the wizard pure and
keeps the storage layer the single source of truth for atomic writes.

## Wizard Flows

### `cam provider add`

```
[name]           textInputStep    pre-filled from positional NAME if provided
                                  validator: non-empty, no whitespace,
                                  not already present in file
[endpoint]       textInputStep    pre-filled from --endpoint
                                  validator: non-empty, contains "://"
[api_key_env]    textInputStep    pre-filled from --api-key-env
                                  validator: empty OR ^[A-Z_][A-Z0-9_]*$
[clients]        multiSelectStep  items = registry.LaunchNames()
                                  pre-checked from --client (replace semantics)
                                  minOne = false (warn but allow)
[models_mode]    pickerStep       choices: "Static list", "Discovery command", "Skip"
                                  pre-resolved when --model or --list-models-cmd given
[models]         (branches)       static  → multiSelectStep with free-text "add new"
                                  dynamic → textInputStep for shell command
                                  skip    → no-op
[use_proxy]      pickerStep       choices: "yes", "no"  default "no"
                                  pre-resolved if --use-proxy/--no-use-proxy given
[keep_proxy]     pickerStep       choices: "yes", "no"  default "no"
                                  pre-resolved if --keep-proxy-config/--no-... given
[description]    textInputStep    pre-filled from --description, empty OK
[review]         renders summary table; confirmStep "Save?" default Y
```

After confirm, the wizard returns a `wizardResultAdd{Name, Endpoint}`.
The command layer calls `providers.Add`, `providers.Save`.

### `cam provider update NAME`

If NAME pinned → skip name picker. If NAME absent → `pickerStep` over
`file.SortedNames()`.

Then the **field menu**: a `multiSelectStep` that shows every editable
field with its current value inline, e.g.

```
[ ] endpoint           = https://api.example.com
[ ] api_key_env        = API_KEY_FOO
[ ] clients            = claude, codex
[ ] models             = (3 entries) | list_models_cmd = "..."
[ ] use_proxy          = false
[ ] keep_proxy_config  = false
[ ] enabled            = true
[ ] description        = "Production endpoint"
```

User toggles the fields they want to edit, presses Enter, and the
wizard walks only those phases. Each list-field edit (clients,
models) first shows a `listOpStep` asking "Replace existing,
Add to, or Remove from?" — mapping cleanly onto today's `+`/`-`/`=`
patch semantics in `providers.ListPatch`.

Final review shows a diff (`before → after` for changed fields only)
and a `confirmStep`.

### `cam provider remove NAME`

- If NAME absent → `pickerStep` over `file.SortedNames()`.
- Then `confirmStep` "Remove provider \"X\"? [y/N]" with default N.
- `--yes` short-circuits the `confirmStep` only. NAME is still
  required as a positional argument; it does not get prompted-for
  when `--yes` is supplied without a NAME (that combination errors).

### `cam provider enable NAME` / `disable NAME`

- If NAME absent → `pickerStep` filtered to the *opposite* state
  (`enable` picks from disabled providers; `disable` picks from
  enabled). Hint says so.
- No confirm — toggle is cheap and reversible.

### `cam provider rename OLD NEW`

- If OLD absent → `pickerStep` over `file.SortedNames()`.
- If NEW absent → `textInputStep`. Validator: non-empty, no whitespace,
  not already in file.
- No confirm — rename is reversible.

## TTY Detection & Mode Dispatch

Two helpers in `provider_cmd.go`:

```go
// wantsInteractive returns true when the user wants the wizard:
// at least one required field is missing AND both stdin/stdout are
// TTYs AND CAM_NO_INTERACTIVE is unset.
func wantsInteractive(cmd *cobra.Command, missing []string) bool

// requireFlagsOrTTY is the non-interactive fallback. Returns an error
// when interactive mode is not available and required flags are missing.
func requireFlagsOrTTY(cmd *cobra.Command, missing []string) error
```

Both stdin and stdout must be TTYs. The existing `inIsTTY` helper in
`provider_cmd.go` covers stdin; a sibling `outIsTTY` is added for
stdout. The double-TTY rule matches what `cam launch` already enforces
in `launch.go`.

Per-subcommand required flags (for "is anything missing?"):

| Subcommand | Required (positional + flag) |
| --- | --- |
| `add` | NAME + `--endpoint` |
| `update` | NAME + at least one mutation flag |
| `remove` | NAME (+ `--yes` for non-TTY) |
| `enable` / `disable` | NAME |
| `rename` | OLD + NEW |

`CAM_NO_INTERACTIVE=1` forces the non-interactive path even on a TTY.

Non-interactive error messages are explicit and actionable:

```
cam provider add: --endpoint is required when not running interactively
  hint: pass --endpoint URL, or run from a terminal for the guided wizard
```

## Validation

Inline, reprompt on error, no network calls:

| Field | Rule |
| --- | --- |
| name | non-empty, no whitespace, not already in file |
| endpoint | non-empty, contains `"://"` |
| api_key_env | empty OR matches `^[A-Z_][A-Z0-9_]*$` |
| clients | warn (not block) when empty — provider becomes unusable |
| models (static) | at least one entry, or explicit "Skip" |
| models (cmd) | non-empty when "Discovery command" branch chosen |
| rename new name | non-empty, no whitespace, not already in file |

When a validator rejects, the wizard re-renders the same step with the
error message above the input. The typed value is preserved so the
user can edit it in place. Esc clears the error and steps back.

## Mixed Mode (flag pre-fill)

`cam provider add NAME --endpoint URL --use-proxy` is partial:
NAME, endpoint, and use_proxy are pre-resolved (the `--use-proxy`
flag's presence pins the use_proxy phase to `true`; an absent flag
leaves the wizard to ask). The wizard:

1. Computes the `pinned` struct from cobra-parsed flags.
2. Phases whose value is pinned are marked `done` and skipped during
   `advanceToNextNeededPhase`.
3. Pinned values still flow into the final review screen so the user
   sees the complete configuration before confirm.

This matches the precedent set by `launch_wizard.go`'s `Pinned`
struct and `validatePinned` function.

## Data Flow — `cam provider add` interactive

```
user runs: cam provider add (TTY, no flags)
  → cobra parses, all flags absent
  → wantsInteractive(...) == true
  → providers.LoadOrInit(path) → file
  → newProviderWizardModel(modeAdd, file, registry, pinned={})
  → tea.NewProgram(model).Run()
       walks: name → endpoint → api_key_env → clients → models_mode
              → models → use_proxy → keep_proxy → description → review
  → wizardResult{kind: add, name: NAME, endpoint: Endpoint{...}}
  → providers.Add(&file, name, ep)
  → providers.Save(path, file)
  → stdout: "Added provider 'NAME'"
```

## Error Handling

- All existing error paths in `provider_cmd.go` are unchanged for
  the non-interactive path.
- Wizard cancel (Esc at phase 0, q, Ctrl+C) → command exits 0 with
  message `"Aborted."`. No file write. Matches the convention already
  used by `providerRemoveCommand` for declined confirms.
- Validation errors are absorbed by the wizard and reprompted; they
  never reach cobra.
- A wizard that completes successfully but whose result is rejected
  by the storage layer (e.g. race: another process added the name
  between wizard start and save) surfaces that error verbatim, same
  as the flag-only path.
- TTY-required errors come from `requireFlagsOrTTY` before any
  bubbletea program starts.

## Testing

Mirror the `launch_wizard_test.go` pattern: drive the bubbletea model
directly with synthetic `tea.KeyMsg` values, assert resulting state
and `wizardResult`.

`provider_wizard_test.go`:
- `add`: full happy-path flow
- `add`: name collision → reprompts with error
- `add`: invalid endpoint → reprompts
- `add`: pre-filled clients from `--client` are pre-checked
- `add`: static models branch (multi-select + free-text entry)
- `add`: dynamic command branch (textInput for command)
- `add`: skip models branch
- `update`: field-menu selection edits only chosen fields
- `update`: list-op picker (replace / add / remove) round-trips
  through `providers.Patch`
- `remove`: picker + confirm Y / picker + confirm N (no-op)
- `enable` / `disable`: picker filters to opposite state
- `rename`: collision rejection

`picker_multi_test.go`:
- toggle, multi-toggle, filter
- Enter with zero selected respects `minOne`
- confirm: default-Y, default-N, Enter respects default

`picker_input_test.go`:
- validator failure shows error, leaves input intact
- Esc clears error and steps back

`cmd_provider_test.go` (extended):
- non-TTY + bare command → error with explicit message
- non-TTY + all required flags → runs unchanged
- `CAM_NO_INTERACTIVE=1` forces non-interactive even on TTY
- TTY + partial flags → wizard fires for missing fields only
  (test via injected fake TTY using `*os.File` from `pty` or
  by exposing a `forceInteractive` test hook on `globalState`)

## Backward Compatibility

- Every existing flag-driven invocation behaves identically.
- No flag is renamed, removed, or has its meaning changed.
- Provider persistence is SQLite-backed in current builds; the JSON notes here are historical.
- `providers.Endpoint`, `Patch`, `LoadOrInit`, `Save`, `Add`,
  `Update`, `Remove`, `Rename`, `SetEnabled` are unchanged.
- The existing inline confirmation prompt in `providerRemoveCommand`
  is replaced by `confirmStep`, but the `--yes` flag still bypasses
  it identically.
- The README gains a short "Interactive mode" subsection under the
  `cam provider` reference.

## Open Decisions Already Resolved

| Decision | Choice |
| --- | --- |
| Entry style | Flag-less subcommand auto-prompts |
| Subcommands with interactive mode | All mutating: add, update, remove, enable, disable, rename |
| Source of client list | tools registry `LaunchNames()` |
| Models input | Branch: static OR list_models_cmd OR skip |
| Non-TTY behaviour | Hard error with explicit message |
| Validation | Inline, reprompt, no network |
| Partial flags | Pre-fill wizard, prompt only missing |
| UI library | Extend existing bubbletea `pickerStep` pattern |
