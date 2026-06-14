import logging
import os
from pathlib import Path
from typing import List, Optional

from .base import CLITool

logger = logging.getLogger(__name__)


class KimiTool(CLITool):
    """Moonshot AI Kimi CLI wrapper."""

    command_name = "kimi"
    tool_key = "kimi"
    install_description = "Moonshot AI Kimi CLI"

    def _write_config(
        self,
        *,
        endpoint_config: dict,
        model: str,
        provider_name: str = "kimi",
    ) -> Path:
        """Write kimi configuration to ~/.kimi/config.toml."""
        config_path = Path.home() / ".kimi" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create TOML content
        toml_content = f'''default_model = "{model}"

[providers.{provider_name}]
type = "kimi"
base_url = "{endpoint_config['endpoint']}"
api_key = "{endpoint_config['actual_api_key']}"

[models.{model}]
provider = "{provider_name}"
model = "{model}"
max_context_size = 262144
'''

        # Write to config file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        return config_path

    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the Moonshot AI Kimi CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Kimi CLI

        Returns:
            Exit code of the Kimi CLI process
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
            "kimi", select_multiple=False
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

        # Write configuration to ~/.kimi/config.toml
        config_path = None
        try:
            config_path = self._write_config(
                endpoint_config=endpoint_config,
                model=model,
                provider_name="kimi"
            )
            print(f"[code-agent-manager] Updated kimi config: {config_path}")
        except Exception as e:
            error_path = config_path or "~/.kimi/config.toml"
            return self._handle_error(f"Failed to write {error_path}", e)

        # Set up environment variables for Kimi
        env = os.environ.copy()
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the Kimi CLI - it will read from the config file
        command = ["kimi"] + args

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"kimi {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "kimi", interactive=True)