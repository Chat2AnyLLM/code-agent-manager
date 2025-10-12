# Code Assistant Manager Upgrade Functionality

## Overview

The Code Assistant Manager provides built-in upgrade functionality for CLI tools that allows users to easily upgrade their installed tools to the latest versions. This functionality is implemented in the `CLITool` base class and works by:

1. Checking if a tool is already installed
2. If installed, prompting the user to upgrade or use the current version
3. If the user chooses to upgrade, running the install command from `tools.yaml`

## How It Works

### 1. Tool Detection
When a tool is executed, the `_ensure_tool_installed` method in the `CLITool` base class checks if the tool's command is available using the `which` command.

### 2. Upgrade Prompt
If the tool is already installed, the user is presented with a menu:
```
Upgrade {tool_name}?
1) Yes, upgrade to latest version
2) No, use current version
3) Skip
```

### 3. Upgrade Execution
If the user selects "Yes, upgrade to latest version", the system:
1. Retrieves the install command from `tools.yaml`
2. Executes the install command using `subprocess.run`
3. Reports success or failure to the user

### 4. Install Command Sources
The install commands are defined in the `tools.yaml` file for each tool. For example:
```yaml
claude-code:
  enabled: true  # Set to false to hide from menus
  install_cmd: npm install -g @anthropic-ai/claude-code@latest
  cli_command: claude
  description: "Claude Code CLI"
```

## Example Workflow

1. User runs `code-assistant-manager claude`
2. System detects `claude` command is available
3. System prompts: "Upgrade Claude Code CLI?"
4. User selects "Yes, upgrade to latest version"
5. System executes: `npm install -g @anthropic-ai/claude-code@latest`
6. System reports: "✓ Claude Code CLI upgraded successfully"

## Key Features

- **Non-intrusive**: Users can choose to skip upgrades
- **Automatic**: Uses the same install command for both initial install and upgrades
- **Transparent**: Shows the exact command being executed
- **Robust**: Handles upgrade failures gracefully
- **Configurable**: Install commands are defined in `tools.yaml`
- **Visibility Control**: Tools can be shown/hidden from menus using the `enabled` key

## Supported Tools

All tools defined in `tools.yaml` with an `install_cmd` field support upgrade functionality:
- Claude Code CLI
- OpenAI Codex CLI
- Qwen Code CLI
- GitHub Copilot CLI
- Tencent CodeBuddy CLI
- Factory.ai Droid CLI
- iFlow CLI
- Crush CLI
- Cursor Agent CLI

Note: Some tools (Zed, Qoder, Neovate) are disabled by default (`enabled: false`) as they are still under development.

## Testing

The upgrade functionality is tested with comprehensive unit tests that verify:
- Successful upgrade execution
- Failure handling
- Proper command execution
- User interaction flows

Tests can be found in `tests/test_upgrade_functionality.py`.
