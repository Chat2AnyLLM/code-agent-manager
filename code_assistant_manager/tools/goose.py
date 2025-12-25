import os
from typing import List

from .base import CLITool


class GooseTool(CLITool):
    """Block Goose CLI wrapper."""

    command_name = "goose"
    tool_key = "goose"
    install_description = "Block Goose - open-source, extensible AI agent"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        # Load environment variables first
        self._load_environment()

        # Check if Goose is installed
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Use environment variables directly
        env = os.environ.copy()
        # Set TLS environment
        self._set_node_tls_env(env)

        # Execute the Goose CLI with the configured environment
        command = [self.command_name, *args]
        return self._run_tool_with_env(command, env, self.command_name, interactive=True)
