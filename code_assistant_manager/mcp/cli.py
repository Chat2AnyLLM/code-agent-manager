"""MCP CLI app for Typer integration."""

import logging
from typing import Optional

import typer
from typer import Context

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools import (
    display_all_tool_endpoints,
    display_tool_endpoints,
)

from .server_commands import app as server_app

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="mcp", help="Manage Model Context Protocol servers", no_args_is_help=True
)


@app.callback()
def mcp_callback(
    ctx: Context,
    endpoints: Optional[str] = typer.Option(
        None,
        "--endpoints",
        help="Display endpoint information for all tools or a specific tool",
    ),
):
    """MCP callback to handle endpoints option."""
    logger.debug(f"MCP callback invoked with endpoints: {endpoints}")
    # Store endpoints in app context
    ctx.ensure_object(dict)
    ctx.obj["endpoints"] = endpoints

    # If endpoints is specified, display and exit
    if endpoints:
        logger.debug(f"Handling endpoints option: {endpoints}")
        # We need config for this, but since this is a subcommand, we might not have config_path
        # For now, assume default config
        try:
            config = ConfigManager()
            if endpoints == "all":
                logger.debug("Displaying all tool endpoints")
                display_all_tool_endpoints(config)
            else:
                logger.debug(f"Displaying endpoints for tool: {endpoints}")
                display_tool_endpoints(config, endpoints)
            raise typer.Exit()
        except Exception as e:
            logger.error(f"Error displaying endpoints: {e}")
            typer.echo(f"Error displaying endpoints: {e}")
            raise typer.Exit(1)


# Add server commands as subcommand
app.add_typer(server_app, name="server")
