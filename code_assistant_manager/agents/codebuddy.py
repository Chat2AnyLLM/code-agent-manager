"""CodeBuddy agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class CodebuddyAgentHandler(BaseAgentHandler):
    """Agent handler for CodeBuddy CLI."""

    @property
    def app_name(self) -> str:
        return "codebuddy"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".codebuddy" / "agents"
