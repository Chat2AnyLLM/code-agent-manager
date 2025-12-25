import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .base import CLITool


class GooseTool(CLITool):
    """Block Goose CLI wrapper."""

    command_name = "goose"
    tool_key = "goose"
    install_description = "Block Goose - open-source, extensible AI agent"

    # Default context limit for Goose models
    DEFAULT_CONTEXT_LIMIT = 128000

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the goose client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "goose")
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

        # Import package-level helper so tests can patch code_assistant_manager.tools.select_model
        from . import select_model

        # Let user select models from this endpoint
        success, selected_model = select_model(
            models, f"Select models from {endpoint_info} (or skip):"
        )

        if success and selected_model:
            return [selected_model]
        else:
            print(f"Skipped {endpoint_name}\n")
            return None

    def _write_goose_config(self, selected_models_by_endpoint: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Write Goose configuration files for custom providers.
        Returns a dictionary of environment variables to set (e.g. API keys).
        """
        config_dir = Path.home() / ".config" / "goose" / "custom_providers"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        extra_env_vars = {}

        for endpoint_name, selected_models in selected_models_by_endpoint.items():
            success, endpoint_config = self.endpoint_manager.get_endpoint_config(endpoint_name)
            if not success:
                continue

            provider_name = endpoint_name.replace(":", "_").replace("-", "_").replace(".", "_").lower()
            # Ensure name starts with a letter if strictly needed, but usually fine
            
            # Determine API key env var name
            api_key_env_var = ""
            if "api_key_env" in endpoint_config:
                api_key_env_var = endpoint_config["api_key_env"]
            elif "actual_api_key" in endpoint_config and endpoint_config["actual_api_key"]:
                # Generate a specific env var for this provider
                api_key_env_var = f"CAM_GOOSE_{provider_name.upper()}_KEY"
                extra_env_vars[api_key_env_var] = endpoint_config["actual_api_key"]
            
            # Construct provider config
            provider_config = {
                "name": provider_name,
                "engine": "openai", # Assuming OpenAI-compatible for now as CAM mostly deals with those
                "display_name": endpoint_config.get("description", endpoint_name),
                "description": f"Configured via Code Assistant Manager from {endpoint_name}",
                "base_url": endpoint_config["endpoint"],
                "models": [],
                "supports_streaming": True
            }

            if api_key_env_var:
                provider_config["api_key_env"] = api_key_env_var
            
            # Add selected models
            for model_name in selected_models:
                provider_config["models"].append({
                    "name": model_name,
                    "context_limit": self.DEFAULT_CONTEXT_LIMIT
                })

            # Write config file
            config_file = config_dir / f"{provider_name}.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(provider_config, f, indent=2)
                
            print(f"✓ Configured provider '{provider_name}' in {config_file}")

        return extra_env_vars

    def _set_default_provider(self, selected_models_by_endpoint: Dict[str, List[str]]) -> None:
        """
        Set the default provider and model in ~/.config/goose/config.yaml.
        Uses the first selected endpoint and its first model.
        """
        if not selected_models_by_endpoint:
            return

        # Pick the first endpoint and its first model
        endpoint_name, models = next(iter(selected_models_by_endpoint.items()))
        if not models:
            return
            
        provider_name = endpoint_name.replace(":", "_").replace("-", "_").replace(".", "_").lower()
        model_name = models[0]
        
        config_file = Path.home() / ".config" / "goose" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load existing goose config: {e}")

        # Update or set the provider and model
        config_data["GOOSE_PROVIDER"] = provider_name
        config_data["GOOSE_MODEL"] = model_name
        
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, sort_keys=False)
            print(f"✓ Set default provider to '{provider_name}' and model to '{model_name}'")
        except Exception as e:
            print(f"Warning: Failed to write default provider to goose config: {e}")

    def run(self, args: List[str] = None) -> int:
        args = args or []

        # Load environment variables first
        self._load_environment()

        # Check if Goose is installed
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Get filtered endpoints that support goose
        filtered_endpoints = self._get_filtered_endpoints()
        
        extra_env_vars = {}

        if not filtered_endpoints:
            print("Warning: No endpoints configured for goose client.")
        else:
            print("\nConfiguring Goose with models from all endpoints...\n")

            # Process each endpoint to collect selected models
            selected_models_by_endpoint: Dict[str, List[str]] = {}
            for endpoint_name in filtered_endpoints:
                selected_models = self._process_endpoint(endpoint_name)
                if selected_models:
                    selected_models_by_endpoint[endpoint_name] = selected_models

            if selected_models_by_endpoint:
                total_models = sum(len(models) for models in selected_models_by_endpoint.values())
                print(f"Total models selected: {total_models}\n")

                # Write configs and get extra env vars
                extra_env_vars = self._write_goose_config(selected_models_by_endpoint)
                
                # Set default provider in global config to avoid "No provider configured" error
                self._set_default_provider(selected_models_by_endpoint)
            else:
                print("No models selected, skipping configuration update.\n")

        # Use environment variables directly
        env = os.environ.copy()
        # Set TLS environment
        self._set_node_tls_env(env)
        
        # Add extra env vars for API keys
        env.update(extra_env_vars)

        # Execute the Goose CLI with the configured environment
        command = [self.command_name, *args]
        return self._run_tool_with_env(command, env, self.command_name, interactive=True)
