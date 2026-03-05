from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class PiCodingAgentConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("pi-coding-agent")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".pi" / "agent" / "settings.json",
            ],
            "project": [
                self.cwd / ".pi" / "settings.json",
            ],
        }
