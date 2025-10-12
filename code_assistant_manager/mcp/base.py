"""Base MCP classes with common functionality."""

import json
import os
import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple


def find_project_root(start_path: Path = None) -> Path:
    """
    Find the project root directory by looking for a .git directory or setup.py file.

    For the code-assistant-manager project, this will look for the project root relative to
    the package location, not the current working directory.

    Args:
        start_path: Path to start searching from. Defaults to the package directory.

    Returns:
        Path to the project root directory.

    Raises:
        FileNotFoundError: If project root cannot be found.
    """
    # Start from the package directory, not the current working directory
    if start_path is None:
        # Get the directory containing this module
        package_dir = Path(__file__).resolve().parent.parent
        start_path = package_dir

    current_path = start_path.resolve()

    # Walk up the directory tree looking for project indicators
    while current_path != current_path.parent:  # Stop at filesystem root
        # Check for common project root indicators
        if (
            (current_path / ".git").exists()
            or (current_path / "setup.py").exists()
            or (current_path / "pyproject.toml").exists()
        ):
            return current_path
        current_path = current_path.parent

    # If we can't find a project root, raise an error
    raise FileNotFoundError("Project root not found")


def find_mcp_config() -> Path:
    """
    Find the mcp.json configuration file.

    Looks in the following locations in order:
    1. Current directory
    2. CODE_ASSISTANT_MANAGER_DIR environment variable directory
    3. Project root directory

    Returns:
        Path to the mcp.json file.

    Raises:
        FileNotFoundError: If mcp.json cannot be found.
    """
    # First check current directory
    current_dir_config = Path.cwd() / "mcp.json"
    if current_dir_config.exists():
        return current_dir_config

    # Then check CODE_ASSISTANT_MANAGER_DIR environment variable
    code_assistant_manager_dir = os.environ.get("__CODE_ASSISTANT_MANAGER_DIR")
    if code_assistant_manager_dir:
        code_assistant_manager_dir_config = (
            Path(code_assistant_manager_dir) / "mcp.json"
        )
        if code_assistant_manager_dir_config.exists():
            return code_assistant_manager_dir_config

    # Then check project root
    try:
        project_root = find_project_root()
        project_root_config = project_root / "mcp.json"
        if project_root_config.exists():
            return project_root_config
    except FileNotFoundError:
        pass

    # If not found anywhere, raise an error
    raise FileNotFoundError(
        "mcp.json file not found in current directory, CODE_ASSISTANT_MANAGER_DIR, or project root"
    )


def print_squared_frame(title: str, content: str = ""):
    """
    Print content within a squared frame that automatically adjusts to accommodate full text.
    Handles ANSI escape codes properly by calculating visual width instead of actual string length.

    Args:
        title: The title to display in the frame
        content: The content to display within the frame
    """

    # Function to strip ANSI escape codes for width calculation
    def strip_ansi(text):
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    # Calculate the maximum visual width needed
    lines_content = content.strip().split("\n") if content else []
    all_texts = [title] + lines_content
    max_visual_width = (
        max(len(strip_ansi(text)) for text in all_texts) if all_texts else len(title)
    )
    width = max_visual_width
    frame_width = width + 4
    border_dashes = frame_width - 2
    # Top border
    top = "╔" + "═" * border_dashes + "╗"
    separator = "╠" + "═" * border_dashes + "╣"
    bottom = "╚" + "═" * border_dashes + "╝"
    print("\n" + top)
    # Title
    print("║" + title.center(frame_width - 2) + "║")
    # Separator
    print(separator)

    # Content
    for line in lines_content:
        line_visual = len(strip_ansi(line))
        spaces = frame_width - 4 - line_visual
        print("║" + "  " + line + " " * spaces + "║")
    # Bottom
    print(bottom)


