"""Plugin command helpers.

Shared utility functions for plugin commands.
"""

import logging

from code_assistant_manager.plugins import get_handler

logger = logging.getLogger(__name__)


def _check_app_cli(app_type: str = "claude"):
    """Check if app CLI is available."""
    import typer

    from code_assistant_manager.menu.base import Colors

    handler = get_handler(app_type)
    if not handler.get_cli_path():
        typer.echo(
            f"{Colors.RED}✗ {app_type.capitalize()} CLI not found. Please install {app_type.capitalize()} first.{Colors.RESET}"
        )
        raise typer.Exit(1)
