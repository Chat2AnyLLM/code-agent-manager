"""Codex agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class CodexAgentHandler(BaseAgentHandler):
    """Agent handler for OpenAI Codex CLI."""

    @property
    def app_name(self) -> str:
        return "codex"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".codex" / "agents"
