from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class ZedConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("zed")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".config" / "zed" / "settings.json"],
            "project": [self.cwd / ".zed" / "settings.json"],
        }
