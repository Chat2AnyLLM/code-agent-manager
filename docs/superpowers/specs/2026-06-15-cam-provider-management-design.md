# `cam provider` — CLI management of SQLite-backed provider records

**Date:** 2026-06-15
**Status:** Design approved, implementation in progress

## Goal

Eliminate manual editing of legacy provider files in favor of SQLite-backed provider management.
Every operation a user needs to perform on the provider catalog must be reachable through `cam` subcommands:

1. If nothing is configured, create the file.
2. Show all providers.
3. Add / remove / update providers.
4. Never require hand-editing JSON.

## Architecture

### 1. Storage layer — `internal/providers/store.go`

A thin write layer on top of the existing read-only `providers.go`. Pure functions, no side effects beyond the explicit `Save` call.

```go
// LoadOrInit loads the file at path. If the file does not exist, it returns
// an empty File{Common:{}, Endpoints:{}} and created=true so callers can
// inform the user that a new file will be written on Save.
func LoadOrInit(path string) (File, bool, error)

// Save writes file to path atomically with 0o600 permissions and 2-space
// JSON indentation. Parent directories are created with 0o700.
func Save(path string, file File) error

// Add inserts ep under name. Returns an error if name already exists.
func Add(file *File, name string, ep Endpoint) error

// Update applies the sparse patch to the endpoint named name. Returns an
// error if the endpoint does not exist.
func Update(file *File, name string, patch Patch) error

// Remove deletes the endpoint named name. Returns false if it was absent.
func Remove(file *File, name string) bool

// Rename moves an endpoint key from oldName to newName.
func Rename(file *File, oldName, newName string) error

// SetEnabled toggles the Enabled flag on the named endpoint.
func SetEnabled(file *File, name string, enabled bool) error
```

`Patch` is a sparse struct: every field is a pointer so callers can express "do not change this". For list fields (`SupportedClient`, `Models`) the patch carries an explicit operation (`SetOp`, `AddOp`, `RemoveOp`) so `cam provider update name --client +droid` can append without replacing.

### 2. CLI layer — `internal/cli/provider_cmd.go`

Wires the cobra command tree. Pattern mirrors `internal/cli/config_cmd.go`:
each subcommand is its own private function that returns a `*cobra.Command`.
All commands honour the existing `--providers PATH` persistent flag and fall back to `providers.DiscoverPath()`.

### 3. App wiring — `internal/cli/app.go`

A single new line: `root.AddCommand(a.providerCommand(state))`.
The root command's `Long` help text is updated to include the `provider/pr` alias.

## Commands

| Command | Purpose |
|---------|---------|
| `cam provider list` | Table: NAME, ENDPOINT, CLIENTS, ENABLED. `--json` for raw. `--enabled-only` to hide disabled. |
| `cam provider show NAME` | Full record (pretty JSON). API key masked by default, `--reveal-key` resolves and shows it. |
| `cam provider add NAME --endpoint URL [opts...]` | Strict: fails if NAME exists. |
| `cam provider update NAME [opts...]` | Strict: fails if NAME missing. Only provided flags change. |
| `cam provider remove NAME` | Confirms unless `--yes`. |
| `cam provider enable NAME` / `disable NAME` | Sets `enabled: true` / `false`. |
| `cam provider rename OLD NEW` | Renames a key, preserving its value. |
| `cam provider init` | No-op if file exists, otherwise writes the empty skeleton. |

Auto-creation: any subcommand that mutates the file calls `LoadOrInit` and writes the skeleton implicitly on first save, so users do not have to run `init` first.

### Flag surface for `add` / `update`

```
--endpoint URL                  (required for add)
--api-key-env NAME              env var holding the key
--client a,b,c                  comma-separated supported_client
--model a,b,c                   list_of_models
--list-models-cmd CMD           shell command for dynamic model discovery
--description TEXT              human-readable description
--use-proxy / --no-use-proxy    bool
--keep-proxy-config / --no-...  bool
--enabled / --disabled          on add only; later use enable/disable subcommands
```

On `update`, the `--client` and `--model` flags accept a `+`, `-`, or `=` prefix to add, remove, or replace items respectively. With no prefix the value is treated as a full replacement (matches add semantics).

## Data flow — `cam provider add NAME ...`

```
user
  → cobra parses flags
  → providers.LoadOrInit(path)            in-memory skeleton if file is missing
  → providers.Add(file, name, endpoint)   error if duplicate
  → providers.Save(path, file)            atomic, 0o600, indent 2
  → stdout: "Added provider 'NAME' to PATH"
```

## Error handling

- Missing required flags for `add` → cobra-level error.
- Duplicate name on `add` → `provider "NAME" already exists`.
- Unknown name on `update`/`remove`/`enable`/`disable`/`rename` → `provider "NAME" not found (try 'cam provider list')`.
- Malformed legacy `providers.json` on migration/load → explicit legacy parse error, unchanged.
- File-write errors → wrapped as `provider: write %s: %w`.
- Permissions: file `0o600`, parent dir `0o700`.

## Testing

Two new test files, both following the existing repo idioms (`t.TempDir`, `t.Setenv`, table-driven where it pays).

`internal/providers/store_test.go`:
- LoadOrInit: existing file, missing file (returns skeleton + `created=true`), malformed JSON.
- Add: happy path, duplicate name.
- Update: sparse patch, list `+`/`-`/`=`, unknown name.
- Remove: happy path, missing key.
- Rename: happy path, source missing, destination collision.
- SetEnabled: enable, disable, unknown name.
- Save: round-trip equality, file mode `0600`, parent-dir creation.

`internal/cli/cmd_provider_test.go`:
- `list` empty / populated / `--json` / `--enabled-only`.
- `show` masked vs `--reveal-key`.
- `add` happy / duplicate / missing-endpoint / with all flags.
- `update` patch / `+`/`-`/`=` list operations / unknown name.
- `remove` happy / missing / `--yes`.
- `enable`, `disable`, `rename`, `init` (first-run vs idempotent).

## Backward compatibility

- `providers.Endpoint` struct gains no new fields. All existing readers (`launch`, `doctor`) work unchanged.
- SQLite is now the source of truth; any remaining providers.json handling is legacy-only.
- README updates should now point users at `cam provider add ...`; this spec is historical context for the original command design.

## Out of scope

- Interactive wizard / TUI for `add`.
- Editing `common` settings (proxies, cache_ttl). A future `cam provider common set KEY VALUE` can build on the same store layer.
- Validating that `--endpoint` is a reachable URL (doctor already does that).
