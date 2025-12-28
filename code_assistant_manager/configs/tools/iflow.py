from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class IFlowConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("iflow")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".iflow" / "settings.json",
                self.home / ".iflow" / "config.json",
            ],
            "project": [self.cwd / "iflow.json"],
        }
