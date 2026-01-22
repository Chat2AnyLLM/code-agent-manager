import logging
import os
from pathlib import Path
from typing import List, Optional

from .base import CLITool

logger = logging.getLogger(__name__)


class AIChatTool(CLITool):
    """AIChat CLI wrapper."""

    command_name = "aichat"
    tool_key = "aichat"
    install_description = "AIChat CLI"

    def _write_config(
        self,
        *,
        endpoint_config: dict,
        model: str,
    ) -> Path:
        """Write aichat configuration to ~/.config/aichat/config.yaml."""
        config_path = Path.home() / ".config" / "aichat" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Get the base URL and API key
        base_url = endpoint_config["endpoint"]
        api_key = endpoint_config["actual_api_key"]

        # Create YAML content based on the user's specified configuration
        # AIChat model format: 'client_name:model_name'
        client_name = "custom"
        formatted_model = f"{client_name}:{model}"

        yaml_content = f"""model: {formatted_model}
use_tools: fs,web_search,code_interpreter,python,terminal,git
temperature: 1
agent_prelude: default

instructions:
  default: |
    You are a helpful AI assistant. You can answer questions, provide explanations, and assist with various tasks.
    If you don't know the answer, you can search the web or use tools to find the information.
    Always be polite and concise in your responses.

clients:
- type: openai-compatible
  name: {client_name}
  api_base: {base_url}
  api_key: {api_key}
  models:
    - name: {model}
"""

        # Write to config file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        return config_path

    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the AIChat CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the AIChat CLI

        Returns:
            Exit code of the AIChat CLI process
        """
        args = args or []

        # Load environment variables first
        self._load_environment()

        # Check if the tool is installed and prompt for upgrade if needed
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Set up endpoint and model using the endpoint manager
        success, result = self._setup_endpoint_and_models(
            "aichat", select_multiple=False
        )
        if not success or result is None:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, _, selected_models = result

        # Handle the case where selected_models might be a string or tuple
        if isinstance(selected_models, str):
            model = selected_models
        elif isinstance(selected_models, tuple) and len(selected_models) > 0:
            model = selected_models[0]  # Take the first model if multiple
        else:
            return self._handle_error("No model selected")

        if not endpoint_config or not model:
            return 1

        # Write configuration to ~/.config/aichat/config.yaml
        config_path = None
        try:
            config_path = self._write_config(
                endpoint_config=endpoint_config,
                model=model,
            )
            print(f"[code-assistant-manager] Updated aichat config: {config_path}")
        except Exception as e:
            error_path = config_path or "~/.config/aichat/config.yaml"
            return self._handle_error(f"Failed to write {error_path}", e)

        # Set up environment variables for AIChat
        env = os.environ.copy()
        # Set TLS environment for Node.js (in case aichat uses it)
        self._set_node_tls_env(env)

        # Execute the AIChat CLI - it will read from the config file
        command = ["aichat"] + args

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"aichat {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "aichat", interactive=True)
