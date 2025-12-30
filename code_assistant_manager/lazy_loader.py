"""Lazy loading utilities for deferred module imports to improve startup time.

This module provides utilities for lazy-loading heavy dependencies that are only
needed when specific commands are executed, not on every CLI invocation.
"""

import importlib
import sys
from typing import Any, Callable, Dict, Optional, Type


class LazyModule:
    """Lazy-loading wrapper for modules.

    Defers module import until first access.
    """

    def __init__(self, module_name: str):
        """Initialize lazy module wrapper.

        Args:
            module_name: Full module path to lazy-load
        """
        self.module_name = module_name
        self._module: Optional[Any] = None

    def _load(self) -> Any:
        """Load the module if not already loaded."""
        if self._module is None:
            self._module = importlib.import_module(self.module_name)
        return self._module

    def __getattr__(self, name: str) -> Any:
        """Get attribute from lazy-loaded module."""
        return getattr(self._load(), name)

    def __dir__(self) -> list:
        """List attributes of lazy-loaded module."""
        return dir(self._load())


class LazyFunction:
    """Lazy-loading wrapper for functions from modules.

    Only imports the module when the function is called.
    """

    def __init__(self, module_name: str, func_name: str):
        """Initialize lazy function wrapper.

        Args:
            module_name: Module containing the function
            func_name: Name of the function to wrap
        """
        self.module_name = module_name
        self.func_name = func_name
        self._func: Optional[Callable] = None

    def _load(self) -> Callable:
        """Load the function if not already loaded."""
        if self._func is None:
            module = importlib.import_module(self.module_name)
            self._func = getattr(module, self.func_name)
        return self._func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the lazy-loaded function."""
        return self._load()(*args, **kwargs)


class LazyAttribute:
    """Lazy-loading wrapper for attributes from modules.

    Only imports the module when the attribute is accessed.
    """

    def __init__(self, module_name: str, attr_name: str):
        """Initialize lazy attribute wrapper.

        Args:
            module_name: Module containing the attribute
            attr_name: Name of the attribute to wrap
        """
        self.module_name = module_name
        self.attr_name = attr_name
        self._attr: Optional[Any] = None
        self._loaded = False

    def _load(self) -> Any:
        """Load the attribute if not already loaded."""
        if not self._loaded:
            module = importlib.import_module(self.module_name)
            self._attr = getattr(module, self.attr_name)
            self._loaded = True
        return self._attr

    def __getattr__(self, name: str) -> Any:
        """Get attribute from lazy-loaded object."""
        return getattr(self._load(), name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call lazy-loaded object if it's callable."""
        return self._load()(*args, **kwargs)

    def __repr__(self) -> str:
        """Represent lazy attribute."""
        if self._loaded:
            return repr(self._attr)
        return f"<LazyAttribute {self.module_name}.{self.attr_name}>"


def lazy_import(module_name: str) -> Any:
    """Create a lazy-loading proxy for a module.

    Usage:
        mcp_app = lazy_import("code_assistant_manager.mcp.cli")
        # ... later when accessed ...
        app.add_typer(mcp_app.app, name="mcp")

    Args:
        module_name: Full module path

    Returns:
        LazyModule proxy that defers import until access
    """
    return LazyModule(module_name)


def lazy_function(module_name: str, func_name: str) -> Callable:
    """Create a lazy-loading wrapper for a function.

    Usage:
        get_tools = lazy_function(
            "code_assistant_manager.tools",
            "get_registered_tools"
        )
        # ... later when called ...
        tools = get_tools()

    Args:
        module_name: Module containing the function
        func_name: Function name

    Returns:
        Callable wrapper that defers import until invocation
    """
    return LazyFunction(module_name, func_name)


def lazy_attr(module_name: str, attr_name: str) -> Any:
    """Create a lazy-loading wrapper for a module attribute.

    Usage:
        ConfigManager = lazy_attr(
            "code_assistant_manager.config",
            "ConfigManager"
        )
        # ... later when used ...
        config = ConfigManager(path)

    Args:
        module_name: Module containing the attribute
        attr_name: Attribute name

    Returns:
        LazyAttribute proxy that defers import until access
    """
    return LazyAttribute(module_name, attr_name)


def preload_tools() -> Dict[str, Type]:
    """Preload all tool modules to populate TOOL_REGISTRY.

    This is called only when tools are actually needed (not on every CLI startup).
    """
    from code_assistant_manager.tools import (
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

    # Try to import MCP tool
    try:
        from code_assistant_manager.mcp import tool as mcp_tool  # noqa: F401
    except ImportError:
        pass

    # Return the registry after all imports
    from code_assistant_manager.tools import get_registered_tools
    return get_registered_tools()
