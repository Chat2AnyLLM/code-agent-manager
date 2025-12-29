import os
from typing import List

from .base import CLITool


class QwenTool(CLITool):
    """Qwen CLI wrapper."""

    command_name = "qwen"
    tool_key = "qwen-code"
    install_description = "Qwen Code CLI"

    def run(self, args: List[str] = None) -> int:
        """
        Run the Qwen CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Qwen CLI

        Returns:
            Exit code of the Qwen CLI process
        """
        args = args or []
        # Set up endpoint and model for Qwen
        success, result = self._validate_and_setup_tool("qwen", select_multiple=False)
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Set up environment variables for Qwen based on tools.yaml configuration
        env = os.environ.copy()
        env["OPENAI_BASE_URL"] = endpoint_config["endpoint"]
        env["OPENAI_API_KEY"] = endpoint_config["actual_api_key"]
        env["OPENAI_MODEL"] = model
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

        # Execute the Qwen CLI with the configured environment
        command = ["qwen"] + args

        # Display the complete command that will be executed
        args_str = " ".join(args) if args else ""
        command_str = f"qwen {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(
            f"OPENAI_BASE_URL={env['OPENAI_BASE_URL']} "
            f"OPENAI_API_KEY=dummy "
            f"OPENAI_MODEL={model} {command_str}"
        )
        print("")
        return self._run_tool_with_env(command, env, "qwen", interactive=True)
