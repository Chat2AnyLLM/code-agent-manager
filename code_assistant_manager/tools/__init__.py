"""Tools package - central registry and base classes."""

import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Type

from ..config import ConfigManager
from ..endpoints import EndpointManager

# Expose registry for backwards compatibility
# Import early since get_registered_tools needs it
from .registry import TOOL_REGISTRY  # noqa: F401,E402

from .base import CLITool

# Backwards-compat: expose UI helpers that used to be available from code_assistant_manager.tools

# Expose model selector functions
from ..menu.menus import display_centered_menu, select_two_models  # noqa: F401

# Expose endpoint display functions
from .endpoint_display import (  # noqa: F401,E402
    display_all_tool_endpoints,
    display_tool_endpoints,
)

# Backwards-compat: expose commonly patched names used in tests
# so tests that patch code_assistant_manager.tools.<name> continue to work.
EndpointManager = EndpointManager  # type: ignore
ConfigManager = ConfigManager  # type: ignore
subprocess = subprocess  # re-export subprocess for tests
Path = Path

# Flag to track if tools have been lazy-loaded
_tools_loaded = False


def _ensure_tools_loaded() -> None:
    """Lazy-load all tool modules to populate TOOL_REGISTRY.

    This is called only when tools are actually needed, not on CLI startup.
    """
    global _tools_loaded
    if _tools_loaded:
        return

    # Import tool modules so their subclasses are registered
    from . import (  # noqa: F401
        blackbox,
        claude,
        codebuddy,
        codex,
        continue_tool,
        copilot,
        crush,
        cursor,
        droid,
        gemini,
        goose,
        iflow,
        neovate,
        opencode,
        qodercli,
        qwen,
        zed,
    )

    # Import MCP tool from the MCP package (handles registration)
    try:
        from ..mcp.tool import MCPTool  # noqa: F401
    except ImportError:
        # Circular import protection - MCPTool will be registered when the package is imported elsewhere
        pass

    _tools_loaded = True


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


def get_registered_tools() -> Dict[str, Type[CLITool]]:
    """Return mapping of command name to tool class by discovering CLITool subclasses.

    Only returns tools that are enabled in tools.yaml (enabled: true or not specified).
    Tools with enabled: false are hidden from menus.

    Note: This function lazy-loads all tool modules on first call.
    """
    _ensure_tools_loaded()

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


# Lazy-load tool classes for backwards compatibility
# These are imported via __getattr__ only when explicitly accessed
def __getattr__(name: str):
    """Lazy-load tool classes when explicitly imported."""
    tool_map = {
        "BlackboxTool": "blackbox",
        "ClaudeTool": "claude",
        "CodeBuddyTool": "codebuddy",
        "CodexTool": "codex",
        "ContinueTool": "continue_tool",
        "CopilotTool": "copilot",
        "CrushTool": "crush",
        "CursorTool": "cursor",
        "DroidTool": "droid",
        "GeminiTool": "gemini",
        "GooseTool": "goose",
        "IfLowTool": "iflow",
        "NeovateTool": "neovate",
        "OpenCodeTool": "opencode",
        "QoderCLITool": "qodercli",
        "QwenTool": "qwen",
        "ZedTool": "zed",
    }

    if name in tool_map:
        module_name = tool_map[name]
        module = __import__(f"code_assistant_manager.tools.{module_name}", fromlist=[name])
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
