"""MCP CLI app for Typer integration."""

import logging
from typing import Optional

import typer

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools import (
    display_all_tool_endpoints,
    display_tool_endpoints,
)

# Import individual commands from server_commands
from .server_commands import (
    add,
    list as list_servers,
    remove,
    search,
    show,
    update,
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="mcp", help="Manage Model Context Protocol servers", no_args_is_help=True
)


@app.command()
def endpoints(
    tool: Optional[str] = typer.Argument(
        None,
        help="Display endpoint information for a specific tool, or use 'all' for all tools",
    ),
):
    """Display endpoint information for MCP-enabled tools."""
    logger.debug(f"Endpoints command invoked with tool: {tool}")
    try:
        config = ConfigManager()
        if tool is None or tool == "all":
            logger.debug("Displaying all tool endpoints")
            display_all_tool_endpoints(config)
        else:
            logger.debug(f"Displaying endpoints for tool: {tool}")
            display_tool_endpoints(config, tool)
    except Exception as e:
        logger.error(f"Error displaying endpoints: {e}")
        typer.echo(f"Error displaying endpoints: {e}")
        raise typer.Exit(1)


@app.command()
def status(
    client: Optional[str] = typer.Option(
        None, "--client", "-c", help="Show status for specific client (or 'all')"
    ),
):
    """Show MCP server installation status across clients."""
    from rich.console import Console
    from rich.table import Table

    from .manager import MCPManager

    console = Console()
    manager = MCPManager()

    if client:
        # Show detailed status for specific client(s)
        if client.lower() == "all":
            clients = manager.get_available_tools()
        else:
            clients = [c.strip() for c in client.split(",")]

        for client_name in clients:
            client_obj = manager.get_client(client_name)
            if not client_obj:
                console.print(f"[red]Error:[/] Client '{client_name}' not supported.")
                continue

            console.print(f"\n[bold]{client_name} MCP Status:[/]")
            client_obj.list_servers()
    else:
        # Show summary status for all clients
        table = Table(title="MCP Status Summary")
        table.add_column("Client", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Servers Count", style="yellow")

        for tool_name in manager.get_available_tools():
            client_obj = manager.get_client(tool_name)
            if client_obj:
                # This is a simplified status - could be enhanced
                table.add_row(tool_name, "Available", "-")

        console.print(table)


# Add all server management commands directly to mcp app
app.command(name="list")(list_servers)
app.command(name="search")(search)
app.command(name="show")(show)
app.command(name="add")(add)
app.command(name="remove")(remove)
app.command(name="update")(update)
