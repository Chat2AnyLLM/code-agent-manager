# Repo Config Driven Catalogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure skills, subagents, plugins, and awesome-prompts use `awesome-repo-configs` as the catalog source instead of directly crawling Chat2AnyLLM catalog repositories, while keeping UI data visible.

**Architecture:** Remove Chat2AnyLLM catalog repositories from bundled fallback repo configs so only user local files and `awesome-repo-configs` remote sources drive metadata refresh. Update prompt sync to resolve the awesome-prompts catalog URL from repo config first, then fall back to the existing environment override/default/bundled JSON behavior. Preserve local prompt rows by upserting awesome-prompts rows rather than replacing unrelated prompt sources.

**Tech Stack:** Go metadata/repoconfig/prompts packages, SQLite stores, React/Vitest Library UI tests, PowerShell/npm/go test verification.

---

## Files

- Modify: `internal/repoconfig/embed/skill_repos.json` — remove Chat2AnyLLM skills catalog fallback.
- Modify: `internal/repoconfig/embed/agent_repos.json` — remove Chat2AnyLLM agents catalog fallback.
- Modify: `internal/repoconfig/embed/plugin_repos.json` — remove Chat2AnyLLM plugins catalog fallback.
- Modify: `internal/repoconfig/embed/prompt_repos.json` — remove direct awesome-prompts fallback catalog.
- Modify: `internal/repoconfig/repoconfig_test.go` — assert bundled fallbacks no longer include Chat2AnyLLM catalogs and remote/local loading still works.
- Modify: `internal/prompts/service.go` — resolve awesome-prompts catalog from repo config before hardcoded URL.
- Modify: `internal/prompts/service_test.go` — assert SyncAll uses configured repo catalog URL and preserves local prompts.
- Keep: `frontend/src/pages/Library.tsx` and `frontend/src/pages/Library.test.tsx` — already show descriptions in list rows.
- Keep: `internal/sidecar/server.go` and `internal/sidecar/server_test.go` — already allow localhost/127.0.0.1 dev UI CORS.

## Task 1: Remove bundled Chat2AnyLLM catalog fallbacks

- [ ] Write failing tests in `internal/repoconfig/repoconfig_test.go`:
  - `TestBundledSkillReposDoNotIncludeChat2AnyLLMCatalog`
  - `TestBundledAgentReposDoNotIncludeChat2AnyLLMCatalog`
  - `TestBundledPluginReposDoNotIncludeChat2AnyLLMCatalog`
  - `TestBundledPromptReposDoNotIncludeDirectAwesomePrompts`
- [ ] Run `go test ./internal/repoconfig` and verify these fail because the bundled JSON still contains those entries.
- [ ] Replace the four bundled JSON files with `{}`.
- [ ] Update older tests that expected bundled repos to exist.
- [ ] Re-run `go test ./internal/repoconfig` and verify it passes.

## Task 2: Make awesome-prompts resolve through repo config first

- [ ] Write a failing test in `internal/prompts/service_test.go` that writes `prompt_repos.json` with a configured `Chat2AnyLLM/awesome-prompts` branch/catalog file and asserts `SyncAll` fetches that configured URL.
- [ ] Run `go test ./internal/prompts` and verify the new test fails because the service still uses the hardcoded URL.
- [ ] Add a small resolver in `internal/prompts/service.go` that calls `repoconfig.LoadEnabled(entities.KindPrompt)` and picks `Chat2AnyLLM/awesome-prompts` when present.
- [ ] Build the raw GitHub URL from `owner`, `repo`, `branch`, and `catalogFile`, defaulting catalog file to `dist/prompts.json`.
- [ ] Preserve environment override behavior: if `CAM_AWESOME_PROMPTS_URL` is set, use it before repo config.
- [ ] Re-run `go test ./internal/prompts` and verify it passes.

## Task 3: Verify UI data chain

- [ ] Run `cam metadata refresh` using the rebuilt binary or `go run . metadata refresh` if testing before install.
- [ ] Verify `cam metadata search "" --type skill`, `--type agent`, and `--type plugin` return data from non-Chat2AnyLLM source repos where possible.
- [ ] Run `npm --prefix frontend test -- Library.test.tsx` to verify the Library UI renders rows and descriptions.
- [ ] Run relevant sidecar tests for CORS and metadata search.

## Task 4: Required project reinstall and final tests

- [ ] Run repository-required reinstall commands after code changes:
  - `rm -rf dist/*`
  - `./install.sh uninstall`
  - `./install.sh`
- [ ] Run all relevant tests one by one per project instruction.
- [ ] Re-run metadata refresh and confirm UI/API data is visible.

## Self-review

- No placeholders remain.
- Each requirement maps to a task: catalog source cleanup (Task 1), awesome-prompts repo-config flow (Task 2), UI data visibility (Task 3), project reinstall and verification (Task 4).
- Type names match existing code: `repoconfig.RepoEntry`, `entities.KindPrompt`, `prompts.Service`, `SyncAll`.
