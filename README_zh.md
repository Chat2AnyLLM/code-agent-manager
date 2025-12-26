# Code Assistant Manager (CAM)

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/code-assistant-manager?color=blue)](https://pypi.org/project/code-assistant-manager/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/code-assistant-manager.svg)](https://pypi.org/project/code-assistant-manager/)

**一个 CLI 统一管理所有 AI 编码助手**
<br>
厌倦了在多个 AI 编码助手之间切换？**CAM** 是一个统一的 Python CLI 工具，可以从单一、优雅的终端界面管理 **16 个 AI 助手**（包括 Claude、Codex、Gemini、Qwen、Copilot、Goose、Continue 等）的配置、提示词、技能和插件。

</div>

---

## 为什么选择 CAM？

在 AI 驱动开发的时代，开发者经常使用多个强大的助手，如 Claude、GitHub Copilot 和 Gemini。然而，这导致了碎片化和低效的工作流程：
- **配置分散：** 每个工具都有自己的设置、API 密钥和配置文件。
- **行为不一致：** 系统提示词和自定义指令分散，导致不同项目中 AI 行为不一致。
- **浪费时间：** 不断在不同的 CLI 和 UI 之间切换会降低生产力。

CAM 通过提供单一、一致的界面来管理所有内容，将混乱的工具包变成一个连贯而强大的开发伙伴。

## 主要特性

- **统一管理：** 一个工具（`cam`）即可安装、配置和运行所有 AI 助手。
- **集中配置：** 通过单一的 `providers.json` 文件管理所有 API 密钥和端点设置，环境变量存储在 `.env` 中。
- **交互式 TUI：** 精美的交互式菜单（`cam launch`），支持箭头键导航，便于操作。
- **MCP 注册表：** 内置注册表，包含 **381 个预配置的 MCP 服务器**，可安装到所有支持的工具。
- **可扩展框架：** 标准化架构，用于管理：
    - **代理（Agents）：** 独立的助手配置（基于 Markdown，带 YAML 前置元数据）。
    - **提示词（Prompts）：** 可跨助手同步的可复用系统提示词（用户级或项目级）。
    - **技能（Skills）：** 代理的自定义工具和功能（基于目录，带 SKILL.md）。
    - **插件（Plugins）：** 支持的助手的市场扩展（GitHub 仓库或本地路径）。
- **MCP 支持：** 对 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的一流支持，允许助手连接外部数据源和工具。
- **并行升级：** 并发工具升级，支持 npm 版本检查和进度可视化。
- **诊断功能：** 全面的 `doctor` 命令，可验证环境、API 密钥、工具安装和缓存状态。

## 支持的 AI 助手

CAM 支持 **16 个 AI 编码助手**：

| 助手 | 命令 | 描述 | 安装方式 |
| :--- | :--- | :--- | :--- |
| **Claude** | `claude` | Anthropic Claude Code CLI | Shell 脚本 |
| **Codex** | `codex` | OpenAI Codex CLI | npm |
| **Gemini** | `gemini` | Google Gemini CLI | npm |
| **Qwen** | `qwen` | 阿里巴巴 Qwen Code CLI | npm |
| **Copilot** | `copilot` | GitHub Copilot CLI | npm |
| **CodeBuddy** | `codebuddy` | 腾讯 CodeBuddy CLI | npm |
| **Droid** | `droid` | Factory.ai Droid CLI | Shell 脚本 |
| **iFlow** | `iflow` | iFlow AI CLI | npm |
| **Crush** | `crush` | Charmland Crush CLI | npm |
| **Cursor** | `cursor-agent` | Cursor Agent CLI | Shell 脚本 |
| **Neovate** | `neovate` | Neovate Code CLI | npm |
| **Qoder** | `qodercli` | Qoder CLI | npm |
| **Zed** | `zed` | Zed 编辑器 | Shell 脚本 |
| **Goose** | `goose` | Block Goose CLI | Shell 脚本 |
| **Continue** | `continue` | Continue.dev CLI | npm |
| **OpenCode** | `opencode` | OpenCode CLI | npm |

## 功能支持矩阵

| 功能 | Claude | Codex | Gemini | Qwen | CodeBuddy | Droid | Copilot |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **代理**管理 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **提示词**同步 | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| **技能**安装 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **插件**支持 | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **MCP** 集成 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**MCP 集成**支持所有 16 个助手，包括：Claude、Codex、Gemini、Qwen、Copilot、CodeBuddy、Droid、iFlow、Zed、Qoder、Neovate、Crush、Cursor、Goose、Continue 和 OpenCode。

> **注意：** 部分工具（Zed、Qoder、Neovate）默认在菜单中隐藏，因为它们仍在开发中。您可以在 `tools.yaml` 中设置 `enabled: true` 来启用它们。

## 安装

```bash
# 通过 pip 安装（Python 3.9+）
pip install code-assistant-manager

# 或从源码安装
git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git
cd code-assistant-manager
pip install -e ".[dev]"
```

## 快速开始

### 1. 设置配置

在 `~/.config/code-assistant-manager/` 或项目根目录创建 `providers.json` 文件：

```json
{
  "common": {
    "http_proxy": "http://proxy.example.com:8080/",
    "https_proxy": "http://proxy.example.com:8080/",
    "cache_ttl_seconds": 86400
  },
  "endpoints": {
    "my-litellm": {
      "endpoint": "https://api.example.com:4142",
      "api_key_env": "API_KEY_LITELLM",
      "list_models_cmd": "python -m code_assistant_manager.v1_models",
      "supported_client": "claude,codex,qwen,copilot",
      "description": "我的 LiteLLM 代理"
    }
  }
}
```

### 2. 设置 API 密钥

在用户主目录或项目根目录创建 `.env` 文件：

```env
API_KEY_LITELLM="your-api-key-here"
GITHUB_TOKEN="your-github-token"
GEMINI_API_KEY="your-gemini-key"
```

### 3. 检查设置

```bash
cam doctor
```

这将运行全面的诊断检查，包括：
- 安装验证
- 配置文件验证
- 环境变量检查（Gemini/Vertex AI、GitHub Copilot）
- 工具安装状态
- 端点连接性
- 缓存状态和安全审计

### 4. 启动助手

```bash
# 交互式菜单选择助手和模型
cam launch

# 或直接启动特定助手
cam launch claude
cam launch codex
cam launch gemini
```

## 命令参考

| 命令 | 别名 | 描述 |
| :--- | :--- | :--- |
| `cam launch [TOOL]` | `l` | 启动交互式 TUI 或特定助手 |
| `cam doctor` | `d` | 运行环境和 API 密钥诊断检查 |
| `cam agent` | `ag` | 管理代理配置（列表、安装、从仓库获取） |
| `cam prompt` | `p` | 管理和同步跨助手的系统提示词 |
| `cam skill` | `s` | 安装和管理技能集合 |
| `cam plugin` | `pl` | 管理市场扩展（插件） |
| `cam mcp` | `m` | 管理 MCP 服务器（添加、移除、列表、安装） |
| `cam upgrade [TARGET]` | `u` | 升级工具（默认：全部），支持并行执行 |
| `cam install [TARGET]` | `i` | upgrade 的别名 |
| `cam uninstall [TARGET]` | `un` | 卸载工具并备份配置 |
| `cam config` | `cf` | 管理 CAM 的内部配置文件 |
| `cam completion` | `c` | 生成 shell 补全脚本（bash、zsh、fish） |
| `cam version` | `v` | 显示当前版本 |

### MCP 子命令

```bash
cam mcp add <tool> <server>      # 为工具添加 MCP 服务器
cam mcp remove <tool> <server>   # 移除 MCP 服务器
cam mcp list <tool>              # 列出已配置的 MCP 服务器
cam mcp install --all            # 为所有工具安装 MCP 服务器
cam mcp registry search <query>  # 搜索 MCP 服务器注册表
```

### 代理子命令

```bash
cam agent list                   # 列出可用代理
cam agent install <agent>        # 安装代理
cam agent fetch                  # 从配置的仓库获取代理
cam agent repos                  # 管理代理仓库
```

### 提示词子命令

```bash
cam prompt list                  # 列出保存的提示词
cam prompt create                # 创建新提示词
cam prompt sync <id> <tool>      # 将提示词同步到工具
cam prompt set-default <id>      # 设置 sync-all 的默认提示词
cam prompt sync-all              # 将默认提示词同步到所有工具
```

### 技能子命令

```bash
cam skill list                   # 列出可用技能
cam skill install <skill>        # 安装技能
cam skill fetch                  # 从配置的仓库获取技能
```

## 开发

### 开发环境设置

```bash
# 克隆并安装
git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git
cd code-assistant-manager
pip install -e ".[dev]"

# 运行测试
pytest

# 带覆盖率运行
pytest --cov=code_assistant_manager

# 代码格式化
black code_assistant_manager tests
isort code_assistant_manager tests

# 代码检查
flake8 code_assistant_manager
mypy code_assistant_manager
```

### 运行特定测试

```bash
pytest tests/test_cli.py           # CLI 测试
pytest tests/test_config.py        # 配置测试
pytest tests/unit/                  # 单元测试
pytest tests/integration/           # 集成测试
```

## 贡献

欢迎贡献！请参阅我们的 [开发者指南](docs/DEVELOPER_GUIDE.md) 和 [贡献指南](docs/CONTRIBUTING.md) 开始。

## 许可证

本项目采用 MIT 许可证。

---

最后更新：2025-11-30
