"""CodeBuddy skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class CodebuddySkillHandler(BaseSkillHandler):
    """Skill handler for CodeBuddy CLI."""

    @property
    def app_name(self) -> str:
        return "codebuddy"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".codebuddy" / "skills"
