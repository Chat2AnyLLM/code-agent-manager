"""CLI tool entry point for MCP (Model Context Protocol) management."""

from typing import List

from ..tools.base import CLITool


class MCPTool(CLITool):
    """MCP (Model Context Protocol) server management tool."""

    command_name = "mcp"
    tool_key = None
    install_description = "MCP Server Manager"

    def __init__(self, config, prog_name: str = "code-assistant-manager mcp"):
        super().__init__(config)
        # Only initialize manager if needed for server commands
        self._manager = None
        self.prog_name = prog_name

    @property
    def manager(self):
        """Lazy initialization of MCP manager."""
        if self._manager is None:
            from .manager import MCPManager

            self._manager = MCPManager()
        return self._manager

    def _warn_about_legacy_configs(self):
        """Warn users about legacy mcp.json files that are no longer used."""
        from pathlib import Path

        home = Path.home()
        legacy_configs = [
            home / ".config" / "mcp.json",
            home / "mcp.json",
            Path.cwd() / "mcp.json",
            Path.cwd() / ".mcp.json",
        ]

        found_legacy = []
        for config_path in legacy_configs:
            if config_path.exists():
                found_legacy.append(str(config_path))

        if found_legacy:
            print("⚠️  DEPRECATED: Legacy mcp.json files detected")
            print("   The following mcp.json files are no longer used:")
            for path in found_legacy:
                print(f"   • {path}")
            print("   All MCP server configurations now come from the registry.")
            print(
                "   Use 'code-assistant-manager mcp server list' to see available servers."
            )
            print("   You can safely delete these legacy config files.\n")

    def run(self, args: List[str] = []) -> int:
        """
        Run the MCP tool with the specified arguments.

        Args:
            args: List of arguments to pass to the MCP tool

        Returns:
            Exit code of the operation
        """
        if not args:
            self._print_help(self.prog_name)
            return 0

        command = args[0]
        remaining_args = args[1:] if len(args) > 1 else []

        # Expand short aliases for subcommands
        command_aliases = {
            "s": "server",
            "l": "list",
            "search": "search",  # no short alias needed
            "show": "show",  # no short alias needed
            "a": "add",
            "r": "remove",
            "u": "update",
        }

        # If the first arg after a subcommand is a short alias, expand it
        if (
            command == "server"
            and remaining_args
            and remaining_args[0] in command_aliases
        ):
            remaining_args[0] = command_aliases[remaining_args[0]]

        # Only servers management commands are supported
        if command in ["server", "s"]:
            return self._handle_servers_command(remaining_args)
        else:
            help_text = f"""
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ Unknown command '{command}'                                                  │
│                                                                             │
│ Only 'server' command is supported. Use '{self.prog_name} server --help' for │
│ available server management commands.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
"""
            print(help_text)
            return 1

    def _print_help(self, prog_name: str = "code-assistant-manager mcp"):
        """Print help information in typer style."""
        help_text = f"""Usage: {prog_name} [OPTIONS] COMMAND [ARGS]...

Manage Model Context Protocol servers.

Options:
  --help  Show this message and exit.

Commands:
  server  Manage MCP servers

Run '{prog_name} server --help' for server management commands.
"""
        print(help_text)

    def _handle_servers_command(self, args: List[str]) -> int:
        """Handle servers management commands."""
        # Check for legacy configs when using server commands
        self._warn_about_legacy_configs()

        # Use typer to handle server commands
        import sys
        from io import StringIO

        # Capture stderr to suppress error messages on invalid args
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            from .server_commands import app as server_app

            server_app(args, prog_name=f"{self.prog_name} server")
            return 0
        except SystemExit as e:
            # Restore stderr
            sys.stderr = old_stderr
            # If server command fails with argument errors, show help instead
            if e.code != 0:
                self._print_help(self.prog_name)
                return 0  # Return 0 since we showed help
            return e.code
        finally:
            # Always restore stderr
            sys.stderr = old_stderr
