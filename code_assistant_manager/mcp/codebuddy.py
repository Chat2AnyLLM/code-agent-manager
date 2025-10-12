"""CodeBuddy MCP client implementation."""

from .base import print_squared_frame
from .base_client import MCPClient


class CodeBuddyMCPClient(MCPClient):
    """MCP client for CodeBuddy tool."""

    def __init__(self):
        super().__init__("codebuddy")

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a server is installed by reading CodeBuddy config files."""
        config_locations = self._get_config_locations(tool_name)
        for config_path in config_locations:
            if config_path.exists():
                try:
                    import json

                    with open(config_path, "r") as f:
                        config = json.load(f)

                    # Check for mcpServers in CodeBuddy config
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        if server_name in config["mcpServers"]:
                            return True
                except Exception:
                    continue
        return False

    def _get_config_paths(self, scope: str):
        """Override to provide CodeBuddy-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        if scope == "user":
            return [home / ".codebuddy.json"]
        elif scope == "project":
            return [Path.cwd() / ".codebuddy" / "mcp.json"]
        else:  # all
            return [home / ".codebuddy.json", Path.cwd() / ".codebuddy" / "mcp.json"]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to a CodeBuddy JSON file."""
        import json
        from pathlib import Path

        config_path = Path(config_path)

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # CodeBuddy uses "mcpServers" structure
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
            print(f"Error adding server to CodeBuddy config {config_path}: {e}")
            return False

    def _get_config_locations(self, tool_name: str):
        """Override to provide CodeBuddy-specific config locations."""
        from pathlib import Path

        home = Path.home()
        # CodeBuddy uses codebuddy.json at user level and .codebuddy/mcp.json at project level
        locations = [
            home / ".codebuddy.json",  # User-level
            Path.cwd() / ".codebuddy" / "mcp.json",  # Project-level
        ]
        return locations

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

        # Load global server configurations
        success, global_config = self.load_config()
        if not success or "servers" not in global_config:
            print("Failed to load server configurations")
            return False
        # Determine target locations based on scope
        locations = self._get_config_locations(self.tool_name)
        if scope == "user":
            target_locations = [locations[0]]  # User-level only
        elif scope == "project":
            target_locations = [locations[1]]  # Project only
        else:
            target_locations = locations

        success_count = 0
        for server_name in tool_configs.keys():
            server_info = global_config["servers"].get(server_name)
            if not server_info:
                print(f"  No server configuration found for {server_name}")
                continue

            # Convert to CodeBuddy format (assuming similar to Claude for now)
            codebuddy_server_info = self._convert_to_codebuddy_format(server_info)

            added = False
            for config_path in target_locations:
                if self._add_server_to_config(
                    config_path, server_name, codebuddy_server_info
                ):
                    level = (
                        "user-level" if config_path == locations[0] else "project-level"
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

    def _convert_to_codebuddy_format(self, server_info: dict) -> dict:
        """Convert global server config to CodeBuddy format."""
        return self._convert_server_to_command_format(server_info)

    def refresh_servers(self) -> bool:
        """Refresh all MCP servers for this tool (only user-level, remove then re-add)."""
        tool_configs = self.get_tool_config(self.tool_name, "user")  # Only user-level
        if not tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"No MCP server configurations found for {self.tool_name}",
            )
            return False

        # Print initial frame for refreshing operation
        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Refreshing MCP servers for {self.tool_name} (user-level only)...",
        )

        success_count = 0
        total_count = len(tool_configs)
        results = []

        for server_name, server_cfg in tool_configs.items():
            print(f"\nRefreshing {server_name} for {self.tool_name}...")

            # Step 1: Remove the server from user-level config
            remove_success = self._remove_server_from_user_config(server_name)
            if remove_success:
                print(
                    f"  ✓ Successfully removed {server_name} from user-level configuration"
                )
            else:
                print(
                    f"  ❌ Failed to remove {server_name} from user-level configuration"
                )
                results.append(f"❌ {server_name}: Failed to remove")
                continue

            # Step 2: Re-add the server to user-level config
            add_success = self._add_server_to_user_config(server_name)

            if add_success:
                print(
                    f"  ✅ Successfully refreshed {server_name} in user-level configuration"
                )
                results.append(f"✅ {server_name}: Refreshed successfully")
                success_count += 1
            else:
                print(
                    f"  ❌ Failed to re-add {server_name} to user-level configuration"
                )
                results.append(f"❌ {server_name}: Failed to re-add")

        # Print success frame
        if success_count > 0:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✓ Successfully refreshed {success_count} MCP servers for {self.tool_name} (user-level)",
            )
        else:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✗ Failed to refresh any MCP servers for {self.tool_name} (user-level)",
            )

        return success_count > 0

    def _remove_server_from_user_config(self, server_name: str) -> bool:
        """Remove a server from user-level CodeBuddy config only."""
        from pathlib import Path

        home = Path.home()
        user_config_path = home / ".codebuddy.json"

        return self._remove_server_from_config(user_config_path, server_name)

    def _add_server_to_user_config(self, server_name: str) -> bool:
        """Add a server to user-level CodeBuddy config only."""
        # Get server configuration from the main config
        success, config = self.load_config()
        if not success or "servers" not in config:
            print(f"  No server configuration found for {server_name}")
            return False

        server_info = config["servers"].get(server_name)
        if not server_info:
            print(f"  Server info not found for {server_name}")
            return False

        # Convert to CodeBuddy format
        codebuddy_server_info = self._convert_to_codebuddy_format(server_info)

        from pathlib import Path

        home = Path.home()
        user_config_path = home / ".codebuddy.json"

        return self._add_server_to_config(
            user_config_path, server_name, codebuddy_server_info
        )

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading CodeBuddy settings.json files."""
        import json

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

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server from CodeBuddy config files based on scope."""
        config_locations = self._get_config_locations(self.tool_name)
        if scope == "user":
            target_locations = [config_locations[0]]  # User-level only
        elif scope == "project":
            target_locations = config_locations[1:]  # Project only
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
