import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import CLITool


class OpenCodeTool(CLITool):
    """OpenCode.ai CLI wrapper."""

    command_name = "opencode"
    tool_key = "opencode"
    install_description = "OpenCode.ai CLI"

    # Default limits for OpenCode models
    DEFAULT_CONTEXT_LIMIT = 256000
    DEFAULT_OUTPUT_LIMIT = 65536

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the opencode client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "opencode")
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

    def _write_opencode_config(self, selected_models_by_endpoint: Dict[str, List[str]]) -> Path:
        """Write OpenCode.ai configuration to ~/.config/opencode/opencode.json."""
        # Set default model to the first selected model with provider prefix
        default_model = None
        for endpoint_name, selected_models in selected_models_by_endpoint.items():
            if selected_models:
                model_name = selected_models[0]
                provider_id = endpoint_name.replace(":", "-").replace("_", "-").lower()
                model_key = model_name.replace("/", "-").replace(":", "-").replace(".", "-").lower()
                default_model = f"{provider_id}/{model_key}"
                break

        opencode_config = {
            "$schema": "https://opencode.ai/config.json",
            "provider": {},
            "mcp": {},
        }

        if default_model:
            opencode_config["model"] = default_model

        # Create providers from selected models
        for endpoint_name, selected_models in selected_models_by_endpoint.items():
            success, endpoint_config = self.endpoint_manager.get_endpoint_config(endpoint_name)
            if not success:
                continue

            provider_id = endpoint_name.replace(":", "-").replace("_", "-").lower()
            provider = {
                "npm": "@ai-sdk/openai-compatible",
                "name": endpoint_config.get("description", endpoint_name),
                "options": {
                    "baseURL": endpoint_config["endpoint"]
                },
                "models": {}
            }

            # Handle API key configuration
            if "api_key_env" in endpoint_config:
                provider["options"]["apiKey"] = f"{{env:{endpoint_config['api_key_env']}}}"
            elif "api_key" in endpoint_config:
                provider["options"]["apiKey"] = endpoint_config["api_key"]

            # Add selected models
            for model_name in selected_models:
                # Fix model name for copilot-api
                if endpoint_name == "copilot-api" and model_name in ["g", "r", "o", "k", "-", "c", "d", "e", "f", "a", "s", "t", "1"]:
                    # If single letters, replace with proper model
                    model_name = "lmstudio/google/gemma-3n-e4b"
                model_key = model_name.replace("/", "-").replace(":", "-").replace(".", "-").lower()
                provider["models"][model_key] = {
                    "name": model_name,
                    "limit": {
                        "context": self.DEFAULT_CONTEXT_LIMIT,
                        "output": self.DEFAULT_OUTPUT_LIMIT
                    }
                }

            opencode_config["provider"][provider_id] = provider

        # Preserve existing MCP servers (if any)
        config_file = Path.home() / ".config" / "opencode" / "opencode.json"
        if config_file.exists():
            try:
                existing = json.loads(config_file.read_text(encoding="utf-8"))
                if isinstance(existing, dict) and isinstance(existing.get("mcp"), dict):
                    opencode_config["mcp"] = existing["mcp"]
            except Exception:
                pass

        # Write the config
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(opencode_config, f, indent=2, ensure_ascii=False)

        return config_file

    def run(self, args: List[str] = None) -> int:
        """
        Configure and launch the OpenCode.ai CLI.

        Args:
            args: List of arguments to pass to the OpenCode CLI

        Returns:
            Exit code of the OpenCode CLI process
        """
        args = args or []

        # Load environment variables first
        self._load_environment()

        # OpenCode.ai is installed at ~/.opencode/bin/opencode
        opencode_path = Path.home() / ".opencode" / "bin" / "opencode"

        # Check if OpenCode.ai is already installed at the expected location
        if opencode_path.exists():
            print(f"✓ OpenCode.ai found at {opencode_path}")
        else:
            # If not found at expected location, try the standard installation check
            if not self._ensure_tool_installed(
                self.command_name, self.tool_key, self.install_description
            ):
                return 1

        # Get filtered endpoints that support opencode
        filtered_endpoints = self._get_filtered_endpoints()

        if not filtered_endpoints:
            print("Warning: No endpoints configured for opencode client.")
            print("OpenCode.ai will use its default configuration.")
        else:
            print("\nConfiguring OpenCode.ai with models from all endpoints...\n")

            # Process each endpoint to collect selected models
            selected_models_by_endpoint: Dict[str, List[str]] = {}
            for endpoint_name in filtered_endpoints:
                selected_models = self._process_endpoint(endpoint_name)
                if selected_models:
                    selected_models_by_endpoint[endpoint_name] = selected_models

            if not selected_models_by_endpoint:
                print("No models selected")
                return 1

            total_models = sum(len(models) for models in selected_models_by_endpoint.values())
            print(f"Total models selected: {total_models}\n")

            # Persist OpenCode.ai config to ~/.config/opencode/opencode.json
            config_file = self._write_opencode_config(selected_models_by_endpoint)
            print(f"OpenCode.ai config written to {config_file}")

        # Verify the executable exists (should be there by now)
        if not opencode_path.exists():
            print(f"Error: OpenCode.ai executable not found at {opencode_path}")
            print("Please run the installation command: curl -fsSL https://opencode.ai/install | bash")
            return 1

        # OpenCode.ai manages its own authentication and configuration
        # Use environment variables directly
        env = os.environ.copy()
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the OpenCode CLI with the configured environment
        command = [str(opencode_path), *args]

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"opencode {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "opencode", interactive=True)
