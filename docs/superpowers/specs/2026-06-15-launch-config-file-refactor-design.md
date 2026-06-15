# Launch via Config Files (not Env Vars) — Design

> Status: APPROVED — drafted 2026-06-15
> Author: jzhu + Claude
> Implements: refactor of `internal/tools/launch.go` and `internal/tools/embed/tools.yaml`.

## 1. Context

When `cam launch <tool>` runs today, `internal/tools/launch.go` builds a
launch-time environment by:

1. Inheriting the process environment.
2. Applying the `env.exported` / `env.managed` / `env.removed` blocks from
   `tools.yaml`.
3. Hard-coding a per-tool `switch tool.Name` block that injects endpoint
   values (`ANTHROPIC_BASE_URL`, `OPENAI_API_KEY`, `BASE_URL`, …) into the
   child process.
4. Exec'ing the tool binary with that merged env.

The child tool reads those env vars and points itself at the chosen
endpoint/model.

The user's directive: **stop setting env vars per tool. Instead, write each
tool's native config file with the selected endpoint/model/api-key, then
launch.**  This makes CAM's effect persistent, debuggable (`cat
~/.codex/config.toml`), and matches how the tools actually want to be
configured outside of CAM.

## 2. Goal

After this refactor ships:

- The per-tool `switch tool.Name` env block in `internal/tools/launch.go` is
  **deleted**.
- For the nine tools listed below, `cam launch <tool>` writes/updates the
  tool's native config file with endpoint / model / API key before
  exec'ing.  The child process is launched with a clean env (process env
  + `tools.yaml` `managed` / `removed` only).
- Tools without a config file (gemini, copilot-api, ampcode, crush,
  opencode, continue, goose, pi-coding-agent) keep their current behavior
  unchanged.
- `cam launch --dry-run` prints the planned config writes without touching
  disk and without exec'ing the tool.

**Tools in scope:**

| Tool key       | Config file                         | Format |
|----------------|--------------------------------------|--------|
| claude-code    | `~/.claude/settings.json`            | json   |
| openai-codex   | `~/.codex/config.toml`               | toml   |
| qwen-code      | `~/.qwen/settings.json`              | json   |
| codebuddy      | `~/.codebuddy.json`                  | json   |
| iflow          | `~/.iflow/settings.json`             | json   |
| aichat         | `~/.config/aichat/config.yaml`       | yaml   |
| kimi           | `~/.kimi/config.toml`                | toml   |
| droid          | `~/.factory/settings.json`           | json   |
| neovate        | `~/.neovate/config.json`             | json   |

## 3. Non-goals

- Restoring the previous config contents after the tool exits.  Writes
  persist (that is the point — they double as the user's "last-used"
  state when running the tool outside of CAM).
- Encrypting API keys on disk.  The file is created at mode 0600; we do
  not introduce a keychain integration.
- Touching install/upgrade/uninstall logic.
- Refactoring how `cam config set` / `cam config unset` work for editors
  that already have full `internal/editorconfig` support.

## 4. Architecture

### 4.1 Package layout

```
internal/
├── tools/
│   ├── registry.go              # ADD: ConfigTarget struct + yaml parse
│   ├── launch.go                # SHRINK: delete per-tool switch
│   ├── configwriter.go          # NEW: Plan + Apply + WriteConfig
│   ├── configwriter_test.go     # NEW
│   ├── configwriter_per_tool_test.go  # NEW: golden table tests
│   ├── codex_postwrite.go       # NEW: wire_api GPT branching
│   ├── codex_postwrite_test.go  # NEW
│   ├── testdata/                # NEW: golden files per tool
│   └── embed/tools.yaml         # ADD: config_target blocks (9 tools)
├── editorconfig/
│   ├── editor.go                # unchanged
│   ├── json_tool.go             # unchanged
│   ├── toml_tool.go             # unchanged
│   ├── yaml_tool.go             # NEW: YAML backend (aichat)
│   ├── yaml_tool_test.go        # NEW
│   ├── keypath.go               # EXTEND: [+] append, [name=v] match
│   └── editorconfig_test.go     # extend with array + yaml cases
└── cli/
    └── launch.go                # MODIFY: call WriteConfig before Run
