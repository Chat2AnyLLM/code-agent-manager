"""CLI command definitions for Code Assistant Manager.

This module contains the core CLI commands. Additional functionality is split into:
- uninstall_commands.py: Uninstall helpers, context, and NPM/config mappings
- completion_commands.py: Shell completion script generation
"""

import logging
import sys
from typing import Optional

import typer
from typer import Context

# Import completion commands to register them with the app
import code_assistant_manager.cli.completion_commands  # noqa: F401
from code_assistant_manager.cli.app import app

# Import from split modules for backward compatibility
from code_assistant_manager.cli.completion_commands import (
    completion,
    generate_completion_script,
)
from code_assistant_manager.cli.options import (
    CONFIG_FILE_OPTION,
    FORCE_OPTION,
    INSTALL_ALIAS_TARGET_OPTION,
    KEEP_CONFIG_OPTION,
    TARGET_OPTION,
    TOOL_NAME_OPTION,
    UNINSTALL_TARGET_OPTION,
    UPGRADE_ALIAS_TARGET_OPTION,
    VALIDATE_VERBOSE_OPTION,
    VERBOSE_DOCTOR_OPTION,
    VERBOSE_OPTION,
)
from code_assistant_manager.cli.uninstall_commands import (
    NPM_PACKAGE_MAP,
    TOOL_CONFIG_DIRS,
    UninstallContext,
    uninstall,
)
# Lazy imports moved inside functions to improve startup time

logger = logging.getLogger(__name__)


# ============================================================================
# Private Helper Functions
# ============================================================================



def _get_config_manager(ctx: Context):
    # Lazy import
    from code_assistant_manager.config import ConfigManager
    
    # Return type hint for clarity
    
    """Get or create ConfigManager from context."""
    try:
        config_path = None
        if ctx and ctx.obj and hasattr(ctx.obj, "get"):
            config_path = ctx.obj.get("config_path")
        return ConfigManager(config_path) if config_path else ConfigManager()
    except Exception:
        return ConfigManager()


# ============================================================================
# Core Commands
# ============================================================================


