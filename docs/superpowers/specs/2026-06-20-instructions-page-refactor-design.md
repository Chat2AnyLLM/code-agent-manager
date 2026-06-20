# Instructions Page Refactor — Local CRUD + Symlink Install — Design

## Context

The current Instructions page (`frontend/src/pages/Library.tsx` rendered as
`<Library kind="instruction" />`) is a remote-catalog browser. It lists
instruction-style Markdown files discovered in upstream GitHub repos
(anthropics/skills, anthropics/claude-code, …) and installs the chosen one to a
coding-agent path such as `~/.claude/CLAUDE.md`.

The product direction has shifted. Instructions are now treated as **user-authored
local content**: the user creates an instruction file in CAM, edits it, persists
it in CAM's SQLite database, and "installs" it by linking it into the
agent-specific path. The page must show, at a glance, which instruction is wired
to which agent.

## Goals

1. Full CRUD over local instruction files (`CLAUDE.md`, `AGENTS.md`,
   `GEMINI.md`, `copilot-instructions.md`, etc.) from the Instructions page.
2. Persistence in `cam.db` (the existing `appstate` SQLite store) so search,
   listing, and disaster recovery come from a single canonical source.
3. Install one saved instruction to a coding-agent path via **symlink** so that
   editing the instruction is immediately reflected wherever it is installed.
   Fall back to **copy** on systems that cannot create symlinks.
4. UI shows the linkage from each instruction to every agent path it is
   installed at (e.g. `Instruction01 → ~/.claude/CLAUDE.md`).

## Non-goals (v1)

- Remote catalog browsing on this page (handled by Skills/Subagents/Plugins).
- Importing existing user-managed `CLAUDE.md`/`AGENTS.md` content into CAM.
- Multi-file instruction bundles.
- Append / merge of multiple instructions into one agent file.
- Path-scoped Copilot `.github/instructions/*.instructions.md` editor UI.
- Auto-syncing externally edited files back into the DB.

## Confirmed product decisions

| Decision | Value |
|---|---|
| Install model | Symlink to source file, copy fallback when symlink unavailable |
| Source of truth | Files on disk under a CAM-managed directory; DB mirrors content |
| Install levels | Both user-level and project-level supported |
| Remote catalog on this page | Removed |
| Windows symlink failure | Auto-fallback to copy, surface a "copy" badge |
| Conflict on install | Refuse and show error; never overwrite |
| Editor UI | Modal with name/description/Markdown textarea |
| Install display | Chips in the Status column with per-install × uninstall |
| Sidebar entry | Remains "Instructions" |

## Data model

Two new tables in the existing `cam.db` (`internal/appstate/store.go` schema):

```sql
CREATE TABLE IF NOT EXISTS instructions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT    NOT NULL UNIQUE,
  description  TEXT    NOT NULL DEFAULT '',
  content      TEXT    NOT NULL DEFAULT '',
  created_at   TEXT    NOT NULL,
  updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS instruction_installs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  instruction_id  INTEGER NOT NULL REFERENCES instructions(id) ON DELETE CASCADE,
  app             TEXT    NOT NULL,
  level           TEXT    NOT NULL,                -- 'user' | 'project'
  project_dir     TEXT    NOT NULL DEFAULT '',     -- '' when level='user'
  target_path     TEXT    NOT NULL,                -- absolute, expanded
  link_kind       TEXT    NOT NULL,                -- 'symlink' | 'copy'
  created_at      TEXT    NOT NULL,
  UNIQUE(app, level, project_dir)                  -- one instruction per agent path
);
```

`UNIQUE(app, level, project_dir)` enforces "one active instruction per agent
path" at the DB layer; the API surfaces this as a conflict.

Managed files live under:
```
~/.config/code-agent-manager/instructions/<safe-name>.md
```
`<safe-name>` is `name` with every character outside `[A-Za-z0-9._-]` replaced
with `_`. `pathutil.ConfigDir()` already supplies the correct base directory on
all platforms.

The legacy entity store (`internal/entities/store.go`,
`~/.config/code-agent-manager/instructions.json`) is **kept** unchanged because
the remote-catalog install flow used by Skills/Subagents/Plugins still depends
on it. The new tables are a separate, additive concern.

## Backend

### New package `internal/instructions`

