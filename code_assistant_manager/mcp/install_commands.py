"""
MCP Server Installation Commands

This module provides command-line interface commands for installing MCP servers
to various MCP-compatible clients. It handles server discovery, installation method
selection, and configuration management.

Key Features:
- Install servers from the local registry to supported clients
- List available installation methods for servers
- Force reinstallation of existing servers
- Support for multiple installation methods (npm, docker, etc.)
"""

from typing import Optional

import typer
from rich.console import Console

from .installation_manager import InstallationManager
from .registry_manager import LocalRegistryManager

# Console for rich text output
console = Console()

# Typer app for CLI commands
app = typer.Typer(help="MCP Server Installation Commands")

# Global managers for server installation and registry access
installation_manager = InstallationManager()
registry_manager = LocalRegistryManager()


@app.command()
def install(
    server_name: str,
    client: str,
    method: Optional[str] = typer.Option(
        None, "--method", "-m", help="Installation method to use"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force installation if server already exists"
    ),
):
    """
    Install an MCP server to a specific client.

    This command installs the specified MCP server from the local registry
    to the target MCP client. It automatically selects the best installation
    method unless one is explicitly specified.

    Args:
        server_name: Name of the MCP server to install
        client: Target MCP client (claude, codex, gemini, etc.)
        method: Optional specific installation method to use
        force: Whether to force reinstallation if server already exists

    Examples:
        code-assistant-manager mcp install memory claude
        code-assistant-manager mcp install filesystem codex --method docker
        code-assistant-manager mcp install memory gemini --force
    """
    # Attempt server installation through the installation manager
    success = installation_manager.install_server(
        server_name=server_name,
        client_name=client,
        installation_method=method,
        force=force,
    )

    # Report installation result to user
    if success:
        console.print(f"[green]Successfully installed '{server_name}' to {client}![/]")
        raise typer.Exit(0)
    else:
        console.print(f"[red]Failed to install '{server_name}' to {client}.[/]")
        raise typer.Exit(1)


@app.command()
def list_methods(server_name: str):
    """
    List available installation methods for a server.

    This command displays all available installation methods for the specified
    MCP server, including their descriptions and commands. It helps users
    understand how to install servers and choose appropriate methods.

    Args:
        server_name: Name of the MCP server to check

    Examples:
        code-assistant-manager mcp list-methods memory
        code-assistant-manager mcp list-methods filesystem
    """
    # Retrieve server schema from registry
    schema = registry_manager.get_server_schema(server_name)

    # Validate server exists in registry
    if not schema:
        console.print(
            f"[red]Error:[/] Server '{server_name}' not found in the local registry."
        )
        raise typer.Exit(1)

    # Check if server has any installation methods defined
    if not schema.installations:
        console.print(f"[yellow]No installation methods found for '{server_name}'.[/]")
        raise typer.Exit(0)

    # Display header for installation methods
    console.print(f"[bold]Installation methods for '{server_name}':[/]")

    # Iterate through each installation method and display details
    for method_name, method in schema.installations.items():
        # Mark recommended methods
        recommended = " [green](recommended)[/]" if method.recommended else ""

        # Display method name and description
        console.print(f"  • {method_name}: {method.description}{recommended}")

        # Display command details if available
        if method.command:
            args_str = " ".join(method.args) if method.args else ""
            console.print(f"    [dim]{method.command} {args_str}[/]")


# Allow running as standalone script for testing
if __name__ == "__main__":
    app()
