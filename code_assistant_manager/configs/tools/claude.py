from pathlib import Path
from typing import Dict, List, Any
from ..base import BaseToolConfig

class ClaudeConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("claude")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".claude.json",  # Main Claude config file
                self.home / ".claude" / "settings.json",
                self.home / ".claude" / "settings.local.json",
            ],
            "project": [
                self.cwd / ".claude" / "settings.json",
                self.cwd / ".claude" / "settings.local.json",
                self.cwd / ".clauderc",
                self.cwd / ".claude" / "mcp.json",
                self.cwd / ".claude" / "mcp.local.json",
            ],
        }

    def _load_file(self, path: Path) -> Dict[str, Any]:
        """Load and filter Claude config file, excluding internal metadata."""
        data = super()._load_file(path)

        # Filter out internal/metadata keys that shouldn't be exposed in config
        internal_keys = {"claude"}  # Add more internal keys here if needed

        filtered_data = {}
        for key, value in data.items():
            if key not in internal_keys:
                filtered_data[key] = value

        return filtered_data
