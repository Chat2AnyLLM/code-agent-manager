import os
from typing import List

from .base import CLITool


class IfLowTool(CLITool):
    """iFlow CLI wrapper."""

    command_name = "iflow"
    tool_key = "iflow"
    install_description = "iFlow CLI"

    def run(self, args: List[str] = None) -> int:
        """
        Run the iFlow CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the iFlow CLI

        Returns:
            Exit code of the iFlow CLI process
        """
        args = args or []
        # Set up endpoint and model for iFlow
        success, result = self._validate_and_setup_tool("iflow", select_multiple=False)
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Set up environment variables for iFlow
        env = os.environ.copy()
        env["IFLOW_BASE_URL"] = endpoint_config["endpoint"]
        env["IFLOW_API_KEY"] = endpoint_config["actual_api_key"]
        env["IFLOW_MODEL_NAME"] = model

        # Check if API key is available
        if not env["IFLOW_API_KEY"]:
            print("Error: API key not resolved for selected endpoint")
            return 1

        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the iFlow CLI with the configured environment
        command = ["iflow", *args]

        # Display the complete command that will be executed
        args_str = " ".join(args) if args else ""
        command_str = f"iflow {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(
            "IFLOW_API_KEY=*** "
            f"IFLOW_BASE_URL={env['IFLOW_BASE_URL']} "
            f"IFLOW_MODEL_NAME={env['IFLOW_MODEL_NAME']} {command_str}"
        )
        print("")
        return self._run_tool_with_env(command, env, "iflow", interactive=True)
