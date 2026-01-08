# Code Assistant Manager (CAM)

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/code%20quality-A+-brightgreen.svg)](https://github.com/Chat2AnyLLM/code-assistant-manager/actions)

**One CLI to Rule Them All.**
<br>
Tired of juggling multiple AI coding assistants? **CAM** is a unified Python CLI to manage configurations, prompts, skills, and plugins for **17 AI assistants** including Claude, Codex, Gemini, Qwen, Copilot, Blackbox, Goose, Continue, and more from a single, polished terminal interface.

</div>

---

## Installation

Choose your preferred installation method:

### Quick Install (Recommended)

```bash
# Install via pip (Python 3.9+)
pip install code-assistant-manager
```

### Alternative Methods

```bash
# Install using the install script
./install.sh

# Or install directly from the web
curl -fsSL https://raw.githubusercontent.com/Chat2AnyLLM/code-assistant-manager/main/install.sh | bash

# Install from source
git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git
cd code-assistant-manager
pip install -e ".[dev]"
```

---

## Quick Start

1. **Set up your API keys** in a `.env` file:
   ```env
   ANTHROPIC_API_KEY="your-anthropic-key"
   GITHUB_TOKEN="your-github-token"
   GEMINI_API_KEY="your-gemini-key"
   ```

2. **Launch the interactive menu:**
   ```bash
   cam launch
   ```

3. **Select your assistant and start coding!**

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
- **Centralized Configuration:** Manage all API keys and endpoint settings from a single `providers.json` file with environment variables in `.env`
- **Interactive TUI:** A polished, interactive menu (`cam launch`) for easy navigation and operation with arrow-key navigation
- **MCP Registry:** Built-in registry with **381 pre-configured MCP servers** ready to install across all supported tools
- **Extensible Framework:** Standardized architecture for managing agents, prompts, skills, and plugins

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

## Agents, Prompts & Skills

### Agents
Manage standalone assistant configurations with markdown-based definitions and YAML front matter.

### Prompts
Reusable system prompts with fancy name generation synced across assistants at user or project scope.

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
| `cam prompt` | `p` | Manage and sync system prompts across assistants |
| `cam skill` | `s` | Install and manage skill collections |
| `cam plugin` | `pl` | Manage marketplace extensions (plugins) |
| `cam mcp` | `m` | Manage MCP servers (add, remove, list, install) |
| `cam upgrade [TARGET]` | `u` | Upgrade tools (default: all) with parallel execution |
| `cam install [TARGET]` | `i` | Alias for upgrade |
| `cam uninstall [TARGET]` | `un` | Uninstall tools and backup configurations |
| `cam config` | `cf` | Manage CAM's internal configuration files |
| `cam version` | `v` | Display current version |

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