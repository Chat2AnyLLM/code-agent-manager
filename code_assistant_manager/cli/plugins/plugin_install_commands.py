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
    """Check if app CLI is available when required by the handler."""
    handler = _get_handler(app_type)
    if getattr(handler, "uses_cli_plugin_commands", False) and not handler.get_cli_path():
        typer.echo(
            f"{Colors.RED}✗ {app_type.capitalize()} CLI not found. Please install {app_type.capitalize()} first.{Colors.RESET}"
        )
        raise typer.Exit(1)


def _resolve_plugin_conflict(plugin_name: str, app_type: str) -> str:
    """Resolve plugin name conflicts across marketplaces.

    Args:
        plugin_name: Name of the plugin to resolve
        app_type: The app type (claude, codebuddy, etc.)

    Returns:
        The marketplace name to use, or raises typer.Exit if not found
    """
    from code_assistant_manager.plugins import PluginManager

    manager = PluginManager()
    handler = _get_handler(app_type)

    # Search all configured marketplaces for this plugin
    found_in_marketplaces = []

    # Check configured marketplaces in CAM
    all_repos = manager.get_all_repos()
    configured_marketplaces = {
        k: v for k, v in all_repos.items() if v.type == "marketplace"
    }

    # Check configured marketplaces for the plugin
    found_in_marketplaces = []
    unreachable_marketplaces = []

    for marketplace_name, repo in configured_marketplaces.items():
        # Handle both PluginRepo objects and installed marketplace dictionaries
        if hasattr(repo, 'repo_owner'):  # PluginRepo object
            repo_owner = repo.repo_owner
            repo_name = repo.repo_name
            repo_branch = repo.repo_branch or "main"
        elif isinstance(repo, dict) and 'source' in repo:  # Installed marketplace dict
            # Skip installed marketplaces - we'll handle them separately
            continue
        else:
            continue

        if not repo_owner or not repo_name:
            continue

        try:
            from code_assistant_manager.plugins.fetch import fetch_repo_info
            info = fetch_repo_info(repo_owner, repo_name, repo_branch)
            if info and info.plugins:
                for plugin in info.plugins:
                    if plugin.get("name", "").lower() == plugin_name.lower():
                        found_in_marketplaces.append({
                            "marketplace": marketplace_name,
                            "plugin": plugin,
                            "source": f"github.com/{repo_owner}/{repo_name}",
                            "available": True
                        })
                        break
        except Exception as e:
            # Log the error but don't skip the marketplace entirely
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to fetch marketplace '{marketplace_name}': {e}")
            # Mark marketplace as unreachable but still show it
            unreachable_marketplaces.append({
                "marketplace": marketplace_name,
                "source": f"github.com/{repo_owner}/{repo_name}",
                "error": str(e),
                "available": False
            })

    # Handle results
    if not found_in_marketplaces:
        typer.echo(
            f"{Colors.RED}✗ Plugin '{plugin_name}' not found in any configured marketplace.{Colors.RESET}"
        )
        typer.echo(f"\n{Colors.CYAN}Available marketplaces:{Colors.RESET}")
        for name in sorted(configured_marketplaces.keys()):
            typer.echo(f"  • {name}")
        # Show unreachable marketplaces if any
        if unreachable_marketplaces:
            typer.echo(f"\n{Colors.YELLOW}Unreachable marketplaces (temporarily unavailable):{Colors.RESET}")
            for unreachable in unreachable_marketplaces:
                typer.echo(f"  • {unreachable['marketplace']} ({unreachable['source']})")
        typer.echo(f"\n{Colors.CYAN}Browse plugins:{Colors.RESET} cam plugin list")
        raise typer.Exit(1)

    elif len(found_in_marketplaces) == 1:
        # Only one marketplace has this plugin - use it
        marketplace = found_in_marketplaces[0]["marketplace"]
        typer.echo(
            f"{Colors.CYAN}Found '{plugin_name}' in marketplace '{marketplace}'{Colors.RESET}"
        )
        return marketplace

    else:
        # Multiple marketplaces have this plugin - prompt user to choose
        typer.echo(
            f"{Colors.YELLOW}⚠ Plugin '{plugin_name}' found in multiple marketplaces:{Colors.RESET}"
        )
        typer.echo()

        # Combine available and unreachable marketplaces for display
        all_marketplaces = found_in_marketplaces + unreachable_marketplaces

        for i, found in enumerate(all_marketplaces, 1):
            marketplace = found["marketplace"]
            source = found["source"]
            plugin_info = found.get("plugin", {})
            available = found.get("available", True)
            version = plugin_info.get("version", "")
            description = plugin_info.get("description", "")

            status_indicator = "" if available else f" {Colors.YELLOW}(unreachable){Colors.RESET}"
            typer.echo(f"  {i}. {Colors.BOLD}{marketplace}{Colors.RESET}{status_indicator}")
            if version:
                typer.echo(f"     Version: {version}")
            if description:
                typer.echo(f"     Description: {description[:60]}{'...' if len(description) > 60 else ''}")
            typer.echo(f"     Source: {source}")
            typer.echo()

        # Prompt user to choose (only allow selecting available marketplaces)
        available_marketplaces = [f for f in all_marketplaces if f.get("available", True)]
        while True:
            try:
                choice = typer.prompt(
                    f"Choose marketplace (1-{len(all_marketplaces)}) or 'cancel'",
                    type=str
                ).strip().lower()

                if choice == "cancel":
                    raise typer.Exit(0)

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(all_marketplaces):
                    selected = all_marketplaces[choice_idx]
                    if not selected.get("available", True):
                        typer.echo(
                            f"{Colors.RED}Cannot select unreachable marketplace '{selected['marketplace']}'. Please choose an available marketplace.{Colors.RESET}"
                        )
                        continue

                    marketplace = selected["marketplace"]
                    typer.echo(
                        f"{Colors.GREEN}Selected: {marketplace}{Colors.RESET}"
                    )
                    return marketplace
                else:
                    typer.echo(
                        f"{Colors.RED}Invalid choice. Please enter 1-{len(all_marketplaces)} or 'cancel'{Colors.RESET}"
                    )
            except ValueError:
                typer.echo(
                    f"{Colors.RED}Invalid input. Please enter a number 1-{len(all_marketplaces)} or 'cancel'{Colors.RESET}"
                )
            except (EOFError, KeyboardInterrupt):
                typer.echo(f"\n{Colors.YELLOW}Cancelled.{Colors.RESET}")
                raise typer.Exit(0)


