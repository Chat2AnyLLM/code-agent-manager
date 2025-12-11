"""Agent management for Code Assistant Manager.

This package provides functionality to manage agents for AI coding assistants.
Agents are markdown files that define custom agent behaviors and are installed to:
- Claude: ~/.claude/agents/
- Codex: ~/.codex/agents/
- Gemini: ~/.gemini/agents/
- Droid: ~/.factory/agents/
- CodeBuddy: ~/.codebuddy/agents/
- OpenCode: ~/.config/opencode/agent/

Reference: https://github.com/iannuttall/claude-agents
"""

from .base import BaseAgentHandler
from .claude import ClaudeAgentHandler
from .codebuddy import CodebuddyAgentHandler
from .codex import CodexAgentHandler
from .copilot import CopilotAgentHandler
from .droid import DroidAgentHandler
from .gemini import GeminiAgentHandler
from .opencode import OpenCodeAgentHandler
from .manager import VALID_APP_TYPES, AgentManager, AGENT_HANDLERS
from .models import Agent, AgentRepo


def get_handler(app_type: str) -> BaseAgentHandler:
    """Get an agent handler instance for the specified app type."""
    handler_class = AGENT_HANDLERS.get(app_type)
    if not handler_class:
        raise ValueError(f"Unknown app type: {app_type}. Valid: {VALID_APP_TYPES}")
    return handler_class()


__all__ = [
    "Agent",
    "AgentRepo",
    "AgentManager",
    "BaseAgentHandler",
    "ClaudeAgentHandler",
    "CodexAgentHandler",
    "GeminiAgentHandler",
    "DroidAgentHandler",
    "CodebuddyAgentHandler",
    "CopilotAgentHandler",
    "OpenCodeAgentHandler",
    "get_handler",
    "VALID_APP_TYPES",
]
