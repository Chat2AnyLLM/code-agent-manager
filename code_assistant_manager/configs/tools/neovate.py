from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class NeovateConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("neovate")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".neovate" / "config.json"],
            "project": [self.cwd / "neovate.json"],
        }
