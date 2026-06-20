# Instructions Page and CLI Rename — Design

## Context

CAM currently models reusable coding-agent instruction files as **prompts**:

- UI route/nav: `Prompts` renders `Library kind="prompt"`.
- Go entity kind: `KindPrompt = "prompt"`.
- CLI: `cam prompt` / alias `p`.
- Metadata: `prompt_repos.json`, `KindPrompt`, prompt discovery, and prompt install targets.
- Install paths already point at instruction-style files, not chat prompts:
  - Claude: `~/.claude/CLAUDE.md`
  - Codex/OpenCode/Cursor-style agents: `AGENTS.md`
  - Gemini: `~/.gemini/GEMINI.md`
  - Copilot: current code uses `~/.copilot/COPILOT.md`, but official Copilot docs use repository-scoped `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, and also mention `AGENTS.md`.

The product concept should be renamed to **Instructions**. Instructions are managed Markdown files that provide persistent guidance to coding agents, such as `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, Copilot custom instruction files, and project-level variants.

Confirmed decisions:

1. **Full rename:** replace the underlying `prompt` kind/storage/config/API/CLI concept with `instruction`, not just labels.
2. **Breaking prompt surface:** do not keep `cam prompt` as a long-term alias and do not keep public prompt APIs/config names. A one-time migration is allowed so existing local data is converted.

## Documentation findings to encode

Implementation should verify the current official docs again before hard-coding paths, but the initial design uses these documented rules:

### Claude Code

Official Claude Code memory docs describe `CLAUDE.md` files for persistent instructions:

