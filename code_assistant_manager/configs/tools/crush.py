from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class CrushConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("crush")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".config" / "crush" / "crush.json"],
            "project": [self.cwd / "crush.json"],
        }
