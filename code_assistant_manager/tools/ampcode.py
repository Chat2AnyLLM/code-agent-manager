import os
from typing import List

from .base import CLITool


class AmpcodeTool(CLITool):
    command_name = "amp"
    tool_key = "ampcode"
    install_description = "Amp CLI - frontier coding agent"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        # Amp CLI handles its own authentication and configuration
        # Load environment first
        load_env = __import__(
            "code_assistant_manager.env_loader", fromlist=["load_env"]
        ).load_env
        load_env()

        env = os.environ.copy()
        self._set_node_tls_env(env)

        # Check if amp command is available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        try:
            command = ["amp"] + args

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"amp {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            result = self._run_command(command, env=env)
            return result.returncode
        except KeyboardInterrupt:
            return 130
        except Exception as e:
            return self._handle_error("Error running amp", e)