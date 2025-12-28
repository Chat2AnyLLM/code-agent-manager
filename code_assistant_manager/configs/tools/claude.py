from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class ClaudeConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("claude")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".claude" / "settings.json",
                self.home / ".claude.json",
                self.home / ".claude" / "settings.local.json",
            ],
            "project": [
                self.cwd / ".claude" / "settings.json",
                self.cwd / ".claude" / "settings.local.json",
                self.cwd / ".clauderc",
            ],
        }
