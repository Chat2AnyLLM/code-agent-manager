import logging
import os
from typing import List

from .base import CLITool

logger = logging.getLogger(__name__)


class CodexTool(CLITool):
    """Codex CLI wrapper."""

    command_name = "codex"
    tool_key = "openai-codex"
    install_description = "OpenAI Codex CLI"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Run the OpenAI Codex CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Codex CLI

        Returns:
            Exit code of the Codex CLI process
        """
        # Set up endpoint and model for Codex
        success, result = self._validate_and_setup_tool("codex", select_multiple=False)
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Set up environment variables for Codex
        env = os.environ.copy()
        env["BASE_URL"] = endpoint_config["endpoint"]
        env["OPENAI_API_KEY"] = endpoint_config["actual_api_key"]
        if env["OPENAI_API_KEY"]:
            print("[code-assistant-manager] OPENAI_API_KEY loaded (masked)")
        else:
            print(
                "[code-assistant-manager] OPENAI_API_KEY not set; model list may be limited"
            )
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Prepare command arguments for Codex
        cmd_args = [
            "-c",
            "model_providers.custom.name=custom",
            "-c",
            f"model_providers.custom.base_url={env['BASE_URL']}",
            "-c",
            f"profiles.custom.model={model}",
            "-c",
            "profiles.custom.model_provider=custom",
            "-c",
            "profiles.custom.model_reasoning_effort=low",
            "-c",
            "model_providers.custom.env_key=OPENAI_API_KEY",
            "-p",
            "custom",
        ]

        # Display the complete command that will be executed
        print("")
        print("Complete command to execute:")
        print(f"OPENAI_API_KEY=dummy codex {' '.join(cmd_args)}")
        print("")

        # Execute the Codex CLI with the configured environment and arguments
        command = ["codex"] + cmd_args + args
        return self._run_tool_with_env(command, env, "codex", interactive=True)
