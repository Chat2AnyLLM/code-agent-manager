"""Qwen MCP client implementation."""

from .base import print_squared_frame
from .base_client import MCPClient


class QwenMCPClient(MCPClient):
    """MCP client for Qwen tool."""

    def __init__(self):
        super().__init__("qwen")

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a server is installed by reading Qwen settings.json file."""
        from pathlib import Path

        config_path = Path.home() / ".qwen" / "settings.json"
        if not config_path.exists():
            return False

        try:
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

            # Check for mcpServers in Qwen config
            if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                return server_name in config["mcpServers"]
        except Exception:
            pass
        return False

    def _get_config_paths(self, scope: str):
        """Override to provide Qwen-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        # Qwen uses one config file regardless of scope
        return [home / ".qwen" / "settings.json"]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to a Qwen JSON file."""
        import json
        from pathlib import Path

        config_path = Path(config_path)

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Qwen uses "mcpServers" structure
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
            print(f"Error adding server to Qwen config {config_path}: {e}")
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading Qwen settings.json file."""
        import json
        from pathlib import Path

        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            print(f"No MCP server configurations found for {self.tool_name}")
            return False

        config_path = Path.home() / ".qwen" / "settings.json"

        if not config_path.exists():
            content = "No MCP servers configured"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            servers = {}
            if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                servers = config["mcpServers"]

            if servers:
                content_lines = ["Configured servers:"]
                for name, config in servers.items():
                    content_lines.append(f"  {name}: {config}")
                content = "\n".join(content_lines)
                print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
                return True
            else:
                content = "No MCP servers configured"
                print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
                return True

        except Exception as e:
            print(f"Warning: Failed to read {config_path}: {e}")
            return False

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server from Qwen settings file."""
        from pathlib import Path

        config_path = Path.home() / ".qwen" / "settings.json"

        if self._remove_server_from_config(config_path, server_name):
            print(f"  Removed {server_name} from Qwen configuration")
            return True
        else:
            print(f"  {server_name} not found in Qwen configuration")
            return False
