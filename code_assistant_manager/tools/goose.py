import json
import os
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

    def _sanitize_provider_name(self, endpoint_name: str) -> str:
        """Sanitize endpoint name to be used as Goose provider id.

        Keep '-' (common in provider ids) but replace characters that are awkward for filenames.
        """
        return endpoint_name.replace(":", "-").replace(".", "-").lower()

    def _sanitize_env_var_suffix(self, name: str) -> str:
        """Sanitize name for use in environment variable identifiers."""
        import re

        return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()

    def _determine_engine_type(self, endpoint_config: Dict[str, str], endpoint_name: str) -> str:
        """Determine appropriate engine type based on endpoint configuration.

        Args:
            endpoint_config: Configuration for the endpoint
            endpoint_name: Name of the endpoint

        Returns:
            Appropriate engine type string
        """
        # Check if endpoint has an explicit engine configuration
        engine_from_config = endpoint_config.get("engine", "")
        if engine_from_config:
            # However, if the configured engine seems incorrect based on endpoint name or URL,
            # override it with the correct engine type
            endpoint_name_lower = endpoint_name.lower()
            endpoint_url = endpoint_config.get("endpoint", "").lower()

            # Override incorrect 'anthropic' engine for OpenAI-compatible endpoints
            if (engine_from_config == "anthropic" and
                (any(pattern in endpoint_name_lower for pattern in ["copilot", "litellm", "openai", "compatible", "openrouter", "anyscale", "fireworks", "together", "perplexity", "openai-compatible", "dashscope", "qwen", "azure"]) or
                 any(pattern in endpoint_url for pattern in ["dashscope", "qwen", "anyscale", "fireworks", "together", "perplexity", "openai-compatible", "litellm", "copilot"]))):
                return "openai"

            # Override incorrect 'anthropic' engine if it's clearly another type
            if (engine_from_config == "anthropic" and
                ("gemini" in endpoint_name_lower or "gemini" in endpoint_url or
                 "vertexai" in endpoint_name_lower or "vertexai" in endpoint_url or
                 "ollama" in endpoint_name_lower or "ollama" in endpoint_url)):
                if "gemini" in endpoint_name_lower or "gemini" in endpoint_url or "vertexai" in endpoint_name_lower or "vertexai" in endpoint_url:
                    return "gemini"
                elif "ollama" in endpoint_name_lower or "ollama" in endpoint_url:
                    return "ollama"

            return engine_from_config

        # Check if endpoint name suggests OpenAI compatibility
        endpoint_name_lower = endpoint_name.lower()
        if any(pattern in endpoint_name_lower for pattern in ["openai", "gpt", "azure", "compatible", "openrouter", "anyscale", "fireworks", "together", "perplexity", "openai-compatible", "dashscope", "qwen"]):
            return "openai"

        # Try to determine from supported_client field
        supported_client = endpoint_config.get("supported_client", "").lower()
        if supported_client:
            # Common patterns for different engine types
            if "openai" in supported_client or "gpt" in supported_client:
                return "openai"
            elif "anthropic" in supported_client or "claude" in supported_client:
                return "anthropic"
            elif "gemini" in supported_client or "vertexai" in supported_client:
                return "gemini"
            elif "ollama" in supported_client:
                return "ollama"
            elif "llama" in supported_client or "llama2" in supported_client or "llama3" in supported_client:
                return "llama"
            elif "huggingface" in supported_client:
                return "huggingface"

        # Try to determine from endpoint URL
        endpoint_url = endpoint_config.get("endpoint", "").lower()
        if endpoint_url:
            if any(pattern in endpoint_url for pattern in ["openai", "azure", "openrouter", "anyscale", "fireworks", "together", "perplexity", "openai-compatible", "dashscope", "qwen"]):
                return "openai"
            elif "anthropic" in endpoint_url or "claude" in endpoint_url:
                return "anthropic"
            elif "gemini" in endpoint_url or "generativelanguage" in endpoint_url:
                return "gemini"
            elif "ollama" in endpoint_url:
                return "ollama"
            elif "huggingface" in endpoint_url:
                return "huggingface"

        # For many OpenAI-compatible endpoints, if they have certain characteristics,
        # assume they are OpenAI compatible
        # Check for common patterns that indicate OpenAI compatibility
        if any(key in endpoint_config for key in ["api_key", "api_base", "model", "stream"]):
            # Many OpenAI-compatible endpoints use standard OpenAI patterns
            return "openai"

        # Default to "openai" as it's the most common case for API-compatible endpoints
        # OpenAI-compatible APIs are very common for custom endpoints
        return "openai"

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the goose client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "goose")
        ]

    def _get_custom_providers(self) -> Dict[str, List[str]]:
        """Read existing custom providers from ~/.config/goose/custom_providers/.

        Returns:
            Dict mapping provider name to list of model names
        """
        custom_dir = Path.home() / ".config" / "goose" / "custom_providers"
        providers = {}

        if not custom_dir.exists():
            return providers

        try:
            for provider_file in custom_dir.glob("*.json"):
                try:
                    with open(provider_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    provider_name = data.get("name", provider_file.stem)
                    models = []

                    if "models" in data and isinstance(data["models"], list):
                        for model in data["models"]:
                            if isinstance(model, dict) and "name" in model:
                                models.append(model["name"])
                            elif isinstance(model, str):
                                models.append(model)

                    if models:
                        providers[provider_name] = models
                except Exception as e:
                    print(f"Warning: Failed to parse {provider_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to read custom providers: {e}")

        return providers

    def _get_available_models(self, endpoint_name: str) -> Optional[List[str]]:
        """Get all available models from an endpoint without showing selection menu."""
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
                import shlex

                env = os.environ.copy()
                env["endpoint"] = endpoint_config.get("endpoint", "")
                env["api_key"] = endpoint_config.get("actual_api_key", "")

                cmd_parts = shlex.split(endpoint_config["list_models_cmd"])
                result = subprocess.run(
                    cmd_parts,
                    shell=False,
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

        return models if models else None

    def _select_models_from_endpoint(self, endpoint_name: str, available_models: List[str]) -> Optional[List[str]]:
        """Let user select multiple models from the given endpoint."""
        success, endpoint_config = self.endpoint_manager.get_endpoint_config(endpoint_name)
        if not success:
            return None

        ep_url = endpoint_config.get("endpoint", "")
        ep_desc = endpoint_config.get("description", "") or ep_url
        endpoint_info = f"{endpoint_name} -> {ep_url} -> {ep_desc}"

        # Import helper for multiple model selection
        from code_assistant_manager.menu.menus import select_multiple_models

        # Non-interactive mode: select first model
        if os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1":
            return [available_models[0]]

        # Let user select multiple models from this endpoint
        success, selected_models = select_multiple_models(
            available_models,
            f"Select models from {endpoint_info} (Cancel to skip):",
            cancel_text="Skip"
        )

        if success and selected_models:
            return selected_models
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

            provider_name = self._sanitize_provider_name(endpoint_name)
            provider_env_suffix = self._sanitize_env_var_suffix(provider_name)

            # Determine API key env var name
            api_key_env_var = ""
            if "api_key_env" in endpoint_config:
                api_key_env_var = endpoint_config["api_key_env"]
            elif "actual_api_key" in endpoint_config and endpoint_config["actual_api_key"]:
                # Generate a specific env var for this provider
                api_key_env_var = f"CAM_GOOSE_{provider_env_suffix}_KEY"
                extra_env_vars[api_key_env_var] = endpoint_config["actual_api_key"]

            # Goose custom providers should use OpenAI engine for compatibility.
            engine_type = "openai"

            # Construct provider config
            provider_config = {
                "name": provider_name,
                "engine": engine_type,
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

            # Write config file with secure permissions (read/write for owner only)
            import os
            config_file = config_dir / f"{provider_name}.json"
            with open(config_file, "w", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as f:
                json.dump(provider_config, f, indent=2)

            print(f"✓ Configured provider '{provider_name}' in {config_file}")

        return extra_env_vars

    def _set_default_provider(self, selected_models_by_endpoint: Dict[str, List[str]]) -> None:
        """
        Set the default provider and model in ~/.config/goose/config.yaml.
        Includes both newly configured endpoints and existing custom providers.
        """
        # Get newly configured endpoints models
        endpoint_models = {}
        for endpoint_name, models in selected_models_by_endpoint.items():
            if models:
                endpoint_models[endpoint_name] = models

        # Get existing custom providers
        custom_models = self._get_custom_providers()

        # Avoid duplicate display: just-configured endpoints are also written as custom providers.
        if endpoint_models and custom_models:
            endpoint_provider_names = {self._sanitize_provider_name(ep) for ep in endpoint_models.keys()}
            for provider_name in list(custom_models.keys()):
                if provider_name in endpoint_provider_names:
                    del custom_models[provider_name]

        # If no options available, return
        if not endpoint_models and not custom_models:
            return

        # If user just selected exactly one model in this run, don't prompt again.
        if endpoint_models and sum(len(ms) for ms in endpoint_models.values()) == 1:
            endpoint_name = next(iter(endpoint_models.keys()))
            model_name = endpoint_models[endpoint_name][0]
            provider_name = self._sanitize_provider_name(endpoint_name)
            self._write_default_to_config(provider_name, model_name)
            return

        # If only endpoint models and they exist
        if endpoint_models and not custom_models:
            endpoint_list = list(endpoint_models.keys())

            # If only one endpoint with models
            if len(endpoint_list) == 1:
                endpoint_name = endpoint_list[0]
                model_name = endpoint_models[endpoint_name][0]
                provider_name = self._sanitize_provider_name(endpoint_name)
                self._write_default_to_config(provider_name, model_name)
                return

            # Non-interactive mode: use first
            if os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1":
                endpoint_name = endpoint_list[0]
                model_name = endpoint_models[endpoint_name][0]
                provider_name = self._sanitize_provider_name(endpoint_name)
                self._write_default_to_config(provider_name, model_name)
                return

            # Show menu
            self._show_and_select_model(endpoint_models, {})
            return

        # If we have custom providers (with or without new endpoints)
        # Always show menu to let user choose from all available
        if os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") != "1":
            self._show_and_select_model(endpoint_models, custom_models)
        else:
            # Non-interactive mode: prefer new endpoints, then custom
            if endpoint_models:
                endpoint_name = list(endpoint_models.keys())[0]
                model_name = endpoint_models[endpoint_name][0]
                provider_name = self._sanitize_provider_name(endpoint_name)
                self._write_default_to_config(provider_name, model_name)
            elif custom_models:
                provider_name = list(custom_models.keys())[0]
                model_name = custom_models[provider_name][0]
                self._write_default_to_config(provider_name, model_name)

    def _show_and_select_model(
        self,
        endpoint_models: Dict[str, List[str]],
        custom_models: Dict[str, List[str]]
    ) -> None:
        """Show menu to select and set default model from all available options."""
        from code_assistant_manager.menu.menus import display_centered_menu

        # Build menu options - unified list of all available models
        all_options = []
        option_to_provider = {}

        # Add endpoint models
        if endpoint_models:
            for endpoint_name, models in endpoint_models.items():
                for model in models:
                    provider_name = self._sanitize_provider_name(endpoint_name)
                    display = f"{model} ({provider_name})"
                    all_options.append(display)
                    option_to_provider[len(all_options) - 1] = (provider_name, model)

        # Add custom providers
        if custom_models:
            for provider_name, models in custom_models.items():
                for model in models:
                    display = f"{model} ({provider_name})"
                    all_options.append(display)
                    option_to_provider[len(all_options) - 1] = (provider_name, model)

        if not all_options:
            return

        # Show menu
        success, idx = display_centered_menu(
            "Select default Goose provider/model:",
            all_options,
            "Cancel"
        )

        if success and idx is not None and idx in option_to_provider:
            provider_name, model_name = option_to_provider[idx]
            self._write_default_to_config(provider_name, model_name)


    def _write_default_to_config(self, provider_name: str, model_name: str) -> None:
        """Write provider and model to goose config.yaml."""
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
            import os
            with open(config_file, "w", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as f:
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

            # First pass: Collect ALL available models from all endpoints
            print("Reading available models from all providers...\n")
            all_available_models: Dict[str, List[str]] = {}
            for endpoint_name in filtered_endpoints:
                available = self._get_available_models(endpoint_name)
                if available:
                    all_available_models[endpoint_name] = available

            if not all_available_models:
                print("No models available from any endpoint.\n")
            else:
                # Show summary of available models
                total_available = sum(len(models) for models in all_available_models.values())
                print(f"Available models found: {total_available}")
                for endpoint_name, models in all_available_models.items():
                    print(f"  • {endpoint_name}: {len(models)} models")
                print()

                # Second pass: Let user select models from each endpoint
                selected_models_by_endpoint: Dict[str, List[str]] = {}
                for endpoint_name in filtered_endpoints:
                    if endpoint_name in all_available_models:
                        selected = self._select_models_from_endpoint(
                            endpoint_name, all_available_models[endpoint_name]
                        )
                        if selected:
                            selected_models_by_endpoint[endpoint_name] = selected

                if selected_models_by_endpoint:
                    total_models = sum(len(models) for models in selected_models_by_endpoint.values())
                    print(f"Total models selected: {total_models}\n")

                    # Write configs and get extra env vars
                    extra_env_vars = self._write_goose_config(selected_models_by_endpoint)

                    # Set default provider in global config
                    self._set_default_provider(selected_models_by_endpoint)
                else:
                    print("No models selected; you can still choose a default from existing Goose custom providers.\n")
                    self._set_default_provider({})


        # Use environment variables directly
        env = os.environ.copy()
        # Set TLS environment
        self._set_node_tls_env(env)

        # Add extra env vars for API keys
        env.update(extra_env_vars)

        # Execute the Goose CLI with the configured environment
        command = [self.command_name, *args]

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"{self.command_name} {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, self.command_name, interactive=True)
