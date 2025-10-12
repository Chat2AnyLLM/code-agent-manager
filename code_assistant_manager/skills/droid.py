"""Droid skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class DroidSkillHandler(BaseSkillHandler):
    """Skill handler for Factory.ai Droid CLI."""

    @property
    def app_name(self) -> str:
        return "droid"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".factory" / "skills"
