import json
import os
from pathlib import Path
from typing import List, Optional

from ..mcp.droid import DroidMCPClient
from .base import CLITool


class DroidTool(CLITool):
    command_name = "droid"
    tool_key = "droid"
    install_description = "Factory.ai Droid CLI"

    def _load_environment(self) -> None:
        """Load environment variables."""
        from ..env_loader import load_env

        load_env()

    def _check_prerequisites(self) -> bool:
        """Check if required commands are available."""
        # Ensure curl is available for installation process
        if not self._check_command_available("curl"):
            print("Error: curl is required for Droid installation")
            return False
        return True

    def _get_filtered_endpoints(self) -> List[str]:
        """Collect endpoints that support the droid client."""
        endpoints = self.config.get_sections(exclude_common=True)
        return [
            ep
            for ep in endpoints
            if self.endpoint_manager._is_client_supported(ep, "droid")
        ]

    def _process_endpoint(self, endpoint_name: str) -> Optional[List[str]]:
        """Process a single endpoint and return selected entries if successful."""
        success, endpoint_config = self.endpoint_manager.get_endpoint_config(
            endpoint_name
        )
        if not success:
            return None

        # Fetch models (no cache prompt since we're aggregating)
        success, models = self.endpoint_manager.fetch_models(
            endpoint_name, endpoint_config, use_cache_if_available=False
        )
        if not success or not models:
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

        # Build entries for each selected model
        entries = []
        for model in selected_models:
            display_name = f"{model} [{endpoint_name}]"
            entry = f"{display_name}|{endpoint_config['endpoint']}|{endpoint_config['actual_api_key']}|generic-chat-completion-api|65536"
            entries.append(entry)

        return entries

    def _write_droid_settings(self, selected_entries: List[str]) -> Path:
        """Persist Droid custom models to ~/.factory/config.json."""
        config_dir = Path.home() / ".factory"
        config_file = config_dir / "config.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Preserve existing settings (plugins, etc) and only update custom_models.
        settings: dict = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f) or {}
            except Exception:
                settings = {}

        json_models = self._build_models_json(selected_entries)

        # Canonical location for Droid BYOK custom models.
        settings["custom_models"] = json_models

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

        return config_file

    def _prepare_environment(self) -> dict:
        """Clean proxy env vars for child process and set TLS env."""
        env = os.environ.copy()
        for key in [
            "http_proxy",
            "HTTP_PROXY",
            "https_proxy",
            "HTTPS_PROXY",
            "no_proxy",
            "NO_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ]:
            env.pop(key, None)
        self._set_node_tls_env(env)
        return env

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Configure and launch the Factory.ai Droid CLI.

        - Loads environment variables
        - Ensures required commands are available
        - Aggregates selected models from configured endpoints
        - Writes custom_models to ~/.factory/config.json and runs the `droid` CLI

        Args:
            args: List of arguments to pass to the Droid CLI

        Returns:
            Exit code of the Droid CLI process
        """
        # Handle MCP subcommands
        if args and args[0] == "mcp":
            return self._handle_mcp_command(args[1:])

        # Load environment
        self._load_environment()

        # Ensure prerequisites are met
        if not self._check_prerequisites():
            return 1

        # Ensure the droid CLI is installed/available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Collect endpoints that support the droid client
        filtered_endpoints = self._get_filtered_endpoints()

        if not filtered_endpoints:
            print("Error: No endpoints configured for droid client")
            return 1

        print("\nConfiguring Droid with models from all endpoints...\n")

        # Process each endpoint to collect selected models
        selected_entries: List[str] = []
        for endpoint_name in filtered_endpoints:
            entries = self._process_endpoint(endpoint_name)
            if entries:
                selected_entries.extend(entries)

        if not selected_entries:
            print("No models selected")
            return 1

        print(f"Total models selected: {len(selected_entries)}\n")

        # Persist Droid custom models to ~/.factory/config.json
        settings_file = self._write_droid_settings(selected_entries)
        print(f"Droid settings written to {settings_file}\n")

        # Clean proxy env vars for child process and set TLS env
        env = self._prepare_environment()

        # Notify user and execute Droid CLI
        print("Starting Factory.ai Droid CLI...")

        command = ["droid"] + args

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"droid {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "droid", interactive=True)

    def _build_models_json(self, entries: List[str]) -> List[dict]:
        """Build models JSON from pipe-delimited entries (compat with legacy implementation)."""
        models: List[dict] = []
        for entry in entries:
            parts = entry.split("|")
            if len(parts) < 5:
                continue
            display, base_url, api_key, _provider, max_tokens = parts[:5]
            model_id = display.split("[")[0].strip()
            try:
                max_tokens_val = int(max_tokens)
            except ValueError:
                max_tokens_val = 0
            models.append(
                {
                    "model_display_name": display,
                    "model": model_id,
                    "base_url": base_url,
                    "api_key": api_key,
                    "provider": "generic-chat-completion-api",
                    "max_tokens": max_tokens_val,
                }
            )
        return models

    def _handle_mcp_command(self, args: List[str]) -> int:
        """Handle MCP subcommands for Droid."""
        if not args:
            help_text = """
 Usage: code-assistant-manager droid mcp <command> [options]

╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add [server_name]      Add MCP servers (all or specific server)              │
│ list                   List configured MCP servers                            │
│ remove [server_name]   Remove MCP servers (all or specific server)           │
│ refresh                Refresh all MCP servers (remove and re-add)           │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:
   code-assistant-manager droid mcp add              Add all MCP servers
   code-assistant-manager droid mcp add memory       Add specific server
   code-assistant-manager droid mcp list             List configured servers
   code-assistant-manager droid mcp remove memory    Remove specific server
   code-assistant-manager droid mcp refresh          Refresh all servers
"""
            print(help_text)
            return 1

        command = args[0]
        client = DroidMCPClient()

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
│ Usage: code-assistant-manager droid mcp add [server_name]                                │
│                                                                             │
│ Examples:                                                                   │
│   code-assistant-manager droid mcp add              Add all MCP servers                │
│   code-assistant-manager droid mcp add memory       Add specific server                │
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
│ Usage: code-assistant-manager droid mcp remove [server_name]                            │
│                                                                             │
│ Examples:                                                                   │
│   code-assistant-manager droid mcp remove           Remove all MCP servers             │
│   code-assistant-manager droid mcp remove memory    Remove specific server             │
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