```
internal/instructions/
  store.go         # CRUD on the two SQLite tables + managed-file mirror
  store_test.go
  install.go       # symlink / copy logic, conflict detection, uninstall
  install_test.go
  paths.go         # delegates to entities.InstructionPath for target paths
```

Public surface:

```go
type Instruction struct {
    ID          int64
    Name        string
    Description string
    Content     string
    CreatedAt   time.Time
    UpdatedAt   time.Time
    Installs    []Install   // populated by ListWithInstalls / Get
}

type Install struct {
    ID         int64
    App        string       // "claude", "codex", "gemini", "copilot", …
    Level      string       // "user" | "project"
    ProjectDir string       // "" when Level=="user"
    TargetPath string       // absolute, e.g. /home/u/.claude/CLAUDE.md
    LinkKind   string       // "symlink" | "copy"
    CreatedAt  time.Time
}

type Store struct { /* opens cam.db via the same path as appstate */ }

func New(dbPath string) *Store
func (s *Store) Init(ctx context.Context) error

// CRUD
func (s *Store) List(ctx context.Context) ([]Instruction, error)
func (s *Store) ListWithInstalls(ctx context.Context) ([]Instruction, error)
func (s *Store) Get(ctx context.Context, id int64) (Instruction, error)
func (s *Store) Create(ctx context.Context, name, desc, content string) (Instruction, error)
func (s *Store) Update(ctx context.Context, id int64, name, desc, content string) (Instruction, error)
func (s *Store) Delete(ctx context.Context, id int64) error

// Install
func (s *Store) Install(ctx context.Context, id int64, app, level, projectDir string) (Install, error)
func (s *Store) Uninstall(ctx context.Context, installID int64) error
```

### Managed-file mirror

`Create` and `Update` keep the SQLite row and the managed file in sync. They
are *not* a single ACID transaction across two storage systems — that's
impossible to guarantee between SQLite and the filesystem — but they are
ordered and self-healing:

1. Validate name (non-empty, no path separators, unique).
2. Write the managed file `~/.config/code-agent-manager/instructions/<safe-name>.md`
   atomically via tmp + `os.Rename`. If this fails, return the error and make
   no DB changes.
3. In a single SQLite transaction:
   a. Insert/update the `instructions` row.
   b. If `name` changed, `os.Rename` the old managed file to the new path and
      re-target every `instruction_installs.target_path` symlink that points
      at the old file. `link_kind="copy"` rows are left alone (the copy
      becomes stale until re-install).
   c. Commit.
4. If step 3 fails after the file write succeeded, attempt to roll the file
   back to its prior content (best-effort). Log and surface the inconsistency
   if the rollback also fails; the next successful `Update` re-syncs both
   sides.

### Install algorithm

```text
target = entities.InstructionPath(app, level, projectDir)
existing, errLstat = os.Lstat(target)
if errLstat == nil:
    if existing.Mode()&os.ModeSymlink != 0:
        resolved = os.Readlink(target)
        if resolved is under our managed dir AND owned by a different instruction:
            return ConflictError("<otherName> is currently installed at <target>; uninstall it first")
    return ConflictError("file already exists at <target>; remove it and retry")

os.MkdirAll(dir(target), 0o755)
src = managed file for this instruction
err = os.Symlink(src, target); linkKind = "symlink"
if err is windows ERROR_PRIVILEGE_NOT_HELD:
    err = copyFile(src, target); linkKind = "copy"
INSERT into instruction_installs(... link_kind=linkKind, target_path=target)
```

### Uninstall

```text
info, errLstat = os.Lstat(install.TargetPath)
if errLstat == nil:
    if info.Mode()&os.ModeSymlink != 0 and os.Readlink == our managed file:
        os.Remove(install.TargetPath)
    else if linkKind == "copy" and content(target) == content(managed file):
        os.Remove(install.TargetPath)
    else:
        leave the file in place (likely user-edited; refuse to destroy)
DELETE from instruction_installs WHERE id = install.ID
```

`Delete(instructionID)` calls `Uninstall` for every install, then deletes the
managed file, then deletes the row (`ON DELETE CASCADE` clears install rows).

### Errors surfaced to callers

- `ErrDuplicateName`            — Create/Update with a name already taken.
- `ErrInvalidName`              — empty or contains a path separator.
- `ErrInstructionNotFound`      — Get/Update/Delete/Install on unknown ID.
- `ConflictError`               — install target already exists.
- `ErrUnsupportedTarget`        — app does not support the requested level.
- `ErrProjectDirRequired`       — level=project with empty projectDir.

