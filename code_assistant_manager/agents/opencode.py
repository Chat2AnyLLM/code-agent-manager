"""OpenCode agent handler."""

from pathlib import Path
from typing import Optional

from .base import BaseAgentHandler


class OpenCodeAgentHandler(BaseAgentHandler):
    """Agent handler for OpenCode.

    OpenCode agents are markdown files stored in:
    - Global: ~/.config/opencode/agent/
    - Project: .opencode/agent/
    """

    @property
    def app_name(self) -> str:
        return "opencode"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".config" / "opencode" / "agent"