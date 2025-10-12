"""Tools package - central registry and base classes."""

import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Type

from ..config import ConfigManager
from ..endpoints import EndpointManager

# Import tool modules so their subclasses are registered
from . import (  # noqa: F401
    claude,
    codebuddy,
    codex,
    copilot,
    crush,
    cursor,
    droid,
    gemini,
    iflow,
    neovate,
    qodercli,
    qwen,
    zed,
)
from .base import CLITool

# Import MCP tool from the MCP package (handles registration)
try:
    from ..mcp.tool import MCPTool  # noqa: F401
except ImportError:
    # Circular import protection - MCPTool will be registered when the package is imported elsewhere
    pass


# Backwards-compat: expose UI helpers that used to be available from code_assistant_manager.tools

# Expose model selector functions
from ..menu.menus import display_centered_menu, select_two_models  # noqa: F401


def select_model(
    models: list[str], prompt: str = "Select a model:"
) -> Tuple[bool, Optional[str]]:
    """Backward-compatible wrapper for model selection.

    Args:
        models: List of available models
        prompt: Display prompt for selection

    Returns:
        Tuple of (success, selected_model)
    """
    success, idx = display_centered_menu(prompt, models, "Cancel")
    if success and idx is not None:
        return True, models[idx]
    return False, None


# Backwards-compatible exports: expose tool classes at package level
from .claude import ClaudeTool  # noqa: F401,E402
from .codebuddy import CodeBuddyTool  # noqa: F401,E402
from .codex import CodexTool  # noqa: F401,E402
from .copilot import CopilotTool  # noqa: F401,E402
from .crush import CrushTool  # noqa: F401,E402
from .cursor import CursorTool  # noqa: F401,E402
from .droid import DroidTool  # noqa: F401,E402

# Expose endpoint display functions
from .endpoint_display import (  # noqa: F401,E402
    display_all_tool_endpoints,
    display_tool_endpoints,
)
from .gemini import GeminiTool  # noqa: F401,E402
from .iflow import IfLowTool  # noqa: F401,E402
from .neovate import NeovateTool  # noqa: F401,E402
from .qodercli import QoderCLITool  # noqa: F401,E402
from .qwen import QwenTool  # noqa: F401,E402

# Expose registry for backwards compatibility
from .registry import TOOL_REGISTRY  # noqa: F401,E402
from .zed import ZedTool  # noqa: F401,E402

# Backwards-compat: expose commonly patched names used in tests
# so tests that patch code_assistant_manager.tools.<name> continue to work.
EndpointManager = EndpointManager  # type: ignore
ConfigManager = ConfigManager  # type: ignore
subprocess = subprocess  # re-export subprocess for tests
Path = Path


def get_registered_tools() -> Dict[str, Type[CLITool]]:
    """Return mapping of command name to tool class by discovering CLITool subclasses.

    Only returns tools that are enabled in tools.yaml (enabled: true or not specified).
    Tools with enabled: false are hidden from menus.
    """
    tools: Dict[str, Type[CLITool]] = {}
    for cls in CLITool.__subclasses__():
        name = getattr(cls, "command_name", None)
        tool_key = getattr(cls, "tool_key", None)
        if name:
            # Check if tool is enabled in registry
            # Use tool_key if available, otherwise fall back to command_name
            key_to_check = tool_key or name
            if TOOL_REGISTRY.is_enabled(key_to_check):
                tools[name] = cls
    return tools
