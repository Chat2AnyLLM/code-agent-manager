import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for external CLI tools loaded from tools.yaml with lazy loading and caching."""

    def __init__(self, config_path: Optional[Path] = None):
        env_override = os.environ.get("CODE_ASSISTANT_MANAGER_TOOLS_FILE")
        if config_path is not None:
            self.config_path = Path(config_path)
        elif env_override:
            self.config_path = Path(env_override)
        else:
            # tools.yaml is in the project root, two levels up from this file
            self.config_path = (
                Path(__file__).resolve().parent.parent.parent / "tools.yaml"
            )
        self._tools = None  # Lazy load on first access
        self._cache_time = None
        self._cache_ttl = 30  # Cache for 30 seconds

    def _load(self) -> Dict[str, dict]:
        """Load tools from packaged resources first, then fall back to file path.

        This attempts to read tools.yaml from package data (works for installed
        wheels and editable installs). If that fails, it falls back to the file
        system path computed in __init__, and finally returns an empty dict on
        error.
        """
        # Try to load tools.yaml from package resources (preferred)
        try:
            import importlib.resources as pkg_resources
        except Exception:
            pkg_resources = None

        if pkg_resources is not None:
            try:
                # Newer API (Python 3.9+)
                if hasattr(pkg_resources, "files"):
                    res = pkg_resources.files("code_assistant_manager").joinpath(
                        "tools.yaml"
                    )
                    if res and res.exists():
                        # as_file gives a pathlib.Path we can read from
                        with pkg_resources.as_file(res) as rf:
                            text = rf.read_text(encoding="utf-8")
                        data = yaml.safe_load(text) or {}
                        tools = data.get("tools", {})
                        return tools if isinstance(tools, dict) else {}
                else:
                    # Older API: open_text
                    try:
                        text = pkg_resources.open_text(
                            "code_assistant_manager", "tools.yaml"
                        ).read()
                        data = yaml.safe_load(text) or {}
                        tools = data.get("tools", {})
                        return tools if isinstance(tools, dict) else {}
                    except Exception as e:
                        # Older API failed, will fall through to filesystem-based loading
                        logger.debug(f"Failed to load via older API: {e}")
            except Exception as e:
                # Fall through to filesystem-based loading
                logger.debug(f"Failed to load from package resources: {e}")

        # Fallback: load from the configured filesystem path (legacy behavior)
        if not self.config_path or not self.config_path.exists():
            return {}
        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError):
            return {}

        tools = data.get("tools", {})
        return tools if isinstance(tools, dict) else {}

    def _ensure_loaded(self):
        # Check if cache is still valid
        if self._tools is None or self._cache_time is None or (time.time() - self._cache_time) > self._cache_ttl:
            self._tools = self._load()
            self._cache_time = time.time()

    def reload(self):
        self._tools = self._load()
        self._cache_time = time.time()

    def get_tool(self, tool_key: str) -> dict:
        self._ensure_loaded()
        entry = self._tools.get(tool_key, {})
        return entry if isinstance(entry, dict) else {}

    def get_install_command(self, tool_key: str) -> Optional[str]:
        tool = self.get_tool(tool_key)
        install_cmd = tool.get("install_cmd") if isinstance(tool, dict) else None
        if isinstance(install_cmd, str):
            return install_cmd.strip()
        return None

    def is_enabled(self, tool_key: str) -> bool:
        """Check if a tool is enabled in tools.yaml.

        Args:
            tool_key: The tool key to check

        Returns:
            True if enabled (default), False if explicitly disabled
        """
        tool = self.get_tool(tool_key)
        if not tool:
            return True  # Unknown tools are enabled by default
        # Default to True if 'enabled' key is not present
        return tool.get("enabled", True)

    def get_enabled_tools(self) -> List[str]:
        """Get list of all enabled tool keys.

        Returns:
            List of tool keys that are enabled
        """
        self._ensure_loaded()
        return [
            key
            for key, config in self._tools.items()
            if isinstance(config, dict) and config.get("enabled", True)
        ]


TOOL_REGISTRY = ToolRegistry()
