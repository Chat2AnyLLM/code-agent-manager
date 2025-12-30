import json
import os
from pathlib import Path
from typing import List

from .base import CLITool


class BlackboxTool(CLITool):
    """Blackbox AI CLI wrapper."""

    command_name = "blackbox"
    tool_key = "blackbox"
    install_description = "Blackbox AI CLI"

    def _write_blackbox_config(
        self, endpoint_config: dict, model: str, endpoint_name: str
    ) -> Path:
        """
        Write Blackbox CLI configuration to ~/.blackboxcli/settings.json.

        Args:
            endpoint_config: Endpoint configuration dictionary
            model: Selected model name
            endpoint_name: Name of the endpoint

        Returns:
            Path to the written settings file
        """
        config_dir = Path.home() / ".blackboxcli"
        config_file = config_dir / "settings.json"

        # Preserve existing configuration if it exists
        existing_config = {}
        if config_file.exists():
            try:
                existing_config = json.loads(config_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Build the Blackbox configuration
        blackbox_config = {
            "security": {
                "auth": {
                    "selectedType": "blackbox-api",
                    "selectedProvider": "blackbox",
                    "blackbox": {
                        "apiKey": endpoint_config.get("actual_api_key", ""),
                        "baseUrl": endpoint_config.get("endpoint", "https://api.blackbox.ai"),
                        "model": model,
                    },
                }
            },
            "model": {"name": model},
        }

        # Merge with existing configuration to preserve other settings
        if isinstance(existing_config, dict):
            # Deep merge security.auth settings
            if "security" not in existing_config:
                existing_config["security"] = {}
            if "auth" not in existing_config["security"]:
                existing_config["security"]["auth"] = {}

            existing_config["security"]["auth"].update(blackbox_config["security"]["auth"])
            existing_config["model"] = blackbox_config["model"]
            final_config = existing_config
        else:
            final_config = blackbox_config

        # Write the configuration
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(final_config, f, indent=2, ensure_ascii=False)

        return config_file

    def run(self, args: List[str] = None) -> int:
        """
        Configure and launch the Blackbox AI CLI.

        Args:
            args: List of arguments to pass to the Blackbox CLI

        Returns:
            Exit code of the Blackbox CLI process
        """
        args = args or []

        # Set up endpoint and model for Blackbox
        success, result = self._validate_and_setup_tool("blackbox", select_multiple=False)
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Write Blackbox configuration file
        config_file = self._write_blackbox_config(endpoint_config, model, endpoint_name)
        print(f"Blackbox configuration written to {config_file}")

        # Set up environment variables for Blackbox based on tools.yaml configuration
        env = os.environ.copy()
        env["BLACKBOX_API_KEY"] = endpoint_config["actual_api_key"]
        env["BLACKBOX_API_BASE_URL"] = endpoint_config["endpoint"]
        env["BLACKBOX_API_MODEL"] = model
        self._set_node_tls_env(env)

        # Execute the Blackbox CLI with the configured environment
        command = ["blackbox"] + args

        # Display the complete command that will be executed
        args_str = " ".join(args) if args else ""
        command_str = f"blackbox {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(
            f"BLACKBOX_API_BASE_URL={env['BLACKBOX_API_BASE_URL']} "
            f"BLACKBOX_API_KEY=*** "
            f"BLACKBOX_API_MODEL={model} {command_str}"
        )
        print("")

        return self._run_tool_with_env(command, env, "blackbox", interactive=True)
