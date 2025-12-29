import os
from typing import List

from .base import CLITool


class NeovateTool(CLITool):
    command_name = "neovate"
    tool_key = "neovate"
    install_description = "Neovate CLI"

    def run(self, args: List[str] = None) -> int:
        """Run the neovate CLI with resolved endpoint and model.

        Steps:
        1. Resolve endpoint and model via helper
        2. Ensure Copilot models are prefixed correctly
        3. Prepare environment and run subprocess
        """
        args = args or []
        success, result = self._validate_and_setup_tool(
            "neovate", select_multiple=False
        )
        if not success:
            return 1

        endpoint_config, endpoint_name, model = result

        # Ensure Copilot models use the github-copilot/ prefix
        if "copilot" in endpoint_name.lower() and not model.startswith(
            "github-copilot/"
        ):
            model = f"github-copilot/{model}"

        # Prepare environment for subprocess
        env = os.environ.copy()
        self._set_node_tls_env(env)
        env["OPENAI_API_KEY"] = endpoint_config["actual_api_key"]
        env["OPENAI_API_BASE"] = endpoint_config["endpoint"]

        # Insert model argument only if not provided by user
        cmd_args = args.copy()
        if "-m" not in cmd_args and "--model" not in cmd_args:
            cmd_args = ["-m", model] + cmd_args

        try:
            command = ["neovate"] + cmd_args

            # Display the complete command
            args_str = " ".join(cmd_args) if cmd_args else ""
            command_str = f"neovate {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            return self._run_tool_with_env(command, env, "neovate", interactive=True)
        except Exception as e:
            # This shouldn't happen since _run_tool_with_env handles the try/except
            return self._handle_error("Error running neovate", e)
