# providers.json Deprecation — Design

## Context

CAM provider data is already stored in the SQLite app state database. The legacy `~/.config/code-agent-manager/providers.json` file is now a stale secondary source that can be re-created by install/setup flows and re-imported into SQLite. Provider configuration should have one source of truth.

Confirmed decision: `providers.json` should be fully deprecated, no longer read or imported, and deleted when encountered. There is no archive/backup step and no fallback compatibility path.

## Goals

- SQLite app state is the only provider source of truth.
- CAM no longer creates, reads, imports, writes, restores, or documents `providers.json` as an active config file.
- The default `~/.config/code-agent-manager/providers.json` is deleted if present.
- `--providers` is removed and no longer points commands at a JSON file.
- Existing provider CLI and desktop flows continue to operate through SQLite.

## Non-goals

- Do not migrate data from `providers.json` during this change.
- Do not archive `providers.json` before deleting it.
- Do not keep a hidden compatibility import path.
- Do not redesign provider schemas or provider command UX.

## Architecture

### Provider storage

`internal/appapi.ProviderAPI` will use `appstate.Store` directly for all provider operations. Methods that currently call `store.ImportProvidersJSON(ctx, api.path())` will stop doing so. `File()` will continue to return the legacy `providers.File` shape for internal callers, but it will be populated from SQLite only.

### Legacy file cleanup

A provider cleanup helper will delete `providers.DefaultPath()` when it exists. This helper should run from provider initialization/startup paths so normal CAM usage removes the obsolete file. Deletion failure should return a clear error, because continuing would leave the deprecated file in place.

The cleanup should only target the canonical default path. There is no custom providers JSON path: the deprecated `--providers` flag is removed.

### Removed `--providers` flag

The root `--providers` flag is removed. Provider commands always use the SQLite app state database selected by `--store` or the default app state path.

### Install and docs

`install.sh` must stop creating `~/.config/code-agent-manager/providers.json` from `providers.json` or `providers.json.example`.

Documentation and project instructions should stop telling users or agents to restore `providers.json.bak`. If a sample provider file remains in the repository, it must be documented as a historical/sample artifact only, not an installed config.

## Data flow

### Provider init/list/show/update

1. Caller invokes provider operation.
2. Provider commands use the SQLite app state path selected by `--store` or the default path.
3. Initialize/open SQLite app state.
4. Delete canonical `providers.json` if present.
5. Read/write provider records from SQLite only.

### Install script

1. Build/install binaries as before.
2. Create required config directories as before.
3. Do not create `providers.json`.
4. Do not copy `providers.json.example`.

## Error handling

- Missing SQLite provider rows: existing empty-provider behavior remains.
- Removed `--providers`: Cobra returns an unknown-flag error.
- Default `providers.json` delete failure: return wrapped error identifying the path.
- Missing `providers.json`: no-op.

## Testing

Go tests should cover:

- `ProviderAPI.Init` deletes canonical `providers.json`.
- `ProviderAPI.File/List/Show/ResolveModels` do not import rows from `providers.json`.
- Provider CLI with `--providers` returns an unknown-flag error.
- Provider commands still add/list/update/remove records through SQLite.
- Installer no longer creates `providers.json` from sample files.

Verification should include:

- Full Go package test sweep discovered with `find` and run package-by-package.
- Frontend tests/build if frontend files are touched.
- Project reinstall sequence updated to omit `providers.json.bak` restore.

## Rollout notes

This is a breaking cleanup. Users with provider data only in `providers.json` must recreate providers via `cam provider add` or existing SQLite-backed UI flows. This matches the confirmed decision to stop reading and delete the file rather than migrate or archive it.
