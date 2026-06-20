# Go CLI Foundation (Sub-project #1) — Design

> Status: APPROVED — drafted 2026-06-15
> Author: jzhu + Claude
> Implements: feature parity step 1 of 10 toward Go ↔ Python CLI parity.

## 1. Context

The Go CLI rewrite at `cmd/cam` + `internal/cli` ships about 1.25k LOC and is mostly a Cobra skeleton with placeholder behavior. The Python CLI at `code_assistant_manager/` is the source of truth and ships ~22.5k LOC of business logic (CLI + MCP + per-tool config + fetching + handlers). The user has asked for a full native Go rewrite at functional parity with Python.

A single design at that scope is infeasible. The work is decomposed into 10 independent sub-projects, each with its own spec/plan cycle. This document specifies **Sub-project #1: Foundation** — the config, providers, env-loading, diagnostics, completion, and global-flag layer that every later sub-project will plug into.

## 2. Goal

After Sub-project #1 ships, the following commands behave equivalently to Python:

- `cam version` (already done)
- `cam completion {bash|zsh|fish|powershell|pwsh}` — replace hand-rolled scripts with Cobra-native generation
- `cam --endpoints {all|<tool>}` and `--debug/-d` global flags
- `cam config list` — list cam.db, config.yaml, .env, and the editor config locations
- `cam config validate` — validate config.yaml (provider state lives in SQLite)
- `cam config show [KEY] --app <tool> --scope {user|project}` — show editor config
- `cam config set KEY VALUE --app <tool> --scope {user|project}` — set editor config
- `cam config unset KEY --app <tool> --scope {user|project}` — unset editor config
- `cam doctor` — diagnostics: installation / config / env / endpoint URL format / cache / Gemini-Vertex auth / GitHub Copilot auth / tool availability

The following remain placeholders (unchanged from today) until later sub-projects:

