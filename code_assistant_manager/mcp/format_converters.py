"""Server format conversion utilities.

Provides functions for converting between different MCP server configuration formats.
"""

import shlex
from typing import List


def _convert_server_to_stdio_format(
    server_info: dict, add_tls_for_tools: List[str] = None
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
    stdio_format = {"type": "stdio", "env": {}}

    # Copy any existing env from server_info
    if "env" in server_info and isinstance(server_info["env"], dict):
        stdio_format["env"].update(server_info["env"])

    # Determine if we should add TLS rejection
    add_tls = False
    if add_tls_for_tools:
        # This would need the tool_name to be passed in or accessed from context
        # For now, we'll skip this logic as it needs refactoring
        pass

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

        # Add tool-specific extras if applicable (this would need tool_name context)
        # if self.tool_name == "codex" and "codex_extra" in server_info:
        #     command += " " + server_info["codex_extra"]

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
    server_info: dict, add_codex_extra: bool = True
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
        # Add codex-specific extras if applicable (needs tool_name context)
        # if add_codex_extra and self.tool_name == "codex" and "codex_extra" in server_info:
        #     command += " " + server_info["codex_extra"]
        command_format["command"] = command

    return command_format