def upgrade(
    ctx: Context,
    target: str = TARGET_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Upgrade CLI tools (alias: u). If not installed, will install.
    If installed, will try to upgrade."""
    from code_assistant_manager.cli.upgrade import handle_upgrade_command
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools import (
        display_all_tool_endpoints,
        display_tool_endpoints,
        get_registered_tools,
    )

    logger.debug(f"Upgrade command called with target: {target}")
    config_path = ctx.obj.get("config_path")
    logger.debug(f"Using config path for upgrade: {config_path}")

    # Initialize config
    try:
        config = ConfigManager(config_path)
        # Validate configuration
        is_valid, errors = config.validate_config()
        if not is_valid:
            logger.error(f"Configuration validation errors during upgrade: {errors}")
            typer.echo("Configuration validation errors:")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        logger.debug("Configuration validated for upgrade")
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found during upgrade: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e

    # Handle --endpoints option if specified
    endpoints = ctx.obj.get("endpoints")
    if endpoints:
        logger.debug(f"Handling endpoints option in upgrade: {endpoints}")
        if endpoints == "all":
            display_all_tool_endpoints(config)
        else:
            display_tool_endpoints(config, endpoints)
        raise typer.Exit()

    registered_tools = get_registered_tools()
    logger.debug(f"Starting upgrade process for target: {target}")
    # By default run quietly; verbose flag overrides to show installer output
    sys.exit(handle_upgrade_command(target, registered_tools, config, verbose=verbose))


@app.command()
def doctor(
    ctx: Context,
    verbose: bool = VERBOSE_DOCTOR_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Run diagnostic checks on the code-assistant-manager installation (alias: d)"""

    # Lazy imports
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools import display_all_tool_endpoints, display_tool_endpoints
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    from code_assistant_manager.cli.doctor import run_doctor_checks

    logger.debug(f"Doctor command called with verbose: {verbose}")
    config_path = ctx.obj.get("config_path")
    logger.debug(f"Using config path for doctor: {config_path}")

    # Initialize config
    try:
        config = ConfigManager(config_path)
        # Load environment variables from .env file
        config.load_env_file()
        # Validate configuration
        is_valid, errors = config.validate_config()
        if not is_valid:
            logger.error(f"Configuration validation errors in doctor: {errors}")
            typer.echo("Configuration validation errors:")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        logger.debug("Configuration loaded and validated for doctor")
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found in doctor: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e

    # Handle --endpoints option if specified
    endpoints = ctx.obj.get("endpoints")
    if endpoints:
        logger.debug(f"Handling endpoints option in doctor: {endpoints}")
        if endpoints == "all":
            display_all_tool_endpoints(config)
        else:
            display_tool_endpoints(config, endpoints)
        raise typer.Exit()

    # Run diagnostic checks
    logger.debug("Starting diagnostic checks")
    return run_doctor_checks(config, verbose)


def launch_alias(ctx: Context, tool_name: str = TOOL_NAME_OPTION):
    """Alias for 'launch' command."""

    # Lazy imports
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools import get_registered_tools
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = None
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    if tool_name:
        # Direct tool invocation - same as main() function does
        registered_tools = get_registered_tools()
        if tool_name in registered_tools and tool_name != "mcp":
            config_path = ctx.obj.get("config_path")
            # Get any extra args passed after the tool name
            tool_args = ctx.args if hasattr(ctx, 'args') else []
            try:
                config = ConfigManager(config_path)
                is_valid, errors = config.validate_config()
                if not is_valid:
                    typer.echo("Configuration validation errors:")
                    for error in errors:
                        typer.echo(f"  - {error}")
                    return 1
                tool_class = registered_tools.get(tool_name)
                tool = tool_class(config)
                return tool.run(tool_args)
            except Exception as e:
                from code_assistant_manager.exceptions import create_error_handler

                error_handler = create_error_handler("cli")
                structured_error = error_handler(e, "Tool execution failed")
                typer.echo(structured_error.get_detailed_message())
                return 1
        else:
            typer.echo(f"Unknown tool: {tool_name}")
            return 1
    else:
        # Show interactive menu for tool selection
        from code_assistant_manager.menu.menus import display_centered_menu

        logger.debug("No tool specified in 'l' alias, showing interactive menu")
        registered_tools = get_registered_tools()
        editor_tools = {k: v for k, v in registered_tools.items() if k not in ["mcp"]}
        tool_names = sorted(editor_tools.keys())

        logger.debug(f"Available tools for menu: {tool_names}")

        success, selected_idx = display_centered_menu(
            title="Select AI Code Editor", items=tool_names, cancel_text="Cancel"
        )

        if not success or selected_idx is None:
            logger.debug("User cancelled menu selection")
            raise typer.Exit(0)

        selected_tool = tool_names[selected_idx]
        logger.debug(f"User selected tool: {selected_tool}")

        # Get config and launch the selected tool
        config_path = ctx.obj.get("config_path")
        logger.debug(f"Using config path: {config_path}")

        try:
            config = ConfigManager(config_path)
            is_valid, errors = config.validate_config()
            if not is_valid:
                logger.error(f"Configuration validation errors: {errors}")
                typer.echo("Configuration validation errors:")
                for error in errors:
                    typer.echo(f"  - {error}")
                raise typer.Exit(1)
            logger.debug("Configuration loaded and validated successfully")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            typer.echo(f"Error: {e}")
            raise typer.Exit(1) from e

        tool_class = editor_tools[selected_tool]
        tool_instance = tool_class(config)
        sys.exit(tool_instance.run([]))


# ============================================================================
# Command Wrappers (registered with Typer app)
# ============================================================================


@app.command("upgrade")
def upgrade_command(
    ctx: Context,
    target: str = TARGET_OPTION,
    verbose: bool = VERBOSE_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Upgrade CLI tools (alias: u). If not installed, will install."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade(ctx, target, verbose)


@app.command("u", hidden=True)
def upgrade_alias_cmd(
    ctx: Context,
    target: str = UPGRADE_ALIAS_TARGET_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Alias for 'upgrade' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade(ctx, target)


@app.command("install")
def install_command(
    ctx: Context,
    target: str = TARGET_OPTION,
    verbose: bool = VERBOSE_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Install CLI tools (alias: i). Same as upgrade - if not installed, will install. If installed, will try to upgrade."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade(ctx, target, verbose)


@app.command("i", hidden=True)
def install_alias_cmd(
    ctx: Context,
    target: str = INSTALL_ALIAS_TARGET_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Alias for 'install' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade(ctx, target)


@app.command("uninstall")
def uninstall_command(
    ctx: Context,
    target: str = UNINSTALL_TARGET_OPTION,
    force: bool = FORCE_OPTION,
    keep_config: bool = KEEP_CONFIG_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Uninstall CLI tools and backup their configuration files."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return uninstall(ctx, target, force, keep_config)


@app.command("version")
def version_command():
    """Show version information."""
    from code_assistant_manager import __version__

    typer.echo(f"code-assistant-manager version {__version__}")
    raise typer.Exit()


@app.command("v", hidden=True)
def version_alias():
    """Alias for 'version' command."""
    return version_command()


@app.command("un", hidden=True)
def uninstall_alias(
    ctx: Context,
    target: str = UNINSTALL_TARGET_OPTION,
    force: bool = FORCE_OPTION,
    keep_config: bool = KEEP_CONFIG_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Alias for 'uninstall' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return uninstall(ctx, target, force, keep_config)


@app.command("d", hidden=True)
def doctor_alias(
    ctx: Context,
    verbose: bool = VERBOSE_DOCTOR_OPTION,
    config: Optional[str] = CONFIG_FILE_OPTION,
):
    """Alias for 'doctor' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return doctor(ctx, verbose, config)


# ============================================================================
# Utility Functions
# ============================================================================


def install(
    ctx: Context,
    target: str = TARGET_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Install CLI tools (alias: i). Same as upgrade - if not installed, will install. If installed, will try to upgrade."""
    return upgrade(ctx, target, verbose)


def upgrade_alias_fn(ctx: Context, target: str = UPGRADE_ALIAS_TARGET_OPTION):
    """Alias for 'upgrade' command."""
    return upgrade(ctx, target)


def install_alias_fn(ctx: Context, target: str = INSTALL_ALIAS_TARGET_OPTION):
    """Alias for 'install' command."""
    return install(ctx, target)


def validate_config(
    config: Optional[str] = CONFIG_FILE_OPTION,
    verbose: bool = VALIDATE_VERBOSE_OPTION,
):
    """Validate the configuration file for syntax and semantic errors."""

    # Lazy imports
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.menu.base import Colors
    try:
        cm = ConfigManager(config)
        typer.echo(
            f"{Colors.GREEN}✓ Configuration file loaded successfully{Colors.RESET}"
        )

        # Run full validation
        is_valid, errors = cm.validate_config()

        if is_valid:
            typer.echo(f"{Colors.GREEN}✓ Configuration validation passed{Colors.RESET}")
            return 0
        else:
            typer.echo(f"{Colors.RED}✗ Configuration validation failed:{Colors.RESET}")
            for error in errors:
                typer.echo(f"  - {error}")
            return 1

    except FileNotFoundError as e:
        typer.echo(f"{Colors.RED}✗ Configuration file not found: {e}{Colors.RESET}")
        return 1
    except ValueError as e:
        typer.echo(f"{Colors.RED}✗ Configuration validation failed: {e}{Colors.RESET}")
        return 1
    except Exception as e:
        typer.echo(
            f"{Colors.RED}✗ Unexpected error during validation: {e}{Colors.RESET}"
        )
        return 1


__all__ = [
    "app",
    "doctor",
    "upgrade",
    "install",
    "uninstall",
    "launch_alias",
    "validate_config",
    "completion",
    "generate_completion_script",
    "TOOL_CONFIG_DIRS",
    "NPM_PACKAGE_MAP",
    "UninstallContext",
]
