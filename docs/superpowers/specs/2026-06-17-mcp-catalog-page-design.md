# MCP Catalog Page — Design

## Context

The MCP Servers page (`frontend/src/pages/MCP.tsx`) currently lists MCP servers
already installed for a single selected client (read-only). The Skills page
(`frontend/src/pages/Library.tsx`) is the desired model: a searchable catalog of
**all** resources, each row showing which agents it is installed to, with a
multi-select dropdown to install into more agents.

Most of the machinery already exists:

- A bundled MCP server catalog: 381 schemas in `internal/mcp/registry/servers/`
  (`ServerSchema` with name, description, categories, tags, `installations`, and
  an `arguments` map of `NAME → {description, required, example}`).
- `Registry.Search/Get/Names`, `ServerSchema.PreferredInstallation()`, and
  `ServerFromSchema(schema)` (builds an installable `Server` from a schema).
- `mcp.AddServer/RemoveServer/ListServers` per `ClientSpec`, and
  `mcp.SupportedClients` (15 clients).
- `desktop.MCPService.SearchRegistry/ShowServer/ListClients/ListInstalled/Add/Remove`.

**Gap:** `SearchRegistry`/`ShowServer` have no HTTP routes, there is no
"install-from-catalog" route, and nothing computes "which clients have this
server installed". The frontend only renders the per-client installed list.

**Decisions (confirmed with user):**

1. **Arguments:** When a server declares required arguments, the install flow
   prompts for them (form pre-filled with each argument's `example`). Servers
   with no required arguments install in one click.
2. **Layout:** Replace the per-client installed list with the catalog view
   (mirroring Skills).

## Design

### Backend — `internal/mcp` (catalog + install-from-schema)

1. **`Registry.All() []ServerSchema`** — returns every schema, sorted by name
   (today `Search("")` returns nil; the catalog page needs the full list). Keep
   `Search` for the query box.

2. **Argument substitution** — add `ServerSchema.RequiredArguments() []ArgumentDef`
   where `ArgumentDef{Name, Description, Example}` lists only `required: true`
   entries (sorted by name). Extend `ServerFromSchema` to take a
   `values map[string]string` and substitute every `${NAME}` in the chosen
   installation's `args` and `env`. Missing values for a *required* argument
   return an error; unreferenced/optional placeholders are left untouched.

3. **`InstalledAcrossClients(clients []ClientSpec, scope Scope) map[string][]string`**
   — reads each client once via `ListServers` and returns `serverName →
   [clientNames...]`. This is the "installed agents" equivalent, computed in one
   pass so the catalog endpoint doesn't fan out per row.

### Backend — `internal/desktop` (DTOs + service)

- New DTOs: `MCPCatalogServerDTO` (name, display_name, description, categories,
  tags, repository url, is_official, `required_arguments []MCPArgumentDTO`,
  `installed_clients []string`) and `MCPArgumentDTO` (name, description,
  example).
- `MCPService.ListCatalog(query string)` → loads the registry, optional
  `Search`, then annotates each schema with `InstalledAcrossClients` for the
  user scope. (Scope fixed to `user` for v1 — matches Skills' fixed target
  model and avoids a second selector.)
- `MCPService.InstallFromCatalog(name string, clients []string, args
  map[string]string) ([]OperationResult, error)` → `Registry.Get`, build the
  server via the new `ServerFromSchema(schema, args)`, then `AddServer` to each
  requested client at user scope. Returns one result per client so the UI can
  report partial success.
- Keep `ListClients` (the agent dropdown source) and the existing
  `Add/Remove/ListInstalled` for the detail/remove actions.

### Backend — `internal/sidecar` (HTTP)

New routes on `Server.Handler()`:

- `GET /api/mcp/catalog?q=&limit=&offset=` → `MCPService.ListCatalog`. Returns
  `{items: [...], total, limit, offset}` to mirror `MetadataSearchResponse`
  (pagination + search box parity with Skills).
- `POST /api/mcp/install` body `{name, clients[], arguments{}}` →
  `MCPService.InstallFromCatalog`, returns `{results: [...]}`.
- `DELETE /api/mcp/servers?client=&name=&scope=user` → existing
  `MCPService.Remove` (wire the route; the page removes a server from a client).
- Keep `GET /api/mcp/clients`.

### Frontend — `frontend/src/pages/MCP.tsx` (rewrite to mirror Library.tsx)

Reuse the existing `ExpandableTable`, `MultiSelect`, and `Page` components so the
look/feel matches Skills exactly.

- **Top bar:** search input + search button + "Installed only" toggle (same as
  Library). No Refresh button — the catalog is bundled, not fetched.
- **Columns:** Name | Repo (link to `repository.url`) | Installed (client
  badges, or "Not installed") | Actions (MultiSelect of clients + Install).
- **Install action:** on click, if the row has `required_arguments`, expand an
  inline form (one input per argument, pre-filled with `example`); submit calls
  `installMCP`. Otherwise install immediately to the selected clients.
- **Expanded row (DetailPanel):** description, categories/tags, the chosen
  installation command+args, and a per-client remove button for each
  `installed_clients` entry.
- **State:** `load(query)` calls `listMCPCatalog`; `installTo(server, clients,
  args)` calls `installMCP` then reloads.

### Frontend — `frontend/src/services/{api,types}.ts`

- `types.ts`: add `MCPCatalogServer`, `MCPArgument`, `MCPCatalogResponse`,
  `MCPCatalogInstallResult`. (Keep `MCPServer`/`MCPClient` for the remove path.)
- `api.ts`: add `listMCPCatalog(q, limit, offset)`, `installMCP(name, clients,
  args)`, `uninstallMCP(client, name, scope)`. Keep `listMCPClients`.

## Data flow

```
UI load ─► GET /api/mcp/clients            (agent dropdown options)
       └► GET /api/mcp/catalog?q=&...       (registry.All + InstalledAcrossClients)
install ─► POST /api/mcp/install {name, clients, arguments}
              └► ServerFromSchema(schema, args) ─► AddServer per client (user scope)
remove  ─► DELETE /api/mcp/servers?client=&name=&scope=user
```

## Error handling

- Unknown server name → 400 `MCP_SERVER_NOT_FOUND`.
- Missing required argument → 400 `MCP_MISSING_ARGUMENT` naming the argument.
- Per-client `AddServer` failure → recorded in results, does not abort other
  clients (partial success), mirroring how Skills install reports per target.
- Registry load failure → 500 `MCP_REGISTRY_LOAD_FAILED` (existing code path).

## Testing

- `internal/mcp`: `Registry.All` returns all + sorted; `RequiredArguments`
  filters `required:true`; `ServerFromSchema(schema, values)` substitutes
  `${NAME}` in args/env and errors on missing required values.
- `internal/desktop`: `ListCatalog` annotates installed clients; `InstallFromCatalog`
  installs to multiple clients and surfaces per-client errors.
- `internal/sidecar`: catalog/install/remove routes return expected shapes.
- Frontend: extend the existing `Library.test.tsx`-style patterns if present; at
  minimum manual verification against the running sidecar.

## Out of scope (v1)

- Project-scope install (user scope only).
- Editing an already-installed server's args in-place (remove + reinstall).
- Argument validation beyond "required present" (no type/format checks).
