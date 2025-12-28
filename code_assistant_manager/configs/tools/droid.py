from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class DroidConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("droid")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".factory" / "mcp.json",
                self.home / ".factory" / "settings.json",
            ],
            "project": [
                self.cwd / ".factory" / "mcp.json",
                self.cwd / ".factory" / "settings.json",
            ],
        }
