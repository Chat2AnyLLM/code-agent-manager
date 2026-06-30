# Source-driven Prompts and MCP Catalogs Design

Date: 2026-06-24

## Goal

CAM should load prompts and MCP server catalogs by reading the upstream catalog `config.yaml` `sources:` sections and fetching each configured source directly. Runtime loading must no longer derive or consume `dist/prompts.json` or `dist/servers.json` from those upstream configs.

This applies to:

- `https://raw.githubusercontent.com/Chat2AnyLLM/awesome-prompts/master/config.yaml`
- `https://raw.githubusercontent.com/Chat2AnyLLM/awesome-mcp-servers/main/config.yaml`

## Non-goals

- Do not implement a general-purpose crawler for arbitrary catalog ecosystems.
- Do not support source formats not currently declared by those two upstream configs.
- Do not create placeholder MCP catalog entries that cannot be installed.
- Do not keep `dist/*.json` as a fallback path for these two runtime loaders.
- Do not change the desktop or CLI public DTO shapes unless needed for errors.

## Current behavior

Prompts and MCP currently treat an upstream `config.yaml` as a pointer to a generated artifact:

```text
config.yaml -> output.dir/formats -> dist/prompts.json or dist/servers.json
```

`internal/catalogconfig.DataFile` only reads the `output` section. It ignores `sources:`.

Skills, agents, instructions, and plugins use a different model: CAM reads repository definition JSON files from configured sources and then fetches repository metadata itself. This design moves prompts and MCP closer to that source-driven behavior while keeping their domain-specific models.

## Desired behavior

Prompts:

```text
awesome-prompts/config.yaml
  -> sources
  -> local / github csv / github md / github txt
  -> normalize into []AwesomePrompt
  -> SyncAll writes prompts table
```

MCP servers:

```text
awesome-mcp-servers/config.yaml
  -> sources
  -> local structured server files / github md
  -> normalize installable entries into []mcp.ServerSchema
  -> Registry merge/search/install remains unchanged
```

## Shared catalog config model

Extend `internal/catalogconfig` to parse both `output` and `sources`:

```go
type Config struct {
    Output  OutputConfig    `yaml:"output"`
    Sources []CatalogSource `yaml:"sources"`
}

type OutputConfig struct {
    Dir     string   `yaml:"dir"`
    Formats []string `yaml:"formats"`
}

type CatalogSource struct {
    Name     string `yaml:"name"`
    Type     string `yaml:"type"`
    Path     string `yaml:"path"`
    URL      string `yaml:"url"`
    Format   string `yaml:"format"`
    FilePath string `yaml:"file_path"`
}
```

Keep `DataFile` only for any remaining compatibility tests or callers. New prompts and MCP runtime paths should call a new parser such as `Parse(data []byte) (Config, error)` and consume `Config.Sources`.

## GitHub source helpers

Add small shared helpers for source aggregation:

- Parse GitHub URLs such as `https://github.com/owner/repo` into owner/repo/ref.
- Build raw file URLs for a repo, branch, and path.
- List repository trees for directory-style sources using the existing metadata browser behavior where practical.
- Resolve relative local paths in a remote config against the config repository, not the user's local filesystem.

For a remote catalog config URL, a source such as:

```yaml
- type: local
  path: prompts/
```

means files under that upstream repository path, not `./prompts` in CAM.

## Prompts loader design

### Supported source shapes

The first implementation covers the current `awesome-prompts/config.yaml` shapes:

1. `type: local`, `path: prompts/`
2. `type: github`, `format: csv`, `file_path: prompts.csv`
3. `type: github`, `format: md`, `file_path: ""`
4. `type: github`, `format: txt`, `file_path: prompts/`

Unknown source types or formats are errors because there is no `dist/prompts.json` fallback.

### Local prompts

For upstream local paths:

- List files under the configured path in the config repository.
- Fetch supported prompt files: `.yaml`, `.yml`, `.json`, `.md`, `.txt`.
- Convert each file into an `AwesomePrompt`.

Parsing rules:

- YAML/JSON: use structured fields when present: slug, title/name, description, prompt/content/text, tags, category, author, variables.
- Markdown: parse frontmatter if present; body is content; fallback title comes from filename.
- TXT: body is content; title comes from filename; category comes from parent directory or source name.

### GitHub CSV prompts

For `github + csv`:

- Fetch the configured raw CSV file.
- Use flexible column matching:
  - title/name
  - prompt/content/text
  - description
  - category
  - tags
  - author
- Skip rows without usable content.
- Use a stable source URL containing row number or stable slug:

```text
https://github.com/owner/repo/blob/<branch>/<file_path>#row=<n>
```

### GitHub Markdown prompts

For `github + md`:

- If `file_path` is non-empty, fetch that Markdown file.
- If `file_path` is empty, list the repository tree and fetch Markdown files.
- Parse frontmatter when present.
- Body becomes prompt content.
- Title falls back to filename/path.

### GitHub TXT prompts

For `github + txt`:

- If `file_path` is a directory, list files under that prefix.
- Fetch `.txt` files.
- Each file becomes one prompt.

### Prompt deduplication

The prompts table is unique by `(source, source_url)`. Source names should be stable slugs derived from config source names, for example:

