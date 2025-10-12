"""Gemini agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class GeminiAgentHandler(BaseAgentHandler):
    """Agent handler for Google Gemini CLI."""

    @property
    def app_name(self) -> str:
        return "gemini"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".gemini" / "agents"