```

### 4.2 Layering

- `internal/tools/configwriter.go` depends on `internal/editorconfig`
  (set/unset primitives) and `internal/pathutil` (`Expand`,
  `EnsureDir`). It does **not** depend on `internal/cli/`.
- `internal/cli/launch.go` depends on `internal/tools` only.
- `internal/editorconfig` gains a YAML backend and array-upsert
  operators; no other package changes.

### 4.3 Data flow on `cam launch <tool>`

1. `cli/launch.go` resolves `tool`, `endpoint`, `endpointName`, `model`,
   `apiKey` (unchanged from today).
2. If `--dry-run`: call `tools.Plan(...)`, render the plan, return.
3. Otherwise: call `tools.WriteConfig(tool, endpoint, endpointName,
   model, apiKey)`.  Aborts on error.
4. Call `tools.ResolveLaunchEnv(...)` to build the (much smaller) child
   env.
5. Call `tools.Run(launch, toolArgs)` — exec the binary.

## 5. `tools.yaml` schema

A new optional top-level field per tool entry:

```yaml
config_target:
  path: <string>          # required; ~ is expanded
  format: json|toml|yaml  # required
  upsert:                 # required; map of key path -> value template
    <key.path>: <value template string>
  remove:                 # optional; list of key paths to delete
    - <key.path>
```

### 5.1 Key paths

- **JSON / YAML:** dotted (`env.ANTHROPIC_BASE_URL`,
  `providers.litellm.baseURL`).
- **TOML:** dotted, with placeholders allowed mid-path
  (`model_providers.{endpoint_name}.base_url`).  Segments with special
  characters are quoted by `editorconfig`.
- **Arrays:** two operators are supported.
  - `customModels[+].field` — always append a new element and set
    `.field` on it.
  - `customModels[displayName={endpoint_name}/{selected_model}].field` —
    upsert: if an element exists whose `displayName` already equals the
    expanded value, target that element; otherwise create a new
    element with `displayName` set to the expanded value and target
    that.  All upserts that share the same `[key=value]` match clause
    within one Apply operate on the same element.
  - Match values may contain placeholders and are expanded before
    matching.  Droid uses
    `customModels[displayName={endpoint_name}/{selected_model}]` so
    re-launching with the same endpoint+model updates the existing
    entry rather than duplicating it.

### 5.2 Value template placeholders

| Placeholder        | Expansion                              |
|--------------------|----------------------------------------|
| `{endpoint}`       | `endpoint.Endpoint` (URL)              |
| `{endpoint_name}`  | providers.json key (e.g. `litellm`)    |
| `{api_key}`        | resolved API key                       |
| `{selected_model}` | chosen model                           |
| `{model_2}`        | secondary model, empty when N/A        |

Substitution is literal string replace, matching the existing
`expandPlaceholders` in `launch.go`.

### 5.3 Type coercion

After substitution, the value string is coerced as:

1. `true|false` → bool
2. integer → int64
3. floating-point → float64
4. otherwise → string

So `"8192"` becomes the integer `8192` in the on-disk file, not the
string `"8192"`.

### 5.4 Per-tool `config_target` blocks

```yaml
claude-code:
  config_target:
    path: ~/.claude/settings.json
    format: json
    upsert:
      env.ANTHROPIC_BASE_URL: "{endpoint}"
      env.ANTHROPIC_AUTH_TOKEN: "{api_key}"
      env.CLAUDE_CODE_OAUTH_TOKEN: "{api_key}"
      env.ANTHROPIC_MODEL: "{selected_model}"
      env.ANTHROPIC_SMALL_FAST_MODEL: "{model_2}"
      env.ANTHROPIC_DEFAULT_SONNET_MODEL: "{selected_model}"
      env.ANTHROPIC_DEFAULT_HAIKU_MODEL: "{selected_model}"
      env.DISABLE_NON_ESSENTIAL_MODEL_CALLS: "1"
      env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"

