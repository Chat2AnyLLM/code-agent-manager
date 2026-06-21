# Borrowing Findings: CC-Switch → Code-Agent Manager

## Date: 2026-06-21

---

## Overview

Analysis of borrowing reusable patterns and components from [CC-Switch](https://github.com/farion1231/cc-switch) (v3.12.3) to enhance [Code-Agent Manager](https://github.com/Chat2AnyLLM/code-agent-manager).

---

## High Priority (Directly Reusable)

### 1. TanStack Query for State Management
- **CC-Switch**: v5 for server state, caching, auto-refetch, optimistic updates
- **CAM**: useState + localStorage
- **Impact**: Major - Eliminates manual state sync, reduces bugs
- **Files to study**: `src/lib/query/queries.ts`, `src/lib/query/mutations.ts`, `src/lib/query/queryClient.ts`

### 2. shadcn/ui Component Library
- **CC-Switch**: 23 Radix-based components (Dialog, Sheet, Popover, Tabs, Switch, etc.)
- **CAM**: Basic ExpandableTable/MultiSelect
- **Impact**: Major - Professional UI foundation
- **Files to study**: `src/components/ui/` directory

### 3. Zod + react-hook-form
- **CC-Switch**: Schema validation, type-safe forms
- **CAM**: No validation
- **Impact**: High - Prevents invalid data entry
- **Files to study**: `src/lib/schemas/`, form components in `src/components/providers/`

### 4. react-i18next
- **CC-Switch**: 3 languages (en/zh/ja), namespace separation
- **CAM**: Basic en/zh
- **Impact**: High - Scalable i18n
- **Files to study**: `src/i18n/`, `src/i18n/locales/`

### 5. MSW for Tauri IPC Mocking
- **CC-Switch**: Mock Service Worker mocking `invoke()` calls
- **CAM**: No Tauri IPC mocking
- **Impact**: High - Reliable frontend testing
- **Files to study**: `tests/msw/` directory

### 6. Error Handling Patterns
- **CC-Switch**: `AppError` enum, error mapping layers, user-friendly messages
- **CAM**: Basic try/catch
- **Impact**: High - Better UX on failures
- **Files to study**: `src-tauri/src/error.rs`, `src/lib/errors/`

### 7. Custom Hooks
- **CC-Switch**: 19 hooks (useProviderActions, useMcp, useSettings, useBackupManager, etc.)
- **CAM**: No custom hooks
- **Impact**: High - Reusable business logic
- **Files to study**: `src/hooks/` directory

---

## Medium Priority (Feature Additions)

| Area | CC-Switch Implementation | Notes |
|------|-------------------------|-------|
| Charts (recharts) | Spending, token usage, provider stats dashboards | Add usage visualization |
| Command Palette (cmdk) | Quick navigation + search | Power-user feature |
| Toast Notifications (sonner) | Success/error/undo toasts | Better feedback |
| Framer Motion | Page transitions, list animations | Polished UX |
| Full-text Search (flexsearch) | Instant search across entities | Better discoverability |
| Backup & Restore | DB backup, config backup, restore | Data safety |
| System Tray | Quick provider switching | Convenience |

---

## Lower Priority (New Capabilities)

| Area | CC-Switch | CAM |
|------|-----------|-----|
| Local Proxy Server | Full HTTP proxy with failover, circuit breaker | None |
| Deep Links | `ccswitch://` URL scheme imports | None |
| WebDAV Sync | Cloud config sync | None |
| Code Editor (CodeMirror) | JSON/Markdown editing | None |
| Drag & Drop (@dnd-kit) | Provider/skill reordering | None |
| Auto-Updates | Tauri plugin updater | None |
| Stream Health Checking | Provider connectivity tests | None |
| Usage Statistics | Daily rollups, model pricing | None |
| Session Management | Browse/view/delete conversations | None |
| Prompt Management | CRUD + cross-app sync | Has Instructions |
| Environment Conflict Detection | Warns about conflicting env vars | None |

---

## Estimated Effort

| Category | Components | Effort |
|----------|-----------|--------|
| Frontend state | TanStack Query setup | ~2-3 days |
| UI components | shadcn/ui integration | ~3-5 days |
| Forms | Zod schemas + react-hook-form | ~2-3 days |
| i18n | react-i18next migration | ~1-2 days |
| Testing | MSW for Tauri IPC mocks | ~1-2 days |
| New features | Charts, cmdk, toasts, animations | ~5-7 days |

**Total estimated effort: ~2-3 weeks** for high+medium priority items.

---

## What CAM Already Does Better

- **Go backend** - More mature CLI with 45 command files, BubbleTea TUI
- **Sidecar pattern** - Clean separation between Tauri shell and Go logic
- **17 agents supported** vs CC-Switch's 5 apps
- **381 MCP servers** in registry
- **Go testing** - 1,423+ tests

---

## Implementation Order

1. TanStack Query (foundation for all state)
2. shadcn/ui (UI components needed by everything else)
3. Zod + react-hook-form (form validation)
4. react-i18next (i18n framework)
5. MSW for Tauri IPC (testing infrastructure)
6. Error handling patterns (backend + frontend)
7. Custom hooks (extract from existing components)