def _resolve_installed_plugin_conflict(plugin_name: str, app_type: str, handler) -> Optional[str]:
    """Resolve conflicts when multiple installed plugins match a name.

    Args:
        plugin_name: Name of the plugin to resolve
        app_type: The app type (claude, codebuddy, etc.)
        handler: The plugin handler

    Returns:
        The marketplace name, or None for standalone plugins, or raises typer.Exit
    """
    # Get all enabled plugins
    enabled_plugins = handler.get_enabled_plugins()

    # Find plugins that match the name
    matching_plugins = []
    for plugin_key, enabled in enabled_plugins.items():
        if not enabled:
            continue

        # Parse plugin key to extract name and marketplace
        if ":" in plugin_key:
            marketplace, name = plugin_key.split(":", 1)
        elif "@" in plugin_key:
            name, marketplace = plugin_key.split("@", 1)
        else:
            name = plugin_key
            marketplace = None

        if name.lower() == plugin_name.lower():
            matching_plugins.append({
                "key": plugin_key,
                "name": name,
                "marketplace": marketplace,
                "display_name": f"{marketplace}:{name}" if marketplace else name
            })

    # Handle results
    if not matching_plugins:
        typer.echo(
            f"{Colors.RED}✗ Plugin '{plugin_name}' is not installed.{Colors.RESET}"
        )
        typer.echo(f"\n{Colors.CYAN}Check installed plugins:{Colors.RESET} cam plugin status")
        raise typer.Exit(1)

    elif len(matching_plugins) == 1:
        # Only one matching plugin - use it
        plugin = matching_plugins[0]
        typer.echo(
            f"{Colors.CYAN}Found installed plugin: {plugin['display_name']}{Colors.RESET}"
        )
        return plugin["marketplace"]

    else:
        # Multiple matching plugins - prompt user to choose
        typer.echo(
            f"{Colors.YELLOW}⚠ Multiple plugins with name '{plugin_name}' are installed:{Colors.RESET}"
        )
        typer.echo()

        for i, plugin in enumerate(matching_plugins, 1):
            typer.echo(f"  {i}. {Colors.BOLD}{plugin['display_name']}{Colors.RESET}")
            typer.echo()

        # Prompt user to choose
        while True:
            try:
                choice = typer.prompt(
                    f"Choose plugin to uninstall (1-{len(matching_plugins)}) or 'cancel'",
                    type=str
                ).strip().lower()

                if choice == "cancel":
                    raise typer.Exit(0)

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(matching_plugins):
                    selected = matching_plugins[choice_idx]
                    typer.echo(
                        f"{Colors.GREEN}Selected: {selected['display_name']}{Colors.RESET}"
                    )
                    return selected["marketplace"]
                else:
                    typer.echo(
                        f"{Colors.RED}Invalid choice. Please enter 1-{len(matching_plugins)} or 'cancel'{Colors.RESET}"
                    )
            except ValueError:
                typer.echo(
                    f"{Colors.RED}Invalid input. Please enter a number 1-{len(matching_plugins)} or 'cancel'{Colors.RESET}"
                )
            except (EOFError, KeyboardInterrupt):
                typer.echo(f"\n{Colors.YELLOW}Cancelled.{Colors.RESET}")
                raise typer.Exit(0)


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
        help="Plugin name or marketplace:plugin-name. Examples: 'code-reviewer' or 'awesome-plugins:code-reviewer'",
    ),
    marketplace: Optional[str] = typer.Option(
        None,
        "--marketplace",
        "-m",
        help="Marketplace name (alternative to marketplace:plugin-name format)",
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
    - marketplace-name:plugin-name (specifies which marketplace to use)

    For marketplace management, use 'cam plugin marketplace install <marketplace>'.
    For browsing available plugins, use 'cam plugin list'.

    Examples:
        cam plugin install code-reviewer
        cam plugin install awesome-plugins:code-reviewer
        cam plugin install --marketplace awesome-plugins code-reviewer
    """
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    _check_app_cli(app)
    handler = _get_handler(app)

    # Parse plugin reference: marketplace:plugin or plugin
    if ":" in plugin and not marketplace:
        marketplace, plugin = plugin.split(":", 1)
    elif "@" in plugin and not marketplace:
        # Support legacy @ syntax for backward compatibility
        plugin, marketplace = plugin.split("@", 1)

    # If no marketplace specified, check for conflicts across marketplaces
    if not marketplace:
        marketplace = _resolve_plugin_conflict(plugin, app)

    # Use @ syntax for Claude CLI compatibility, but show : syntax in output
    plugin_ref = f"{plugin}@{marketplace}" if marketplace else plugin
    display_ref = f"{marketplace}:{plugin}" if marketplace else plugin
    typer.echo(f"{Colors.CYAN}Installing plugin: {display_ref}...{Colors.RESET}")

    if getattr(handler, "uses_cli_plugin_commands", False):
        success, msg = handler.install_plugin(plugin, marketplace)
    else:
        # Install directly from CAM-configured marketplace (no app CLI required)
        from code_assistant_manager.plugins import PluginManager
        from code_assistant_manager.plugins.fetch import fetch_repo_info

        manager = PluginManager()
        repo = manager.get_repo(marketplace) if marketplace else None
        if not repo or not repo.repo_owner or not repo.repo_name:
            typer.echo(
                f"{Colors.RED}✗ Marketplace '{marketplace}' not found in CAM configuration.{Colors.RESET}"
            )
            raise typer.Exit(1)

        info = fetch_repo_info(repo.repo_owner, repo.repo_name, repo.repo_branch or "main")
        if not info or not info.plugins:
            typer.echo(
                f"{Colors.RED}✗ Could not fetch plugins from marketplace '{marketplace}'.{Colors.RESET}"
            )
            raise typer.Exit(1)

        match = next(
            (p for p in info.plugins if p.get("name", "").lower() == plugin.lower()),
            None,
        )
        plugin_path = None
        source = match.get("source") if isinstance(match, dict) else None
        if isinstance(source, str):
            plugin_path = source.lstrip("./")
        elif isinstance(source, dict):
            plugin_path = source.get("path") or source.get("dir")

        if not plugin_path:
            plugin_path = f"plugins/{plugin}"

        try:
            handler.install_from_github(
                repo.repo_owner,
                repo.repo_name,
                repo.repo_branch or "main",
                plugin_path=plugin_path,
                marketplace_name=marketplace,
            )
            success, msg = True, f"Plugin installed: {display_ref}"
        except Exception as e:
            success, msg = False, str(e)

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

    # Parse plugin reference: marketplace:plugin or plugin
    marketplace = None
    if ":" in plugin:
        marketplace, plugin = plugin.split(":", 1)
    elif "@" in plugin:
        # Support legacy @ syntax for backward compatibility
        plugin, marketplace = plugin.split("@", 1)

    # If no marketplace specified, check which installed plugins match this name
    if not marketplace:
        marketplace = _resolve_installed_plugin_conflict(plugin, app, handler)

    if not force:
        display_name = f"{marketplace}:{plugin}" if marketplace else plugin
        typer.confirm(f"Uninstall plugin '{display_name}'?", abort=True)

    display_name = f"{marketplace}:{plugin}" if marketplace else plugin
    typer.echo(f"{Colors.CYAN}Uninstalling plugin: {display_name}...{Colors.RESET}")
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
        # Match exact key or plugin name part (before @ or after :)
        if "@" in key:
            key_name = key.split("@")[0]
        elif ":" in key:
            key_name = key.split(":")[-1]  # Take the part after the last colon
        else:
            key_name = key

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
