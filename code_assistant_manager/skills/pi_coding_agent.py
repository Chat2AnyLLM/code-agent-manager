"""Pi Coding Agent skill handler implementation."""

import logging
from pathlib import Path

from .base import BaseSkillHandler

logger = logging.getLogger(__name__)


class PiCodingAgentSkillHandler(BaseSkillHandler):
    """Handler for Pi Coding Agent skills."""

    @property
    def app_name(self) -> str:
        return "pi-coding-agent"

    @property
    def _default_skills_dir(self) -> Path:
        """Get the default skills directory for Pi Coding Agent.

        Pi Coding Agent loads skills from multiple locations:
        - Global: ~/.pi/agent/skills/
        - Project: .pi/skills/

        Using the global location as primary default.
        """
        return Path.home() / ".pi" / "agent" / "skills"