openai-codex:
  config_target:
    path: ~/.codex/config.toml
    format: toml
    upsert:
      model_providers.{endpoint_name}.name: "{endpoint_name}"
      model_providers.{endpoint_name}.base_url: "{endpoint}"
      model_providers.{endpoint_name}.env_key: "OPENAI_API_KEY"
      profiles.{selected_model}.model: "{selected_model}"
      profiles.{selected_model}.model_provider: "{endpoint_name}"
      profiles.{selected_model}.model_reasoning_effort: "low"

qwen-code:
  config_target:
    path: ~/.qwen/settings.json
    format: json
    upsert:
      env.OPENAI_BASE_URL: "{endpoint}"
      env.OPENAI_API_KEY: "{api_key}"
      env.OPENAI_MODEL: "{selected_model}"

codebuddy:
  config_target:
    path: ~/.codebuddy.json
    format: json
    upsert:
      env.CODEBUDDY_BASE_URL: "{endpoint}"
      env.CODEBUDDY_API_KEY: "{api_key}"

iflow:
  config_target:
    path: ~/.iflow/settings.json
    format: json
    upsert:
      env.IFLOW_BASE_URL: "{endpoint}"
      env.IFLOW_API_KEY: "{api_key}"
      env.IFLOW_MODEL_NAME: "{selected_model}"

aichat:
  config_target:
    path: ~/.config/aichat/config.yaml
    format: yaml
    upsert:
      clients.{endpoint_name}.type: "openai-compatible"
      clients.{endpoint_name}.api_base: "{endpoint}"
      clients.{endpoint_name}.api_key: "{api_key}"
      clients.{endpoint_name}.models[+].name: "{selected_model}"

kimi:
  config_target:
    path: ~/.kimi/config.toml
    format: toml
    upsert:
      provider: "{endpoint_name}"
      providers.{endpoint_name}.base_url: "{endpoint}"
      providers.{endpoint_name}.api_key: "{api_key}"
      providers.{endpoint_name}.model: "{selected_model}"

droid:
  config_target:
    path: ~/.factory/settings.json
    format: json
    upsert:
      customModels[displayName={endpoint_name}/{selected_model}].displayName: "{endpoint_name}/{selected_model}"
      customModels[displayName={endpoint_name}/{selected_model}].model: "{selected_model}"
      customModels[displayName={endpoint_name}/{selected_model}].baseUrl: "{endpoint}"
      customModels[displayName={endpoint_name}/{selected_model}].apiKey: "{api_key}"
      customModels[displayName={endpoint_name}/{selected_model}].provider: "openai"
      customModels[displayName={endpoint_name}/{selected_model}].maxOutputTokens: "8192"

neovate:
  config_target:
    path: ~/.neovate/config.json
    format: json
    upsert:
      providers.{endpoint_name}.baseURL: "{endpoint}"
      providers.{endpoint_name}.apiKey: "{api_key}"
      providers.{endpoint_name}.model: "{selected_model}"
      defaultProvider: "{endpoint_name}"
```

### 5.5 Pruning the old `env.exported` blocks

For the nine refactored tools, the existing `env.exported` block in
`tools.yaml` is trimmed: every endpoint-derived var (BASE_URL, API key,
MODEL, etc.) is moved into `config_target.upsert`.  Only the
process-only knob `NODE_TLS_REJECT_UNAUTHORIZED: "0"` survives — and
that one moves under `env.managed` since it is no longer a
placeholder-expanded value.

## 6. Writer behavior

### 6.1 Public API

```go
package tools

// PlannedWrite is one upsert/remove that the writer will apply.
type PlannedWrite struct {
    KeyPath string // expanded key path (placeholders substituted)
    Value   any    // string, bool, int64, float64; nil for Remove
    Op      string // "upsert" | "remove"
}

