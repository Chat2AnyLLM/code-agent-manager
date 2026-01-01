"""Plugin management for AI coding assistants.

This module provides functionality to manage plugins for AI coding assistants:
- Claude Code: ~/.claude/plugins/
- Codex: ~/.codex/plugins/
- Copilot: ~/.copilot/plugins/

Plugins are installed from GitHub repositories or local directories.
"""

from .base import BasePluginHandler
from .claude import ClaudePluginHandler
from .codebuddy import CodebuddyPluginHandler
from .codex import CodexPluginHandler
from .copilot import CopilotPluginHandler
from .droid import DroidPluginHandler
from .fetch import (
    FetchedRepoInfo,
    fetch_repo_info,
    fetch_repo_info_from_url,
    parse_github_url,
)
from .gemini import GeminiPluginHandler
from .manager import (
    PLUGIN_HANDLERS,
    VALID_APP_TYPES,
    PluginManager,
    get_handler,
)
from .models import Marketplace, Plugin, PluginRepo

__all__ = [
    # Models
    "Plugin",
    "Marketplace",
    "PluginRepo",
    # Base handler
    "BasePluginHandler",
    # App-specific handlers
    "ClaudePluginHandler",
    "CodexPluginHandler",
    "CopilotPluginHandler",
    "GeminiPluginHandler",
    "DroidPluginHandler",
    "CodebuddyPluginHandler",
    # Manager
    "PluginManager",
    "get_handler",
    # Fetch utilities
    "FetchedRepoInfo",
    "fetch_repo_info",
    "fetch_repo_info_from_url",
    "parse_github_url",
    # Constants
    "PLUGIN_HANDLERS",
    "VALID_APP_TYPES",
]
