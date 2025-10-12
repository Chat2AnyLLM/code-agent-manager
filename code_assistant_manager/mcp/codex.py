"""Codex MCP client implementation."""

from .base import print_squared_frame
from .base_client import MCPClient


class CodexMCPClient(MCPClient):
    """MCP client for Codex tool with Codex-specific characteristics."""

    def __init__(self):
        super().__init__("codex")

    def _get_config_locations(self, tool_name: str):
        """Override to provide Codex-specific config locations."""
        from pathlib import Path

        home = Path.home()
        # Codex only uses TOML config at ~/.codex/config.toml
        return [home / ".codex" / "config.toml"]

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a server to Codex config files based on scope."""
        # For Codex, scope doesn't really apply since it only has one config file
        # We'll treat all scopes the same way
        return self._add_server_to_codex_config(server_name)

    def _add_server_to_codex_config(self, server_name: str) -> bool:
        """Add a server to Codex TOML config."""
        # Get server configuration using the new method
        server_info = self.get_server_config(server_name)
        if not server_info:
            print(f"  No server configuration found for {server_name}")
            return False

        # Convert to Codex format
        codex_server_info = self._convert_to_codex_format(server_info)

        config_locations = self._get_config_locations(self.tool_name)
        config_path = config_locations[0]  # Codex only has one config file

        return self._add_server_to_config(config_path, server_name, codex_server_info)

    def _convert_to_codex_format(self, server_info: dict) -> dict:
        """Convert global server config to Codex mcp_servers format."""
        return self._convert_server_to_stdio_format(
            server_info, add_tls_for_tools=["claude", "codex"]
        )

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server from Codex config files."""
        # For Codex, scope doesn't apply since it only has one config file
        config_locations = self._get_config_locations(self.tool_name)
        config_path = config_locations[0]

        return self._remove_server_from_config(config_path, server_name)

    def add_all_servers(self, scope: str = "user") -> bool:
        """Add all MCP servers for Codex."""
        tool_configs = self.get_tool_config(self.tool_name, scope)
        if not tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"No MCP server configurations found for {self.tool_name}",
            )
            return False

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Adding MCP servers for {self.tool_name}...",
        )

        success_count = 0
        for server_name in tool_configs.keys():
            server_info = self.get_server_config(server_name)
            if not server_info:
                print(f"  No server configuration found for {server_name}")
                continue

            # Convert to Codex format
            codex_server_info = self._convert_to_codex_format(server_info)

            config_locations = self._get_config_locations(self.tool_name)
            config_path = config_locations[0]

            if self._add_server_to_config(config_path, server_name, codex_server_info):
                print(f"  Added {server_name} to Codex configuration")
                success_count += 1
            else:
                print(f"  ✗ Failed to add {server_name}")

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

    def refresh_servers(self) -> bool:
        """Refresh all MCP servers for Codex (remove then re-add)."""
        tool_configs = self.get_tool_config(
            self.tool_name, "user"
        )  # Only user-level for Codex
        if not tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"No MCP server configurations found for {self.tool_name}",
            )
            return False

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Refreshing MCP servers for {self.tool_name}...",
        )

        success_count = 0
        total_count = len(tool_configs)
        results = []

        for server_name, server_cfg in tool_configs.items():
            print(f"\nRefreshing {server_name} for {self.tool_name}...")

            # Step 1: Remove the server
            if self.remove_server(server_name):
                print(f"  ✓ Successfully removed {server_name}")
            else:
                print(f"  ❌ Failed to remove {server_name}")
                results.append(f"❌ {server_name}: Failed to remove")
                continue

            # Step 2: Re-add the server
            if self._add_server_to_codex_config(server_name):
                print(f"  ✅ Successfully refreshed {server_name}")
                results.append(f"✅ {server_name}: Refreshed successfully")
                success_count += 1
            else:
                print(f"  ❌ Failed to re-add {server_name}")
                results.append(f"❌ {server_name}: Failed to re-add")

        if success_count == total_count:
            content = (
                f"Overall Status: ✅ Successfully refreshed all {total_count} MCP servers for {self.tool_name}\n\n"
                + "\n".join(results)
            )
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH COMPLETE", content
            )
            return True
        else:
            content = (
                f"Overall Status: ❌ Failed to refresh {total_count - success_count}/{total_count} MCP servers for {self.tool_name}\n\n"
                + "\n".join(results)
            )
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH FAILED", content
            )
            return False

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by reading Codex TOML config file."""
        import tomllib

        config_locations = self._get_config_locations(self.tool_name)
        config_path = config_locations[0]

        if not config_path.exists():
            content = "No MCP servers configured"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            servers = {}
            if "mcp_servers" in config and isinstance(config["mcp_servers"], dict):
                servers = config["mcp_servers"]

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

    def _get_config_paths(self, scope: str):
        """Override to provide Codex-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        # Codex only uses one config file regardless of scope
        return [home / ".codex" / "config.toml"]

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to a Codex TOML file."""
        from pathlib import Path

        import tomli_w

        config_path = Path(config_path)

        try:
            # Load existing config
            config = {}
            if config_path.exists():
                import tomllib

                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

            # Ensure mcp_servers exists
            if "mcp_servers" not in config:
                config["mcp_servers"] = {}

            # Add the server config
            config["mcp_servers"][server_name] = client_config

            # Write back
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)

            return True

        except Exception as e:
            print(f"Error adding server to Codex config {config_path}: {e}")
            return False