## HTTP API (sidecar)

New file `internal/sidecar/instructions_handler.go`, wired in `server.go`
alongside the metadata routes.

```
GET    /api/instructions                       → [{id,name,description,updated_at,installs:[…]}]
POST   /api/instructions                       body: {name,description,content}                → Instruction
GET    /api/instructions/{id}                  → Instruction (with content + installs)
PUT    /api/instructions/{id}                  body: {name,description,content}                → Instruction
DELETE /api/instructions/{id}                  → 204

POST   /api/instructions/{id}/installs         body: {app,level,project_dir}                   → Install
DELETE /api/instructions/installs/{installId}  → 204

GET    /api/instructions/targets               → [{app, supports:{user:bool, project:bool}}]
```

Status codes:
- `201 Created` for POST `/api/instructions` and POST `…/installs`.
- `204 No Content` for the two DELETEs.
- `400` for validation errors (`ErrInvalidName`, `ErrProjectDirRequired`,
  `ErrUnsupportedTarget` — the (app, level) combination is rejected on input).
- `404` for unknown IDs (`ErrInstructionNotFound`).
- `409` for `ErrDuplicateName` and `ConflictError` (target path already
  occupied by something CAM did not place there in this install action).

The `/api/instructions/targets` response is derived from
`entities.instructionApps`:

```json
[
  {"app":"claude",  "supports":{"user":true,"project":true}},
  {"app":"gemini",  "supports":{"user":true,"project":true}},
  {"app":"copilot", "supports":{"user":false,"project":true}},
  {"app":"codex",   "supports":{"user":true,"project":true}},
  …
]
```

The existing `/api/metadata/*` endpoints continue to handle catalog flows for
the other kinds and are untouched.

## Frontend

### Routing

`frontend/src/App.tsx`:

```tsx
{route === 'instructions' && <Instructions />}
```

`<Library kind="instruction" />` is removed from the route table. `Library.tsx`
keeps serving the other three kinds (`skill`, `agent`, `plugin`) unchanged.

### New page `frontend/src/pages/Instructions.tsx`

Components:

- `Instructions` — page-level; fetches `/api/instructions` on mount, holds
  search, modal-open state, install-popover state.
- `InstructionsTable` — wraps `ExpandableTable`. Columns: Name, Description,
  Installed (chips), Actions (Edit / Install ▾ / Delete). Expanding a row shows
  the Markdown content as a read-only `<pre>` plus a list of installs with
  full target paths.
- `EditorModal` — opened by `+ New instruction` or `Edit`. Fields:
  - Name: text input, validated unique client-side after debounce and
    server-side on submit; restricted to `[A-Za-z0-9._-]`.
  - Description: text input.
  - Content: monospace `<textarea>` of approximately 20 rows.
  - Buttons: Save (POST or PUT), Cancel.
- `InstallPopover` — opened by `Install ▾`. Fields:
  - Agent: dropdown populated from `/api/instructions/targets`.
  - Level: radio with User / Project. Each radio disables itself based on the
    selected agent's `supports` map.
  - Project directory: text input visible only when Level=Project; required.
  - Install button → POST `/api/instructions/{id}/installs`; on 409 the error
    text is rendered inside the popover, the popover stays open.
- `InstalledChip` — renders e.g. `claude (user) ×`. `×` calls
  DELETE `/api/instructions/installs/{installId}`. `link_kind="copy"` chips get
  a subdued "copy" suffix and a tooltip explaining that re-installation is
  required to pick up edits.

### Service layer

Extend `frontend/src/services/api.ts` with:

```ts
listInstructions(): Promise<Instruction[]>
getInstruction(id: number): Promise<Instruction>
createInstruction(body: {name; description; content}): Promise<Instruction>
updateInstruction(id, body): Promise<Instruction>
deleteInstruction(id): Promise<void>
installInstruction(id, {app, level, project_dir}): Promise<Install>
uninstallInstruction(installId): Promise<void>
instructionTargets(): Promise<Array<{app: string; supports: {user: boolean; project: boolean}}>>
```

Types added to `services/types.ts`.

### i18n

Add `instructions.*` keys (page title, button labels, modal labels, error
messages). Remove `library.instructions.*` keys once the new page lands.

