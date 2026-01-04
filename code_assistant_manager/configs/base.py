"""Base configuration class for AI code assistants."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

logger = logging.getLogger(__name__)


class BaseToolConfig(ABC):
    """Base class for tool configuration management."""

    def __init__(self, tool_name: str):
        """Initialize with tool name."""
        self.tool_name = tool_name
        self.home = Path.home()
        self.cwd = Path.cwd()

    @abstractmethod
    def get_scope_paths(self) -> Dict[str, List[Path]]:
        """Return mapping of scopes to list of possible config paths.

        Returns:
            Dict[str, List[Path]]: e.g., {'user': [Path(...)], 'project': [Path(...)]}
        """
        pass

    def get_config_path(self, scope: str) -> Optional[Path]:
        """Get the primary config path for a given scope.

        Args:
            scope: 'user' or 'project'

        Returns:
            Path object or None if scope not supported
        """
        paths = self.get_scope_paths().get(scope, [])
        if not paths:
            return None

        # Return the first path that exists, or the first path if none exist (for creation)
        for path in paths:
            if path.exists():
                return path
        return paths[0]

    def load_config(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration.

        Args:
            scope: If provided, load only that scope. If None, load all scopes.

        Returns:
            Dict with scope keys if scope is None, or config dict if scope provided.
        """
        if scope:
            path = self.get_config_path(scope)
            if not path or not path.exists():
                return {}
            return self._load_file(path)

        # Load all scopes
        results = {}
        for s_name, paths in self.get_scope_paths().items():
            merged_data = {}
            loaded_paths = []

            # Load all existing files for this scope and merge them
            for path in paths:
                if path.exists():
                    try:
                        file_data = self._load_file(path)
                        # Deep merge the data
                        self._deep_merge(merged_data, file_data)
                        loaded_paths.append(str(path))
                    except Exception as e:
                        logger.warning(f"Failed to load {path}: {e}")
                        continue

            if merged_data:
                # Use the first loaded path as the representative path
                results[s_name] = {
                    "data": merged_data,
                    "path": loaded_paths[0] if loaded_paths else str(paths[0]),
                }

        return results

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _load_file(self, path: Path) -> Dict[str, Any]:
        """Load a single config file."""
        if path.suffix == ".toml":
            with open(path, "rb") as f:
                return tomllib.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    def save_config(self, data: Dict[str, Any], scope: str) -> Path:
        """Save configuration to the specified scope.

        Args:
            data: Configuration data dict
            scope: 'user' or 'project'

        Returns:
            Path where config was saved
        """
        path = self.get_config_path(scope)
        if not path:
            raise ValueError(f"Unsupported scope: {scope}")

        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".toml":
            with open(path, "wb") as f:
                tomli_w.dump(data, f)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        
        return path

    def set_value(self, key_path: str, value: str, scope: str) -> Path:
        """Set a configuration value using dotted notation.

        Args:
            key_path: Dotted key path (e.g., 'profiles.default.model')
            value: Value to set
            scope: Scope to save to

        Returns:
            Path where config was saved
        """
        config_data = self.load_config(scope)
        
        # Parse key path
        parts = self._parse_key_path(key_path)
        
        # Set nested value
        self._set_nested_value(config_data, parts, value)
        
        return self.save_config(config_data, scope)

    def unset_value(self, key_path: str, scope: str) -> bool:
        """Unset a configuration value.

        Args:
            key_path: Dotted key path
            scope: Scope to remove from

        Returns:
            True if key was found and removed, False otherwise
        """
        config_data = self.load_config(scope)
        if not config_data:
            return False

        parts = self._parse_key_path(key_path)
        
        # Special handling for potentially merged keys in TOML
        # (similar to what was in app.py)
        if len(parts) > 2 and self.get_config_path(scope).suffix == ".toml":
            # Heuristic check for version numbers split by dots
            pass  # Logic can be refined if needed

        found = self._unset_nested_value(config_data, parts)
        
        if found:
            self.save_config(config_data, scope)
            
        return found

    def _parse_key_path(self, key_path: str) -> List[str]:
        """Parse dotted key path, handling quotes."""
        import re
        # Regex matches quoted strings OR unquoted parts
        parts = re.split(r'(?<!\\)"(?:\\.|[^"\\])*"(?:\s*\.\s*|\s*$)|\s*\.\s*', key_path.strip())
        
        cleaned = []
        for part in parts:
            part = part.strip()
            if part and part not in ['.', '']:
                if part.startswith('"') and part.endswith('"'):
                    part = part[1:-1].replace('\"', '"')
                cleaned.append(part)
        return cleaned

    def _set_nested_value(self, data: Dict, key_parts: List[str], val: Any):
        """Set value in nested dict, creating intermediates."""
        if len(key_parts) == 1:
            data[key_parts[0]] = val
            return

        current_key = key_parts[0]
        if current_key not in data or not isinstance(data[current_key], dict):
            data[current_key] = {}
        
        self._set_nested_value(data[current_key], key_parts[1:], val)

    def _unset_nested_value(self, data: Dict, key_parts: List[str]) -> bool:
        """Unset value in nested dict."""
        if len(key_parts) == 1:
            key = key_parts[0]
            candidates = [key]
            # Try quoted version if it has special chars
            if '/' in key or any(c in key for c in '.-'):
                candidates.append(f'"{key}"')
                
            for candidate in candidates:
                if candidate in data:
                    del data[candidate]
                    return True
            return False

        current_key = key_parts[0]
        if current_key not in data or not isinstance(data[current_key], dict):
            return False

        return self._unset_nested_value(data[current_key], key_parts[1:])
