"""Plugin installation commands.

Handles install, uninstall, enable, disable, and validate operations.
"""

import logging
from typing import Optional

import typer

from code_assistant_manager.cli.option_utils import resolve_single_app
from code_assistant_manager.menu.base import Colors
from code_assistant_manager.plugins import VALID_APP_TYPES, get_handler
from code_assistant_manager.plugins.base import BasePluginHandler

logger = logging.getLogger(__name__)

plugin_app = typer.Typer(
    help="Manage plugins and marketplaces for AI assistants (Claude, CodeBuddy)",
    no_args_is_help=True,
)


def _get_handler(app_type: str = "claude") -> BasePluginHandler:
    """Get plugin handler instance for the specified app type."""
    return get_handler(app_type)


def _check_app_cli(app_type: str = "claude"):
    """Check if app CLI is available."""
    handler = _get_handler(app_type)
    if not handler.get_cli_path():
        typer.echo(
            f"{Colors.RED}✗ {app_type.capitalize()} CLI not found. Please install {app_type.capitalize()} first.{Colors.RESET}"
        )
        raise typer.Exit(1)


def _set_plugin_enabled(handler, plugin: str, enabled: bool) -> bool:
    """Set a plugin's enabled state in Claude's settings.json.

    Args:
        handler: Claude plugin handler
        plugin: Plugin name (with or without @marketplace suffix)
        enabled: True to enable, False to disable

    Returns:
        True if plugin was found and updated, False otherwise
    """
    import json

    settings_file = handler.settings_file
    if not settings_file.exists():
        return False

    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
    except Exception:
        return False

    enabled_plugins = settings.get("enabledPlugins", {})

    # Find matching plugin key
    plugin_lower = plugin.lower()
    matching_key = None
    for key in enabled_plugins:
        key_name = key.split("@")[0] if "@" in key else key
        if key.lower() == plugin_lower or key_name.lower() == plugin_lower:
            matching_key = key
            break

    if not matching_key:
        return False

    # Update the enabled state
    enabled_plugins[matching_key] = enabled
    settings["enabledPlugins"] = enabled_plugins

    # Write back
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


