from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class GeminiConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("gemini")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".gemini" / "settings.json"],
            "project": [self.cwd / ".gemini" / "settings.json"],
        }
