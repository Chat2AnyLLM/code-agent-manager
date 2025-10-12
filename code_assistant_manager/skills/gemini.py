"""Gemini skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class GeminiSkillHandler(BaseSkillHandler):
    """Skill handler for Google Gemini CLI."""

    @property
    def app_name(self) -> str:
        return "gemini"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".gemini" / "skills"
