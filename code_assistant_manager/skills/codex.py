"""Codex skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class CodexSkillHandler(BaseSkillHandler):
    """Skill handler for OpenAI Codex CLI."""

    @property
    def app_name(self) -> str:
        return "codex"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".codex" / "skills"
