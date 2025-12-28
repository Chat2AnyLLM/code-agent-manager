from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class CodexConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("codex")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [self.home / ".codex" / "config.toml"],
            "project": [self.cwd / ".codex" / "config.toml"],
        }
