import os
from typing import List

from .base import CLITool


class PiCodingAgentTool(CLITool):
    """Pi Coding Agent CLI wrapper."""

    command_name = "pi"
    tool_key = "pi-coding-agent"
    install_description = "Pi Coding Agent"

    def run(self, args: List[str] = None) -> int:
        """
        Run the Pi Coding Agent with the specified arguments.

        Args:
            args: List of arguments to pass to Pi Coding Agent

        Returns:
            Exit code of the Pi Coding Agent process
        """
        args = args or []

        # Load environment
        load_env = __import__(
            "code_assistant_manager.env_loader", fromlist=["load_env"]
        ).load_env
        load_env()

        env = os.environ.copy()
        self._set_node_tls_env(env)

        # Check if pi command is available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        try:
            command = ["pi"] + args

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"pi {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            result = self._run_command(command, env=env)
            return result.returncode
        except KeyboardInterrupt:
            return 130
        except Exception as e:
            return self._handle_error("Error running pi", e)
