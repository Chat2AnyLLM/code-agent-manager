from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class CodeBuddyConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("codebuddy")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".codebuddy.json"],
            "project": [self.cwd / ".codebuddy" / "mcp.json"],
        }