- User instructions: `~/.claude/CLAUDE.md`.
- Project instructions: `./CLAUDE.md` or `./.claude/CLAUDE.md`.
- Local instructions: `./CLAUDE.local.md`.
- Managed policy instructions:
  - macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`
  - Linux/WSL: `/etc/claude-code/CLAUDE.md`
  - Windows: `C:\Program Files\ClaudeCode\CLAUDE.md`
- Claude Code reads `CLAUDE.md`, not `AGENTS.md`; for repos using `AGENTS.md`, official guidance is to create a `CLAUDE.md` that imports `@AGENTS.md` or symlink where appropriate.

### GitHub Copilot

Official GitHub Copilot custom-instructions docs describe:

- Repository-wide instructions: `.github/copilot-instructions.md`.
- Path-specific instructions: `.github/instructions/NAME.instructions.md` with frontmatter `applyTo` globs.
- Agent instructions: one or more `AGENTS.md` files anywhere in the repository, with nearest file in the directory tree winning.
- Alternative root-level agent files: `CLAUDE.md` or `GEMINI.md`.
- Personal instructions exist, but the fetched page did not provide a local file path.

### Gemini CLI

Gemini CLI context-file docs describe:

- Global context: `~/.gemini/GEMINI.md`.
- Workspace/project context: `GEMINI.md` files in configured workspace directories and parent directories.
- Just-in-time context: `GEMINI.md` files discovered as tools access files/directories.
- Default filename: `GEMINI.md`.
- Custom context names via `context.fileName` in settings, e.g. `["AGENTS.md", "CONTEXT.md", "GEMINI.md"]`.

### Codex / AGENTS.md

OpenAI Codex public docs navigation references `AGENTS.md` under Codex configuration, and the `openai/codex` repository itself uses a root `AGENTS.md`. The exact official page for hierarchy/precedence needs implementation-time verification before path rules are finalized.

## Product model

Rename the old Prompt concept to Instruction everywhere users see or automate it.

### Entity kind

- Replace `KindPrompt = "prompt"` with `KindInstruction = "instruction"`.
- Metadata rows use `kind = "instruction"`.
- UI route uses `instructions`.
- CLI command uses `cam instruction`.
- Config file uses `instruction_repos.json`.
- Embedded config uses `internal/repoconfig/embed/instruction_repos.json`.
- Tests/docs should refer to instructions unless they discuss legacy migration.

### Instruction entity

An instruction entity is a managed Markdown instruction file with:

- `name` — display name such as `Instruction 01`.
- `description` — what behavior/context it provides.
- `content` — Markdown file body.
- `repo/source` metadata for catalog-installed instructions.
- install targets: one or more coding agents.
- install level: user or project where supported.
- project directory: required for project-level installs.

The metadata index can continue treating instruction catalog items as `.md` files, analogous to the old prompt discovery. The user-facing meaning changes from reusable chat prompts to installable coding-agent instruction files.

## UI design

### Navigation

- Rename sidebar item `Prompts` → `Instructions`.
- Route should become `instructions`.
- Page title: `Instructions`.
- Description: “Search, install, and refresh coding-agent instruction files such as CLAUDE.md, AGENTS.md, GEMINI.md, and Copilot instruction files.”

### Instructions page

Reuse `Library.tsx` table patterns:

- Search box.
- Refresh button.
- Installed-only toggle.
- Expandable rows.
- Name column links to the GitHub source location through existing `item_path`/source URL behavior.
- Repo column links to the source repo.
- Status column shows installed targets.
- Actions column installs to selected agents.

### Install controls

Extend the install flow for instructions:

1. Select one or more coding agents.
2. Select install level:
   - User level.
   - Project level.
3. If project level is selected, require a project directory.
4. Install writes the instruction file to the correct agent-specific path.

The level control should be disabled or hidden when the selected target has no known path for that level. When multiple selected targets support different levels, the UI should show only levels supported by all selected targets, or show per-target validation errors. Recommended v1: show a simple global level selector and validate selected targets before install.

## CLI design

### Canonical command

Replace `cam prompt` with:

```bash
cam instruction list
cam instruction search <query>
cam instruction show <name>
cam instruction add <name> --file instruction.md --description "..."
cam instruction update <name> --file instruction.md
cam instruction remove <name>
cam instruction install <name> --app claude --level user
cam instruction install <name> --app claude --level project --project-dir /path/to/repo
cam instruction status
```

No long-term `cam prompt` alias. Running `cam prompt` after the migration should fail with a clear error such as:

> `cam prompt` was renamed to `cam instruction`. Use `cam instruction --help`.

This is intentionally not a hidden alias because the requested product surface is breaking.

### Metadata CLI

Metadata commands should accept and display `instruction`, not `prompt`:

```bash
cam metadata search --type instruction
cam metadata install --type instruction ...
```

If old `prompt` metadata/config is detected, the migration should convert it rather than preserve public prompt support.

## Install path model

Replace `promptApps` with instruction install rules that support levels.

### Data structure

Move from `map[app]string` to a richer model:

```go
type InstructionInstallPaths struct {
  UserPath string
  ProjectPath string
}
```

Examples to encode after final doc verification:

- Claude:
  - user: `~/.claude/CLAUDE.md`
  - project: `<project>/CLAUDE.md` (or `<project>/.claude/CLAUDE.md` if selected explicitly; official docs support both project forms)
- Gemini:
  - user: `~/.gemini/GEMINI.md`
  - project: `<project>/GEMINI.md`
- Copilot:
  - user: no file path from fetched docs; likely not supported in v1 until verified.
  - project/repo: `<project>/.github/copilot-instructions.md`.
  - optional path-scoped: `<project>/.github/instructions/NAME.instructions.md` is a later enhancement.
- AGENTS.md-compatible tools:
  - user: keep current known user paths where the tool has one.
  - project: `<project>/AGENTS.md`.

### README.md

`README.md` sometimes plays the instruction role informally, but v1 should **not** install to README.md by default. It can be listed in documentation as an informal convention. Installing into README.md risks overwriting human-facing project docs.

## Backend/API changes

### Entity layer

- Rename `KindPrompt` to `KindInstruction`.
- Rename prompt install comments and functions to instruction terminology.
- Update `AppPathsFor`, `SupportedApps`, install, uninstall, and installed-status detection.
- Add level-aware install for instructions.
- Preserve skill/agent/plugin behavior unchanged.

### Metadata

- Refresh kinds: `skill`, `agent`, `instruction`, `plugin`.
- Discover instructions as Markdown files, equivalent to old prompt discovery.
- Config loader uses `instruction_repos.json`.
- Embedded config file renamed to `instruction_repos.json`.
- Store/search/count use `instruction` kind.
- Detail and install endpoints accept `instruction`.

### Sidecar HTTP

Update public API surfaces:

- `GET /api/metadata/search?type=instruction`
- `POST /api/metadata/install` body uses `kind: "instruction"`.
- `GET /api/metadata/targets?kind=instruction`.
- Existing `prompt` requests should return a helpful 400 after migration, not silently work.

## Migration

On startup or metadata-store initialization, run a one-time migration:

1. Rename metadata rows `kind = 'prompt'` to `kind = 'instruction'`.
2. Rename or copy user config:
   - `prompt_repos.json` → `instruction_repos.json`.
   - If both exist, prefer `instruction_repos.json` and leave `prompt_repos.json` untouched.
3. Rename local entity storage if the Go app stores prompt entities separately.
4. Record migration completion in app state or infer idempotently from the absence of prompt rows/files.

Because the requested public surface is breaking, migration should convert data but not keep prompt command/API compatibility.

## Error handling

- Unsupported target app for instruction install → clear error naming app and level.
- Project-level install without `project_dir` → validation error before writing.
- Project path does not exist or is not a directory → validation error.
- Existing file at target path:
  - Preserve current safety behavior for app-wide instruction files; do not blindly truncate unrelated user content unless user explicitly overwrites.
  - Recommended v1: write only when target file is missing, or append/replace only when the file has a CAM-managed marker. If not managed, show “file exists; manual merge required.”
- Official path unknown (e.g. Copilot user-level) → target level is disabled or install returns “unsupported until path is verified.”

## Testing

### Go tests

- Entity kind rename compiles and all non-instruction kinds still install correctly.
- Instruction user-level install writes expected files for Claude/Gemini/AGENTS-compatible tools.
- Instruction project-level install requires project dir and writes expected files.
- Unsupported target/level returns clear errors.
- Migration converts prompt rows to instruction rows idempotently.
- Metadata search/install/targets work for `instruction` and reject `prompt`.
- CLI help lists `instruction`, not `prompt`.
- `cam prompt` fails with the rename guidance.

### Frontend tests

- Sidebar shows `Instructions`, not `Prompts`.
- Instructions page renders `Library kind="instruction"`.
- Install action exposes agent picker + level selector + project-dir field for project level.
- Source/repo links remain clickable.
- Old prompt labels disappear from i18n visible UI.

### Manual verification

- Refresh metadata.
- Install an instruction named `Instruction 01` to Claude user level and verify `~/.claude/CLAUDE.md` behavior or safe-conflict handling.
- Install to a temporary project directory and verify the project-level instruction file path.
- Run `cam instruction --help`.
- Run `cam prompt --help` and verify the intentional rename error.

## Out of scope for v1

- README.md installation.
- Copilot personal/user-level file support unless official docs provide a local file path.
- Path-scoped Copilot `.github/instructions/*.instructions.md` editor UI.
- Multi-file instruction bundles.
- Instruction merge UI for existing unmanaged files.
- Keeping `prompt` as a compatibility alias.

## Implementation sequence

1. Add instruction kind and path model.
2. Add migration from prompt data/config to instruction.
3. Update metadata refresh/search/install to use instruction.
4. Update CLI from prompt to instruction.
5. Update UI route/nav/i18n/tests.
6. Add level-aware instruction install controls and backend payload.
7. Update docs and run full tests.
