import os
from typing import List

from .base import CLITool


class ZedTool(CLITool):
    command_name = "zed"
    tool_key = "zed"
    install_description = "Zed Editor"

    def run(self, args: List[str] = None) -> int:
        """
        Run the Zed editor with the specified arguments.

        Args:
            args: List of arguments to pass to Zed

        Returns:
            Exit code of the Zed process
        """
        args = args or []
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        try:
            command = ["zed", *args]
            return self._run_tool_with_env(
                command, os.environ.copy(), "zed", interactive=True
            )
        except Exception as e:
            # This shouldn't happen since _run_tool_with_env handles the try/except
            return self._handle_error("Error running zed", e)