- `cam launch` (sub-project #2)
- `cam install / upgrade / uninstall` (sub-project #3)
- `cam mcp` (sub-project #4)
- `cam prompt` (sub-project #5)
- `cam skill` (sub-project #6)
- `cam agent` (sub-project #7)
- `cam plugin` (sub-project #8)
- `cam extension` (sub-project #9)

## 3. Non-goals

- Endpoint reachability probes (only URL-format validation).
- `tools.yaml` execution (install/upgrade commands).
- Per-tool launch logic, env-builders, prompts/skills/agents/plugins/MCP/extensions.

## 4. Architecture

### 4.1 Package layout

```
cmd/
├── cam/main.go                  # unchanged
└── code-agent-manager/main.go   # unchanged

internal/
├── cli/                         # Cobra command tree (presentation layer)
│   ├── app.go                   # App struct, root command wiring (existing, refactored)
│   ├── global.go                # NEW: globalState, persistent flags, --endpoints short-circuit
│   ├── version.go               # NEW: version subcommand
│   ├── completion.go            # NEW: Cobra-native completion
│   ├── doctor.go                # NEW: doctor subcommand
│   ├── config_cmd.go            # NEW: config list/show/set/unset/validate
│   ├── launch.go                # MOVED from commands.go (placeholder, unchanged)
│   ├── lifecycle.go             # MOVED from commands.go (placeholder, unchanged)
│   ├── management.go            # MOVED from config.go (placeholder, unchanged)
│   ├── mcp.go                   # unchanged placeholder
│   └── tool_menu.go             # unchanged
├── providers/                   # provider data domain (historically providers.json, now SQLite app state)
│   ├── providers.go
│   ├── loader.go
│   ├── resolver.go
│   └── providers_test.go
├── camconfig/                   # config.yaml domain
│   ├── camconfig.go
│   ├── embed/config.yaml        # bundled fallback (//go:embed)
│   └── camconfig_test.go
├── envfile/                     # .env discovery + load
│   ├── envfile.go
│   └── envfile_test.go
├── editorconfig/                # per-editor config show/set/unset (JSON + TOML)
│   ├── editor.go                # ToolConfig interface, registry
│   ├── json_tool.go             # JSON-backed editors
│   ├── toml_tool.go             # codex (TOML)
│   ├── keypath.go               # ParseTOMLKeyPath, Get/Set/Unset, Flatten, ParseScalar
│   └── editorconfig_test.go
├── doctor/                      # diagnostics
│   ├── doctor.go                # Check interface, Reporter, Run
│   ├── checks.go                # all check implementations
│   └── doctor_test.go
├── pathutil/                    # ~ expansion, configDir
│   ├── pathutil.go
│   └── pathutil_test.go
└── ui/                          # output helpers
    ├── ui.go                    # Printer (Reporter implementation)
    └── ui_test.go
```

### 4.2 Layering rules

- `cli/*` depends on `internal/*` + `ui/`. Knows no JSON/TOML/YAML schemas directly.
- `doctor/*` depends on `providers/`, `camconfig/`, `envfile/`, `editorconfig/`, `pathutil/`, `ui/`. Does not import `cli/`.
- `providers/`, `camconfig/`, `envfile/`, `editorconfig/`, `pathutil/` depend only on stdlib + `gopkg.in/yaml.v3` + `pelletier/go-toml/v2`. No sibling cross-imports.
- `ui/` depends only on stdlib + `fatih/color` + `mattn/go-isatty`.

### 4.3 New dependencies

| Package | Purpose |
|---|---|
| `github.com/fatih/color` | TTY-aware ANSI colors |
| `github.com/mattn/go-isatty` | TTY detection |

## 5. Component specifications

### 5.1 `internal/providers/`

```go
type File struct {
    Common    map[string]any
    Endpoints map[string]Endpoint
}

type Endpoint struct {
    Endpoint        string
    APIKeyEnv       string
    SupportedClient string
    ListModelsCmd   string
    Models          []string
    KeepProxyConfig bool
    UseProxy        bool
    Enabled         *bool   // tri-state: nil → true
    Description     string
}

func Load(path string) (File, error)
func LegacyDefaultPath() string      // deprecated ~/.config/code-agent-manager/providers.json
func DiscoverPath() string           // first existing of DefaultPath / cwd / home
func (e Endpoint) IsEnabled() bool
func (e Endpoint) Clients() []string
func ResolveAPIKey(e Endpoint, env func(string) string) string
```

JSON field tags match Python's `providers.json` schema. `IsEnabled()` returns `true` when `Enabled` is nil or `*true`.

### 5.2 `internal/camconfig/`

```go
type CamConfig struct {
    Cache        CacheConfig
    Repositories map[string]RepoSources
}

type CacheConfig struct {
    Enabled    bool
    Directory  string  // ~ expanded
    TTLSeconds int
}

type RepoSources struct { Sources []RepoSource }
type RepoSource    struct { Type, Path, URL string }

func Load(path string) (CamConfig, error)
func DefaultPath() string
//go:embed embed/config.yaml
var bundledConfig []byte
func Bundled() (CamConfig, error)
```

`Load` falls back to `Bundled` when path is missing.

### 5.3 `internal/envfile/`

```go
func Find(custom string, strict bool) (string, error)
func Load(path string) (map[string]string, error)
func ApplyToProcess(vars map[string]string)
```

Search order on empty `custom`:

1. Walk `cwd` upward until a `.env` exists or hit root / `.git`.
2. `~/.env`
3. `~/.config/code-agent-manager/.env`

Parser: stdlib only. Lines `KEY=VALUE`, strip surrounding `"` or `'`, ignore `#` comments and blank lines. Reject lines without `=`.

### 5.4 `internal/editorconfig/`

```go
type Scope string
const (
    UserScope    Scope = "user"
    ProjectScope Scope = "project"
)

type ToolConfig interface {
    Name() string
    Description() string
    Format() string                                // "json" | "toml"
    PathFor(Scope) string                          // "" if scope unsupported
    Load(Scope) (data map[string]any, path string, err error)
    LoadAll() map[string]ScopedConfig              // {user|project: {Data, Path}}
    Set(Scope, keyPath string, value any) (savedPath string, err error)
    Unset(Scope, keyPath string) (found bool, savedPath string, err error)
}

type ScopedConfig struct {
    Data map[string]any
    Path string
}

type Registry struct{ /* map[string]ToolConfig */ }
func DefaultRegistry() *Registry
func (r *Registry) Get(name string) (ToolConfig, bool)
func (r *Registry) Names() []string                // sorted
```

Implementations:

- `jsonToolConfig` (claude, cursor-agent, gemini, copilot, qwen, codebuddy, droid, iflow, neovate, qodercli, zed, crush) — `encoding/json` with `json.Indent` for 2-space stable output.
- `tomlToolConfig` (codex) — `pelletier/go-toml/v2`, supports TOML quoted key paths.

Editor metadata table:

| Name | Format | User paths (first existing wins; first is also create-path) | Project path |
|---|---|---|---|
| `claude` | json | `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/settings.local.json` | `.claude/settings.json` |
| `cursor-agent` | json | `~/.cursor/settings.json`, `~/.cursor/mcp.json` | `.cursor/settings.json` |
| `gemini` | json | `~/.gemini/settings.json` | `.gemini/settings.json` |
| `copilot` | json | `~/.copilot/mcp-config.json`, `~/.copilot/mcp.json` | — |
| `codex` | toml | `~/.codex/config.toml` | — |
| `qwen` | json | `~/.qwen/settings.json` | — |
| `codebuddy` | json | `~/.codebuddy.json` | `.codebuddy/mcp.json` |
| `crush` | json | `~/.config/crush/crush.json` | — |
| `droid` | json | `~/.factory/mcp.json`, `~/.factory/settings.json` | — |
| `iflow` | json | `~/.iflow/settings.json`, `~/.iflow/config.json` | — |
| `neovate` | json | `~/.neovate/config.json` | — |
| `qodercli` | json | `~/.qodercli/config.json` | — |
| `zed` | json | `~/.config/zed/settings.json` | — |

Key-path engine in `keypath.go`:

```go
func Parse(raw string) ([]string, error)
func Get(data map[string]any, parts []string) (any, bool)
func Set(data map[string]any, parts []string, value any)
func Unset(data map[string]any, parts []string) (found bool)
func Flatten(data map[string]any, prefix string) map[string]string
func ParseScalar(raw string) any  // bool > int > float > string
```

`Parse` handles TOML quoted segments like `codex.profiles."alibaba/glm-4.5".model`.

### 5.5 `internal/doctor/`

```go
type Reporter interface {
    Header(string)
    Info(string)
    Pass(string)
    Warn(msg, hint string)
    Fail(msg, hint string)
}

type Check interface {
    Name() string
    Run(ctx context.Context, r Reporter) Result
}

type Result struct{ Issues int }

func Run(ctx context.Context, r Reporter, checks []Check) int
```

Checks (one struct each):

| Check | Verifies |
|---|---|
| `InstallationCheck`  | binary version present, Go runtime version |
| `ConfigCheck`        | SQLite store exists and can be queried |
| `EnvCheck`           | locate `.env` via `envfile.Find`, perms ≤ 0o600 |
| `EndpointFormatCheck`| every endpoint has `http(s)://` URL |
| `CacheCheck`         | `~/.cache/code-agent-manager/repos` size + file count + newest/oldest mtime |
| `GeminiAuthCheck`    | `GEMINI_API_KEY` set, or all four `GOOGLE_*` vars (and `GOOGLE_APPLICATION_CREDENTIALS` file exists) |
| `CopilotAuthCheck`   | `GITHUB_TOKEN` set |
| `ToolsAvailableCheck`| each tool key from bundled `tools.yaml` resolves via `exec.LookPath` |

`ToolsAvailableCheck` reads a `//go:embed`'d copy of `tools.yaml` so #1 doesn't need the full registry. Sub-project #2 replaces this with the real registry.

Doctor exit code: 0 on success, 1 only when `InstallationCheck` fails (matches Python). Warnings/failures in other checks contribute to issue count but do not fail the command.

### 5.6 `internal/ui/`

```go
type Printer struct {
    Out, Err io.Writer
    Color    bool
}
func New(out, errw io.Writer) *Printer  // Color = isatty(out) && NO_COLOR=="" && term != "dumb"
func (p *Printer) Header(msg string)
func (p *Printer) Info(msg string)
func (p *Printer) Pass(msg string)
func (p *Printer) Warn(msg, hint string)
func (p *Printer) Fail(msg, hint string)
```

ANSI styling uses `fatih/color`. When `Color` is `false`, output is plain — important for `cmd.OutOrStdout()` capture in tests.

### 5.7 `internal/cli/`

`globalState` extends to:

```go
type globalState struct {
    configPath    string  // --config
    providersPath string  // --providers (existing)
    storePath     string  // --store    (existing)
    endpoints     string  // --endpoints (NEW)
    debug         bool    // --debug / -d (NEW)
}
```

`rootCommand` PersistentPreRunE:

1. Configure log level when `debug == true`.
2. If `endpoints != ""`, print endpoints and return a sentinel error (`errEndpointsHandled`) that `App.Run` translates to exit 0 without invoking the subcommand body.

Config command tree:

| Sub-command | Args / flags | Behavior |
|---|---|---|
| `config list` | none | Print CAM config files (providers/config.yaml/env) + all editor config locations from the registry, marking existence with `✓`. |
| `config validate` | `--verbose/-v`, inherits `--config` | Validate SQLite store selection via `--store`; load `config.yaml` from `--config` (or default+bundled). Print `Configuration is valid` on success, errors with non-zero exit on failure. |
| `config show [KEY]` | `--app/-a` (default `claude`), `--scope/-s` (default unset = both) | Load editor config via registry. Print flattened key=value lines for all keys, or just one when `KEY` provided. |
| `config set KEY[=VALUE] [VALUE]` | `--app/-a` (required if no dotted prefix), `--scope/-s` (default `user`) | Accept `KEY=VALUE` single-arg or `KEY VALUE` two-arg form (Python takes two args). `ParseScalar` coerces. Print `Set <key> = <value> (<scope> scope)` and config path. |
| `config unset KEY` | `--app/-a` (required if no dotted prefix), `--scope/-s` (default `user`) | Remove key. Print `Unset <key> from <scope> scope` or warning if missing. |

Completion command uses Cobra's built-in generators:

```go
cmd.Root().GenBashCompletionV2(out, true)
cmd.Root().GenZshCompletion(out)
cmd.Root().GenFishCompletion(out, true)
cmd.Root().GenPowerShellCompletionWithDesc(out)
```

`pwsh` normalizes to `powershell`. Output must contain `<shell> completion` so existing test assertions hold.

### 5.8 Compatibility with existing tests

Existing `internal/cli/cli_test.go` makes assertions that must continue to hold:

| Test | Assertion preserved by |
|---|---|
| `TestRootHelpShowsCommandSurfaceAndAliases` | Same command tree + aliases on root |
| `TestVersionCommandAndAlias` | `version`, `v`, `--version` still emit `version` text |
| `TestCompletionCommandSupportsAliasesAndShells` | Cobra-generated output still contains `<shell> completion` header — we wrap output with a `# code-agent-manager <shell> completion` banner |
| `TestCompletionRejectsUnsupportedShell` | `Unsupported shell:` error stays |
| `TestCommandAliasesShowHelp` | All aliases still registered |
| `TestConfigListShowValidateSetUnset` | **Updated** to test Python-equivalent behavior: `config validate` uses `--config`; `config show` accepts `--app` (default `claude`); `config set/unset` accept either `KEY=VALUE` (legacy) or `KEY VALUE` (Python). Test file is updated to use a CAM config path that exists and to call set/unset on a registered editor with a temp `HOME` so the editor config writes to an isolated directory. |
| `TestConfigListHonorsCAMConfigDir` | `config list` honors `CAM_CONFIG_DIR` |
| `TestDoctorValidatesProvidersConfigAndEnv` | Doctor output extends — original assertions (`Providers: 1`, `test-endpoint`, `Environment: CAM_TEST_API_KEY set`) preserved via a backwards-compat block at the top of doctor output |
| `TestLaunch*` | `launch` placeholder code is moved verbatim to `launch.go`, no behavioral change |
| `TestManagementCommandsHaveWorkingListInstallRemoveFlow` | Management placeholder code moved verbatim to `management.go` |
| `TestMCPServerAddListRemoveFlow` | `mcp.go` unchanged |
| `TestUpgradeInstallUninstallDryRun` | Lifecycle placeholder code moved verbatim |

## 6. Data flow

### 6.1 `cam config show codex.profiles.foo.model --app codex`

```
cli.App.Run
  └── rootCommand → config → show
       └── editorconfig.DefaultRegistry().Get("codex")
            └── tomlToolConfig.Load(BothScopes)
                 └── keypath.Flatten + keypath.Get
                      └── ui.Printer.Info(value)
```

### 6.2 Historical `cam doctor --providers ~/providers.json` (deprecated)

```
cli.App.Run
  └── rootCommand → doctor
       └── doctor.Run(ctx, ui.Printer, [Installation, Config, Env, EndpointFormat, Cache, GeminiAuth, CopilotAuth, ToolsAvailable])
            ├── ConfigCheck         → providers.Load(state.providersPath)
            ├── EndpointFormatCheck → iterate providers.File.Endpoints
            ├── EnvCheck            → envfile.Find("")
            ├── CacheCheck          → walk ~/.cache/code-agent-manager/repos
            └── ToolsAvailableCheck → exec.LookPath(toolName) for each key in bundled tools.yaml
```

## 7. Error handling

- Parse errors: returned to caller, displayed via `App.Run` as `fmt.Fprintln(stderr, err)` + exit 1.
- Missing config file when running `doctor`: warn, don't fail.
- `config set/unset` on missing key (unset only): print warning, exit 0 (matches Python).
- `--endpoints` short-circuit: PersistentPreRunE returns `errEndpointsHandled`; `App.Run` recognizes this sentinel and exits 0.

## 8. Testing

Test bar: table-driven unit tests for every public function + a few integration tests.

| Package | Test focus |
|---|---|
| `providers/` | `Load` (happy path, missing file, malformed JSON), `Clients()` splitting, `ResolveAPIKey` with env injection |
| `camconfig/` | `Load` (happy path, missing → bundled fallback, malformed YAML), cache directory `~` expansion |
| `envfile/` | `Find` with all branches (custom strict, walk upward, home), `Load` parser corner cases (quotes, comments, blank lines, malformed) |
| `editorconfig/` | `keypath` Parse/Get/Set/Unset/Flatten/ParseScalar tables; `jsonToolConfig` round-trip Load→Set→Load; `tomlToolConfig` round-trip with quoted keys; Registry contains expected 13 entries |
| `doctor/` | Each check with a fake `Reporter` recording calls; deterministic clock injection where mtime is involved |
| `pathutil/` | `~` expansion, `configDir` honors `CAM_CONFIG_DIR`, sane defaults |
| `ui/` | Color-on/off toggling honors `NO_COLOR` and isatty fake; Reporter methods write to correct sinks |
| `cli/` | Updated `cli_test.go` integration cases (see §5.8); new tests for `--endpoints`, `--debug`, per-editor `config show/set/unset`, native completion shells |

All tests use `testing.T.Setenv`, `testing.T.TempDir`, table-driven structure, `cmd.OutOrStdout` for capture, and `t.Parallel()` where safe.

Per CLAUDE.md, after coding completes we run every Go test by enumerating files with `find` and `go test ./<pkg>`:

```bash
find . -path ./code_assistant_manager -prune -o -name '*_test.go' -print
go test ./...        # baseline
go test -race ./...  # race detector for confidence
```

## 9. Build & install

`install.sh` and `Makefile` continue to produce two binaries (`cam`, `code-agent-manager`) from the same Go source. No changes required.

CLAUDE.md mandates this reinstall sequence after any change:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed
```

This sub-project does not alter that contract.

## 10. Rollout

Single commit (or small commit chain) merged to a feature branch and PR'd to `main`. No feature flag — the Python CLI keeps running on the `code-agent-manager` Python entry point that pip installs side-by-side, so this Go change cannot break Python users.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Cobra's generated completion output differs from Python's hand-rolled scripts in ways users notice | Wrap output with banner; document migration in release notes; sub-project #10 polishes further |
| Editor metadata table goes stale as Python adds new tools | Centralized in one Go file (`editorconfig/editor.go`); add a unit test that asserts the Go list matches a JSON dump generated from Python's `list_config()` (deferred to a small later task) |
| Per-editor JSON write loses comments / preserves wrong formatting | We don't preserve comments (Python doesn't either for JSON); only TOML uses go-toml which preserves more |
| `--endpoints` global flag interfering with subcommand parsing | Implemented as PersistentPreRunE returning a sentinel error; verified by unit test |

## 12. Open decisions

None — questions answered by user:

- Full native rewrite, sub-projects one at a time, starting with Foundation.
- `cam` (Go) and `code-agent-manager` (Python) coexist; install.sh already installs both as Go binaries today, with Python still available from pip if user installs both packages.
- Test bar: table-driven unit + integration.
