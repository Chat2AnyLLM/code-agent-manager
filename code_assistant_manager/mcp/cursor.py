"""Cursor Agent MCP client implementation."""

import json
from pathlib import Path

from .base_client import MCPClient


class CursorAgentMCPClient(MCPClient):
    """MCP client for Cursor Agent tool."""

    def __init__(self):
        super().__init__("cursor-agent")

    def _get_config_paths(self, scope: str) -> list[Path]:
        """
        Get the configuration file paths for the Cursor Agent client.

        Cursor Agent uses mcp.json files in ~/.cursor/ and project .cursor/ directories.
        """
        from pathlib import Path

        home = Path.home()

        if scope == "user":
            return [home / ".cursor" / "mcp.json"]
        elif scope == "project":
            return [
                Path.cwd() / ".cursor" / "mcp.json",
                Path.cwd() / ".cursor" / "mcp.local.json",
            ]
        else:  # all
            return [
                home / ".cursor" / "mcp.json",
                Path.cwd() / ".cursor" / "mcp.json",
                Path.cwd() / ".cursor" / "mcp.local.json",
            ]

    def _add_server_config_to_file(
        self, config_path: Path, server_name: str, client_config: dict
    ) -> bool:
        """
        Add server configuration to Cursor Agent's config file.

        Cursor Agent uses mcpServers section in mcp.json files.
        """
        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        config = json.loads(content)
                    else:
                        config = {}

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add the server config
            config["mcpServers"][server_name] = client_config

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Error adding server to Cursor Agent config file {config_path}: {e}")
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """
        List MCP servers for Cursor Agent by reading mcp.json files directly.
        """
        from .base import print_squared_frame

        config_paths = self._get_config_paths(scope)
        all_servers = {}

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        content = f.read().strip()
                        if not content:
                            continue
                        config = json.loads(content)

                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        level = (
                            "user-level"
                            if ".cursor/mcp.json" in str(config_path)
                            and "~" in str(config_path)
                            else "project-level"
                        )
                        for server_name, server_config in config["mcpServers"].items():
                            all_servers[f"{server_name} ({level})"] = server_config

                except Exception as e:
                    print(f"Warning: Failed to read {config_path}: {e}")
                    continue

        if all_servers:
            server_list = "\n".join(
                [f"  {name}: {config}" for name, config in all_servers.items()]
            )
            content = f"Configured MCP servers:\n{server_list}"
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
