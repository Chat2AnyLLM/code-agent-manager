"""Configuration file handling utilities.

Provides functions for loading and saving JSON/TOML configuration files.
"""

import json
from pathlib import Path
from typing import Optional, Tuple

# Common MCP server config key names in different config formats
MCP_SERVER_KEYS = ["mcpServers", "servers", "mcp_servers"]


def _load_config_file(config_path: Path) -> Tuple[Optional[dict], bool]:
    """
    Load a config file (JSON or TOML).

    Returns:
        Tuple of (config_dict or None, is_toml)
    """
    is_toml = config_path.suffix == ".toml"

    if not config_path.exists():
        return {}, is_toml

    try:
        if is_toml:
            import tomllib

            with open(config_path, "rb") as f:
                return tomllib.load(f), is_toml
        else:
            with open(config_path, "r") as f:
                return json.load(f), is_toml
    except Exception:
        return None, is_toml


def _save_config_file(config_path: Path, config: dict, is_toml: bool) -> bool:
    """Save a config dict to file (JSON or TOML)."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if is_toml:
            import tomli_w

            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)
        else:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def _find_server_container(
    config: dict, server_name: str
) -> Optional[Tuple[str, dict]]:
    """
    Find which container (mcpServers, servers, etc.) holds a server.

    Returns:
        Tuple of (container_key, container_dict) or None if not found
    """
    for key in MCP_SERVER_KEYS:
        if key in config and isinstance(config[key], dict):
            if server_name in config[key]:
                return key, config[key]

    # Check direct entry
    if server_name in config and isinstance(config[server_name], dict):
        return None, config  # None key means direct entry

    return None


def _server_exists_in_config(config: dict, server_name: str) -> bool:
    """Check if a server already exists in any config structure."""
    for key in MCP_SERVER_KEYS:
        if key in config and isinstance(config[key], dict):
            if server_name in config[key]:
                return True

    # Check direct entry
    if server_name in config and isinstance(config[server_name], dict):
        return True

    return False


def _get_preferred_container_key(config: dict, is_toml: bool) -> str:
    """Get the preferred container key for adding new servers."""
    # Prefer existing containers
    for key in MCP_SERVER_KEYS:
        if key in config and isinstance(config[key], dict):
            return key

    return "mcpServers"  # Default fallback


def _remove_server_from_containers(config: dict, server_name: str) -> bool:
    """Remove a server from any config container structure."""
    removed = False

    # Check structured containers
    for key in MCP_SERVER_KEYS:
        if key in config and isinstance(config[key], dict):
            if server_name in config[key]:
                del config[key][server_name]
                removed = True

    # Check direct entry
    if server_name in config and isinstance(config[server_name], dict):
        del config[server_name]
        removed = True

    return removed


def _add_server_to_config(
    config: dict, server_name: str, server_info: dict, is_toml: bool = False
) -> bool:
    """
    Add a server to a config structure.

    Args:
        config: The config dict to modify
        server_name: Name of the server to add
        server_info: Server configuration info
        is_toml: Whether this is a TOML config

    Returns:
        bool: Success or failure
    """
    # Check if server already exists
    if _server_exists_in_config(config, server_name):
        return False

    # Find or create the appropriate container
    container_key = _get_preferred_container_key(config, is_toml)
    if container_key not in config:
        config[container_key] = {}

    # Add the server
    config[container_key][server_name] = server_info

    return True
