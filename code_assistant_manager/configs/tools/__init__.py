"""Tool-specific configuration registry."""

from typing import Dict, Optional, Type
from ..base import BaseToolConfig

from .claude import ClaudeConfig
from .codex import CodexConfig
from .cursor import CursorConfig
from .gemini import GeminiConfig
from .copilot import CopilotConfig
from .qwen import QwenConfig
from .codebuddy import CodeBuddyConfig
from .crush import CrushConfig
from .droid import DroidConfig
from .iflow import IFlowConfig
from .neovate import NeovateConfig
from .qoder import QoderConfig
from .zed import ZedConfig

# Registry
_CONFIG_CLASSES: Dict[str, Type[BaseToolConfig]] = {
    "claude": ClaudeConfig,
    "codex": CodexConfig,
    "cursor-agent": CursorConfig,
    "gemini": GeminiConfig,
    "copilot": CopilotConfig,
    "qwen": QwenConfig,
    "codebuddy": CodeBuddyConfig,
    "crush": CrushConfig,
    "droid": DroidConfig,
    "iflow": IFlowConfig,
    "neovate": NeovateConfig,
    "qodercli": QoderConfig,
    "zed": ZedConfig,
}


def get_tool_config(tool_name: str) -> Optional[BaseToolConfig]:
    """Get config instance for a tool."""
    cls = _CONFIG_CLASSES.get(tool_name)
    if cls:
        return cls()
    return None
