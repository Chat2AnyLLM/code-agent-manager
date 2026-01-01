"""Qwen skill handler implementation."""

import logging
from pathlib import Path

from .base import BaseSkillHandler

logger = logging.getLogger(__name__)


class QwenSkillHandler(BaseSkillHandler):
    """Handler for Qwen Code skills."""

    @property
    def app_name(self) -> str:
        return "qwen"

    @property
    def _default_skills_dir(self) -> Path:
        """Get the default skills directory for Qwen."""
        # Note: This is an assumption based on common patterns.
        # Qwen Code CLI documentation should be consulted for exact path if different.
        return Path.home() / ".qwen" / "skills"