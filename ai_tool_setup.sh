#!/usr/bin/env bash
# ai_tool_setup.sh - Python Project Setup Script
# Source this file from your ~/.bashrc to enable convenient wrapper functions for the Python CLI
# Usage: source /path/to/ai_tool_setup.sh
#
# This script:
# - Sets up the Code Assistant Manager environment
# - Loads .env variables via load_env.sh
# - Provides shell function wrappers that call the Python CLI
# - Creates default config file if needed
#
# API keys should be stored in settings.conf (see settings.conf.example).

# Resolve script directory
__CODE_ASSISTANT_MANAGER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CONFIG_FILE="$__CODE_ASSISTANT_MANAGER_DIR/settings.conf"

# Export the toolbox directory so alias scripts can use it
export __CODE_ASSISTANT_MANAGER_DIR

# Environment variables from .env are loaded by the Python CLI implementation.
# The legacy `load_env.sh` helper has been removed; Python code uses python-dotenv.

# Helper: list sections in settings.conf (excluding [common] section)
_ai_list_sections() {
  [ -f "$CONFIG_FILE" ] || return 1
  awk '/^\s*\[/{gsub(/\[|\]/,"",$0); if($0 != "common") print $0}' "$CONFIG_FILE"
}

# Helper: get a key value for a section
_ai_get_value() {
  local section="$1" key="$2"
  [ -f "$CONFIG_FILE" ] || return 1
  awk -v sec="$section" -v key="$key" '
    BEGIN{insec=0}
    /^\s*\[/{s=$0; gsub(/\[|\]/,"",s); insec=(s==sec)}
    insec && $0 ~ "^[ \t]*"key"[ \t]*=" { val=substr($0, index($0, "=")+1); gsub(/^[ \t]+|[ \t]+$/,"",val); print val; exit }
  ' "$CONFIG_FILE"
}

# If the simple awk above fails on some shells, provide a fallback parser
_ai_get_value_fallback() {
  local section="$1" key="$2" line insec=0 val
  while IFS= read -r line; do
    # trim
    line="${line%%\#*}"
    [[ -z "$line" ]] && continue
    if [[ "$line" =~ ^\s*\[(.+)\]\s*$ ]]; then
      [[ "${BASH_REMATCH[1]}" == "$section" ]] && insec=1 || insec=0
      continue
    fi
    if [[ $insec -eq 1 && "$line" =~ ^\s*([^=]+)=\s*(.*)\s*$ ]]; then
      k="${BASH_REMATCH[1]// /}"
      v="${BASH_REMATCH[2]}"
      if [[ "$k" == "$key" ]]; then
        printf "%s" "$v"
        return 0
      fi
    fi
  done < "$CONFIG_FILE"
  return 1
}

# Choose parser based on availability
_ai_get() {
  local val
  val=$(_ai_get_value "$@" 2>/dev/null) || val=$(_ai_get_value_fallback "$@" 2>/dev/null)
  printf "%s" "$val"
}

# Export helper functions so alias scripts can use them
export -f _ai_list_sections
export -f _ai_get_value
export -f _ai_get_value_fallback
export -f _ai_get

# Common helper functions removed - using Python CLI only
# For environment variable management, environment variables are handled by the Python package.

# Python CLI wrappers - calling the unified Python implementation with new subcommand structure
# Shell scripts are now deprecated in favor of the Python package

claude() {
  python -m code_assistant_manager launch claude "$@"
}

codex() {
  python -m code_assistant_manager launch codex "$@"
}

copilot() {
  python -m code_assistant_manager launch copilot "$@"
}

gemini() {
  python -m code_assistant_manager launch gemini "$@"
}

droid() {
  python -m code_assistant_manager launch droid "$@"
}

qwen() {
  python -m code_assistant_manager launch qwen "$@"
}

codebuddy() {
  python -m code_assistant_manager launch codebuddy "$@"
}

iflow() {
  python -m code_assistant_manager launch iflow "$@"
}

qodercli() {
  python -m code_assistant_manager launch qodercli "$@"
}

zed() {
  python -m code_assistant_manager launch zed "$@"
}

neovate() {
  python -m code_assistant_manager launch neovate "$@"
}

# If settings.conf doesn't exist, create an example copy next to this script
if [ ! -f "$CONFIG_FILE" ] && [ -f "$__CODE_ASSISTANT_MANAGER_DIR/settings.conf.example" ]; then
  cp "$__CODE_ASSISTANT_MANAGER_DIR/settings.conf.example" "$CONFIG_FILE"
  echo "Created example config at $CONFIG_FILE. Edit it and replace placeholder api_key values."
fi

# Prevent direct execution (only allow sourcing)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Error: This script must be sourced, not executed." >&2
  echo "Usage: source ${BASH_SOURCE[0]}" >&2
  exit 1
fi

# Usage instructions
cat <<USAGE

✓ Code Assistant Manager loaded successfully!

IMPORTANT: Shell scripts are now DEPRECATED. All commands use the Python CLI with new subcommand structure.

To enable claude/codex wrappers automatically, add this to your ~/.bashrc:

  source "$__CODE_ASSISTANT_MANAGER_DIR/ai_tool_setup.sh"

Available commands (all call Python CLI with new subcommand structure):
  - claude         : Claude Code CLI
  - codex          : OpenAI Codex CLI
  - copilot        : GitHub Copilot CLI
  - gemini         : Google Gemini CLI
  - droid          : Factory.ai Droid CLI
  - qwen           : Qwen Code CLI
  - codebuddy      : Tencent CodeBuddy CLI
  - iflow          : iFlow CLI
  - qodercli       : Qoder CLI - to be implemented
  - zed            : Zed Editor - to be implemented
  - neovate        : Neovate Code CLI - to be implemented

Direct Python usage (recommended):
  - python -m code_assistant_manager launch claude    Claude Code CLI
  - python -m code_assistant_manager launch codex     OpenAI Codex CLI
  - python -m code_assistant_manager launch copilot   GitHub Copilot CLI
  - python -m code_assistant_manager launch gemini    Google Gemini CLI
  - python -m code_assistant_manager launch droid     Factory.ai Droid CLI
  - python -m code_assistant_manager launch qwen      Qwen Code CLI
  - python -m code_assistant_manager launch codebuddy Tencent CodeBuddy CLI
  - python -m code_assistant_manager launch iflow     iFlow CLI
  - python -m code_assistant_manager launch qodercli  Qoder CLI - to be implemented
  - python -m code_assistant_manager launch zed       Zed Editor - to be implemented
  - python -m code_assistant_manager launch neovate   Neovate Code CLI - to be implemented

Additional commands:
  - python -m code_assistant_manager mcp [args...]     Manage MCP servers
  - python -m code_assistant_manager upgrade [tool]    Upgrade CLI tools

Configuration:
  - Edit $CONFIG_FILE to configure endpoints and API keys
  - Environment variables can be set via settings.conf or loaded by the Python package from a .env file

Security note:
  - API keys should be stored in settings.conf or environment variables
  - Do not commit secrets to version control

USAGE
