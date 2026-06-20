# Wails Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Wails-style React desktop frontend with Go backend services exposing code-agent-manager operations, comprehensive tests, and passing validation.

**Architecture:** Keep existing CLI binaries intact. Add `internal/desktop` as a thin API/service layer over existing Go packages and add `frontend` as a React/Vite/TypeScript UI. Use tests to drive service behavior and frontend pages.

**Tech Stack:** Go, React, TypeScript, Vite, Vitest, React Testing Library, lightweight CSS, Playwright smoke test scaffold.

---

## Files

### Create
- `internal/desktop/types.go` — shared DTOs and structured errors.
- `internal/desktop/provider_service.go` — provider API methods.
- `internal/desktop/mcp_service.go` — MCP API methods.
- `internal/desktop/entity_service.go` — prompt/skill/agent/plugin API methods.
- `internal/desktop/tool_service.go` — tool/lifecycle API methods.
- `internal/desktop/doctor_service.go` — doctor checks API methods.
- `internal/desktop/config_service.go` — config API methods.
- `internal/desktop/launch_service.go` — launch planning API methods.
- `internal/desktop/app_service.go` — version/app helper API methods.
- `internal/desktop/*_test.go` — service tests.
- `cmd/cam-desktop/main.go` — desktop app entry point.
- `frontend/package.json` — frontend scripts and dependencies.
- `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/*` — React app.
- `frontend/src/pages/*.tsx` — seven UI pages.
- `frontend/src/services/api.ts` — typed API adapter.
- `frontend/src/test/*.test.tsx` — frontend tests.
- `frontend/tests/e2e/smoke.spec.ts` — Playwright smoke scaffold.

### Modify
- `go.mod` — add any required Go dependencies only if needed.
- `install.sh` — add desktop build/install/uninstall support.

---

## Task 1: Add desktop DTOs and error helpers

**Files:**
- Create: `internal/desktop/types.go`
- Test: `internal/desktop/types_test.go`

- [ ] Write tests for `NewError`, `ProviderDTO`, and operation response structs.
- [ ] Implement DTOs with JSON tags.
- [ ] Run: `go test ./internal/desktop -run TestAppError -v`.

## Task 2: Provider service

**Files:**
- Create: `internal/desktop/provider_service.go`
- Test: `internal/desktop/provider_service_test.go`

- [ ] Write tests using temp `CAM_CONFIG_DIR` and temp providers path.
- [ ] Implement `NewProviderService`, `List`, `Show`, `Add`, `Update`, `Remove`, `Enable`, `Disable`, `Rename`, `Init`, `ResolveModels`.
- [ ] Run: `go test ./internal/desktop -run TestProviderService -v`.

## Task 3: MCP service

**Files:**
- Create: `internal/desktop/mcp_service.go`
- Test: `internal/desktop/mcp_service_test.go`

- [ ] Write tests for clients list, registry search, and installed listing with temp config.
- [ ] Implement `ListClients`, `SearchRegistry`, `ShowServer`, `ListInstalled`.
- [ ] Implement safe `Add` and `Remove` wrappers.
- [ ] Run: `go test ./internal/desktop -run TestMCPService -v`.

## Task 4: Entity service

**Files:**
- Create: `internal/desktop/entity_service.go`
- Test: `internal/desktop/entity_service_test.go`

- [ ] Write tests for kind validation and local store list/search.
- [ ] Implement `List`, `Search`, `Install`, `Uninstall`, `Update` with clear errors for unsupported paths.
- [ ] Run: `go test ./internal/desktop -run TestEntityService -v`.

## Task 5: Tool and launch services

**Files:**
- Create: `internal/desktop/tool_service.go`
- Create: `internal/desktop/launch_service.go`
- Test: `internal/desktop/tool_service_test.go`
- Test: `internal/desktop/launch_service_test.go`

