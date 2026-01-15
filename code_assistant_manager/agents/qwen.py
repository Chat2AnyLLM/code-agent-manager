"""Qwen agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class QwenAgentHandler(BaseAgentHandler):
    """Agent handler for Qwen CLI.

    Qwen agents are markdown files stored in:
    - Global: ~/.qwen/agents/
    - Project: .qwen/agents/
    """

    @property
    def app_name(self) -> str:
        return "qwen"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".qwen" / "agents"