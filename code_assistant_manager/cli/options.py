"""Shared Typer options for CLI modules."""

import typer

# Module-level typer.Option constants to fix B008 linting errors
CONFIG_FILE_OPTION = typer.Option(None, "--config", "-c", help="Path to config file")
CONFIG_OPTION = typer.Option(
    None, "--config", "-c", help="Path to settings.conf configuration file"
)
DEBUG_OPTION = typer.Option(False, "--debug", "-d", help="Enable debug logging")
ENDPOINTS_OPTION = typer.Option(
    None,
    "--endpoints",
    help="Display endpoint information for all tools or a specific tool",
)
FORCE_OPTION = typer.Option(False, "--force", "-f", help="Skip confirmation prompt")
INSTALL_ALIAS_TARGET_OPTION = typer.Argument("all", help="Tool to install or 'all'")
KEEP_CONFIG_OPTION = typer.Option(
    False, "--keep-config", "-k", help="Keep configuration files (don't backup)"
)
SHELL_OPTION = typer.Argument(..., help="Shell type (bash, zsh)")
SCOPE_OPTION = typer.Option(
    "user",
    "--scope",
    "-s",
    help="Configuration scope (user, project)",
)
TARGET_OPTION = typer.Argument("all", help="Tool to upgrade or 'all'")
TOOL_ARGS_OPTION = typer.Argument(None, help="Arguments for the editor")
TOOL_NAME_OPTION = typer.Argument(None, help="Tool to launch")
UNINSTALL_TARGET_OPTION = typer.Argument(..., help="Tool to uninstall or 'all'")
UPGRADE_ALIAS_TARGET_OPTION = typer.Argument("all", help="Tool to upgrade or 'all'")
VALIDATE_VERBOSE_OPTION = typer.Option(
    False, "--verbose", "-v", help="Show detailed output"
)
VERBOSE_DOCTOR_OPTION = typer.Option(
    False, "--verbose", "-v", help="Show detailed output"
)
VERBOSE_OPTION = typer.Option(
    False,
    "--verbose",
    "-v",
    help="Enable verbose installer output (overrides quiet default)",
)
VERSION_OPTION = typer.Option(
    None,
    "--version",
    help="Show version information",
)
