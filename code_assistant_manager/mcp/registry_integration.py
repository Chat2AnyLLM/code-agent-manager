"""Registry integration utilities.

Provides functions for working with MCP server registries.
"""

from typing import Dict


def _convert_schema_to_client_format(schema) -> Dict:
    """
    Convert a ServerSchema to client-compatible configuration format.

    Args:
        schema: ServerSchema object from registry

    Returns:
        Dict in client configuration format
    """
    # Use the preferred installation method for this tool
    install_method = _select_best_installation_method(schema)

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


def _select_best_installation_method(schema):
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


def _generate_config_from_registry(registry_manager) -> tuple[bool, dict]:
    """
    Generate client configuration from registry data.

    Returns:
        Tuple of (success, config_dict)
    """
    if not registry_manager:
        return False, {}

    all_schemas = registry_manager.list_server_schemas()

    # Convert registry schemas to client-compatible format
    servers = {}
    for name, schema in all_schemas.items():
        if _is_compatible_with_client(schema):
            servers[name] = _convert_schema_to_client_format(schema)

    return True, {"servers": servers}


def _is_compatible_with_client(schema) -> bool:
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


def _build_commands_for_tool_from_schema(
    tool_name: str, server_name: str, schema, scope: str
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
    install_method = _select_best_installation_method(schema)
    if not install_method:
        return {}

    # Build commands based on installation method type
    if install_method.type == "npm":
        package_cmd = (
            f"npx -y {install_method.package}"
            if install_method.package
            else install_method.command
        )
        add_cmd = f"{tool_name} mcp add {server_name} --scope {scope} -- {package_cmd}"
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