class MCPBase(ABC):
    """Base class for MCP functionality with common operations."""

    def __init__(self):
        self.config = None
        self.config_path = None

    def load_config(self) -> Tuple[bool, Dict]:
        """Load MCP configuration from mcp.json."""
        try:
            if not self.config_path:
                self.config_path = find_mcp_config()
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
            return True, self.config
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return False, {}
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse mcp.json - {e}")
            return False, {}
        except Exception as e:
            print(f"Error: Failed to read mcp.json - {e}")
            return False, {}

    def get_available_tools(self) -> List[str]:
        """Get all available tools from the MCP configuration."""
        success, config = self.load_config()
        if not success:
            return []

        # Check if using new simplified structure
        if "global" in config and "servers" in config:
            # New simplified structure - check for all_tools first, then fall back to flag-based approach
            all_tools = config.get("global", {}).get("all_tools", [])
            if all_tools:
                return sorted(list(set(all_tools)))
            # Fallback to old approach for backward compatibility
            tools_with_scope = set(
                config.get("global", {}).get("tools_with_scope_flag", [])
            )
            tools_with_tls = set(
                config.get("global", {}).get("tools_with_tls_flag", [])
            )
            return sorted(list(tools_with_scope | tools_with_tls))

        # Legacy structure
        tools = set()
        mcp_servers = config.get("mcpServer", {})

        for server_config in mcp_servers.values():
            # Add all tool names found in server configurations
            for tool_name in server_config.keys():
                if tool_name:  # Skip empty keys
                    tools.add(tool_name)

        # Remove empty string and None values if any
        tools.discard("")

        return sorted(list(tools))

    def get_tool_config(self, tool_name: str, scope: str = "user") -> Dict[str, Dict]:
        """Extract tool configuration from the MCP config."""
        success, config = self.load_config()
        if not success:
            return {}

        # Check if using new simplified structure
        if "global" in config and "servers" in config:
            return self._get_tool_config_new(config, tool_name, scope)

        # Legacy structure
        mcp_servers = config.get("mcpServer", {})
        tool_configs = {}

        for server_name, server_config in mcp_servers.items():
            if tool_name in server_config:
                tool_configs[server_name] = server_config[tool_name]

        return tool_configs

    def _get_tool_config_new(
        self, config: Dict, tool_name: str, scope: str
    ) -> Dict[str, Dict]:
        """Generate tool configuration from the new simplified MCP config."""
        global_config = config.get("global", {})
        servers_config = config.get("servers", {})

        tools_with_scope = set(global_config.get("tools_with_scope", []))
        # Backward compatibility: if old keys exist, use them
        if "tools_with_user_scope" in global_config and not tools_with_scope:
            tools_with_scope = set(global_config.get("tools_with_user_scope", []))
        tools_with_tls = set(global_config.get("tools_with_tls_flag", []))
        tools_with_cli_separator = set(
            global_config.get("tools_with_cli_separator", [])
        )

        tool_configs = {}

        for server_name, server_info in servers_config.items():
            # Build commands based on server type and tool-specific requirements
            commands = self._build_commands_for_tool(
                tool_name,
                server_name,
                server_info,
                tools_with_scope,
                scope,
                tools_with_tls,
                tools_with_cli_separator,
            )
            if commands:
                tool_configs[server_name] = commands

        return tool_configs

    def _build_commands_for_tool(
        self,
        tool_name: str,
        server_name: str,
        server_info: Dict,
        tools_with_scope: set,
        scope_type: str,
        tools_with_tls: set,
        tools_with_cli_separator: set,
    ) -> Dict[str, str]:
        """Build add, remove, and list commands for a specific tool and server."""
        # Check if server has a package (npm-style) or command (direct execution)
        if "package" in server_info:
            return self._build_package_commands(
                tool_name,
                server_name,
                server_info,
                tools_with_scope,
                scope_type,
                tools_with_tls,
                tools_with_cli_separator,
            )
        elif "command" in server_info:
            return self._build_command_commands(
                tool_name,
                server_name,
                server_info,
                tools_with_scope,
                scope_type,
                tools_with_cli_separator,
            )
        else:
            return {}  # Server has neither package nor command

    def _build_package_commands(
        self,
        tool_name: str,
        server_name: str,
        server_info: Dict,
        tools_with_scope: set,
        scope_type: str,
        tools_with_tls: set,
        tools_with_cli_separator: set,
    ) -> Dict[str, str]:
        """Build commands for npm-style package servers."""
        package = server_info["package"]
        # Handle special quoting for certain tools
        if tool_name in server_info.get("quote_package_for", []):
            package = f'"{package}"'

        # Build the package command
        package_cmd = f"npx -y {package}"

        # Determine scope and TLS flags
        scope_flag = ""
        if tool_name in tools_with_scope:
            scope_flag = f"--scope {scope_type}"
        tls_flag = (
            "--env NODE_TLS_REJECT_UNAUTHORIZED='0'"
            if tool_name in tools_with_tls
            else ""
        )

        # Build add command
        add_parts = [tool_name, "mcp add", server_name]
        if tool_name in tools_with_cli_separator:
            if scope_flag:
                add_parts.append(scope_flag)
            if tls_flag:
                add_parts.append(tls_flag)
            add_parts.append("--")
        else:
            if scope_flag:
                add_parts.append(scope_flag)
            if tls_flag:
                add_parts.append(tls_flag)
        add_parts.append(package_cmd)

        add_cmd = " ".join(part for part in add_parts if part)

        # Build remove command
        remove_cmd = f"{tool_name} mcp remove {server_name}"

        # Build list command
        list_cmd = f"{tool_name} mcp list"

        return {"add_cmd": add_cmd, "remove_cmd": remove_cmd, "list_cmd": list_cmd}

    def _build_command_commands(
        self,
        tool_name: str,
        server_name: str,
        server_info: Dict,
        tools_with_scope: set,
        scope_type: str,
        tools_with_cli_separator: set,
    ) -> Dict[str, str]:
        """Build commands for direct command execution servers."""
        command = server_info["command"]

        # Add codex-specific extras if applicable
        if tool_name == "codex" and "codex_extra" in server_info:
            command += " " + server_info["codex_extra"]

        # Determine scope flag for add command
        scope_flag = ""
        if tool_name in tools_with_scope:
            scope_flag = f"--scope {scope_type}"

        # Build add command
        add_parts = [tool_name, "mcp add", server_name]
        if tool_name in tools_with_cli_separator:
            if scope_flag:
                add_parts.append(scope_flag)
            add_parts.append("--")
        else:
            if scope_flag:
                add_parts.append(scope_flag)
        add_parts.append(command)

        add_cmd = " ".join(part for part in add_parts if part)

        # Build remove command
        remove_cmd = f"{tool_name} mcp remove {server_name}"

        # Build list command
        list_cmd = f"{tool_name} mcp list"

        return {"add_cmd": add_cmd, "remove_cmd": remove_cmd, "list_cmd": list_cmd}

    def is_server_installed(self, tool_name: str, server_name: str) -> bool:
        """Check if a specific MCP server is installed for a tool.

        First tries to check config files directly, then falls back to executing
        the list command if config-based check fails.
        """
        # Try config-based check first (more secure, doesn't require shell execution)
        if self._check_server_in_config_files(tool_name, server_name):
            return True

        # Fall back to command execution
        tool_configs = self.get_tool_config(tool_name)
        if not tool_configs:
            return False

        # Get the list command for this tool
        list_cmd = None
        for server_cfg in tool_configs.values():
            list_cmd = server_cfg.get("list_cmd")
            if list_cmd:
                break

        if not list_cmd:
            return False

        # Execute the list command and check output
        try:
            result = subprocess.run(
                shlex.split(list_cmd), shell=False, capture_output=True, text=True
            )
            if result.returncode == 0:
                # Check if the server is in the output
                output = result.stdout.lower()
                # Look for the server name in the output
                return server_name.lower() in output
            return False
        except Exception:
            return False

    def _check_server_in_config_files(self, tool_name: str, server_name: str) -> bool:
        """Check if server is installed by reading MCP config files directly."""
        config_locations = self._get_config_locations(tool_name)
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

                    # Check for common MCP server structures
                    for server_key in ["mcpServers", "servers", "mcp_servers"]:
                        if server_key in config and isinstance(
                            config[server_key], dict
                        ):
                            if server_name in config[server_key]:
                                return True
                except Exception:
                    continue
        return False

    def execute_command(self, command: str, description: str = "") -> Tuple[bool, str]:
        """Execute a shell command and return success status with output."""
        return self._execute_command(command, description)

    def _execute_command(self, command: str, description: str = "") -> Tuple[bool, str]:
        """Execute a shell command and return success status with output."""
        try:
            if description:
                print(description)
            print(f"  Complete command: {command}")
            result = subprocess.run(
                shlex.split(command), shell=False, capture_output=True, text=True
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    @abstractmethod
    def add_server(self, server_name: str, scope: str = "user") -> bool:
        """Add a specific MCP server."""

    @abstractmethod
    def remove_server(self, server_name: str, scope: str = "user") -> bool:
        """Remove a specific MCP server."""

    @abstractmethod
    def list_servers(self, scope: str = "all") -> bool:
        """List all MCP servers."""
