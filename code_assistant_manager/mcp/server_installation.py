"""Server installation utilities.

Provides functions for installing and removing MCP servers.
"""


def _check_and_install_server(
    tool_name: str,
    server_name: str,
    add_cmd: str,
    get_server_config_func,
    execute_command_func,
    is_server_installed_func,
) -> bool:
    """Check and install a server with fallback logic."""

    if is_server_installed_func(tool_name, server_name):
        print(f"✓ {server_name} is already installed for {tool_name}")
        return True
    else:
        # Load server info to show details
        server_info = get_server_config_func(server_name)

        print(f"Installing MCP server '{server_name}' for {tool_name}...")
        if server_info:
            if "package" in server_info:
                print(f"  Server package: {server_info['package']}")
            elif "command" in server_info:
                print(f"  Server command: {server_info['command']}")
            if "codex_extra" in server_info and tool_name == "codex":
                print(f"  Codex extra args: {server_info['codex_extra']}")

        # Try the tool's add command
        success, output = execute_command_func(add_cmd)
        if success:
            # Verify the server was actually installed
            if is_server_installed_func(tool_name, server_name):
                print(f"✓ Successfully installed {server_name} for {tool_name}")
                return True
            else:
                # Tool command succeeded but server still not installed - try fallback
                print(
                    f"  ⚠️  Add command succeeded but {server_name} is still not installed"
                )
                print(f"  Trying fallback addition...")
                add_success = _fallback_add_server(
                    server_name, tool_name, get_server_config_func
                )
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
            add_success = _fallback_add_server(
                server_name, tool_name, get_server_config_func
            )
            if add_success:
                print(f"  ✅ Fallback addition successful for {server_name}")
                return True
            else:
                print(f"  ❌ Fallback addition also failed for {server_name}")
                return False


def _fallback_add_server(
    server_name: str, tool_name: str, get_server_config_func
) -> bool:
    """Attempt to add MCP server configuration directly to config files."""

    from .config_paths import _get_config_locations
    from .server_config import _add_server_to_config

    # Get server configuration
    server_info = get_server_config_func(server_name)
    if not server_info:
        print(f"  No server configuration found for {server_name}")
        return False

    # Get possible config file locations based on tool name
    config_locations = _get_config_locations(tool_name)

    # Exclude the global project mcp.json
    from .base import find_mcp_config

    global_config_path = find_mcp_config()
    config_locations = [loc for loc in config_locations if loc != global_config_path]

    for config_path in config_locations:
        if _add_server_to_config(config_path, server_name, server_info):
            print(f"  Added {server_name} to {config_path}")
            return True

    return False


def _fallback_remove_server(server_name: str, tool_name: str) -> bool:
    """Attempt to remove MCP server configuration directly from config files."""

    from .config_paths import _get_config_locations
    from .server_config import _remove_server_from_config

    # Get possible config file locations based on tool name
    config_locations = _get_config_locations(tool_name)

    # Exclude the global project mcp.json
    from .base import find_mcp_config

    global_config_path = find_mcp_config()
    config_locations = [loc for loc in config_locations if loc != global_config_path]

    for config_path in config_locations:
        if _remove_server_from_config(config_path, server_name):
            print(f"  Removed {server_name} from {config_path}")
            return True

    return False


def _execute_remove_command(
    server_name: str, tool_name: str, remove_cmd: str, execute_command_func
) -> bool:
    """Execute the remove command for a specific MCP server."""
    print(f"Removing MCP server '{server_name}' for {tool_name}...")
    success, output = execute_command_func(remove_cmd)
    if success:
        print(f"✓ Successfully removed {server_name} for {tool_name}")
        return True
    else:
        print(f"✗ Failed to remove {server_name} for {tool_name}")
        if output:
            print(f"Error: {output}")
        return False