### Existing `Library.tsx`

Loses its `instruction` kind branches but otherwise unchanged. The
`titleKeys`/`descriptionKeys` records drop the `instruction` entries.

## Error handling

| Situation | Behavior |
|---|---|
| Duplicate name on Create/Update | 409 `instruction named '<name>' already exists`; modal shows it under the Name field. |
| Empty / path-separator name | 400; same error shown in the modal. |
| Install target already exists (not our symlink) | 409 `file already exists at <target>; remove it and retry`; popover stays open. |
| Install target is our symlink for a different instruction | 409 `<otherName> is currently installed at <target>; uninstall it first`. |
| Install with unsupported level for that agent | 409 `<app> does not support <level>-level installs`. |
| Symlink failure on Windows | Silent fallback to copy; install row records `link_kind="copy"`; first occurrence per session surfaces a one-time info banner. |
| Delete instruction while installs exist | Cascade: each install is uninstalled (best-effort filesystem cleanup, errors logged) before the DB row is removed. |
| Rename | Managed file renamed atomically; symlink installs re-targeted; copy installs become stale until re-install. |
| External edit to the managed file | Symlink installs reflect it instantly; DB `content` column drifts (acceptable for v1, no auto-sync). |

## Testing

### Go — `internal/instructions/`

- `store_test.go`:
  - Create / List / Get / Update / Delete round-trip.
  - Rename moves the managed file and re-targets symlinks; leaves copies stale.
  - Duplicate-name returns `ErrDuplicateName`.
  - Empty / path-separator name returns `ErrInvalidName`.
  - Delete cascades install rows.
- `install_test.go`:
  - Symlink install on Unix; resolved link points at the managed file.
  - Copy fallback when `os.Symlink` returns `ERROR_PRIVILEGE_NOT_HELD` (mocked
    in the test by injecting a forced-failure variant of the syscall on
    non-Windows so coverage is portable).
  - Conflict when target exists.
  - Conflict when our own symlink there already points at a different
    instruction.
  - User vs project paths resolve via `entities.InstructionPath`.
  - Uninstall removes our symlink; leaves user-edited copies in place.

### Go — `internal/appstate/store_test.go` (extended)

- Opening a `cam.db` from before this change creates the new tables without
  losing existing `providers` / `app_state` rows.

### Go — `internal/sidecar/instructions_handler_test.go`

- Each endpoint: happy path plus the validation/conflict errors above.
- `targets` returns the expected app map.

### Frontend — `frontend/src/pages/Instructions.test.tsx`

- Empty state renders, then a created instruction appears.
- Editor modal: create, edit, delete flows; validation errors render inline.
- Install popover: agent + level selection; project-dir requirement;
  successful install adds a chip; uninstall chip × removes the install.
- Server 409 conflict renders inside the popover and the popover stays open.

### Manual smoke (per project `CLAUDE.md` reinstall flow)

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
```

Then:

1. Create `Instruction01` with sample content.
2. Install to Claude (user-level). Verify `~/.claude/CLAUDE.md` is a symlink
   pointing at `~/.config/code-agent-manager/instructions/Instruction01.md`.
3. Edit the content in the modal. Re-open `~/.claude/CLAUDE.md`; the change
   is visible.
4. Install the same instruction to a Codex project-level path; verify
   `<project>/AGENTS.md` is a symlink to the same managed file.
5. Uninstall the Claude install via the chip ×; verify the symlink is removed
   and the file is gone, but the managed file (and the Codex install) remain.

## Implementation sequence

1. Add the two `CREATE TABLE` statements to `internal/appstate/store.go`'s
   `schemaSQL`; verify existing DBs upgrade.
2. Build `internal/instructions` package: `Store` + CRUD + managed-file mirror.
3. Add install / uninstall: symlink-with-copy-fallback, conflict detection.
4. Wire sidecar handlers under `/api/instructions/*` and add handler tests.
5. Extend `frontend/src/services/api.ts` + `services/types.ts`.
6. Build `frontend/src/pages/Instructions.tsx` and its sub-components.
7. Switch `frontend/src/App.tsx` to render `<Instructions />` in place of
   `<Library kind="instruction" />`.
8. Update i18n keys (`instructions.*` added, `library.instructions.*` removed).
9. Get all Go and frontend tests green.
10. Reinstall per project `CLAUDE.md` and run the manual smoke checklist.
