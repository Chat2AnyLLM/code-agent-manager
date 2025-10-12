"""Claude-specific prompt handler."""

from pathlib import Path
from typing import Optional

from .base import BasePromptHandler


class ClaudePromptHandler(BasePromptHandler):
    """Prompt handler for Claude Code.

    User-level prompt: ~/.claude/CLAUDE.md
    Project-level prompt: ./CLAUDE.md
    """

    @property
    def tool_name(self) -> str:
        return "claude"

    @property
    def _default_user_prompt_path(self) -> Optional[Path]:
        return Path.home() / ".claude" / "CLAUDE.md"

    @property
    def _default_project_prompt_filename(self) -> Optional[str]:
        return "CLAUDE.md"