- [ ] Write tests for tool listing, launch choices, and dry-run planning.
- [ ] Implement `ToolService.List`, `ToolService.Install`, `ToolService.Uninstall`, `ToolService.Upgrade`.
- [ ] Implement `LaunchService.ListTools`, `ListProvidersForTool`, `ListModelsForProvider`, `DryRun`.
- [ ] Run: `go test ./internal/desktop -run 'Test(Tool|Launch)Service' -v`.

## Task 6: Config, doctor, and app services

**Files:**
- Create: `internal/desktop/config_service.go`
- Create: `internal/desktop/doctor_service.go`
- Create: `internal/desktop/app_service.go`
- Test: `internal/desktop/config_service_test.go`
- Test: `internal/desktop/doctor_service_test.go`
- Test: `internal/desktop/app_service_test.go`

- [ ] Write tests for config file listing, app version, and doctor result mapping.
- [ ] Implement config read/edit wrappers.
- [ ] Implement doctor check runner returning structured results.
- [ ] Implement version helper.
- [ ] Run: `go test ./internal/desktop -v`.

## Task 7: Desktop entry point

**Files:**
- Create: `cmd/cam-desktop/main.go`

- [ ] Add a buildable Go entry point that wires services.
- [ ] If Wails v3 is unavailable in the environment, keep the entry build-tagged or dependency-light so the repo still tests.
- [ ] Run: `go test ./cmd/cam-desktop ./internal/desktop`.

## Task 8: React frontend scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`

- [ ] Add scripts: `test`, `test:run`, `test:coverage`, `build`, `test:e2e`.
- [ ] Build app shell with sidebar navigation and seven routes.
- [ ] Run: `npm --prefix frontend test -- --run`.

## Task 9: API adapter and mocked bindings

**Files:**
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/mockData.ts`
- Test: `frontend/src/services/api.test.ts`

- [ ] Implement typed adapter that uses Wails bindings when present and mock fallback in browser/test mode.
- [ ] Test all adapter methods return typed data.
- [ ] Run: `npm --prefix frontend test -- --run src/services/api.test.ts`.

## Task 10: Pages and components

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Providers.tsx`
- Create: `frontend/src/pages/MCP.tsx`
- Create: `frontend/src/pages/Library.tsx`
- Create: `frontend/src/pages/Configuration.tsx`
- Create: `frontend/src/pages/Diagnostics.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: reusable components under `frontend/src/components/`
- Test: `frontend/src/pages/*.test.tsx`

- [ ] Implement each page with visible operations matching the CLI command surface.
- [ ] Add page tests that assert critical controls render and invoke API methods.
- [ ] Run: `npm --prefix frontend test -- --run`.

## Task 11: Frontend coverage and build

**Files:**
- Modify: `frontend/package.json`
- Create: additional tests as needed.

- [ ] Run frontend tests with coverage.
- [ ] Add missing tests until meaningful coverage is achieved.
- [ ] Run frontend build.

## Task 12: Playwright smoke scaffold

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/smoke.spec.ts`

- [ ] Add one smoke test that opens the built frontend and verifies Dashboard/Providers/Diagnostics navigation.
- [ ] Run: `npm --prefix frontend run test:e2e` if browser deps are available; otherwise document the environment limitation in final output.

## Task 13: install.sh desktop support

**Files:**
- Modify: `install.sh`
- Test: use shell syntax check and dry-run behavior if supported.

- [ ] Add `--desktop` parsing.
- [ ] Add desktop build/install helper.
- [ ] Add uninstall cleanup for `cam-desktop` and Linux `.desktop` entry/icon.
- [ ] Run: `bash -n install.sh`.

## Task 14: Full verification

**Files:** all changed files.

- [ ] Run all Go tests discovered via `find . -name '*_test.go'` package-by-package, as required by project instructions.
- [ ] Run frontend tests.
- [ ] Run frontend build.
- [ ] Run reinstall sequence required by `CLAUDE.md`:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed
```

- [ ] Report exact pass/fail results.

## Self-Review

- Spec coverage: backend services, seven pages, tests, install support, CLI coexistence are all represented.
- Placeholder scan: no TBD/TODO/later placeholders remain.
- Type consistency: services and frontend adapter use matching DTO names.