// Plan resolves all placeholders and returns the ordered list of writes
// without touching disk.  Used by --dry-run and Apply alike.
func Plan(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) ([]PlannedWrite, error)

// Apply writes the planned writes to tool.ConfigTarget.path atomically.
// Returns the written path or empty when tool has no config_target.
func Apply(tool Tool, plan []PlannedWrite) (writtenPath string, err error)

// WriteConfig is Plan + Apply, the typical launch.go call site.
func WriteConfig(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) (writtenPath string, err error)
```

### 6.2 Guarantees

1. **No `config_target` → no-op.**  Returns `("", nil)`.
2. **Deterministic ordering.**  Iterate `upsert` keys in lexicographic
   order of the full key path.  Array `[+]` and `[key=value]` operators
   resolve to a target element before per-element field writes are
   applied; the resolution is itself deterministic (first matching
   element wins for `[key=value]`; a new element appended for `[+]`).
3. **Atomic write.**  Write to `<path>.tmp.<pid>`, fsync, rename.  File
   mode 0600, parent dir 0700.
4. **Read-modify-write.**  Read once, mutate the in-memory tree, write
   once.
5. **Preserves unrelated content.**  Only keys named in `upsert`/`remove`
   are touched.
6. **Type coercion** as per §5.3.
7. **`remove` on absent key is not an error.**
8. **Codex post-hook.**  After generic Apply, if `tool.Name ==
   "openai-codex"`:
   - selected model starts with `gpt`: set
     `model_providers.<endpoint_name>.wire_api = "responses"`
   - otherwise: unset that key.
   The post-hook reuses the same atomic-write path.
9. **Fail closed.**  Any error aborts the launch — the tool is never
   exec'd if the config write failed.

## 7. `launch.go` changes

### 7.1 `internal/tools/launch.go`

Remove the `switch tool.Name` block (lines 51–75 today).  After the
change, `ResolveLaunchEnv` carries only:

- inherited process env
- `tool.Env.Exported` (with placeholder expansion — preserved as the
  user-extensible escape hatch)
- `tool.Env.Managed`
- `tool.Env.Removed`
- placeholder-expanded `cli_parameters.injected`

### 7.2 `internal/cli/launch.go`

```go
endpoint, epName, err := resolveEndpoint(...)
model := chooseModel(...)
apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)

if dryRun {
    plan, err := tools.Plan(tool, endpoint, epName, model, apiKey)
    if err != nil { return err }
    printDryRun(cmd.OutOrStdout(), tool, endpoint, model, plan, toolArgs)
    return nil
}

if _, err := tools.WriteConfig(tool, endpoint, epName, model, apiKey); err != nil {
    return fmt.Errorf("launch: write %s config: %w", tool.Name, err)
}

launch := tools.ResolveLaunchEnv(tool, endpoint, epName, model)
code, err := tools.Run(launch, toolArgs)
```

### 7.3 `--dry-run` output

```
Tool: claude
Endpoint: https://litellm.example.com
Model: claude-sonnet-4
Config writes (~/.claude/settings.json):
  upsert env.ANTHROPIC_BASE_URL = "https://litellm.example.com"
  upsert env.ANTHROPIC_AUTH_TOKEN = "sk-***...***abcd"
  upsert env.ANTHROPIC_MODEL = "claude-sonnet-4"
  upsert env.ANTHROPIC_DEFAULT_SONNET_MODEL = "claude-sonnet-4"
  upsert env.DISABLE_NON_ESSENTIAL_MODEL_CALLS = "1"