- `local_prompts`
- `prompts_chat`
- `leaked_system_prompts`
- `ai_boost_awesome_prompts`

`source_url` should be a stable GitHub blob URL, optionally with a fragment for CSV rows.

### Prompt failure behavior

- Config fetch failure: return error.
- Config parse failure: return error.
- Unknown source type/format: return error.
- Source fetch failure: return error for that source and fail the overall load.
- Bad row/file inside an otherwise readable source: skip with diagnostics.
- All sources produce zero prompts: return error.

## MCP loader design

### Supported source shapes

The first implementation covers the current `awesome-mcp-servers/config.yaml` shapes:

1. `type: local`, `path: servers/`
2. `type: github`, `format: md`, `file_path: README.md`

Unknown source types or formats are errors because there is no `dist/servers.json` fallback.

### Local server schemas

For upstream local server paths:

- List files under `servers/` in `Chat2AnyLLM/awesome-mcp-servers`.
- Fetch `.json`, `.yaml`, and `.yml` files.
- Parse each into `mcp.ServerSchema`.
- Validate installable schema requirements:
  - name is non-empty
  - description is non-empty
  - installations is non-empty
  - at least one installation can become an existing `mcp.Server`

Local source entries are maintained schemas, so malformed local files should fail the source instead of being silently skipped.

### GitHub Markdown MCP sources

For `github + md`:

- Fetch the configured Markdown file.
- Extract candidate MCP entries from tables and recognizable list sections.
- Capture candidate metadata:
  - name
  - description
  - repository or homepage URL
  - categories/tags when obvious
- Build an installable `ServerSchema` only when installation can be confidently inferred.

Acceptable install inference includes:

- explicit command snippets such as `npx`, `uvx`, `docker run`, or `python -m`
- explicit package manager references with package names that can map to an existing installation type
- explicit HTTP/SSE server URLs that can map to URL-based installation

If no installable command or URL can be derived, skip the candidate. Do not create non-installable placeholder entries.

### MCP merge behavior

Merge sources in config order:

1. Local Servers
2. Punkpeye Awesome MCP Servers
3. Official MCP Servers

Earlier source wins for duplicate `ServerSchema.Name`. This preserves curated local schemas over inferred Markdown entries.

### MCP failure behavior

- Config fetch failure: return error.
- Config parse failure: return error.
- Unknown source type/format: return error.
- Local structured file malformed: return error.
- Markdown candidate not installable: skip with diagnostics.
- All sources produce zero installable servers: return error.

## Diagnostics

Use an internal diagnostic structure for tests and error messages:

```go
type SourceDiagnostic struct {
    Source  string
    Loaded  int
    Skipped int
    Errors  []string
}
```

Public APIs may keep returning current shapes, but errors should include enough source context to debug failures. Diagnostics should not include secrets or request headers.

## Compatibility

Unchanged:

- CLI and desktop MCP registry list/search/install method names.
- Existing MCP client config read/write behavior.
- Existing prompt store schema unless diagnostics require additional internal-only fields.
- Existing local MCP override path `~/.config/code-agent-manager/mcp_servers.json` can remain a direct JSON source in CAM config.

Changed:

- Runtime prompts loading no longer uses `dist/prompts.json` by default.
- Runtime MCP catalog loading no longer uses `dist/servers.json` for remote config YAML sources.
- Tests that expected `config.yaml -> dist/*.json` must be updated.
- Documentation must stop describing prompts/MCP as generated dist artifact consumers.

`CAM_AWESOME_PROMPTS_URL` is an old direct JSON override. Keep it only for explicit dev/test direct-source paths if needed. The production default should use `awesome-prompts/config.yaml` sources.

## Testing plan

### catalogconfig

- Parses `output` and `sources` from YAML.
- Preserves existing `DataFile` behavior if the function remains.
- Reports malformed YAML clearly.

### prompts

- Config `sources:` are parsed and used.
- `local` source loads prompt files from the config repository path.
- `github + csv` maps rows to prompts.
- `github + md` with empty `file_path` scans Markdown files.
- `github + txt` scans text files under a directory.
- Unknown source format returns error.
- No `dist/prompts.json` fetch occurs in source-driven tests.
- All-zero result returns error.

### MCP

- Remote config YAML `sources:` are parsed and used.
- Remote config no longer resolves to `dist/servers.json`.
- Local `servers/` loads structured schemas.
- GitHub Markdown source only loads installable entries.
- Non-installable Markdown entries are skipped.
- Duplicate names preserve earlier source priority.
- All-zero installable result returns error.

### Integration

- `cam mcp server list/search/show` still work through `mcp.LoadRegistry`.
- Desktop `ListRegistry` still returns registry items and install type.
- Prompt sync writes prompt rows from source aggregation.

## Implementation sequence

1. Extend `internal/catalogconfig` with `sources` parsing.
2. Add GitHub source helper functions or a small package for URL/raw/tree operations.
3. Replace prompt dist resolution with source aggregation.
4. Replace MCP YAML dist resolution with source aggregation.
5. Add diagnostics and source-context error messages.
6. Update tests.
7. Update README/docs wording.
8. Run focused tests, then broader project tests according to project instructions.
