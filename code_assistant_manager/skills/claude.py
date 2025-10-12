"""Claude skill handler."""

from pathlib import Path

from .base import BaseSkillHandler


class ClaudeSkillHandler(BaseSkillHandler):
    """Skill handler for Claude Code."""

    @property
    def app_name(self) -> str:
        return "claude"

    @property
    def _default_skills_dir(self) -> Path:
        return Path.home() / ".claude" / "skills"
