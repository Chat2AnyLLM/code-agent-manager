"""Droid agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class DroidAgentHandler(BaseAgentHandler):
    """Agent handler for Factory.ai Droid CLI."""

    @property
    def app_name(self) -> str:
        return "droid"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".factory" / "agents"
