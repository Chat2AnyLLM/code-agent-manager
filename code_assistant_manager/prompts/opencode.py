"""OpenCode-specific prompt handler."""

from pathlib import Path
from typing import Optional

from .base import BasePromptHandler


class OpenCodePromptHandler(BasePromptHandler):
    """Prompt handler for OpenCode.

    User-level prompt: ~/.config/opencode/AGENTS.md
    Project-level prompt: ./AGENTS.md
    """

    @property
    def tool_name(self) -> str:
        return "opencode"

    @property
    def _default_user_prompt_path(self) -> Optional[Path]:
        return Path.home() / ".config" / "opencode" / "AGENTS.md"

    @property
    def _default_project_prompt_filename(self) -> Optional[str]:
        return "AGENTS.md"