@plugin_app.command("install")
def install_plugin(
    plugin: str = typer.Argument(
        ...,
        help="Plugin name or plugin@marketplace. Examples: 'code-reviewer' or 'code-reviewer@awesome-plugins'",
    ),
    marketplace: Optional[str] = typer.Option(
        None,
        "--marketplace",
        "-m",
        help="Marketplace name (alternative to plugin@marketplace format)",
    ),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type to install to ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Install a plugin from available marketplaces.

    Installs a plugin to Claude or CodeBuddy from configured marketplaces.
    The plugin can be specified as:
    - plugin-name (searches all configured marketplaces)
    - plugin-name@marketplace-name (specifies which marketplace to use)

    For marketplace management, use 'cam plugin marketplace install <marketplace>'.
    For browsing available plugins, use 'cam plugin browse'.

    Examples:
        cam plugin install code-reviewer
        cam plugin install code-reviewer@awesome-plugins
        cam plugin install --marketplace awesome-plugins code-reviewer
    """
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    plugin_ref = f"{plugin}@{marketplace}" if marketplace else plugin
    typer.echo(f"{Colors.CYAN}Installing plugin: {plugin_ref}...{Colors.RESET}")

    success, msg = handler.install_plugin(plugin, marketplace)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        typer.echo(
            f"\n{Colors.YELLOW}Note: Restart Claude Code to load the new plugin.{Colors.RESET}"
        )
    else:
        typer.echo(f"{Colors.RED}✗ {msg}{Colors.RESET}")
        raise typer.Exit(1)


@plugin_app.command("uninstall")
def uninstall_plugin(
    plugin: str = typer.Argument(..., help="Plugin name to uninstall"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type to uninstall from ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Uninstall an installed plugin.

    For marketplace plugins, this removes the plugin from enabled plugins settings.
    For standalone plugins, this uses the app's CLI to fully uninstall.
    """
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    if not force:
        typer.confirm(f"Uninstall plugin '{plugin}'?", abort=True)

    typer.echo(f"{Colors.CYAN}Uninstalling plugin: {plugin}...{Colors.RESET}")
    success, msg = handler.uninstall_plugin(plugin)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        typer.echo(
            f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
        )
    else:
        # Claude CLI failed - try to remove from settings directly
        # This handles marketplace plugins which can't be "uninstalled" via CLI
        typer.echo(
            f"{Colors.YELLOW}Claude CLI uninstall failed, trying to remove from settings...{Colors.RESET}"
        )

        removed = _remove_plugin_from_settings(handler, plugin)
        if removed:
            typer.echo(
                f"{Colors.GREEN}✓ Removed '{plugin}' from enabled plugins{Colors.RESET}"
            )
            typer.echo(
                f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
            )
        else:
            typer.echo(
                f"{Colors.RED}✗ Plugin '{plugin}' not found in settings{Colors.RESET}"
            )
            raise typer.Exit(1)


def _remove_plugin_from_settings(handler, plugin: str) -> bool:
    """Remove a plugin from Claude's settings.json.

    Args:
        handler: Claude plugin handler
        plugin: Plugin name (with or without @marketplace suffix)

    Returns:
        True if plugin was found and removed, False otherwise
    """
    import json

    settings_file = handler.settings_file
    if not settings_file.exists():
        return False

    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
    except Exception:
        return False

    enabled = settings.get("enabledPlugins", {})
    if not enabled:
        return False

    # Find matching plugin key(s)
    keys_to_remove = []
    plugin_lower = plugin.lower()
    for key in enabled:
        # Match exact key or plugin name part (before @)
        key_name = key.split("@")[0] if "@" in key else key
        if key.lower() == plugin_lower or key_name.lower() == plugin_lower:
            keys_to_remove.append(key)

    if not keys_to_remove:
        return False

    # Remove the plugin(s)
    for key in keys_to_remove:
        del enabled[key]

    settings["enabledPlugins"] = enabled

    # Write back
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


@plugin_app.command("enable")
def enable_plugin(
    plugin: str = typer.Argument(..., help="Plugin name to enable"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Enable a disabled plugin."""
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    typer.echo(f"{Colors.CYAN}Enabling plugin: {plugin}...{Colors.RESET}")
    success, msg = handler.enable_plugin(plugin)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        typer.echo(
            f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
        )
    else:
        # Claude CLI failed - try to enable in settings directly
        typer.echo(
            f"{Colors.YELLOW}Claude CLI enable failed, trying to update settings...{Colors.RESET}"
        )

        enabled = _set_plugin_enabled(handler, plugin, True)
        if enabled:
            typer.echo(f"{Colors.GREEN}✓ Enabled '{plugin}' in settings{Colors.RESET}")
            typer.echo(
                f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
            )
        else:
            typer.echo(
                f"{Colors.RED}✗ Plugin '{plugin}' not found in settings{Colors.RESET}"
            )
            raise typer.Exit(1)


@plugin_app.command("disable")
def disable_plugin(
    plugin: str = typer.Argument(..., help="Plugin name to disable"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Disable an enabled plugin."""
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    typer.echo(f"{Colors.CYAN}Disabling plugin: {plugin}...{Colors.RESET}")
    success, msg = handler.disable_plugin(plugin)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        typer.echo(
            f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
        )
    else:
        # Claude CLI failed - try to disable in settings directly
        typer.echo(
            f"{Colors.YELLOW}Claude CLI disable failed, trying to update settings...{Colors.RESET}"
        )

        disabled = _set_plugin_enabled(handler, plugin, False)
        if disabled:
            typer.echo(f"{Colors.GREEN}✓ Disabled '{plugin}' in settings{Colors.RESET}")
            typer.echo(
                f"\n{Colors.YELLOW}Note: Restart Claude Code to apply changes.{Colors.RESET}"
            )
        else:
            typer.echo(
                f"{Colors.RED}✗ Plugin '{plugin}' not found in settings{Colors.RESET}"
            )
            raise typer.Exit(1)


@plugin_app.command("validate")
def validate_plugin(
    path: str = typer.Argument(..., help="Path to plugin or marketplace to validate"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Validate a plugin or marketplace manifest."""
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    typer.echo(f"{Colors.CYAN}Validating: {path}...{Colors.RESET}")
    success, msg = handler.validate_plugin(path)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
    else:
        typer.echo(f"{Colors.RED}✗ {msg}{Colors.RESET}")
        raise typer.Exit(1)
