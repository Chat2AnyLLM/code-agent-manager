# Deep Codebase Metrics Analysis

**Generated:** 2025-11-28
**Repository:** code-agent-manager

---

## 📊 Executive Summary

| Metric | Value | Health |
|--------|-------|--------|
| Total Source Files | 96 | ✅ Good |
| Total Lines of Code | 24,046 | ✅ Manageable |
| Total Functions | 949 | ✅ Good |
| Total Classes | 143 | ✅ Good |
| Docstring Coverage | 86% | ✅ Excellent |
| Type Hint Coverage | 89% | ✅ Excellent |
| Simple Functions (CC ≤ 5) | 77% | ✅ Excellent |
| Complex Functions (CC > 15) | 2% (19 functions) | ⚠️ Needs Attention |

---

## 📏 File Size Distribution

```
File Size               Count   Distribution
────────────────────────────────────────────
Small (<100 lines)        34   ████████████████████
Medium (100-300 lines)    28   ████████████████
Large (300-500 lines)     21   ████████████
X-Large (>500 lines)      13   ███████ ⚠️
```

### X-Large Files (>500 lines) - Refactoring Candidates

| File | Lines | Priority |
|------|------:|----------|
| `cli/commands.py` | 1,338 | 🔴 Critical |
| `mcp/base_client.py` | 1,188 | 🔴 Critical |
| `cli/plugin_commands.py` | 956 | 🟠 High |
| `cli/prompts_commands.py` | 842 | 🟠 High |
| `menu/base.py` | 744 | 🟡 Medium |
| `config.py` | 608 | 🟡 Medium |
| `endpoints.py` | 576 | 🟡 Medium |
| `tools/base.py` | 564 | 🟡 Medium |
| `tools/crush.py` | 551 | 🟡 Medium |
| `plugins/manager.py` | 547 | 🟡 Medium |
| `prompts/manager.py` | 540 | 🟡 Medium |
| `skills/manager.py` | 525 | 🟡 Medium |
| `cli/skills_commands.py` | 524 | 🟡 Medium |

---

## 🔄 Cyclomatic Complexity Distribution

```
Complexity Level         Count   Percentage
─────────────────────────────────────────────
Simple (1-5)              731   77% ███████████████████████
Moderate (6-10)           172   18% █████
Complex (11-15)            27    3% █
Very Complex (>15)         19    2% ⚠️
```

### Very High Complexity Functions (CC > 15)

These functions are the most difficult to test and maintain:

| CC | File | Function | Line | Root Cause |
|---:|------|----------|-----:|------------|
| 68 | `cli/upgrade.py` | `handle_upgrade_command()` | 12 | Multiple upgrade paths |
| 51 | `cli/doctor.py` | `run_doctor_checks()` | 16 | Many diagnostic checks |
| 32 | `cli/plugin_commands.py` | `browse_marketplace()` | 620 | Mixed concerns |
| 30 | `mcp/claude.py` | `list_servers()` | 274 | Complex config parsing |
| 25 | `config.py` | `validate_command()` | 384 | Large pattern lists |
| 24 | `config.py` | `validate_config()` | 195 | Nested validation |
| 22 | `mcp/copilot.py` | `list_servers()` | 241 | Config parsing |
| 22 | `mcp/codebuddy.py` | `list_servers()` | 264 | Config parsing |
| 20 | `mcp/server_commands.py` | `show()` | 111 | Display branching |
| 18 | `cli/utils.py` | `legacy_main()` | 21 | Legacy code |
| 18 | `mcp/base_client.py` | `_read_servers_from_configs()` | 423 | Multi-format parsing |
| 17 | `plugins/base.py` | `_download_repo()` | 341 | Error handling |
| 17 | `mcp/base_client.py` | `_read_servers_from_configs_legacy()` | 477 | Legacy support |
| 17 | `skills/base.py` | `_download_repo()` | 179 | Error handling |
| 17 | `agents/base.py` | `_download_repo()` | 223 | Error handling |

---

## 📝 Code Quality Metrics

### Documentation Coverage (86% - Excellent)

```
                    With Docstrings    Without Docstrings
Functions:              820 (86%)          129 (14%)
                   ████████████████████   ███
```

**Analysis:** The codebase has excellent documentation coverage. Most functions have descriptive docstrings, which significantly aids maintainability.

### Type Hint Coverage (89% - Excellent)

