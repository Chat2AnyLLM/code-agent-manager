"""Codex-specific prompt handler."""

from pathlib import Path
from typing import Optional

from .base import BasePromptHandler


class CodexPromptHandler(BasePromptHandler):
    """Prompt handler for OpenAI Codex CLI.

    User-level prompt: ~/.codex/AGENTS.md
    Project-level prompt: ./AGENTS.md
    """

    @property
    def tool_name(self) -> str:
        return "codex"

    @property
    def _default_user_prompt_path(self) -> Optional[Path]:
        return Path.home() / ".codex" / "AGENTS.md"

    @property
    def _default_project_prompt_filename(self) -> Optional[str]:
        return "AGENTS.md"
