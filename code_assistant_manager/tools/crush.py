import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from ..mcp.crush import CrushMCPClient
from .base import CLITool


class CrushTool(CLITool):
    command_name = "crush"
    tool_key = "crush"
    install_description = "Charmland Crush CLI"

    def _load_environment(self) -> None:
        """Load environment variables."""
        from ..env_loader import load_env

        load_env()

    def _check_prerequisites(self) -> bool:
        """Check if required commands are available."""
        return True

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the crush client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "crush")
        ]

    def _get_available_mcp_servers(self) -> Dict[str, dict]:
        """Get available MCP servers from the registry.

        NOTE: This method is currently unused. It was previously used to auto-install
        all 374+ servers from the registry, which was dangerous. Kept for potential
        future use with proper user confirmation and server selection.
        """
        try:
            from ..mcp.registry_manager import LocalRegistryManager

            registry_manager = LocalRegistryManager()
            schemas = registry_manager.list_server_schemas()
            # Convert schemas to dict format for easier processing
            return {name: schema.__dict__ for name, schema in schemas.items()}
        except ImportError:
            print("Registry manager not available")
            return {}

    def _process_mcp_server(
        self, server_name: str, server_info: dict
    ) -> Optional[dict]:
        """Process a single MCP server and return server config if successful.

        NOTE: Currently unused - see _get_available_mcp_servers docstring.
        """
        # Convert server info to Crush MCP format
        crush_server_config = self._convert_server_to_crush_format(
            server_name, server_info
        )
        if crush_server_config:
            return {server_name: crush_server_config}
        return None

    def _convert_server_to_crush_format(
        self, server_name: str, server_info: dict
    ) -> Optional[dict]:
        """Convert MCP server info to Crush-compatible format.

        NOTE: Currently unused - see _get_available_mcp_servers docstring.
        """
        # Get installations from server info
        installations = server_info.get("installations", {})

        # Prefer npm installation method
        install_method = installations.get("npm")
        if not install_method:
            # Fall back to first available method
            install_method = (
                next(iter(installations.values())) if installations else None
            )

        if not install_method:
            return None

        # Convert based on installation method type
        method_type = getattr(install_method, "type", "stdio")

        if method_type == "npm":
            # STDIO server
            config = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", getattr(install_method, "package", "")],
                "timeout": 120,
                "disabled": False,
            }

            # Add environment variables if present
            if getattr(install_method, "env", {}):
                config["env"] = install_method.env

        elif method_type == "http":
            # HTTP server
            config = {
                "type": "http",
                "url": getattr(install_method, "url", ""),
                "timeout": 120,
                "disabled": False,
            }

            # Add headers if present
            if getattr(install_method, "headers", {}):
                config["headers"] = install_method.headers

        elif method_type == "sse":
            # Server-Sent Events server
            config = {
                "type": "sse",
                "url": getattr(install_method, "url", ""),
                "timeout": 120,
                "disabled": False,
            }

            # Add headers if present
            if getattr(install_method, "headers", {}):
                config["headers"] = install_method.headers

        else:
            # Generic stdio server
            config = {
                "type": "stdio",
                "command": getattr(install_method, "command", "echo"),
                "args": getattr(install_method, "args", []),
                "timeout": 120,
                "disabled": False,
            }

            # Add environment variables if present
            if getattr(install_method, "env", {}):
                config["env"] = install_method.env

        return config

    def _get_model_defaults(self, model_id: str) -> dict:
        """Get default cost and capability information for a model."""
        # Common model configurations - can be overridden in providers.json
        model_defaults = {
            "gpt-4": {
                "cost_per_1m_in": 30.0,
                "cost_per_1m_out": 60.0,
                "cost_per_1m_in_cached": 7.5,
                "cost_per_1m_out_cached": 15.0,
                "context_window": 8192,
                "default_max_tokens": 4096,
            },
            "gpt-4-turbo": {
                "cost_per_1m_in": 10.0,
                "cost_per_1m_out": 30.0,
                "cost_per_1m_in_cached": 2.5,
                "cost_per_1m_out_cached": 7.5,
                "context_window": 128000,
                "default_max_tokens": 4096,
            },
            "gpt-3.5-turbo": {
                "cost_per_1m_in": 0.5,
                "cost_per_1m_out": 1.5,
                "cost_per_1m_in_cached": 0.125,
                "cost_per_1m_out_cached": 0.375,
                "context_window": 16385,
                "default_max_tokens": 4096,
            },
            "claude-3-sonnet": {
                "cost_per_1m_in": 3.0,
                "cost_per_1m_out": 15.0,
                "cost_per_1m_in_cached": 0.75,
                "cost_per_1m_out_cached": 3.75,
                "context_window": 200000,
                "default_max_tokens": 4096,
            },
            "claude-3-haiku": {
                "cost_per_1m_in": 0.25,
                "cost_per_1m_out": 1.25,
                "cost_per_1m_in_cached": 0.0625,
                "cost_per_1m_out_cached": 0.3125,
                "context_window": 200000,
                "default_max_tokens": 4096,
            },
            "deepseek-chat": {
                "cost_per_1m_in": 0.27,
                "cost_per_1m_out": 1.1,
                "cost_per_1m_in_cached": 0.07,
                "cost_per_1m_out_cached": 1.1,
                "context_window": 64000,
                "default_max_tokens": 5000,
            },
        }

        # Check if user has custom model configurations in providers.json
        crush_config = self.config.config_data.get("crush", {})
        custom_models = crush_config.get("model_configs", {})

        # Return custom config if available, otherwise default, otherwise generic defaults
        if model_id in custom_models:
            return custom_models[model_id]
        elif model_id in model_defaults:
            return model_defaults[model_id]
        else:
            # Generic defaults for unknown models
            return {
                "cost_per_1m_in": 1.0,
                "cost_per_1m_out": 2.0,
                "cost_per_1m_in_cached": 0.25,
                "cost_per_1m_out_cached": 0.5,
                "context_window": 128000,
                "default_max_tokens": 4096,
            }

    def _process_endpoint(self, endpoint_name: str) -> Optional[dict]:
        """Process a single endpoint and return provider config if successful."""
        success, endpoint_config = self.endpoint_manager.get_endpoint_config(
            endpoint_name
        )
        if not success:
            return None

        # Check if we have configured models in providers.json
        configured_models = self._get_configured_models()
        if configured_models:
            # Use configured models instead of fetching
            models = configured_models
            print(f"Using configured models for {endpoint_name}")
        else:
            # Fetch models dynamically from endpoint
            success, models = self.endpoint_manager.fetch_models(
                endpoint_name, endpoint_config, use_cache_if_available=False
            )
            if not success or not models:
                print(f"Warning: No models found for {endpoint_name}\n")
                return None

        ep_url = endpoint_config.get("endpoint", "")
        ep_desc = endpoint_config.get("description", "") or ep_url
        endpoint_info = f"{endpoint_name} -> {ep_url} -> {ep_desc}"

        # Import package-level helper so tests can patch code_assistant_manager.tools.select_model
        from . import select_model

        success, model = select_model(
            models, f"Select model from {endpoint_info} (or skip):"
        )
        if success and model:
            # Get API key from endpoint config
            api_key = endpoint_config.get("actual_api_key", "")
            if not api_key:
                print(f"Warning: No API key found for {endpoint_name}")
                return None

            # Get model defaults
            model_defaults = self._get_model_defaults(model)

            # Create provider config for crush.json
            provider_config = {
                "type": "openai",
                "base_url": ep_url,
                "api_key": f"${endpoint_config.get('api_key_env', 'API_KEY')}",
                "models": [
                    {
                        "id": model,
                        "name": f"{model} [{endpoint_name}]",
                        **model_defaults,
                    }
                ],
            }
            return {endpoint_name: provider_config}
        else:
            print(f"Skipped {endpoint_name}\n")
            return None

    def _write_crush_config(self, mcp_servers: List[dict]) -> Path:
        """Persist Crush config to ~/.config/crush/crush.json.

        NOTE: Currently unused - see _get_available_mcp_servers docstring.
        """
        config_dir = Path.home() / ".config" / "crush"
        config_file = config_dir / "crush.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Merge all MCP server configs
        servers = {}
        for config in mcp_servers:
            servers.update(config)

        crush_config = {"$schema": "https://charm.land/crush.json", "mcp": servers}

        with open(config_file, "w") as f:
            json.dump(crush_config, f, indent=2)

        return config_file

    def _get_configured_models(self) -> Optional[List[str]]:
        """Get configured models from providers.json for crush."""
        crush_config = self.config.config_data.get("crush", {})
        configured_models = crush_config.get("configured_models", [])
        return configured_models if configured_models else None

    def _write_crush_providers_config(self, provider_configs: List[dict]) -> Path:
        """Persist Crush providers config to ~/.config/crush/crush.json and ensure default LSP config is present."""
        config_dir = Path.home() / ".config" / "crush"
        config_file = config_dir / "crush.json"
        config_dir.mkdir(parents=True, exist_ok=True)
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    existing_config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_config = {"$schema": "https://charm.land/crush.json"}
        else:
            existing_config = {"$schema": "https://charm.land/crush.json"}

        # Merge all provider configs
        providers = {}
        for config in provider_configs:
            providers.update(config)

        # Update the config with providers
        existing_config["providers"] = providers

        # Default LSP configuration to include if not present
        default_lsp = {
            "go": {"command": "gopls", "env": {"GOTOOLCHAIN": "go1.24.5"}},
            "typescript": {
                "command": "typescript-language-server",
                "args": ["--stdio"],
            },
            "nix": {"command": "nil"},
            "python-lsp": {
                "command": "pylsp",
                "args": ["--stdio"],
                "extensions": [".py"],
            },
        }

        # Merge default LSP entries without overwriting user-defined ones
        if "lsp" not in existing_config or not isinstance(
            existing_config.get("lsp"), dict
        ):
            existing_config["lsp"] = default_lsp
        else:
            for key, val in default_lsp.items():
                if key not in existing_config["lsp"]:
                    existing_config["lsp"][key] = val

        with open(config_file, "w") as f:
            json.dump(existing_config, f, indent=2)

        return config_file

    def _prepare_environment(self) -> dict:
        """Set up environment variables for crush."""
        env = os.environ.copy()
        self._set_node_tls_env(env)
        return env

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Launch the Charmland Crush CLI.

        - Loads environment variables
        - Ensures required commands are available
        - Launches the `crush` CLI

        Note: MCP servers are NOT auto-configured. Users must manually add servers
        using 'cam mcp server add <server_name> --client crush'.

        Args:
            args: List of arguments to pass to the Crush CLI

        Returns:
            Exit code of the Crush CLI process
        """
        # Handle MCP subcommands
        if args and args[0] == "mcp":
            return self._handle_mcp_command(args[1:])

        # Load environment
        self._load_environment()

        # Ensure prerequisites are met
        if not self._check_prerequisites():
            return 1

        # Ensure the crush CLI is installed/available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Collect endpoints that support the crush client
        filtered_endpoints = self._get_filtered_endpoints()

        if filtered_endpoints:
            print("\nConfiguring Crush with models from all endpoints...\n")

            # Process each endpoint to collect selected providers
            provider_configs: List[dict] = []
            for endpoint_name in filtered_endpoints:
                config = self._process_endpoint(endpoint_name)
                if config:
                    provider_configs.append(config)

            if provider_configs:
                print(f"Total providers configured: {len(provider_configs)}\n")

                # Persist Crush providers config to ~/.config/crush/crush.json
                config_file = self._write_crush_providers_config(provider_configs)
                print(f"Crush providers config written to {config_file}\n")
            else:
                print("No providers configured\n")
        else:
            print("No endpoints configured for crush client\n")

        # NOTE: We intentionally do NOT auto-install all MCP servers from the registry
        # The registry contains 374+ servers which would be dangerous to install automatically.
        # Users should use 'cam mcp server add <server_name> --client crush' to add servers manually.
        print("\n⚠️  Note: MCP servers are NOT automatically installed.")
        print(
            "    Use 'cam mcp server add <server_name> --client crush' to add MCP servers.\n"
        )

        # Set up environment
        env = self._prepare_environment()

        # Notify user and execute Crush CLI
        print("Starting Charmland Crush CLI...")
        print(f"DEBUG: running: crush {' '.join(args)}\n")

        command = ["crush"] + args

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"crush {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "crush", interactive=True)

    def _handle_mcp_command(self, args: List[str]) -> int:
        """Handle MCP subcommands for Crush."""
        if not args:
            help_text = """
 Usage: code-assistant-manager crush mcp <command> [options]

╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add [server_name]      Add MCP servers (all or specific server)              │
│ list                   List configured MCP servers                            │
│ remove [server_name]   Remove MCP servers (all or specific server)           │
│ refresh                Refresh all MCP servers (remove and re-add)           │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:
   code-assistant-manager crush mcp add              Add all MCP servers
   code-assistant-manager crush mcp add memory       Add specific server
   code-assistant-manager crush mcp list             List configured servers
   code-assistant-manager crush mcp remove memory    Remove specific server
   code-assistant-manager crush mcp refresh          Refresh all servers
"""
            print(help_text)
            return 1

        command = args[0]
        client = CrushMCPClient()

        if command == "add":
            if len(args) == 1:
                # Add all servers from global config
                return 0 if client.add_all_servers() else 1
            elif len(args) == 2:
                # Add specific server from global config
                server_name = args[1]
                success = client.add_server(server_name)
                from code_assistant_manager.mcp.base import print_squared_frame

                if success:
                    content = f"✓ Successfully added MCP server '{server_name}'"
                    print_squared_frame(
                        f"{client.tool_name.upper()} MCP SERVERS", content
                    )
                else:
                    content = f"✗ Failed to add MCP server '{server_name}'"
                    print_squared_frame(
                        f"{client.tool_name.upper()} MCP SERVERS", content
                    )
                return 0 if success else 1
            else:
                help_text = """
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ Usage: code-assistant-manager crush mcp add [server_name]                                │
│                                                                             │
│ Examples:                                                                   │
│   code-assistant-manager crush mcp add              Add all MCP servers                │
│   code-assistant-manager crush mcp add memory       Add specific server                │
╰──────────────────────────────────────────────────────────────────────────────╯
"""
                print(help_text)
                return 1
        elif command == "list":
            return 0 if client.list_servers() else 1
        elif command == "remove":
            if len(args) == 1:
                # Remove all servers
                return 0 if client.remove_all_servers() else 1
            elif len(args) == 2:
                # Remove specific server
                server_name = args[1]
                success = client.remove_server(server_name)
                from code_assistant_manager.mcp.base import print_squared_frame

                if success:
                    content = f"✓ Successfully removed MCP server '{server_name}'"
                    print_squared_frame(
                        f"{client.tool_name.upper()} MCP SERVERS", content
                    )
                else:
                    content = f"✗ Failed to remove MCP server '{server_name}'"
                    print_squared_frame(
                        f"{client.tool_name.upper()} MCP SERVERS", content
                    )
                return 0 if success else 1
            else:
                help_text = """
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ Usage: code-assistant-manager crush mcp remove [server_name]                            │
│                                                                             │
│ Examples:                                                                   │
│   code-assistant-manager crush mcp remove           Remove all MCP servers             │
│   code-assistant-manager crush mcp remove memory    Remove specific server             │
╰──────────────────────────────────────────────────────────────────────────────╯
"""
                print(help_text)
                return 1
        elif command == "refresh":
            return 0 if client.refresh_servers() else 1
        else:
            help_text = f"""
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ Unknown MCP command: {command}                                               │
│                                                                             │
│ Available commands: add, list, remove, refresh                              │
╰──────────────────────────────────────────────────────────────────────────────╯
"""
            print(help_text)
            return 1
