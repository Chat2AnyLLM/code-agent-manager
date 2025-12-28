from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class CursorConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("cursor-agent")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".cursor" / "mcp.json",
                self.home / ".cursor" / "settings.json",
            ],
            "project": [
                self.cwd / ".cursor" / "mcp.json",
                self.cwd / ".cursor" / "settings.json",
            ],
        }
