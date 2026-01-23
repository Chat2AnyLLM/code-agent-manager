from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig


class OpenCodeConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("opencode")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".config" / "opencode" / "opencode.json"],
            "project": [self.cwd / ".config" / "opencode" / "opencode.json"],
        }

    def set_value(self, key_path: str, value: str, scope: str) -> Path:
        """Override set_value to handle plugin array specially."""
        config_data = self.load_config(scope)

        # Parse key path
        parts = self._parse_key_path(key_path)

        # Special handling for plugin key - treat as array
        if len(parts) == 1 and parts[0] == "plugin":
            # Handle plugin array
            if "plugin" not in config_data:
                config_data["plugin"] = []

            if not isinstance(config_data["plugin"], list):
                # Convert existing value to array
                existing_value = config_data["plugin"]
                config_data["plugin"] = [existing_value]

            # Append new value if not already present
            if value not in config_data["plugin"]:
                config_data["plugin"].append(value)
        else:
            # Use default behavior for other keys
            self._set_nested_value(config_data, parts, value)

        return self.save_config(config_data, scope)