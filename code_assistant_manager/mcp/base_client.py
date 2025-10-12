"""Base MCP client class with common functionality."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from .base import MCPBase, print_squared_frame

# Import from the new modules
from .config_helpers import (
    _get_preferred_container_key,
    _load_config_file,
    _remove_server_from_containers,
    _save_config_file,
    _server_exists_in_config,
)
from .config_paths import _get_config_locations


class MCPClient(MCPBase):
    """Base client class for MCP tool-specific operations."""

    def __init__(self, tool_name: str):
        super().__init__()
        self.tool_name = tool_name
        # Add registry integration
        try:
            from .registry_manager import LocalRegistryManager

            self.registry_manager = LocalRegistryManager()
        except ImportError:
            # Fallback if registry not available
            self.registry_manager = None

    def add_server_with_config(
        self, server_name: str, server_config, scope: str = "user"
    ) -> bool:
        """
        Add a server to the client using a provided server configuration.

        Args:
            server_name: Name of the server to add
            server_config: Server configuration object (STDIOServerConfig or RemoteServerConfig)
            scope: Scope for the configuration ("user", "project", etc.)

        Returns:
            bool: Success or failure
        """
        # Convert the server config to client format and add it
        client_config = self._convert_server_config_to_client_format(server_config)

        # Get the appropriate config file for this scope
        config_paths = self._get_config_paths(scope)
        if not config_paths:
            print(f"No config paths found for scope '{scope}'")
            return False

        # Try to add to each config path
        for config_path in config_paths:
            if self._add_server_config_to_file(config_path, server_name, client_config):
                return True

        return False

    def _convert_server_config_to_client_format(self, server_config) -> Dict:
        """
        Convert a ServerConfig object to client-compatible format.

        Args:
            server_config: STDIOServerConfig or RemoteServerConfig object

        Returns:
            Dict in client configuration format
        """
        if hasattr(server_config, "url") and server_config.url:
            # Remote server
            config = {
                "type": "http",
                "url": server_config.url,
            }
            if hasattr(server_config, "headers") and server_config.headers:
                config["headers"] = server_config.headers
            return config
        else:
            # STDIO server
            config = {
                "type": "stdio",
                "command": getattr(server_config, "command", "echo"),
            }

            args = getattr(server_config, "args", [])
            if args:
                config["args"] = args
            else:
                config["args"] = []

            env = getattr(server_config, "env", {})
            if env:
                config["env"] = env

            return config

    def _convert_server_to_stdio_format(
        self, server_info: dict, add_tls_for_tools: List[str] = None
    ) -> dict:
        """
        Generic conversion method for server info to stdio format.

        This method handles the common pattern of converting server configurations
        to stdio format used by MCP clients, reducing code duplication.

        Args:
            server_info: Server configuration dictionary
            add_tls_for_tools: List of tool names that should have NODE_TLS_REJECT_UNAUTHORIZED set

        Returns:
            Dictionary in stdio format for MCP client configuration
        """
        import shlex

        stdio_format = {"type": "stdio", "env": {}}

        # Copy any existing env from server_info
        if "env" in server_info and isinstance(server_info["env"], dict):
            stdio_format["env"].update(server_info["env"])

        add_tls = add_tls_for_tools and self.tool_name in add_tls_for_tools

        # Handle string command inputs
        if isinstance(server_info, str):
            parts = shlex.split(server_info)
            stdio_format["command"] = parts[0]
            stdio_format["args"] = parts[1:]
            if add_tls:
                stdio_format["env"]["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            return stdio_format

        # Handle package-based servers
        if "package" in server_info:
            stdio_format["command"] = "npx"
            stdio_format["args"] = ["-y", server_info["package"]]
            if add_tls:
                stdio_format["env"]["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

        # Handle command-based servers
        elif "command" in server_info:
            command = server_info["command"]

            # Add tool-specific extras if applicable
            if self.tool_name == "codex" and "codex_extra" in server_info:
                command += " " + server_info["codex_extra"]

            if isinstance(command, str):
                parts = shlex.split(command)
                stdio_format["command"] = parts[0]
                stdio_format["args"] = parts[1:]
            else:
                stdio_format["command"] = command
                stdio_format["args"] = server_info.get("args", [])

            # If args are explicitly provided in server_info, use those instead
            if "args" in server_info and isinstance(server_info["args"], list):
                stdio_format["args"] = server_info["args"]

            if add_tls:
                stdio_format["env"]["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

        return stdio_format

    def _convert_server_to_command_format(
        self, server_info: dict, add_codex_extra: bool = True
    ) -> dict:
        """
        Generic conversion method for server info to simple command format.

        This method handles the pattern used by CodeBuddy where only a command string is needed.

        Args:
            server_info: Server configuration dictionary
            add_codex_extra: Whether to add codex-specific extras for codex tool

        Returns:
            Dictionary with command field for simple command format
        """
        command_format = {}

        # Handle package-based servers
        if "package" in server_info:
            command_format["command"] = f"npx -y {server_info['package']}"
        # Handle command-based servers
        elif "command" in server_info:
            command = server_info["command"]
            # Add codex-specific extras if applicable
            if (
                add_codex_extra
                and self.tool_name == "codex"
                and "codex_extra" in server_info
            ):
                command += " " + server_info["codex_extra"]
            command_format["command"] = command

        return command_format

    def _get_config_paths_for_scope(self, scope: str) -> List[Path]:
        """
        Get config paths based on scope, using _get_config_paths() as the base.

        Args:
            scope: Configuration scope ("user", "project", "all")

        Returns:
            List of Path objects for the appropriate scope
        """
        all_paths = self._get_config_paths("all")  # Get all possible paths

        if not all_paths:
            return []

        if scope == "user":
            # Return first path (typically user-level)
            return [all_paths[0]] if all_paths else []
        elif scope == "project":
            # Return paths after first (typically project-level)
            return all_paths[1:] if len(all_paths) > 1 else []
        else:  # "all" or any other scope
            return all_paths

    def _get_preferred_config_structure(self, config: dict) -> str:
        """
        Determine the preferred config structure for a given config file.

        Args:
            config: The parsed config dictionary

        Returns:
            Preferred structure name: "mcpServers", "servers", "mcp", "mcp_servers", or "direct"
        """
        # Priority order for config structures
        structures = ["mcpServers", "servers", "mcp", "mcp_servers"]

        for structure in structures:
            if structure in config and isinstance(config[structure], dict):
                return structure

        # Check for direct server entries (server names as top-level keys)
        for key, value in config.items():
            if key not in ["$schema", "version"] and isinstance(value, dict):
                # Check if it looks like a server config
                if any(
                    server_key in value for server_key in ["type", "command", "url"]
                ):
                    return "direct"

        return "mcpServers"  # Default fallback

    def _batch_operation_with_scope(
        self, operation_func, scope: str = "user", operation_name: str = "operation"
    ) -> bool:
        """
        Generic helper for batch operations (add_all, remove_all) with scope handling.

        Args:
            operation_func: Function to call for each server (should take server_name and server_cfg, return bool)
            scope: Configuration scope
            operation_name: Name of the operation for logging

        Returns:
            bool: Overall success
        """
        tool_configs = self.get_tool_config(self.tool_name, scope)
        if not tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"No MCP server configurations found for {self.tool_name}",
            )
            return False

        print_squared_frame(
            f"{self.tool_name.upper()} MCP SERVERS",
            f"{operation_name} MCP servers for {self.tool_name}...",
        )
        results = []

        # Process servers in parallel
        with ThreadPoolExecutor(max_workers=len(tool_configs)) as executor:
            futures = {
                executor.submit(operation_func, server_name, server_cfg): server_name
                for server_name, server_cfg in tool_configs.items()
            }

            for future in as_completed(futures):
                server_name = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error processing {server_name}: {e}")
                    results.append(False)

        if all(results):
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✓ Successfully {operation_name.lower()}d all MCP servers for {self.tool_name}",
            )
            return True
        else:
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS",
                f"✗ Failed to {operation_name.lower()} some MCP servers for {self.tool_name}",
            )
            return False

    def _read_servers_from_configs(
        self, config_locations: List[Path], tool_configs: dict = None
    ) -> dict:
        """
        Read servers from multiple config files with different formats.

        Args:
            config_locations: List of config file paths to check
            tool_configs: Optional tool configs for filtering (if None, read all found servers)

        Returns:
            Dict of server_name -> config mapping
        """
        servers_found = {}

        for config_path in config_locations:
            if config_path.exists():
                try:
                    # Determine file type and load config
                    if config_path.suffix == ".toml":
                        import tomllib

                        with open(config_path, "rb") as f:
                            config = tomllib.load(f)
                    else:
                        import json

                        with open(config_path, "r") as f:
                            config = json.load(f)

                    # Get the preferred structure for this config
                    structure = self._get_preferred_config_structure(config)

                    if structure == "direct":
                        # Direct server entries
                        for key, value in config.items():
                            if key not in ["$schema", "version"] and isinstance(
                                value, dict
                            ):
                                if tool_configs is None or key in tool_configs:
                                    servers_found[key] = value
                    else:
                        # Structured config (mcpServers, servers, mcp, etc.)
                        if structure in config and isinstance(config[structure], dict):
                            for server_name, server_config in config[structure].items():
                                if tool_configs is None or server_name in tool_configs:
                                    servers_found[server_name] = server_config

                except Exception as e:
                    print(f"Warning: Failed to read {config_path}: {e}")
                    continue

        return servers_found

    def _read_servers_from_configs_legacy(self, scope: str, tool_configs: dict) -> dict:
        """
        Legacy method for reading servers from configs (for backward compatibility).

        This replicates the old list_servers logic for cases where _get_config_paths is not implemented.
        """
        import json

        from .base import find_mcp_config

        # Try to find and read config files directly
        config_locations = self._get_config_locations(self.tool_name)

        # Exclude the global project mcp.json to avoid showing global config servers
        global_config_path = find_mcp_config()
        config_locations = [
            loc for loc in config_locations if loc != global_config_path
        ]

        servers_found = {}

        for config_path in config_locations:
            if config_path.exists():
                try:
                    if config_path.suffix == ".toml":
                        import tomllib

                        with open(config_path, "rb") as f:
                            config = tomllib.load(f)
                    else:
                        with open(config_path, "r") as f:
                            config = json.load(f)

                    # Look for server structures: mcpServers, servers, mcp_servers, or direct entries
                    if "mcpServers" in config and isinstance(
                        config["mcpServers"], dict
                    ):
                        servers_found.update(config["mcpServers"])
                    if "servers" in config and isinstance(config["servers"], dict):
                        servers_found.update(config["servers"])
                    if "mcp_servers" in config and isinstance(
                        config["mcp_servers"], dict
                    ):
                        servers_found.update(config["mcp_servers"])
                    # Also check for direct server entries (keys that match known servers)
                    for server_name in tool_configs.keys():
                        if server_name in config and isinstance(
                            config[server_name], dict
                        ):
                            servers_found[server_name] = config[server_name]

                except Exception as e:
                    print(f"Warning: Failed to read {config_path}: {e}")
                    continue

        return servers_found

    def _get_config_paths(self, scope: str) -> List[Path]:
        """
        Get the configuration file paths for a given scope.

        Args:
            scope: Configuration scope ("user", "project", etc.)

        Returns:
            List of Path objects for configuration files
        """
        # This should be implemented by subclasses
        raise NotImplementedError

    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a specific MCP server for this tool."""
        tool_configs = self.get_tool_config(self.tool_name, scope)
        if server_name not in tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: Server '{server_name}' not found in configuration",
            )
            return False

        server_cfg = tool_configs[server_name]
        add_cmd = server_cfg.get("add_cmd")
        if not add_cmd:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: No add command found for {server_name}",
            )
            return False

        return self._check_and_install_server(server_name, add_cmd)

    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a specific MCP server for this tool."""
        tool_configs = self.get_tool_config(self.tool_name)
        if server_name not in tool_configs:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: Server '{server_name}' not found in configuration",
            )
            return False

        server_cfg = tool_configs[server_name]
        remove_cmd = server_cfg.get("remove_cmd")
        if not remove_cmd:
            print_squared_frame(
                f"{self.tool_name.upper()} - {server_name.upper()}",
                f"Error: No remove command found for {server_name}",
            )
            return False

        return self._execute_remove_command(server_name, remove_cmd)

    def list_servers(self, scope: str = "all") -> bool:
        """List MCP servers for this tool by reading config files directly."""
        tool_configs = self.get_tool_config(self.tool_name)
        if not tool_configs:
            # No server configurations available at all - return False without output
            return False

        # Try to use the new consolidated config reading method
        try:
            config_locations = self._get_config_paths_for_scope(scope)
            servers_found = self._read_servers_from_configs(
                config_locations, tool_configs
            )
        except NotImplementedError:
            # Fall back to the old method if _get_config_paths is not implemented
            servers_found = self._read_servers_from_configs_legacy(scope, tool_configs)

        if servers_found:
            server_list = "\n".join(
                [f"  {name}: {config}" for name, config in servers_found.items()]
            )
            content = f"Configured MCP servers:\n{server_list}"
            print_squared_frame(f"{self.tool_name.upper()} MCP SERVERS", content)
            return True
        else:
            # Fallback to running the list command if no servers found in config files
            # Get the list command from the first available server config
            list_cmd = None
            for server_cfg in tool_configs.values():
                list_cmd = server_cfg.get("list_cmd")
                if list_cmd:
                    break

            if list_cmd:
                print(f"Listing MCP servers for {self.tool_name}...")
                success, output = self.execute_command(list_cmd)
                if success:
                    content = f"Listing configured MCP servers...\n{output}"
                    print_squared_frame(
                        f"{self.tool_name.upper()} MCP SERVERS", content
                    )
                    return True
                else:
                    error_content = "Error: Failed to list MCP servers"
                    if output:
                        error_content += f"\n{output}"
                    print_squared_frame(
                        f"{self.tool_name.upper()} MCP SERVERS", error_content
                    )
                    return False
            else:
                # No servers configured and no list command available - return False silently
                # Don't print anything to maintain backward compatibility with tests
                return False

    def add_all_servers(self, scope: str = "user") -> bool:
        """Add all MCP servers for this tool."""

        def add_operation(server_name: str, server_cfg: dict) -> bool:
            add_cmd = server_cfg.get("add_cmd", "")
            if add_cmd:
                return self._check_and_install_server(server_name, add_cmd)
            return False

        return self._batch_operation_with_scope(add_operation, scope, "Adding")

    def remove_all_servers(self) -> bool:
        """Remove all MCP servers for this tool using fallback config editing."""

        def remove_operation(server_name: str, server_cfg: dict) -> bool:
            return self._fallback_remove_server(server_name)

        return self._batch_operation_with_scope(remove_operation, "all", "Removing")

    def get_server_config_from_registry(self, server_name: str) -> Dict:
        """
        Get server configuration from registry, converted to client-compatible format.

        Args:
            server_name: Name of the server to get config for

        Returns:
            Server configuration dict compatible with client format
        """
        if not self.registry_manager:
            return {}

        schema = self.registry_manager.get_server_schema(server_name)
        if not schema:
            return {}

        # Convert registry schema to client-compatible format
        return self._convert_schema_to_client_format(schema)

    def _convert_schema_to_client_format(self, schema) -> Dict:
        """
        Convert a ServerSchema to client-compatible configuration format.

        Args:
            schema: ServerSchema object from registry

        Returns:
            Dict in client configuration format
        """
        # Use the preferred installation method for this tool
        install_method = self._select_best_installation_method(schema)

        if not install_method:
            return {}

        config = {
            "command": install_method.command,
            "args": install_method.args,
            "env": install_method.env,
        }

        # Add package info if available
        if install_method.package:
            config["package"] = install_method.package

        return config

    def _select_best_installation_method(self, schema):
        """
        Select the best installation method for this client from schema.

        Args:
            schema: ServerSchema object

        Returns:
            InstallationMethod or None
        """
        if not hasattr(schema, "installations") or not schema.installations:
            return None

        # Always use the first installation method from the schema
        return next(iter(schema.installations.values()), None)

    def _generate_config_from_registry(self) -> tuple[bool, dict]:
        """
        Generate client configuration from registry data.

        Returns:
            Tuple of (success, config_dict)
        """
        if not self.registry_manager:
            return False, {}

        all_schemas = self.registry_manager.list_server_schemas()

        # Convert registry schemas to client-compatible format
        servers = {}
        for name, schema in all_schemas.items():
            if self._is_compatible_with_client(schema):
                servers[name] = self._convert_schema_to_client_format(schema)

        return True, {"servers": servers}

    def _is_compatible_with_client(self, schema) -> bool:
        """
        Check if a server schema is compatible with this client.

        Args:
            schema: ServerSchema to check

        Returns:
            True if compatible, False otherwise
        """
        # Default implementation - can be overridden by subclasses
        # Check if the schema has any installation methods
        return bool(hasattr(schema, "installations") and schema.installations)

    def get_server_config(self, server_name: str) -> Dict:
        """
        Registry-only get_server_config that only uses registry data.

        Args:
            server_name: Name of the server to get config for

        Returns:
            Server configuration dict
        """
        # Only use registry
        return self.get_server_config_from_registry(server_name)

    def load_config(self) -> tuple[bool, dict]:
        """
        Registry-only load_config that generates configurations from registry data.

        Returns:
            Tuple of (success, config_dict)
        """
        # Generate config from registry only
        return self._generate_config_from_registry()

    def get_tool_config(self, tool_name: str, scope: str = "user") -> Dict[str, Dict]:
        """
        Registry-only get_tool_config that only uses registry data.

        Args:
            tool_name: Name of the tool to get config for
            scope: Scope for the configuration

        Returns:
            Dict of server configurations for the tool
        """
        # Only use registry servers
        tool_configs = {}

        if self.registry_manager:
            all_schemas = self.registry_manager.list_server_schemas()
            for server_name, schema in all_schemas.items():
                if self._is_compatible_with_client(schema):
                    # Convert schema to tool config format
                    commands = self._build_commands_for_tool_from_schema(
                        tool_name, server_name, schema, scope
                    )
                    if commands:
                        tool_configs[server_name] = commands

        return tool_configs

    def _build_commands_for_tool_from_schema(
        self, tool_name: str, server_name: str, schema, scope: str
    ) -> Dict[str, str]:
        """
        Build add/remove/list commands for a tool from registry schema.

        Args:
            tool_name: Name of the tool
            server_name: Name of the server
            schema: ServerSchema object
            scope: Configuration scope

        Returns:
            Dict with command strings
        """
        # Select best installation method
        install_method = self._select_best_installation_method(schema)
        if not install_method:
            return {}

        # Build commands based on installation method type
        if install_method.type == "npm":
            package_cmd = (
                f"npx -y {install_method.package}"
                if install_method.package
                else install_method.command
            )
            add_cmd = (
                f"{tool_name} mcp add {server_name} --scope {scope} -- {package_cmd}"
            )
            remove_cmd = f"{tool_name} mcp remove {server_name}"
            list_cmd = f"{tool_name} mcp list"

        elif install_method.type in ["uvx", "python", "docker", "cli", "custom"]:
            command = install_method.command or ""
            if install_method.args:
                command += " " + " ".join(install_method.args)
            add_cmd = f"{tool_name} mcp add {server_name} --scope {scope} -- {command}"
            remove_cmd = f"{tool_name} mcp remove {server_name}"
            list_cmd = f"{tool_name} mcp list"

        elif install_method.type == "http":
            # For HTTP servers, we might need special handling
            if install_method.url:
                add_cmd = f"{tool_name} mcp add {server_name} --scope {scope} -- {install_method.url}"
            else:
                return {}
            remove_cmd = f"{tool_name} mcp remove {server_name}"
            list_cmd = f"{tool_name} mcp list"

        else:
            return {}

        return {"add_cmd": add_cmd, "remove_cmd": remove_cmd, "list_cmd": list_cmd}

    def _check_and_install_server(self, server_name: str, add_cmd: str) -> bool:

        if self.is_server_installed(self.tool_name, server_name):
            print(f"✓ {server_name} is already installed for {self.tool_name}")
            return True
        else:
            # Load server info to show details
            server_info = self.get_server_config(server_name)

            print(f"Installing MCP server '{server_name}' for {self.tool_name}...")
            if server_info:
                if "package" in server_info:
                    print(f"  Server package: {server_info['package']}")
                elif "command" in server_info:
                    print(f"  Server command: {server_info['command']}")
                if "codex_extra" in server_info and self.tool_name == "codex":
                    print(f"  Codex extra args: {server_info['codex_extra']}")

            # Try the tool's add command
            success, output = self.execute_command(add_cmd)
            if success:
                # Verify the server was actually installed
                if self.is_server_installed(self.tool_name, server_name):
                    print(
                        f"✓ Successfully installed {server_name} for {self.tool_name}"
                    )
                    return True
                else:
                    # Tool command succeeded but server still not installed - try fallback
                    print(
                        f"  ⚠️  Add command succeeded but {server_name} is still not installed"
                    )
                    print(f"  Trying fallback addition...")
                    add_success = self._fallback_add_server(server_name)
                    if add_success:
                        print(f"  ✅ Fallback addition successful for {server_name}")
                        return True
                    else:
                        print(f"  ❌ Fallback addition also failed for {server_name}")
                        return False
            else:
                # Tool command failed - try fallback
                print(f"  Tool add command failed, trying fallback addition...")
                if output:
                    print(f"  Error: {output}")
                add_success = self._fallback_add_server(server_name)
                if add_success:
                    print(f"  ✅ Fallback addition successful for {server_name}")
                    return True
                else:
                    print(f"  ❌ Fallback addition also failed for {server_name}")
                    return False

    def refresh_servers(self) -> bool:
        """Refresh all MCP servers for this tool (remove then re-add)."""
        tool_configs = self.get_tool_config(self.tool_name)
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

            # Step 1: Try to remove the server
            remove_success = False

            # Try the tool's remove command
            success, _ = self.execute_command(server_cfg.get("remove_cmd", ""))
            if success:
                # Check if the server was actually removed
                still_installed = self.is_server_installed(self.tool_name, server_name)
                if not still_installed:
                    remove_success = True
                    print(f"  ✓ Successfully removed {server_name}")
                else:
                    # Tool command succeeded but server still installed - try fallback
                    print(
                        f"  ⚠️  Remove command succeeded but {server_name} is still installed"
                    )
                    print(f"  Trying fallback removal...")
                    remove_success = self._fallback_remove_server(server_name)
                    if remove_success:
                        print(f"  ✅ Fallback removal successful for {server_name}")
                    else:
                        print(f"  ❌ Fallback removal also failed for {server_name}")
            else:
                # Tool command failed - try fallback
                print(f"  Tool remove command failed, trying fallback removal...")
                remove_success = self._fallback_remove_server(server_name)
                if remove_success:
                    print(f"  ✅ Fallback removal successful for {server_name}")
                else:
                    print(f"  ❌ Fallback removal also failed for {server_name}")

            if not remove_success:
                print(f"  ❌ Failed to remove {server_name}")
                results.append(f"❌ {server_name}: Failed to remove")
                continue

            # Step 4: Re-add the server
            add_success = self._check_and_install_server(
                server_name, server_cfg.get("add_cmd", "")
            )

            if add_success:
                print(f"  ✅ Successfully refreshed {server_name}")
                results.append(f"✅ {server_name}: Refreshed successfully")
                success_count += 1
            else:
                print(f"  ❌ Failed to re-add {server_name}")
                results.append(f"❌ {server_name}: Failed to re-add")

        # Final summary
        summary = "\n".join(results)
        if success_count == total_count:
            content = f"Overall Status: ✅ Successfully refreshed all {total_count} MCP servers for {self.tool_name}\n\n{summary}"
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH COMPLETE", content
            )
            return True
        else:
            content = f"Overall Status: ❌ Failed to refresh {total_count - success_count}/{total_count} MCP servers for {self.tool_name}\n\n{summary}"
            print_squared_frame(
                f"{self.tool_name.upper()} MCP SERVERS - REFRESH FAILED", content
            )
            return False

    def _execute_remove_command(self, server_name: str, remove_cmd: str) -> bool:
        """Execute the remove command for a specific MCP server."""
        print(f"Removing MCP server '{server_name}' for {self.tool_name}...")
        success, output = self.execute_command(remove_cmd)
        if success:
            print(f"✓ Successfully removed {server_name} for {self.tool_name}")
            return True
        else:
            print(f"✗ Failed to remove {server_name} for {self.tool_name}")
            if output:
                print(f"Error: {output}")
            return False

    def _fallback_add_server(self, server_name: str) -> bool:
        """Attempt to add MCP server configuration directly to config files."""

        from .base import find_mcp_config

        # Get server configuration - try registry first, then legacy
        server_info = self.get_server_config(server_name)
        if not server_info:
            print(f"  No server configuration found for {server_name}")
            return False

        # Get possible config file locations based on tool name
        config_locations = self._get_config_locations(self.tool_name)

        # Exclude the global project mcp.json
        global_config_path = find_mcp_config()
        config_locations = [
            loc for loc in config_locations if loc != global_config_path
        ]

        for config_path in config_locations:
            if self._add_server_to_config(config_path, server_name, server_info):
                print(f"  Added {server_name} to {config_path}")
                return True

        return False

    def _fallback_remove_server(self, server_name: str) -> bool:
        """Attempt to remove MCP server configuration directly from config files."""

        from .base import find_mcp_config

        # Get possible config file locations based on tool name
        config_locations = self._get_config_locations(self.tool_name)

        # Exclude the global project mcp.json
        global_config_path = find_mcp_config()
        config_locations = [
            loc for loc in config_locations if loc != global_config_path
        ]

        for config_path in config_locations:
            if self._remove_server_from_config(config_path, server_name):
                print(f"  Removed {server_name} from {config_path}")
                return True

        return False

    def _add_server_to_config(
        self, config_path: Path, server_name: str, server_info: dict
    ) -> bool:
        """Add a server to a specific MCP config file."""
        try:
            # Load existing config
            config, is_toml = _load_config_file(config_path)
            if config is None:
                # File exists but is invalid, can't safely modify
                return False

            # Check if server already exists
            if _server_exists_in_config(config, server_name):
                return False

            # Find or create the appropriate container
            container_key = _get_preferred_container_key(config, is_toml)
            if container_key not in config:
                config[container_key] = {}

            # Add the server
            config[container_key][server_name] = server_info

            # Save and return
            if _save_config_file(config_path, config, is_toml):
                return True

        except Exception as e:
            print(
                f"  Warning: Failed to process {config_path}: {type(e).__name__}: {e}"
            )

        return False

    def _get_config_locations(self, tool_name: str):
        """Get possible MCP configuration file locations for a tool."""
        # Use the centralized config paths function
        return _get_config_locations(tool_name)

    def _remove_server_from_config(self, config_path: Path, server_name: str) -> bool:
        """Remove a server from a specific MCP config file."""
        if not config_path.exists():
            return False

        try:
            config, is_toml = _load_config_file(config_path)
            if config is None:
                return False

            if _remove_server_from_containers(config, server_name):
                return _save_config_file(config_path, config, is_toml)

        except Exception as e:
            print(
                f"  Warning: Failed to process {config_path}: {type(e).__name__}: {e}"
            )

        return False
