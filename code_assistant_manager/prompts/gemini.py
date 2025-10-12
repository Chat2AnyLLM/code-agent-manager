"""Gemini-specific prompt handler."""

from pathlib import Path
from typing import Optional

from .base import BasePromptHandler


class GeminiPromptHandler(BasePromptHandler):
    """Prompt handler for Google Gemini CLI.

    User-level prompt: ~/.gemini/GEMINI.md
    Project-level prompt: ./GEMINI.md
    """

    @property
    def tool_name(self) -> str:
        return "gemini"

    @property
    def _default_user_prompt_path(self) -> Optional[Path]:
        return Path.home() / ".gemini" / "GEMINI.md"

    @property
    def _default_project_prompt_filename(self) -> Optional[str]:
        return "GEMINI.md"
