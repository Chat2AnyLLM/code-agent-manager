"""Crush MCP client implementation."""

import json
from pathlib import Path

from .base_client import MCPClient


class CrushMCPClient(MCPClient):
    """MCP client for Crush tool."""

    def __init__(self):
        super().__init__("crush")

    def _get_config_paths(self, scope: str) -> list[Path]:
        """
        Get the configuration file paths for the Crush client.

        For Crush, we use the crush.json file in ~/.config/crush/
        """
        config_dir = Path.home() / ".config" / "crush"
        config_file = config_dir / "crush.json"
        return [config_file]

    def _add_server_config_to_file(
        self, config_path: Path, server_name: str, client_config: dict
    ) -> bool:
        """
        Add server configuration to Crush's config file.

        Crush uses an "mcp" section directly, not "mcpServers".
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

            # Ensure mcp section exists
            if "mcp" not in config:
                config["mcp"] = {}

            # Add the server config
            config["mcp"][server_name] = client_config

            # Ensure schema is present
            if "$schema" not in config:
                config["$schema"] = "https://charm.land/crush.json"

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Error adding server to Crush config file {config_path}: {e}")
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """
        List MCP servers for Crush by reading the crush.json file directly.
        """
        config_file = Path.home() / ".config" / "crush" / "crush.json"

        if not config_file.exists():
            print(f"No Crush configuration found at {config_file}")
            return False

        try:
            with open(config_file, "r") as f:
                content = f.read().strip()
                if not content:
                    print(f"Crush configuration file is empty at {config_file}")
                    return False
                config = json.loads(content)

            if "mcp" in config and isinstance(config["mcp"], dict):
                servers = config["mcp"]
                if servers:
                    server_list = "\n".join(
                        [f"  {name}: {config}" for name, config in servers.items()]
                    )
                    content = f"Configured MCP servers:\n{server_list}"
                    from .base import print_squared_frame

                    print_squared_frame(
                        f"{self.tool_name.upper()} MCP SERVERS", content
                    )
                    return True
                else:
                    content = "No MCP servers configured"
                    from .base import print_squared_frame

                    print_squared_frame(
                        f"{self.tool_name.upper()} MCP SERVERS", content
                    )
                    return True
            else:
                print(f"No MCP section found in {config_file}")
                return False

        except Exception as e:
            print(f"Error reading Crush config file {config_file}: {e}")
            return False
