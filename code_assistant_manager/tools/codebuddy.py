import os
from typing import List

from .base import CLITool


class CodeBuddyTool(CLITool):
    """CodeBuddy CLI wrapper."""

    command_name = "codebuddy"
    tool_key = "codebuddy"
    install_description = "Tencent CodeBuddy CLI"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Run the Tencent CodeBuddy CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the CodeBuddy CLI

        Returns:
            Exit code of the CodeBuddy CLI process
        """
        # Set up endpoint and model for CodeBuddy
        success, result = self._validate_and_setup_tool(
            "codebuddy", select_multiple=False
        )
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Set up environment variables for CodeBuddy
        env = os.environ.copy()
        env["CODEBUDDY_BASE_URL"] = endpoint_config["endpoint"]
        env["CODEBUDDY_API_KEY"] = endpoint_config["actual_api_key"]

        # Display API key status
        if env["CODEBUDDY_API_KEY"]:
            print("[code-assistant-manager] CODEBUDDY_API_KEY loaded (masked)")
        else:
            print(
                "[code-assistant-manager] CODEBUDDY_API_KEY not set; model list may be limited"
            )

        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the CodeBuddy CLI with the configured environment and model
        command = ["codebuddy", "--model", model] + args

        # Display the complete command that will be executed
        args_str = " ".join(args) if args else ""
        command_str = f"codebuddy --model {model} {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(
            f"CODEBUDDY_API_KEY=*** CODEBUDDY_BASE_URL={env['CODEBUDDY_BASE_URL']} {command_str}"
        )
        print("")
        return self._run_tool_with_env(command, env, "codebuddy", interactive=True)
