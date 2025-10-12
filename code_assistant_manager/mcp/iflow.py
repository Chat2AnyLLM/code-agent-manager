"""Iflow MCP client implementation."""

from .base import print_squared_frame
from .base_client import MCPClient


class IflowMCPClient(MCPClient):
    """MCP client for Iflow tool with Iflow-specific characteristics."""

    def __init__(self):
        super().__init__("iflow")

    def _get_config_locations(self, tool_name: str):
        """Override to provide Iflow-specific config locations."""
        from pathlib import Path

        home = Path.home()
        # Iflow only uses settings.json at user and project levels
        return [
            home / ".iflow" / "settings.json",  # User-level
            Path.cwd() / ".iflow" / "settings.json",  # Project-level
        ]

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a server is installed by reading Iflow settings.json files."""
        config_locations = self._get_config_locations(tool_name)
        for config_path in config_locations:
            if config_path.exists():
                try:
                    import json

                    with open(config_path, "r") as f:
                        config = json.load(f)

                    # Check for mcpServers in Iflow settings
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        if server_name in config["mcpServers"]:
                            return True
                except Exception:
                    continue
        return False

    def _get_config_paths(self, scope: str):
        """Override to provide Iflow-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        if scope == "user":
            return [home / ".iflow" / "settings.json"]
        elif scope == "project":
            return [Path.cwd() / ".iflow" / "settings.json"]
        else:  # all
            return [
                home / ".iflow" / "settings.json",
                Path.cwd() / ".iflow" / "settings.json",
            ]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to an Iflow JSON file."""
        import json
        from pathlib import Path

        config_path = Path(config_path)

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Iflow uses "mcpServers" structure
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
            print(f"Error adding server to Iflow config {config_path}: {e}")
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading Iflow settings.json files."""

        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            print(f"No MCP server configurations found for {self.tool_name}")
            return False

        config_locations = self._get_config_locations(self.tool_name)
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
        user_servers = {}
        project_servers = {}

        for i, config_path in enumerate(config_locations):
            if config_path.exists():
                try:
                    import json

                    with open(config_path, "r") as f:
                        config = json.load(f)

                    # Check for mcpServers in Iflow settings
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        if i == 0:  # user-level ~/.iflow/settings.json
                            user_servers.update(config["mcpServers"])
                        else:  # project-level .iflow/settings.json
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
        """Remove a server from Iflow config files based on scope."""
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
