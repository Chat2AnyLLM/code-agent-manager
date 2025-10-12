"""Prompt management package for Code Assistant Manager.

This package provides functionality to manage prompts for AI coding assistants.
Each tool (Claude, Codex, Gemini, Copilot) has its own handler implementation.

Usage:
    from code_assistant_manager.prompts import PromptManager, Prompt

    manager = PromptManager()

    # Create a prompt
    prompt = Prompt(id="my-prompt", name="My Prompt", content="...")
    manager.create(prompt)

    # Sync to a tool
    manager.activate("my-prompt", app_type="claude", level="user")

    # For Copilot instructions
    manager.sync_copilot_instructions("my-prompt", instruction_type="repo-wide")

Supported Tools:
    - claude: Claude Code (~/.claude/CLAUDE.md, ./CLAUDE.md)
    - codex: OpenAI Codex CLI (~/.codex/AGENTS.md, ./AGENTS.md)
    - gemini: Google Gemini CLI (~/.gemini/GEMINI.md, ./GEMINI.md)
    - copilot: GitHub Copilot CLI (.github/copilot-instructions.md, .github/instructions/)
"""

from .base import BasePromptHandler
from .claude import ClaudePromptHandler
from .codex import CodexPromptHandler
from .copilot import (
    COPILOT_INSTRUCTIONS_DIR,
    COPILOT_REPO_INSTRUCTIONS,
    CopilotPromptHandler,
    format_copilot_frontmatter,
    parse_copilot_frontmatter,
)
from .gemini import GeminiPromptHandler
from .manager import PROMPT_HANDLERS, VALID_APP_TYPES, PromptManager, get_handler
from .models import Prompt

# Backward compatibility aliases
USER_PROMPT_FILE_PATHS = {
    "claude": ClaudePromptHandler().user_prompt_path,
    "codex": CodexPromptHandler().user_prompt_path,
    "gemini": GeminiPromptHandler().user_prompt_path,
}

PROJECT_PROMPT_FILE_NAMES = {
    "claude": ClaudePromptHandler().project_prompt_filename,
    "codex": CodexPromptHandler().project_prompt_filename,
    "gemini": GeminiPromptHandler().project_prompt_filename,
}

PROMPT_FILE_PATHS = USER_PROMPT_FILE_PATHS


def get_prompt_file_path(app_type: str, level: str = "user", project_dir=None):
    """Backward compatible function to get prompt file path."""
    try:
        handler = get_handler(app_type)
        return handler.get_prompt_file_path(level, project_dir)
    except ValueError:
        return None


def get_copilot_instructions_path(project_dir=None, repo_wide: bool = True):
    """Backward compatible function to get Copilot instructions path."""
    handler = CopilotPromptHandler()
    return handler.get_instructions_path(project_dir, repo_wide)


__all__ = [
    # Main classes
    "PromptManager",
    "Prompt",
    "BasePromptHandler",
    # Tool-specific handlers
    "ClaudePromptHandler",
    "CodexPromptHandler",
    "GeminiPromptHandler",
    "CopilotPromptHandler",
    # Helper functions
    "get_handler",
    "get_prompt_file_path",
    "get_copilot_instructions_path",
    "parse_copilot_frontmatter",
    "format_copilot_frontmatter",
    # Constants
    "VALID_APP_TYPES",
    "PROMPT_HANDLERS",
    "USER_PROMPT_FILE_PATHS",
    "PROJECT_PROMPT_FILE_NAMES",
    "PROMPT_FILE_PATHS",
    "COPILOT_REPO_INSTRUCTIONS",
    "COPILOT_INSTRUCTIONS_DIR",
]
