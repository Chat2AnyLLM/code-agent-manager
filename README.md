# Code Assistant Manager (CAM)

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/code%20quality-A+-brightgreen.svg)](https://github.com/Chat2AnyLLM/code-agent-manager/actions)

**One CLI to Rule Them All.**
<br>
Tired of juggling multiple AI coding assistants? **CAM** is a unified Go CLI to manage configurations, instructions, skills, plugins, MCP servers, and launch settings for **17 AI assistants** including Claude, Codex, Gemini, Qwen, Copilot, Blackbox, Goose, Continue, and more from a single terminal interface.

</div>

---

## Installation

### Prerequisites

- Go 1.26.2 or newer

### Quick Install (Recommended)

Since CAM is distributed from source, build and install the Go binaries locally:

```bash
# Clone the repository
git clone https://github.com/Chat2AnyLLM/code-agent-manager.git
cd code-agent-manager

# Run the install script
./install.sh
```

### Alternative Methods

```bash
# Install using the install script directly
./install.sh

# Or install from the web
curl -fsSL https://raw.githubusercontent.com/Chat2AnyLLM/code-agent-manager/main/install.sh | bash

# Install from source directly
git clone https://github.com/Chat2AnyLLM/code-agent-manager.git
cd code-agent-manager
go test ./...
go build -o dist/cam ./cmd/cam
```

---

## Quick Start

1. **Create your base config files**:
   ```bash
   mkdir -p ~/.config/code-agent-manager
   touch ~/.env
   chmod 600 ~/.env
   ```

2. **Set up your API keys** in `.env`:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-key"
   export GITHUB_TOKEN="your-github-token"
   export GEMINI_API_KEY="your-gemini-key"
   ```

3. **Source the environment file and verify setup:**
   ```bash
   source ~/.env
   cam doctor
   ```

4. **Launch the interactive menu:**
   ```bash
   cam launch
   ```

5. **Select your assistant and start coding!**

---

## Desktop App and Developer Workflow

CAM now uses a **Tauri desktop shell** with a **Go sidecar API**. The same Go backend packages power both the terminal CLI and the desktop UI, so provider and launch behavior stays consistent across interfaces.

### Start the desktop app

Use `make start` from the repository root:

```bash
make start
```

`make start`, `make app`, and `make dev` all run the same full desktop startup path. They build the Go sidecar expected by Tauri, start the Vite frontend dev server through Tauri, and open the desktop window.

### Start browser-only frontend

Use this when you only want the React UI in a browser with mock/fallback data or a manually configured sidecar URL:

```bash
make frontend
```

The browser frontend listens on `http://127.0.0.1:5173` by default. Override the host or port when needed:

```bash
make frontend FRONTEND_HOST=127.0.0.1 FRONTEND_PORT=5174
```

### Start the Go sidecar directly

Use this for API testing without opening the desktop window:

```bash
make sidecar
```

By default, the sidecar binds to `127.0.0.1` and chooses a random port (`SIDECAR_PORT=0`). It prints startup JSON containing the selected port and bearer token. Override values when needed:

```bash
make sidecar SIDECAR_PORT=54321
```

### Build desktop assets and sidecar

```bash
make desktop-build
```

This runs the frontend production build, builds the Go sidecar, and checks the Tauri shell with Cargo. On Windows, the Makefile sets `CARGO_HTTP_CHECK_REVOKE=false` to avoid certificate revocation-check failures when Cargo downloads crates.

### Other useful make targets

```bash
make start  # start the full Tauri desktop app
make build   # build CLI binaries and sidecar into dist/
make test    # run Go tests
make check   # run Go vet, Go tests, frontend tests/build, sidecar build, and cargo check
make clean   # remove generated build outputs
```

---

### Configuration files

CAM uses these main configuration files:

- `~/.config/code-agent-manager/cam.db`: SQLite app state database that stores providers and other state.
- `~/.env`: API keys and sensitive environment variables.
- `~/.config/code-agent-manager/config.yaml`: repository-source config for instructions, skills, agents, plugins, and MCP server catalogs.

### How `config.yaml` is used for instruction/skill/agent/plugin/MCP sources

- CAM loads `~/.config/code-agent-manager/config.yaml` first; if missing, it falls back to the bundled Go config at `internal/camconfig/embed/config.yaml`.
- The file defines source lists for `instructions`, `skills`, `agents`, `plugins`, and `mcpServers`.
- Local JSON sources (`instruction_repos.json`, `skill_repos.json`, `agent_repos.json`, `plugin_repos.json`) are loaded first.
- Remote sources are merged after local sources and do not override existing local keys.
- Remote responses are cached in `~/.cache/code-agent-manager/repos` (TTL controlled by `config.yaml`).
- Prompt and MCP catalog sources default to their upstream `config.yaml` files; CAM reads the `sources:` entries and fetches the configured upstream files directly instead of consuming generated `dist/*.json` artifacts.

---

## Why CAM?

In the era of AI-driven development, developers often use multiple powerful assistants like Claude, GitHub Copilot, and Gemini. However, this leads to a fragmented and inefficient workflow:

- **Scattered Configurations:** Each tool has its own setup, API keys, and configuration files.
- **Inconsistent Behavior:** System prompts and custom instructions diverge, leading to different AI behaviors across projects.
- **Wasted Time:** Constantly switching between different CLIs and UIs is a drain on productivity.

CAM solves this by providing a single, consistent interface to manage everything, turning a chaotic toolkit into a cohesive and powerful development partner.

---

## Key Features

### Core Capabilities

- **Unified Management:** One tool (`cam`) to install, configure, and run all your AI assistants
- **Centralized Configuration:** Manage API keys with environment variables in `.env` and persist provider settings in CAM's SQLite app state
- **Interactive TUI:** A polished, interactive menu (`cam launch`) for easy navigation and operation with arrow-key navigation
- **MCP Catalog Registry:** Source-backed catalog with **381+ pre-configured MCP servers** ready to install across all supported tools
- **Extensible Framework:** Standardized architecture for managing agents, instructions, skills, and plugins

### Supported AI Assistants

CAM supports **17 AI coding assistants**:

| Assistant | Command | Install Method |
| :--- | :--- | :--- |
| **Claude** | `claude` | Shell script |
| **Codex** | `codex` | npm |
| **Gemini** | `gemini` | npm |
| **Qwen** | `qwen` | npm |
| **Copilot** | `copilot` | npm |
| **CodeBuddy** | `codebuddy` | npm |
| **Droid** | `droid` | Shell script |
| **iFlow** | `iflow` | npm |
| **Crush** | `crush` | npm |
| **Cursor** | `cursor-agent` | Shell script |
| **Blackbox** | `blackbox` | Shell script |
| **Neovate** | `neovate` | npm |
| **Qoder** | `qodercli` | npm |
| **Zed** | `zed` | Shell script |
| **Goose** | `goose` | Shell script |
| **Continue** | `continue` | npm |
| **OpenCode** | `opencode` | npm |

---

## Agents, Instructions & Skills

### Agents
Manage standalone assistant configurations with markdown-based definitions and YAML front matter.

### Instructions
Managed coding-agent instruction files such as CLAUDE.md, AGENTS.md, GEMINI.md, and Copilot instruction files, installable at user or project scope where supported.

### Skills
Custom tools and functionalities for your agents (directory-based with SKILL.md).

### Plugins
Marketplace extensions for supported assistants (GitHub repos or local paths).

---

## Command Reference

| Command | Alias | Description |
| :--- | :--- | :--- |
| `cam launch [TOOL]` | `l` | Launch interactive TUI or a specific assistant |
| `cam doctor` | `d` | Run diagnostic checks on environment and API keys |
| `cam agent` | `ag` | Manage agent configurations (list, install, fetch from repos) |
| `cam instruction` | — | Manage and sync coding-agent instruction files across assistants |
| `cam skill` | `s` | Install and manage skill collections |
| `cam plugin` | `pl` | Manage marketplace extensions (plugins) |
| `cam mcp` | `m` | Manage MCP servers (add, remove, list, install) |
| `cam upgrade [TARGET]` | `u` | Upgrade tools (default: all) with parallel execution |
| `cam install [TARGET]` | `i` | Alias for upgrade |
| `cam uninstall [TARGET]` | `un` | Uninstall tools and backup configurations |
| `cam config` | `cf` | Manage CAM's internal configuration files |
| `cam version` | `v` | Display current version |

Note: non-boolean CLI options are long-form only. For example, use `--config` and `--scope` (not `-c` or `-s`).

---

## Governance & Quality

CAM is governed by a speckit-driven development framework ensuring consistent, high-quality evolution with:
- **Constitutional Principles:** Unified interface, security-first design, TDD practices, extensible architecture, quality assurance
- **Enterprise Security:** Config-first approach eliminates shell injection vulnerabilities
- **Comprehensive Testing:** Enterprise-grade test suite with 1,423+ tests
- **Automated Quality Assurance:** Built-in complexity monitoring, file size limits, and CI/CD quality gates

---

## Community & Support

- **Discord:** Join our community for discussions and support
- **GitHub Issues:** Report bugs and request features
- **Contributing:** See our [Contributing Guidelines](docs/CONTRIBUTING.md)

---

## License

This project is licensed under the MIT License.
