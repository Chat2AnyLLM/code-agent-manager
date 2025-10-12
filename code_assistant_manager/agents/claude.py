"""Claude agent handler."""

from pathlib import Path

from .base import BaseAgentHandler


class ClaudeAgentHandler(BaseAgentHandler):
    """Agent handler for Claude Code.

    Claude agents are markdown files stored in ~/.claude/agents/
    Reference: https://github.com/iannuttall/claude-agents
    """

    @property
    def app_name(self) -> str:
        return "claude"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".claude" / "agents"
