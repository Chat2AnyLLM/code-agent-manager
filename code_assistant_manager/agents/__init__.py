"""Agent management for Code Assistant Manager.

This package provides functionality to manage agents for AI coding assistants.
Agents are markdown files that define custom agent behaviors and are installed to:
- Claude: ~/.claude/agents/
- Codex: ~/.codex/agents/
- Gemini: ~/.gemini/agents/
- Droid: ~/.factory/agents/
- CodeBuddy: ~/.codebuddy/agents/

Reference: https://github.com/iannuttall/claude-agents
"""

from .base import BaseAgentHandler
from .claude import ClaudeAgentHandler
from .codebuddy import CodebuddyAgentHandler
from .codex import CodexAgentHandler
from .copilot import CopilotAgentHandler
from .droid import DroidAgentHandler
from .gemini import GeminiAgentHandler
from .manager import VALID_APP_TYPES, AgentManager
from .models import Agent, AgentRepo

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
    "VALID_APP_TYPES",
]
