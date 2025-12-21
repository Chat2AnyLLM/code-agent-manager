"""Copilot skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class CopilotSkillHandler(BaseSkillHandler):
    """Skill handler for GitHub Copilot CLI."""

    @property
    def app_name(self) -> str:
        return "copilot"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".copilot" / "skills"
