from pathlib import Path
from typing import Dict, List
from ..base import BaseToolConfig

class CopilotConfig(BaseToolConfig):
    def __init__(self):
        super().__init__("copilot")

    def get_scope_paths(self) -> Dict[str, List[Path]]:
        return {
            "user": [
                self.home / ".copilot" / "mcp-config.json",
                self.home / ".copilot" / "mcp.json",
            ],
            "project": [
                self.cwd / ".copilot" / "mcp.json",
            ],
        }
