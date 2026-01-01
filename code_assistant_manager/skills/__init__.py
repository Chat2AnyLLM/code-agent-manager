"""Skill management for Code Assistant Manager.

This package provides functionality to manage skills for AI coding assistants.
Skills are downloaded from GitHub repositories and installed to:
- Claude: ~/.claude/skills/
- Codex: ~/.codex/skills/
- Copilot: ~/.copilot/skills/
- Gemini: ~/.gemini/skills/
- Droid: ~/.factory/skills/
- CodeBuddy: ~/.codebuddy/skills/
"""

from .base import BaseSkillHandler
from .claude import ClaudeSkillHandler
from .codebuddy import CodebuddySkillHandler
from .codex import CodexSkillHandler
from .copilot import CopilotSkillHandler
from .droid import DroidSkillHandler
from .gemini import GeminiSkillHandler
from .qwen import QwenSkillHandler

__all__ = [
    "Skill",
    "SkillRepo",
    "SkillManager",
    "BaseSkillHandler",
    "ClaudeSkillHandler",
    "CodexSkillHandler",
    "CopilotSkillHandler",
    "GeminiSkillHandler",
    "DroidSkillHandler",
    "CodebuddySkillHandler",
    "QwenSkillHandler",
]