```
                    With Type Hints    Without Type Hints
Functions:              852 (89%)          97 (11%)
                   ██████████████████████  ██
```

**Analysis:** Strong type hint adoption. This enables better IDE support, catch bugs early, and improves code readability.

---

## 📚 Dependency Analysis

### Top Dependencies by Import Count

| Dependency | Imports | Category |
|------------|--------:|----------|
| `pathlib` | 75 | Standard Library |
| `typing` | 71 | Standard Library |
| `code_assistant_manager` | 59 | Internal |
| `json` | 51 | Standard Library |
| `logging` | 32 | Standard Library |
| `os` | 27 | Standard Library |
| `typer` | 17 | CLI Framework |
| `subprocess` | 14 | Standard Library |
| `abc` | 10 | Standard Library |
| `shutil` | 10 | Standard Library |

### Dependency Health Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| External Dependencies | ✅ Minimal | Few third-party deps (typer, requests, pydantic) |
| Standard Library Usage | ✅ Good | Heavy use of built-in modules |
| Internal Coupling | 🟡 Moderate | 59 internal imports - review for circular deps |
| CLI Framework | ✅ Consistent | Typer used throughout |

---

## 🔗 Module Coupling Analysis

### High-Traffic Modules (Most Imported)

1. **`base` modules** (45 imports) - Good abstraction pattern
2. **`models`** (10 imports) - Data model centralization
3. **`base_client`** (13 imports) - MCP client base class

### Potential Issues

- **`cli/commands.py`** (1,338 lines) imports many modules - candidate for splitting
- **`mcp/base_client.py`** (1,188 lines) - complex inheritance hierarchy

---

## 📈 Trend Indicators

Based on git history and current metrics:

### Positive Trends ✅
- Recent commits show complexity reduction efforts (`5ca0ed4`)
- Test coverage is improving with dedicated test commits
- New features follow modular patterns (agents, skills as packages)

### Areas Needing Attention ⚠️
- Legacy upgrade/doctor functions have very high complexity
- Several CLI modules exceed size limits
- Some `list_servers()` implementations are duplicated across MCP clients

---

## 🎯 Actionable Recommendations

### Immediate (This Sprint)

1. **Refactor `handle_upgrade_command()` (CC=68)**
   - Split into separate upgrade strategies per tool
   - Use strategy pattern

2. **Refactor `run_doctor_checks()` (CC=51)**
   - Extract each check into a separate function
   - Use a check registry pattern

3. **Split `cli/commands.py` (1,338 lines)**
   - Create `endpoint_commands.py`
   - Create `launch_commands.py`
   - Create `model_commands.py`

### Short-Term (Next 2 Sprints)

4. **Consolidate `list_servers()` implementations**
   - DRY violation across `claude.py`, `copilot.py`, `codebuddy.py`
   - Move common logic to `base_client.py`

5. **Extract `_download_repo()` to shared module**
   - Identical implementations in `plugins/base.py`, `skills/base.py`, `agents/base.py`

### Long-Term (Quarterly)

6. **Consider splitting `mcp/base_client.py`**
   - Separate config reading from client operations
   - Create dedicated config parser module

7. **Increase test coverage for complex functions**
   - Priority: All CC > 15 functions

---

## 📊 Health Score Card

| Category | Score | Grade |
|----------|------:|-------|
| File Organization | 75/100 | B |
| Code Complexity | 70/100 | B- |
| Documentation | 90/100 | A |
| Type Safety | 90/100 | A |
| Test Coverage | 65/100 | C+ |
| Dependency Management | 85/100 | A- |
| **Overall** | **79/100** | **B+** |

---

## Appendix: Methodology

### Cyclomatic Complexity Calculation

CC is calculated by counting:
- +1 for each `if`, `elif`, `while`, `for`
- +1 for each `except` handler
- +1 for each `with` statement
- +1 for each `assert`
- +1 for each boolean operator (`and`, `or`)
- +1 for each comprehension

### File Size Categories

- **Small**: < 100 lines (ideal for most modules)
- **Medium**: 100-300 lines (acceptable for complex modules)
- **Large**: 300-500 lines (consider splitting)
- **X-Large**: > 500 lines (should be split)

### Health Score Formula

```
Health = 100 - (max_complexity * 3) - (lines / 100 * 5)
```

Where:
- Files with CC > 10 are penalized heavily
- Files > 500 lines are considered unhealthy
