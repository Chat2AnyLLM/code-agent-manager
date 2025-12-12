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

    def _normalize_mcp_servers(self, servers):
        """Normalize Continue's mcpServers to the list-of-objects format.

        Continue's newer format:
          mcpServers:
            - name: foo
              command: ...

        We also accept the legacy dict format:
          mcpServers:
            foo: {command: ...}
        """
        if isinstance(servers, list):
            return [s for s in servers if isinstance(s, dict)]

        if isinstance(servers, dict):
            normalized = []
            for name, cfg in servers.items():
                if not isinstance(cfg, dict):
                    continue
                item = {"name": name}
                item.update(cfg)
                normalized.append(item)
            return normalized

        return []

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

            servers = self._normalize_mcp_servers(config.get("mcpServers"))

            new_entry = {"name": server_name}
            new_entry.update(client_config)

            updated = False
            for i, item in enumerate(servers):
                if item.get("name") == server_name:
                    servers[i] = new_entry
                    updated = True
                    break

            if not updated:
                servers.append(new_entry)

            config["mcpServers"] = servers

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

                servers = config.get("mcpServers")

                if isinstance(servers, dict):
                    if server_name in servers:
                        del servers[server_name]
                        config["mcpServers"] = servers
                        with open(config_path, "w", encoding="utf-8") as f:
                            yaml.safe_dump(config, f, sort_keys=False)
                        removed_any = True
                        break

                if isinstance(servers, list):
                    new_servers = [
                        s
                        for s in servers
                        if not (isinstance(s, dict) and s.get("name") == server_name)
                    ]
                    if len(new_servers) != len(servers):
                        config["mcpServers"] = new_servers
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

                parsed = {}
                if isinstance(servers, dict):
                    parsed = servers
                elif isinstance(servers, list):
                    for item in servers:
                        if not isinstance(item, dict):
                            continue
                        name = item.get("name")
                        if not name:
                            continue
                        parsed[name] = {k: v for k, v in item.items() if k != "name"}
                else:
                    continue

                if config_path == home / ".continue" / "config.yaml":
                    user_servers.update(parsed)
                elif config_path == cwd / ".continue" / "config.yaml":
                    project_servers.update(parsed)
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
