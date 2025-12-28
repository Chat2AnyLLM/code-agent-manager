from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class QoderConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("qodercli")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".qodercli" / "config.json"],
            "project": [self.cwd / "qoder.json"],
        }
