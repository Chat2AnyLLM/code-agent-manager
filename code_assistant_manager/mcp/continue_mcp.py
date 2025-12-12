"""Continue MCP client implementation."""

from pathlib import Path

import yaml

from .base import print_squared_frame
from .base_client import MCPClient


class ContinueMCPClient(MCPClient):
    """MCP client for Continue.dev."""

    def __init__(self):
        super().__init__("continue")

    def _get_config_paths(self, scope: str):
        home = Path.home()
        if scope == "user":
            return [home / ".continue" / "config.yaml"]
        elif scope == "project":
            return [Path.cwd() / ".continue" / "config.yaml"]
        else:  # all
            return [
                home / ".continue" / "config.yaml",
                Path.cwd() / ".continue" / "config.yaml",
            ]

    def _get_config_locations(self, tool_name: str):
        # Used by list_servers()
        return self._get_config_paths("all")

    def _convert_server_config_to_client_format(self, server_config) -> dict:
        # Continue uses the standard MCP "mcpServers" format (stdio/http)
        return super()._convert_server_config_to_client_format(server_config)

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        config_path = Path(config_path)
        try:
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                    if isinstance(loaded, dict):
                        config = loaded

            if "mcpServers" not in config or not isinstance(
                config.get("mcpServers"), dict
            ):
                config["mcpServers"] = {}

            config["mcpServers"][server_name] = client_config

            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error adding server to Continue config {config_path}: {e}")
            return False

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        server_config = self.get_server_config_from_registry(server_name)
        if not server_config:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: Server '{server_name}' not found in registry",
            )
            return False

        client_config = self._convert_server_config_to_client_format(server_config)
        config_paths = self._get_config_paths(scope)
        for config_path in config_paths:
            if self._add_server_config_to_file(config_path, server_name, client_config):
                level = (
                    "user-level" if config_path == config_paths[0] else "project-level"
                )
                print(
                    f"✓ Successfully added {server_name} to {level} Continue configuration"
                )
                return True

        print_squared_frame(
            f"{self.tool_name.upper()} - {server_name.upper()}",
            "Error: Failed to add server to any config file",
        )
        return False

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        config_paths = self._get_config_paths(scope)
        removed_any = False

        for config_path in config_paths:
            config_path = Path(config_path)
            if not config_path.exists():
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                if not isinstance(config, dict):
                    continue

                if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                    if server_name in config["mcpServers"]:
                        del config["mcpServers"][server_name]
                        with open(config_path, "w", encoding="utf-8") as f:
                            yaml.safe_dump(config, f, sort_keys=False)
                        removed_any = True
                        break
            except Exception:
                continue

        if removed_any:
            print(f"  Removed {server_name} from {self.tool_name} configuration")
        else:
            print(f"  {server_name} not found in {self.tool_name} configuration")
        return removed_any

    def list_servers(self, scope: str = "all") -> bool:
        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            print(f"No MCP server configurations found for {self.tool_name}")
            return False

        config_locations = self._get_config_locations(self.tool_name)
        user_servers = {}
        project_servers = {}

        home = Path.home()
        cwd = Path.cwd()

        for config_path in config_locations:
            config_path = Path(config_path)
            if not config_path.exists():
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                if not isinstance(config, dict):
                    continue
                servers = config.get("mcpServers")
                if not isinstance(servers, dict):
                    continue

                if config_path == home / ".continue" / "config.yaml":
                    user_servers.update(servers)
                elif config_path == cwd / ".continue" / "config.yaml":
                    project_servers.update(servers)
            except Exception:
                continue

        content_lines = []
        show_user = scope in ["all", "user"]
        show_project = scope in ["all", "project"]

        if show_user and user_servers:
            content_lines.append("User-level servers:")
            content_lines.extend(
                [f"  {name}: {cfg}" for name, cfg in user_servers.items()]
            )
            if show_project and project_servers:
                content_lines.append("")

        if show_project and project_servers:
            content_lines.append("Project-level servers:")
            content_lines.extend(
                [f"  {name}: {cfg}" for name, cfg in project_servers.items()]
            )

        if content_lines:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS", "\n".join(content_lines)
            )
        else:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS", "No MCP servers configured"
            )
        return True
