"""Copilot MCP client implementation."""

import json
from pathlib import Path
from typing import Dict

from .base import print_squared_frame
from .base_client import MCPClient


class CopilotMCPClient(MCPClient):
    """MCP client for Copilot tool with Copilot-specific characteristics."""

    def __init__(self):
        super().__init__("copilot")

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a server is installed by reading Copilot mcp-config.json files."""
        config_locations = self._get_config_locations(tool_name)
        for config_path in config_locations:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)

                    # Check for mcpServers in Copilot config
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        if server_name in config["mcpServers"]:
                            return True
                except Exception:
                    continue
        return False

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a server by directly editing Copilot mcp-config.json files based on scope."""
        return self._fallback_add_server_scoped(server_name, scope)

    def _fallback_add_server_scoped(self, server_name: str, scope: str) -> bool:
        """Add a server to Copilot config files based on scope."""
        # Get server configuration - try registry first, then legacy
        server_info = self.get_server_config(server_name)
        if not server_info:
            print(f"  No server configuration found for {server_name}")
            return False

        # Convert to Copilot format
        copilot_server_info = self._convert_to_copilot_format(server_info)

        # Determine target locations based on scope
        config_locations = self._get_config_locations(self.tool_name)
        if scope == "user":
            target_locations = [config_locations[0]]  # User-level only
        elif scope == "project":
            # Project shared and personal (skip user)
            target_locations = config_locations[1:]
        else:
            target_locations = config_locations

        for config_path in target_locations:
            if self._add_server_to_config(
                config_path, server_name, copilot_server_info
            ):
                level = (
                    "user-level"
                    if config_path == config_locations[0]
                    else "project-level"
                )
                print(f"  Added {server_name} to {level} configuration")
                return True

        return False

    def _convert_server_config_to_client_format(self, server_config) -> Dict:
        """
        Override to provide Copilot-specific server config conversion.

        Args:
            server_config: STDIOServerConfig or RemoteServerConfig object

        Returns:
            Dict in Copilot configuration format
        """
        if hasattr(server_config, "url") and server_config.url:
            # Remote server (shouldn't happen for memory server, but handle it)
            config = {
                "type": "http",
                "url": server_config.url,
                "tools": ["*"],
            }
            if hasattr(server_config, "headers") and server_config.headers:
                config["headers"] = server_config.headers
            return config
        else:
            # STDIO server - convert to Copilot format
            # Get the basic server info first
            server_info = {
                "command": getattr(server_config, "command", "echo"),
                "args": getattr(server_config, "args", []),
                "env": getattr(server_config, "env", {}),
            }

            # Use the Copilot-specific conversion
            result = self._convert_to_copilot_format(server_info)
            return result

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server by directly editing Copilot mcp-config.json files based on scope."""
        config_locations = self._get_config_locations(self.tool_name)

        if scope == "user":
            target_locations = [config_locations[0]]  # User-level only
        elif scope == "project":
            # Project shared and personal (skip user)
            target_locations = config_locations[1:]
        else:
            target_locations = config_locations

        success = False
        for config_path in target_locations:
            if self._remove_server_from_config(config_path, server_name):
                level = (
                    "user-level"
                    if config_path == config_locations[0]
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

    def add_all_servers(self, scope: str = "user") -> bool:
        """Add all MCP servers for this tool based on scope."""
        tool_configs = self.get_tool_config(self.tool_name, scope)
        if not tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"No MCP server configurations found for {self.tool_name}",
            )
            return False

        # Print initial frame for adding operation
        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Adding MCP servers for {self.tool_name}...",
        )

        if scope == "user":
            target_locations = [
                self._get_config_locations(self.tool_name)[0]
            ]  # User-level only
        elif scope == "project":
            target_locations = self._get_config_locations(self.tool_name)[
                1:
            ]  # Project only
        else:
            target_locations = self._get_config_locations(self.tool_name)

        success_count = 0
        for server_name in tool_configs.keys():
            server_info = self.get_server_config(server_name)
            if not server_info:
                print(f"  No server configuration found for {server_name}")
                continue

            # Convert to Copilot format
            copilot_server_info = self._convert_to_copilot_format(server_info)

            added = False
            for config_path in target_locations:
                if self._add_server_to_config(
                    config_path, server_name, copilot_server_info
                ):
                    level = (
                        "user-level"
                        if config_path == target_locations[0]
                        else "project-level"
                    )
                    print(f"  Added {server_name} to {level} configuration")
                    added = True
                    success_count += 1
                    break  # Add to first available location
            if not added:
                print(f"  ✗ Failed to add {server_name}")

        # Print success frame
        if success_count > 0:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✓ Successfully added {success_count} MCP servers for {self.tool_name}",
            )
        else:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✗ Failed to add any MCP servers for {self.tool_name}",
            )

        return success_count > 0

    def _convert_to_copilot_format(self, server_info: dict) -> dict:
        """Convert global server config to Copilot mcpServers format."""
        # Check if this is an HTTP/remote server
        if "url" in server_info and server_info.get("type") == "http":
            copilot_format = {
                "type": "http",
                "url": server_info["url"],
                "tools": ["*"],
            }
            if "headers" in server_info:
                copilot_format["headers"] = server_info["headers"]
            return copilot_format

        # Otherwise handle as local/stdio server
        # Start with the stdio format conversion
        stdio_format = self._convert_server_to_stdio_format(server_info)

        # Convert Copilot-specific format
        copilot_format = {
            "type": "local",  # Copilot uses "local" instead of "stdio"
            "command": stdio_format.get("command", "echo"),
            "args": stdio_format.get("args", []),
            "tools": ["*"],  # Copilot requires tools specification
        }

        # Include env if present
        if "env" in stdio_format and stdio_format["env"]:
            copilot_format["env"] = stdio_format["env"]

        return copilot_format

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading Copilot mcp-config.json files."""
        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            print(f"No MCP server configurations found for {self.tool_name}")
            return False

        config_locations = self._get_config_locations(self.tool_name)
        user_servers = {}
        project_servers = {}

        for i, config_path in enumerate(config_locations):
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)

                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        if i == 0:  # user-level
                            user_servers.update(config["mcpServers"])
                        else:  # project-level
                            project_servers.update(config["mcpServers"])

                except Exception as e:
                    print(f"Warning: Failed to read {config_path}: {e}")
                    continue

        content_lines = []

        show_user = scope in ["all", "user"]
        show_project = scope in ["all", "project"]

        if show_user and user_servers:
            content_lines.append("User-level servers:")
            for name, config in user_servers.items():
                content_lines.append(f"  {name}: {config}")
            if show_project and project_servers:
                content_lines.append("")

        if show_project and project_servers:
            content_lines.append("Project-level servers:")
            for name, config in project_servers.items():
                content_lines.append(f"  {name}: {config}")

        servers_to_show = (show_user and user_servers) or (
            show_project and project_servers
        )

        if servers_to_show:
            content = "\n".join(content_lines)
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True
        else:
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
            return True

    def _get_config_locations(self, tool_name: str):
        """Override to provide Copilot-specific config locations."""
        home = Path.home()
        # Copilot uses mcp-config.json at user level only
        locations = [
            home / ".copilot" / "mcp-config.json",  # User-level (primary)
            Path.cwd() / ".mcp.json",  # Project-level
        ]
        return locations

    def _get_config_paths(self, scope: str):
        """Override to provide Copilot-specific config paths for scope-based operations."""
        home = Path.home()
        if scope == "user":
            return [home / ".copilot" / "mcp-config.json"]
        elif scope == "project":
            return [Path.cwd() / ".mcp.json"]
        else:  # all
            return [home / ".copilot" / "mcp-config.json", Path.cwd() / ".mcp.json"]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to a Copilot JSON file."""
        config_path = Path(config_path)

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Ensure mcpServers exists
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
            print(f"Error adding server to Copilot config {config_path}: {e}")
            return False

    def _add_server_to_config(
        self, config_path, server_name: str, server_info: dict
    ) -> bool:
        """Add a server to a Copilot config file."""
        # Convert to Copilot format first
        copilot_server_info = self._convert_to_copilot_format(server_info)
        return self._add_server_config_to_file(
            config_path, server_name, copilot_server_info
        )

    def _remove_server_from_config(self, config_path, server_name: str) -> bool:
        """Remove a server from a Copilot config file."""
        config_path = Path(config_path)

        try:
            if not config_path.exists():
                return False

            with open(config_path, "r") as f:
                config = json.load(f)

            # Check if the server exists in mcpServers
            if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                if server_name in config["mcpServers"]:
                    del config["mcpServers"][server_name]

                    # Write back
                    with open(config_path, "w") as f:
                        json.dump(config, f, indent=2)
                    return True

            return False

        except Exception as e:
            print(f"Error removing server from Copilot config {config_path}: {e}")
            return False
