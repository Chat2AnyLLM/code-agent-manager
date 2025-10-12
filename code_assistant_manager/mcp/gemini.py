"""Gemini MCP client implementation."""

import logging

from .base import print_squared_frame
from .base_client import MCPClient


class GeminiMCPClient(MCPClient):
    """MCP client for Gemini tool with Gemini-specific characteristics."""

    def __init__(self):
        super().__init__("gemini")

    def _convert_server_config_to_client_format(self, server_config) -> dict:
        """
        Override to provide Gemini-specific server config conversion.

        For HTTP-type servers, Gemini uses 'httpUrl' instead of 'url'.

        Args:
            server_config: STDIOServerConfig or RemoteServerConfig object

        Returns:
            Dict in Gemini configuration format
        """
        if hasattr(server_config, "url") and server_config.url:
            # Remote/HTTP server - use Gemini's httpUrl format
            config = {
                "httpUrl": server_config.url,
            }
            if hasattr(server_config, "headers") and server_config.headers:
                config["headers"] = server_config.headers
            return config
        else:
            # STDIO server - use base implementation
            config = {
                "type": "stdio",
                "command": getattr(server_config, "command", "echo"),
            }

            args = getattr(server_config, "args", [])
            if args:
                config["args"] = args
            else:
                config["args"] = []

            env = getattr(server_config, "env", {})
            if env:
                config["env"] = env

            return config

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a server to Gemini config files immediately using config file editing for efficiency."""
        # Get server configuration from registry
        server_config = self.get_server_config_from_registry(server_name)
        if not server_config:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: Server '{server_name}' not found in registry",
            )
            return False

        # Convert to client format
        client_config = self._convert_server_config_to_client_format(server_config)

        # Get the appropriate config file for this scope
        config_paths = self._get_config_paths(scope)
        logging.debug(
            f"Config files for scope '{scope}': {[str(p) for p in config_paths]}"
        )
        if not config_paths:
            print(f"No config paths found for scope '{scope}'")
            return False

        # Try to add to each config path
        for config_path in config_paths:
            if self._add_server_config_to_file(config_path, server_name, client_config):
                level = (
                    "user-level" if config_path == config_paths[0] else "project-level"
                )
                print(
                    f"✓ Successfully added {server_name} to {level} Gemini configuration"
                )
                return True

        print_squared_frame(
            f"{self.tool_name.upper()} - {server_name.upper()}",
            f"Error: Failed to add server to any config file",
        )
        return False

    def add_servers(self, server_names: list, scope: str = "user") -> bool:
        """Add multiple servers to Gemini config files efficiently in a single operation."""
        if not server_names:
            print("No servers specified to add")
            return False

        # Get configurations for all servers
        server_configs = {}
        failed_servers = []

        for server_name in server_names:
            server_config = self.get_server_config_from_registry(server_name)
            if not server_config:
                failed_servers.append(server_name)
                continue

            # Convert to client format
            client_config = self._convert_server_config_to_client_format(server_config)
            server_configs[server_name] = client_config

        # Report failed servers
        if failed_servers:
            print_squared_frame(
                f"{self.tool_name.upper()} - FAILED SERVERS",
                f"The following servers were not found in registry: {', '.join(failed_servers)}",
            )

        if not server_configs:
            print("No valid servers to add")
            return False

        # Get the appropriate config file for this scope
        config_paths = self._get_config_paths(scope)
        logging.debug(
            f"Config files for scope '{scope}': {[str(p) for p in config_paths]}"
        )
        if not config_paths:
            print(f"No config paths found for scope '{scope}'")
            return False

        # Try to add to each config path
        for config_path in config_paths:
            if self._add_servers_config_to_file(config_path, server_configs):
                level = (
                    "user-level" if config_path == config_paths[0] else "project-level"
                )
                added_servers = list(server_configs.keys())
                print(
                    f"✓ Successfully added {len(added_servers)} servers ({', '.join(added_servers)}) to {level} Gemini configuration"
                )
                return True

        print_squared_frame(
            f"{self.tool_name.upper()} - BULK ADD ERROR",
            f"Error: Failed to add servers to any config file",
        )
        return False

    def _get_config_locations(self, tool_name: str):
        """Override to provide Gemini-specific config locations."""
        # Use base implementation which already includes Gemini-specific locations
        return super()._get_config_locations(tool_name)

    def _get_config_paths(self, scope: str):
        """Override to provide Gemini-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        if scope == "user":
            return [home / ".gemini" / "settings.json"]
        elif scope == "project":
            return [Path.cwd() / ".gemini" / "settings.json"]
        else:  # all
            return [
                home / ".gemini" / "settings.json",
                Path.cwd() / ".gemini" / "settings.json",
            ]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to a Gemini JSON file."""
        import json
        from pathlib import Path

        config_path = Path(config_path)
        logging.debug(f"Adding server '{server_name}' to config file: {config_path}")

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Gemini uses "mcpServers" structure
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add the server config
            config["mcpServers"][server_name] = client_config

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Error adding server to Gemini config {config_path}: {e}")
            return False

    def _add_servers_config_to_file(self, config_path, server_configs: dict) -> bool:
        """Add multiple server configs to a Gemini JSON file in a single operation."""
        import json
        from pathlib import Path

        config_path = Path(config_path)
        server_names = list(server_configs.keys())
        logging.debug(f"Adding servers {server_names} to config file: {config_path}")

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Gemini uses "mcpServers" structure
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add all server configs at once
            config["mcpServers"].update(server_configs)

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Error adding servers to Gemini config {config_path}: {e}")
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading Gemini settings.json files."""

        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            print(f"No MCP server configurations found for {self.tool_name}")
            return False

        config_locations = self._get_config_locations(self.tool_name)
        logging.debug(
            f"Config locations being checked: {[str(p) for p in config_locations]}"
        )
        servers_data = self._collect_servers_from_configs(config_locations)
        content_lines = self._build_content_lines(servers_data, scope)

        if content_lines:
            content = "\n".join(content_lines)
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True
        else:
            self._show_empty_servers_message(scope)
            return True

    def _collect_servers_from_configs(self, config_locations):
        """Collect server data from all config locations."""
        import json
        from pathlib import Path

        user_servers = {}
        project_servers = {}

        home = Path.home()
        cwd = Path.cwd()

        for config_path in config_locations:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)

                    # Check for mcpServers in Gemini settings
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        # Determine if this is user-level or project-level
                        if config_path.parent == home / ".gemini":
                            user_servers.update(config["mcpServers"])
                        elif config_path.parent == cwd / ".gemini":
                            project_servers.update(config["mcpServers"])

                except Exception as e:
                    print(f"Warning: Failed to read {config_path}: {e}")
                    continue

        return {"user": user_servers, "project": project_servers}

    def _build_content_lines(self, servers_data, scope):
        """Build content lines for displaying servers."""
        content_lines = []
        user_servers = servers_data["user"]
        project_servers = servers_data["project"]

        show_user = scope in ["all", "user"]
        show_project = scope in ["all", "project"]

        if show_user and user_servers:
            content_lines.append("User-level servers:")
            content_lines.extend(
                [f"  {name}: {config}" for name, config in user_servers.items()]
            )
            if show_project and project_servers:
                content_lines.append("")

        if show_project and project_servers:
            content_lines.append("Project-level servers:")
            content_lines.extend(
                [f"  {name}: {config}" for name, config in project_servers.items()]
            )

        return content_lines

    def _show_empty_servers_message(self, scope):
        """Show appropriate message when no servers are configured."""
        level_desc = (
            ""
            if scope == "all"
            else (
                "user-level"
                if scope == "user"
                else "project-level" if scope == "project" else "configuration"
            )
        )
        if level_desc:
            content = f"No MCP servers configured in {level_desc} configuration"
        else:
            content = "No MCP servers configured"
        print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server from Gemini config files based on scope."""
        from pathlib import Path

        config_locations = self._get_config_locations(self.tool_name)

        home = Path.home()
        cwd = Path.cwd()

        if scope == "user":
            target_locations = [home / ".gemini" / "settings.json"]
        elif scope == "project":
            target_locations = [cwd / ".gemini" / "settings.json"]
        else:
            target_locations = [
                home / ".gemini" / "settings.json",
                cwd / ".gemini" / "settings.json",
            ]

        logging.debug(
            f"Target config files for scope '{scope}': {[str(p) for p in target_locations]}"
        )

        success = False
        for config_path in target_locations:
            if self._remove_server_from_config(config_path, server_name):
                level = (
                    "user-level"
                    if config_path.parent == home / ".gemini"
                    else "project-level"
                )
                print(f"  Removed {server_name} from {level} configuration")
                success = True
                break  # Remove from first found location

        if not success:
            level = (
                "user-level"
                if scope == "user"
                else "project-level" if scope == "project" else "configuration"
            )
            print(f"  {server_name} not found in {level} configuration")

        return success