```

API keys are rendered via `providers.MaskedAPIKey`.

## 8. Testing

### 8.1 `internal/tools/configwriter_test.go`

| Test | Asserts |
|---|---|
| `TestPlan_PlaceholderSubstitution`           | All five placeholders expand in both keys and values. |
| `TestPlan_TypeCoercion`                      | `true`/int/float/string coercion. |
| `TestPlan_OrderingDeterministic`             | Byte-identical plan across runs. |
| `TestApply_JSON_PreservesUnrelatedKeys`      | Unrelated keys untouched. |
| `TestApply_TOML_PreservesUnrelatedTables`    | Unrelated tables untouched. |
| `TestApply_YAML_PreservesUnrelatedKeys`      | Unrelated YAML keys untouched. |
| `TestApply_AtomicWriteOnFailure`             | Original file unchanged on marshal error. |
| `TestApply_CreatesParentDir`                 | Parent dir created at mode 0700. |
| `TestApply_FilePermissions`                  | Written file is mode 0600. |
| `TestApply_NoConfigTarget_Noop`              | Tools without `config_target` no-op. |
| `TestApply_RemoveAbsentKey_NotError`         | `remove` on missing key succeeds. |
| `TestApply_ArrayUpsertByMatch`               | Droid: re-running with the same `displayName` updates in place; a different `displayName` appends a new element. |
| `TestApply_ArrayAppend`                      | `[+]` always appends; multiple upserts sharing one `[+]` site write to the same fresh element. |

### 8.2 `internal/tools/codex_postwrite_test.go`

| Test | Asserts |
|---|---|
| `TestCodexPostHook_GPTSetsWireAPI`           | `gpt-4o` → `wire_api = "responses"`. |
| `TestCodexPostHook_NonGPTUnsetsWireAPI`      | `claude-sonnet-4` unsets the key if present. |
| `TestCodexPostHook_NoCodexNoop`              | Hook ignores non-codex tools. |

### 8.3 `internal/tools/configwriter_per_tool_test.go`

Table-driven golden tests, one sub-test per refactored tool (9 cases).
Fixtures: minimal endpoint, single model, fake API key.  Asserts the
resulting on-disk file matches `testdata/<tool>.expected.<ext>`.

### 8.4 `internal/editorconfig/yaml_tool_test.go`

| Test | Asserts |
|---|---|
| `TestYAML_LoadEmpty`                         | Missing file → empty map. |
| `TestYAML_SetAndUnset_PreservesOther`        | Unrelated keys preserved. |
| `TestYAML_AtomicWrite`                       | Same atomicity guarantees. |
| `TestYAML_ArrayUpsertByMatch`                | `clients[+]` and `clients[k=v]` semantics. |

### 8.5 `internal/cli/cmd_launch_test.go`

| Test | Asserts |
|---|---|
| `TestLaunch_DryRun_PrintsConfigPlan`         | `--dry-run` output contains `Config writes (...)`. |
| `TestLaunch_DryRun_DoesNotTouchDisk`         | Disk unchanged after `--dry-run`. |
| `TestLaunch_WritesConfigBeforeExec`          | Stub records config file existence pre-exec. |
| `TestLaunch_ConfigWriteFailureAborts`        | Stub `exec` not called on write failure; non-zero exit. |
| `TestLaunch_NoEndpointVarsExportedToChild`   | `ANTHROPIC_BASE_URL`, `OPENAI_API_KEY`, `BASE_URL` absent in child env. |

### 8.6 Existing tests touched

- `internal/tools/registry_test.go` — parse `config_target`.
- `internal/cli/cmd_launch_test.go` — drop assertions on env exports for
  the nine refactored tools.

## 9. Migration & rollback

- **Migration.**  None required for users; on first launch after upgrade
  the config files are simply written.  Pre-existing `env.exported`
  lines in a user-overridden `~/.config/code-agent-manager/tools.yaml`
  continue to work — `env.exported` is unchanged; only the bundled
  defaults are trimmed.
- **CHANGELOG.**  Add an entry noting that endpoint-derived env vars are
  no longer exported into the child process; instead the tool's native
  config file is written.
- **Rollback.**  Revert the commit; the per-tool switch block returns.
  Config files already on disk are harmless to keep — they were going
  to be written eventually anyway and tools tolerate them.

## 10. Open issues (none)

Section 5.4's earlier open issues (YAML backend for aichat, array
upsert for Droid) were resolved during brainstorming in favor of
extending `internal/editorconfig`.  All decisions are captured above.
