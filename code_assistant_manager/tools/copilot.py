import os
from typing import List

from .base import CLITool


class CopilotTool(CLITool):
    command_name = "copilot"
    tool_key = "copilot-api"
    install_description = "GitHub Copilot CLI"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        # Copilot CLI does not rely on endpoint selection; it uses GITHUB_TOKEN
        # Load environment first
        load_env = __import__(
            "code_assistant_manager.env_loader", fromlist=["load_env"]
        ).load_env
        load_env()

        env = os.environ.copy()
        self._set_node_tls_env(env)

        # Check if copilot command is available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Ensure GITHUB_TOKEN is present
        if not os.environ.get("GITHUB_TOKEN"):
            return self._handle_error(
                "GITHUB_TOKEN not set; please export or add to .env", exit_code=1
            )

        try:
            command = ["copilot", "--banner"] + args

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"copilot --banner {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            result = self._run_command(command, env=env)
            return result.returncode
        except KeyboardInterrupt:
            return 130
        except Exception as e:
            return self._handle_error("Error running copilot", e)
