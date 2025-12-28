from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class QwenConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("qwen")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".qwen" / "settings.json"],
            "project": [self.cwd / ".qwen" / "settings.json"],
        }
