import logging
import os
import subprocess
from typing import List

from .base import CLITool

logger = logging.getLogger(__name__)


class CursorTool(CLITool):
    """Cursor Agent CLI wrapper."""

    command_name = "cursor-agent"
    tool_key = "cursor-agent"
    install_description = "Cursor Agent CLI"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Run the Cursor Agent CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Cursor Agent CLI

        Returns:
            Exit code of the Cursor Agent CLI process
        """
        # Set up environment variables for Cursor Agent manually
        # (Cursor Agent doesn't require full endpoint configuration like Claude)
        env = os.environ.copy()
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

        # Check for CURSOR_API_KEY in environment
        api_key = os.environ.get("CURSOR_API_KEY")
        if api_key:
            env["CURSOR_API_KEY"] = api_key
        else:
            print("Warning: CURSOR_API_KEY environment variable not set")
            print("Cursor Agent may not work properly without authentication")

        # Execute cursor-agent with the provided arguments
        try:
            cmd = ["cursor-agent"] + args

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"cursor-agent {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=env)
            return result.returncode
        except FileNotFoundError:
            print("Error: cursor-agent command not found.")
            print("Please ensure cursor-agent is installed and in your PATH.")
            print("Run: curl https://cursor.com/install -fsS | bash")
            return 1
        except Exception as e:
            print(f"Error running cursor-agent: {e}")
            return 1
