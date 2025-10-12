"""Droid MCP client implementation."""

from pathlib import Path

from .base import print_squared_frame
from .base_client import MCPClient


class DroidMCPClient(MCPClient):
    """MCP client for Droid tool with direct config file fallback."""

    def __init__(self):
        super().__init__("droid")

    def _get_config_locations(self, tool_name: str):
        """Override to prioritize Droid-specific config location."""
        locations = super()._get_config_locations(tool_name)
        # Add Droid-specific location at the beginning
        from pathlib import Path

        home = Path.home()
        droid_location = home / ".factory" / "mcp.json"
        locations.insert(0, droid_location)  # Add to beginning
        return locations

    def _get_config_paths(self, scope: str):
        """Override to provide Droid-specific config paths for scope-based operations."""
        from pathlib import Path

        home = Path.home()
        # Droid uses a single config file for all scopes
        return [home / ".factory" / "mcp.json"]

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a server is installed by directly reading droid's config file instead of using subprocess."""
        import json
        from pathlib import Path

        # Only check droid's mcpServers structure
        droid_config_path = Path.home() / ".factory" / "mcp.json"

        if droid_config_path.exists():
            try:
                with open(droid_config_path, "r") as f:
                    config = json.load(f)

                # Check for mcpServers structure
                if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                    return server_name in config["mcpServers"]

            except Exception:
                return False

        return False

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a server by immediately using fallback (direct config file editing) instead of subprocess commands."""
        return self._fallback_add_server(server_name)

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a server by immediately using fallback (direct config file editing)."""
        return self._fallback_remove_server(server_name)

    def list_servers(self, scope: str = "all") -> bool:
        """List servers by checking only droid's mcpServers structure."""
        import json
        from pathlib import Path

        # Only check droid's mcpServers structure
        droid_config_path = Path.home() / ".factory" / "mcp.json"

        if droid_config_path.exists():
            try:
                with open(droid_config_path, "r") as f:
                    config = json.load(f)

                # Only use mcpServers structure for droid
                servers = {}
                if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                    servers = config["mcpServers"]

                if servers:
                    server_list = "\n".join(
                        [f"  {name}: {config}" for name, config in servers.items()]
                    )
                    content = f"Configured MCP servers:\n{server_list}"
                    print_squared_frame(
                        f"{self.tool_name.upper()} MCP SERVERS", content
                    )
                    return True
            except Exception as e:
                error_content = f"Failed to read droid config: {e}"
                print_squared_frame(
                    f"{self.tool_name.upper()} MCP SERVERS", error_content
                )
                return False

        content = "No MCP servers configured"
        print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
        return True  # Not an error, just no servers found

    def add_all_servers(self, scope: str = "user") -> bool:
        """Add all servers by immediately using fallback for each."""
        tool_configs = self.get_tool_config(self.tool_name, scope)
        if not tool_configs:
            content = f"No MCP server configurations found for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return False

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Adding MCP servers for {self.tool_name}...",
        )

        success_count = 0
        for server_name in tool_configs.keys():
            if self._fallback_add_server(server_name):
                success_count += 1

        if success_count == len(tool_configs):
            content = f"✓ Successfully added all MCP servers for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True
        else:
            content = f"⚠️  Added {success_count}/{len(tool_configs)} MCP servers for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return success_count > 0

    def remove_all_servers(self) -> bool:
        """Remove all servers by immediately using fallback for each."""
        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            content = f"No MCP server configurations found for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return False

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Removing MCP servers for {self.tool_name}...",
        )

        success_count = 0
        for server_name in tool_configs.keys():
            if self._fallback_remove_server(server_name):
                success_count += 1

        if success_count == len(tool_configs):
            content = f"✓ Successfully removed all MCP servers for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True
        else:
            content = f"⚠️  Removed {success_count}/{len(tool_configs)} MCP servers for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return success_count > 0

    def refresh_servers(self) -> bool:
        """Refresh all servers currently configured in droid's mcpServers structure."""
        import json
        from pathlib import Path

        # Get currently configured servers from droid's mcpServers structure
        droid_config_path = Path.home() / ".factory" / "mcp.json"
        if not droid_config_path.exists():
            content = f"No MCP servers configured for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True

        try:
            with open(droid_config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            content = f"Failed to read droid config: {e}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return False

        # Find configured servers in mcpServers structure
        current_servers = set()
        if "mcpServers" in config and isinstance(config["mcpServers"], dict):
            # Only refresh servers that exist in global config AND are in droid's mcpServers
            global_success, global_config = self.load_config()
            if global_success and "servers" in global_config:
                global_servers = set(global_config["servers"].keys())
                current_servers = set(config["mcpServers"].keys()) & global_servers
            else:
                current_servers = set()

        if not current_servers:
            content = f"No MCP servers configured for {self.tool_name}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"Refreshing MCP servers for {self.tool_name}...",
        )

        success_count = 0
        total_count = len(current_servers)
        results = []

        for server_name in current_servers:
            print(f"Refreshing {server_name} for {self.tool_name}...")

            # Remove first
            remove_success = self._fallback_remove_server(server_name)
            if remove_success:
                # Then re-add
                add_success = self._fallback_add_server(server_name)
                if add_success:
                    print(f"  ✅ Successfully refreshed {server_name}")
                    results.append(f"✅ {server_name}: Refreshed successfully")
                    success_count += 1
                else:
                    print(f"  ❌ Failed to re-add {server_name}")
                    results.append(f"❌ {server_name}: Failed to re-add")
            else:
                print(f"  ❌ Failed to remove {server_name}")
                results.append(f"❌ {server_name}: Failed to remove")

        # Final summary
        summary = "\n".join(results)
        if success_count == total_count:
            content = f"Overall Status: ✅ Successfully refreshed all {total_count} MCP servers for {self.tool_name}\n\n{summary}"
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH COMPLETE", content
            )
            return True
        else:
            content = f"Overall Status: ⚠️  Refreshed {success_count}/{total_count} MCP servers for {self.tool_name}\n\n{summary}"
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH PARTIAL", content
            )
            return success_count > 0

    def _fallback_add_server(self, server_name: str) -> bool:
        """Override to only add to droid's mcpServers structure."""
        from pathlib import Path

        # Get server configuration from the main config
        success, config = self.load_config()
        if not success or "servers" not in config:
            print(f"  No server configuration found for {server_name}")
            return False

        server_info = config["servers"].get(server_name)
        if not server_info:
            print(f"  Server info not found for {server_name}")
            return False

        # Only use droid's mcpServers structure
        droid_config_path = Path.home() / ".factory" / "mcp.json"
        return self._add_server_to_droid_mcpServers(
            droid_config_path, server_name, server_info
        )

    def _fallback_remove_server(self, server_name: str) -> bool:
        """Override to only remove from droid's mcpServers structure."""
        from pathlib import Path

        # Only use droid's mcpServers structure
        droid_config_path = Path.home() / ".factory" / "mcp.json"
        return self._remove_server_from_droid_mcpServers(droid_config_path, server_name)

    def _add_server_to_droid_mcpServers(
        self, config_path: Path, server_name: str, server_info: dict
    ) -> bool:
        """Add a server only to the mcpServers structure in droid config."""
        import json

        try:
            config = {}

            # Read existing config if it exists
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Only use mcpServers structure for droid
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Convert global server format to droid format
            droid_server_info = self._convert_to_droid_format(server_info)

            if server_name not in config["mcpServers"]:
                config["mcpServers"][server_name] = droid_server_info

                # Ensure parent directory exists
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                return True

        except Exception as e:
            print(f"  Warning: Failed to process {config_path}: {e}")

        return False

    def _remove_server_from_droid_mcpServers(
        self, config_path: Path, server_name: str
    ) -> bool:
        """Remove a server only from the mcpServers structure in droid config."""
        import json

        if not config_path.exists():
            return False

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Only use mcpServers structure for droid
            if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                if server_name in config["mcpServers"]:
                    del config["mcpServers"][server_name]
                    with open(config_path, "w") as f:
                        json.dump(config, f, indent=2)
                    return True

        except Exception as e:
            print(f"  Warning: Failed to process {config_path}: {e}")

        return False

    def _convert_to_droid_format(self, global_server_info: dict) -> dict:
        """Convert global server config format to droid mcpServers format."""
        droid_format = self._convert_server_to_stdio_format(global_server_info)
        droid_format["disabled"] = False
        return droid_format

    def _add_server_config_to_file(
        self, config_path, server_name: str, client_config: dict
    ) -> bool:
        """Add server config to droid's mcp.json file."""
        import json
        from pathlib import Path

        config_path = Path(config_path)

        try:
            config = {}

            # Read existing config if it exists
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

            # Only use mcpServers structure for droid
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add disabled field to client_config
            droid_server_info = dict(client_config)
            droid_server_info["disabled"] = False

            if server_name not in config["mcpServers"]:
                config["mcpServers"][server_name] = droid_server_info

                # Ensure parent directory exists
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                return True

        except Exception as e:
            print(f"  Warning: Failed to process {config_path}: {e}")

        return False
