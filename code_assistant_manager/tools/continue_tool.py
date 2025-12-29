import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .base import CLITool


class ContinueTool(CLITool):
    """Continue.dev CLI wrapper."""

    command_name = "cn"
    tool_key = "continue"
    install_description = "Continue.dev CLI"

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the continue client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "continue")
        ]

    def _process_endpoint(self, endpoint_name: str) -> Optional[List[str]]:
        """Process a single endpoint and return selected models if successful."""
        success, endpoint_config = self.endpoint_manager.get_endpoint_config(
            endpoint_name
        )
        if not success:
            return None

        # Get models from list_models_cmd
        models = []
        if "list_models_cmd" in endpoint_config:
            try:
                import subprocess

                env = os.environ.copy()
                env["endpoint"] = endpoint_config.get("endpoint", "")
                env["api_key"] = endpoint_config.get("actual_api_key", "")

                result = subprocess.run(
                    endpoint_config["list_models_cmd"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                if result.returncode == 0 and result.stdout.strip():
                    models = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            except Exception as e:
                print(f"Warning: Failed to execute list_models_cmd for {endpoint_name}: {e}")
                return None
        else:
            # Fallback if no list_models_cmd
            models = [endpoint_name.replace(":", "-").replace("_", "-")]

        if not models:
            print(f"Warning: No models found for {endpoint_name}\n")
            return None

        ep_url = endpoint_config.get("endpoint", "")
        ep_desc = endpoint_config.get("description", "") or ep_url
        endpoint_info = f"{endpoint_name} -> {ep_url} -> {ep_desc}"

        # Import helper for multiple model selection
        from code_assistant_manager.menu.menus import select_multiple_models

        # Non-interactive mode: select first model
        if os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1":
            selected_models = [models[0]]
        else:
            success, selected_models = select_multiple_models(
                models,
                f"Select models from {endpoint_info} (Cancel to skip):",
                cancel_text="Skip"
            )
            if not success or not selected_models:
                print(f"Skipped {endpoint_name}\n")
                return None

        return selected_models

    def _write_continue_config(self, selected_models: List[tuple]) -> Path:
        """Write Continue.dev configuration to ~/.continue/config.yaml."""
        # Create config structure
        continue_config = {
            "name": "Code Assistant Manager Config",
            "version": "0.0.1",
            "schema": "v1",
            "models": [],
        }

        # Create models from selected endpoints
        for endpoint_name, model_name in selected_models:
            success, endpoint_config = self.endpoint_manager.get_endpoint_config(endpoint_name)
            if not success:
                continue

            # Create model entry
            model_entry = {
                "name": f"{endpoint_name} - {model_name}",
                "provider": "openai",
                "model": model_name,
                "apiBase": endpoint_config["endpoint"],
                "requestOptions": {
                    "verifySsl": False
                }
            }

            # Handle API key configuration - use actual resolved key
            api_key = endpoint_config.get("actual_api_key", "")
            if api_key:
                model_entry["apiKey"] = api_key

            continue_config["models"].append(model_entry)

        # Preserve existing MCP servers (if any)
        config_file = Path.home() / ".continue" / "config.yaml"
        if config_file.exists():
            try:
                existing = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
                if isinstance(existing, dict) and "mcpServers" in existing:
                    existing_servers = existing.get("mcpServers")
                    if isinstance(existing_servers, dict):
                        # Convert legacy dict format to Continue's list-of-objects format
                        converted = []
                        for name, cfg in existing_servers.items():
                            if not isinstance(cfg, dict):
                                continue
                            item = {"name": name}
                            item.update(cfg)
                            converted.append(item)
                        continue_config["mcpServers"] = converted
                    elif isinstance(existing_servers, list):
                        continue_config["mcpServers"] = existing_servers
            except Exception:
                pass

        # Write the config
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(continue_config, f, sort_keys=False)

        return config_file

    def run(self, args: List[str] = None) -> int:
        """
        Configure and launch the Continue.dev CLI.

        Args:
            args: List of arguments to pass to the Continue CLI

        Returns:
            Exit code of the Continue CLI process
        """
        args = args or []

        # Load environment variables first
        self._load_environment()

        # Check if Continue.dev is installed
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Get filtered endpoints that support continue
        filtered_endpoints = self._get_filtered_endpoints()

        if not filtered_endpoints:
            print("Warning: No endpoints configured for continue client.")
            print("Continue.dev will use its default configuration.")
        else:
            print("\nConfiguring Continue.dev with models from all endpoints...\n")

            # Process each endpoint to collect selected models
            selected_models: List[tuple] = []  # (endpoint_name, model_name)
            for endpoint_name in filtered_endpoints:
                models = self._process_endpoint(endpoint_name)
                if models:
                    for model in models:
                        selected_models.append((endpoint_name, model))

            if not selected_models:
                print("No models selected")
                return 1

            print(f"Total models selected: {len(selected_models)}\n")

            # Generate Continue.dev config file
            config_file = self._write_continue_config(selected_models)
            print(f"Continue.dev config written to {config_file}")

        # Set up environment for Continue
        env = os.environ.copy()
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the Continue CLI with the configured environment
        command = [self.command_name, *args]

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"{self.command_name} {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, self.command_name, interactive=True)
