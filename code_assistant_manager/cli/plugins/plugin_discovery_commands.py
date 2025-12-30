"""Plugin discovery commands.

Handles browse, view, fetch, and info operations.
"""

import logging
from typing import Optional

import typer

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.plugins import (
    VALID_APP_TYPES,
    PluginManager,
    get_handler,
    parse_github_url,
)

logger = logging.getLogger(__name__)

plugin_app = typer.Typer(
    help="Manage plugins and marketplaces for AI assistants (Claude, CodeBuddy)",
    no_args_is_help=True,
)


def _filter_plugins(
    plugins: list[dict],
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Filter plugins by query string and/or category."""
    result = plugins

    if query:
        query_lower = query.lower()
        result = [
            p
            for p in result
            if query_lower in p.get("name", "").lower()
            or query_lower in p.get("description", "").lower()
        ]

    if category:
        category_lower = category.lower()
        result = [p for p in result if category_lower in p.get("category", "").lower()]

    return result


def _display_plugin(plugin: dict) -> None:
    """Display a single plugin entry."""
    name = plugin.get("name", "unknown")
    version = plugin.get("version", "")
    desc = plugin.get("description", "")
    cat = plugin.get("category", "")

    version_str = f" v{version}" if version else ""
    cat_str = f" [{cat}]" if cat else ""

    typer.echo(
        f"  {Colors.BOLD}{name}{Colors.RESET}{version_str}{Colors.CYAN}{cat_str}{Colors.RESET}"
    )
    if desc:
        if len(desc) > 80:
            desc = desc[:77] + "..."
        typer.echo(f"    {desc}")


def _display_marketplace_header(
    info, query: Optional[str], category: Optional[str], total: int
) -> None:
    """Display marketplace info header."""
    typer.echo(
        f"\n{Colors.BOLD}{info.name}{Colors.RESET} - {info.description or 'No description'}"
    )
    if info.version:
        typer.echo(f"Version: {info.version}")
    typer.echo(f"Total plugins: {info.plugin_count}")
    if query or category:
        typer.echo(f"Matching: {total}")


def _display_marketplace_footer(info, marketplace: str, total: int, limit: int) -> None:
    """Display marketplace footer with categories and install hint."""
    if total > limit:
        typer.echo(f"\n  ... and {total - limit} more")

    categories = {p.get("category") for p in info.plugins if p.get("category")}
    if categories:
        typer.echo(
            f"\n{Colors.CYAN}Categories:{Colors.RESET} {', '.join(sorted(categories))}"
        )

    typer.echo(
        f"\n{Colors.CYAN}Install with:{Colors.RESET} cam plugin install <marketplace>:<plugin-name>"
    )
    typer.echo()


def _display_marketplace_not_found(
    manager: PluginManager, handler, marketplace: str
) -> None:
    """Display error message when marketplace is not found."""
    typer.echo(
        f"{Colors.RED}✗ Marketplace '{marketplace}' not found in config or Claude.{Colors.RESET}"
    )
    typer.echo(f"\n{Colors.CYAN}Available repos:{Colors.RESET}")
    for name in manager.get_all_repos():
        typer.echo(f"  • {name}")
    typer.echo(f"\n{Colors.CYAN}Installed marketplaces:{Colors.RESET}")
    for name in handler.get_known_marketplaces():
        typer.echo(f"  • {name}")


def _resolve_marketplace_repo(
    manager: PluginManager, handler, marketplace: str
) -> tuple[Optional[str], Optional[str], str]:
    """Resolve marketplace name to repo owner/name/branch.

    Returns:
        Tuple of (repo_owner, repo_name, repo_branch) or (None, None, "main") if not found
    """
    repo = manager.get_repo(marketplace)

    if repo and repo.repo_owner and repo.repo_name:
        return repo.repo_owner, repo.repo_name, repo.repo_branch

    # Try app's known marketplaces as fallback
    return _resolve_from_known_marketplaces(handler, marketplace)


def _resolve_from_known_marketplaces(
    handler, marketplace: str
) -> tuple[Optional[str], Optional[str], str]:
    """Fallback resolution from app's known_marketplaces.json."""
    import json

    known_file = handler.known_marketplaces_file
    if not known_file.exists():
        return None, None, "main"

    try:
        with open(known_file, "r") as f:
            known = json.load(f)

        if marketplace not in known:
            return None, None, "main"

        source_url = known[marketplace].get("source", {}).get("url", "")
        if "github.com" not in source_url:
            return None, None, "main"

        parsed = parse_github_url(source_url)
        if parsed:
            return parsed
    except Exception:
        pass

    return None, None, "main"




@plugin_app.command("view")
def view_plugin(
    plugin: str = typer.Argument(
        ...,
        help="Plugin name to view (e.g., 'document-skills' or 'awesome-plugins:document-skills')",
    ),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """View detailed information about a specific plugin.

    Shows the plugin description, version, category, and source marketplace.
    You can specify just the plugin name or include the marketplace name
    with the : format (e.g., 'marketplace:plugin-name').
    """
    from code_assistant_manager.cli.option_utils import resolve_single_app
    from code_assistant_manager.plugins.fetch import fetch_repo_info

    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    manager = PluginManager()

    # Parse plugin name and marketplace if provided
    parts = plugin.split(":")
    plugin_name = parts[0]
    marketplace_filter = parts[1] if len(parts) > 1 else None

    # Support legacy @ syntax for backward compatibility
    if "@" in plugin_name and not marketplace_filter:
        plugin_name, marketplace_filter = plugin_name.split("@", 1)

    all_repos = manager.get_all_repos()
    if not all_repos:
        typer.echo(f"{Colors.YELLOW}No plugin repositories configured{Colors.RESET}")
        raise typer.Exit(1)

    # Search for the plugin
    found_plugin = None
    found_marketplace = None

    for repo_name, repo in all_repos.items():
        if marketplace_filter and repo_name.lower() != marketplace_filter.lower():
            continue

        if not repo.repo_owner or not repo.repo_name:
            continue

        # Fetch repo info
        info = fetch_repo_info(
            repo.repo_owner, repo.repo_name, repo.repo_branch or "main"
        )
        if not info:
            continue

        if info.type == "marketplace":
            # Search in marketplace plugins
            for p in info.plugins:
                if p.get("name", "").lower() == plugin_name.lower():
                    found_plugin = p
                    found_marketplace = repo_name
                    break
        else:
            # Check if this is the plugin
            if info.name.lower() == plugin_name.lower():
                found_plugin = {
                    "name": info.name,
                    "version": info.version or "1.0.0",
                    "description": info.description or "No description provided",
                    "category": "",
                    "source": info.plugin_path or "./",
                }
                found_marketplace = repo_name
                break

        if found_plugin:
            break

    if not found_plugin:
        typer.echo(
            f"{Colors.RED}✗ Plugin '{plugin}' not found in configured repositories{Colors.RESET}"
        )
        typer.echo()
        typer.echo(f"{Colors.CYAN}Try listing available plugins:{Colors.RESET}")
        if marketplace_filter:
            typer.echo(f"  cam plugin list {marketplace_filter}")
        else:
            typer.echo(f"  cam plugin list")
        raise typer.Exit(1)

    # Display plugin details
    typer.echo(f"\n{Colors.BOLD}{found_plugin.get('name', 'Unknown')}{Colors.RESET}")

    version = found_plugin.get("version")
    if version:
        typer.echo(f"{Colors.CYAN}Version:{Colors.RESET} {version}")

    category = found_plugin.get("category")
    if category:
        typer.echo(f"{Colors.CYAN}Category:{Colors.RESET} {category}")

    typer.echo(f"{Colors.CYAN}Marketplace:{Colors.RESET} {found_marketplace}")

    description = found_plugin.get("description")
    if description:
        typer.echo(f"\n{Colors.CYAN}Description:{Colors.RESET}")
        typer.echo(f"  {description}")

    source = found_plugin.get("source")
    if source:
        typer.echo(f"\n{Colors.CYAN}Source:{Colors.RESET} {source}")

    skills = found_plugin.get("skills")
    if skills:
        typer.echo(f"\n{Colors.CYAN}Skills:{Colors.RESET}")
        for skill in skills:
            typer.echo(f"  • {skill}")

    typer.echo()
    typer.echo(
        f"{Colors.CYAN}Install:{Colors.RESET} cam plugin install {found_marketplace}:{plugin_name}"
    )
    typer.echo()


@plugin_app.command("status")
def plugin_status(
    app_type: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)}). If not specified, shows status for all apps.",
    ),
):
    """Show plugin system status for an app, or all apps if none specified."""
    from code_assistant_manager.cli.option_utils import resolve_single_app

    # If no app specified, show status for all apps
    if app_type is None:
        typer.echo(f"\n{Colors.BOLD}Plugin System Status (All Apps):{Colors.RESET}\n")

        # Show common CAM configuration
        manager = PluginManager()
        all_repos = manager.get_all_repos()
        configured_marketplaces = {
            k: v for k, v in all_repos.items() if v.type == "marketplace"
        }
        configured_plugins = {k: v for k, v in all_repos.items() if v.type == "plugin"}

        typer.echo(
            f"{Colors.CYAN}Configured Marketplaces (CAM):{Colors.RESET} {len(configured_marketplaces)}"
        )
        for name, repo in sorted(configured_marketplaces.items()):
            if repo.repo_owner and repo.repo_name:
                typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
            else:
                typer.echo(f"  • {name}")

        if configured_plugins:
            typer.echo(
                f"\n{Colors.CYAN}Configured Plugins (CAM):{Colors.RESET} {len(configured_plugins)}"
            )
            for name, repo in sorted(configured_plugins.items()):
                if repo.repo_owner and repo.repo_name:
                    typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
                else:
                    typer.echo(f"  • {name}")

        typer.echo(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}\n")

        for app in VALID_APP_TYPES:
            show_app_info(app, show_cam_config=False)
            if app != VALID_APP_TYPES[-1]:  # Don't add separator after last app
                typer.echo(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}\n")
        return

    # Show info for specific app
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    show_app_info(app)


def show_app_info(app: str, show_cam_config: bool = True):
    """Show plugin system information for a specific app."""
    handler = get_handler(app)
    manager = PluginManager()

    typer.echo(f"\n{Colors.BOLD}{app.capitalize()} Plugin System:{Colors.RESET}\n")

    # Show paths
    typer.echo(f"{Colors.CYAN}Configuration:{Colors.RESET}")
    typer.echo(f"  Home: {handler.home_dir}")
    typer.echo(f"  Plugins: {handler.user_plugins_dir}")
    typer.echo(f"  Marketplaces: {handler.marketplaces_dir}")
    typer.echo(f"  Settings: {handler.settings_file}")

    # Check status
    typer.echo(f"\n{Colors.CYAN}Status:{Colors.RESET}")

    home_exists = handler.home_dir.exists()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}"
        if home_exists
        else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} Home directory exists")

    plugins_exists = handler.user_plugins_dir.exists()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}"
        if plugins_exists
        else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} Plugins directory exists")

    cli_path = handler.get_cli_path()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}" if cli_path else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} {app.capitalize()} CLI: {cli_path or 'Not found'}")

    # Get configured repos from CAM (only show once for all apps)
    all_repos = manager.get_all_repos()
    configured_marketplaces = {
        k: v for k, v in all_repos.items() if v.type == "marketplace"
    }
    configured_plugins = {k: v for k, v in all_repos.items() if v.type == "plugin"}

    # Show configured marketplaces (from CAM) - only when requested
    if show_cam_config and app == VALID_APP_TYPES[0]:  # Only show global config once
        typer.echo(
            f"\n{Colors.CYAN}Configured Marketplaces (CAM):{Colors.RESET} {len(configured_marketplaces)}"
        )
        for name, repo in sorted(configured_marketplaces.items()):
            if repo.repo_owner and repo.repo_name:
                typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
            else:
                typer.echo(f"  • {name}")

        # Show configured plugins (from CAM)
        if configured_plugins:
            typer.echo(
                f"\n{Colors.CYAN}Configured Plugins (CAM):{Colors.RESET} {len(configured_plugins)}"
            )
            for name, repo in sorted(configured_plugins.items()):
                if repo.repo_owner and repo.repo_name:
                    typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
                else:
                    typer.echo(f"  • {name}")

    # Show installed marketplaces (from app)
    installed_marketplaces = handler.get_known_marketplaces()
    typer.echo(
        f"\n{Colors.CYAN}Installed Marketplaces ({app.capitalize()}):{Colors.RESET} {len(installed_marketplaces)}"
    )
    for name, info in sorted(installed_marketplaces.items()):
        source = info.get("source", {})
        source_url = source.get("url", "")
        # Extract repo from URL like https://github.com/owner/repo.git
        if "github.com" in source_url:
            repo_part = source_url.replace("https://github.com/", "").replace(
                ".git", ""
            )
            typer.echo(f"  • {name} ({repo_part})")
        else:
            typer.echo(f"  • {name}")

    # Show installed/enabled plugins with details
    enabled = handler.get_enabled_plugins()
    enabled_plugins = {k: v for k, v in enabled.items() if v}
    disabled_plugins = {k: v for k, v in enabled.items() if not v}

    typer.echo(
        f"\n{Colors.CYAN}Installed Plugins ({app.capitalize()}):{Colors.RESET} {len(enabled_plugins)} enabled, {len(disabled_plugins)} disabled"
    )

    if enabled_plugins:
        typer.echo(f"\n  {Colors.GREEN}Enabled:{Colors.RESET}")
        for plugin_key in sorted(enabled_plugins.keys()):
            # Parse plugin key (format: marketplace:plugin-name or plugin-name)
            if ":" in plugin_key:
                marketplace, plugin_name = plugin_key.split(":", 1)
                typer.echo(
                    f"    {Colors.GREEN}✓{Colors.RESET} {plugin_name} ({marketplace})"
                )
            elif "@" in plugin_key:
                # Legacy @ syntax support
                plugin_name, marketplace = plugin_key.split("@", 1)
                typer.echo(
                    f"    {Colors.GREEN}✓{Colors.RESET} {plugin_name} ({marketplace})"
                )
            else:
                typer.echo(f"    {Colors.GREEN}✓{Colors.RESET} {plugin_key}")

    if disabled_plugins:
        typer.echo(f"\n  {Colors.RED}Disabled:{Colors.RESET}")
        for plugin_key in sorted(disabled_plugins.keys()):
            # Parse plugin key (format: marketplace:plugin-name or plugin-name)
            if ":" in plugin_key:
                marketplace, plugin_name = plugin_key.split(":", 1)
                typer.echo(
                    f"    {Colors.RED}✗{Colors.RESET} {plugin_name} ({marketplace})"
                )
            elif "@" in plugin_key:
                # Legacy @ syntax support
                plugin_name, marketplace = plugin_key.split("@", 1)
                typer.echo(
                    f"    {Colors.RED}✗{Colors.RESET} {plugin_name} ({marketplace})"
                )
            else:
                typer.echo(f"    {Colors.RED}✗{Colors.RESET} {plugin_key}")

    typer.echo()


@plugin_app.command("status")
def plugin_status(
    app_type: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)}). If not specified, shows status for all apps.",
    ),
):
    """Show plugin system status for an app, or all apps if none specified."""
    from code_assistant_manager.cli.option_utils import resolve_single_app

    # If no app specified, show status for all apps
    if app_type is None:
        typer.echo(f"\n{Colors.BOLD}Plugin System Status (All Apps):{Colors.RESET}\n")

        # Show common CAM configuration
        manager = PluginManager()
        all_repos = manager.get_all_repos()
        configured_marketplaces = {
            k: v for k, v in all_repos.items() if v.type == "marketplace"
        }
        configured_plugins = {k: v for k, v in all_repos.items() if v.type == "plugin"}

        typer.echo(
            f"{Colors.CYAN}Configured Marketplaces (CAM):{Colors.RESET} {len(configured_marketplaces)}"
        )
        for name, repo in sorted(configured_marketplaces.items()):
            if repo.repo_owner and repo.repo_name:
                typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
            else:
                typer.echo(f"  • {name}")

        if configured_plugins:
            typer.echo(
                f"\n{Colors.CYAN}Configured Plugins (CAM):{Colors.RESET} {len(configured_plugins)}"
            )
            for name, repo in sorted(configured_plugins.items()):
                if repo.repo_owner and repo.repo_name:
                    typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
                else:
                    typer.echo(f"  • {name}")

        typer.echo(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}\n")

        for app in VALID_APP_TYPES:
            show_app_info(app, show_cam_config=False)
            if app != VALID_APP_TYPES[-1]:  # Don't add separator after last app
                typer.echo(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}\n")
        return

    # Show info for specific app
    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    show_app_info(app)


def show_app_info(app: str, show_cam_config: bool = True):
    """Show plugin system information for a specific app."""
    handler = get_handler(app)
    manager = PluginManager()

    typer.echo(f"\n{Colors.BOLD}{app.capitalize()} Plugin System:{Colors.RESET}\n")

    # Show paths
    typer.echo(f"{Colors.CYAN}Configuration:{Colors.RESET}")
    typer.echo(f"  Home: {handler.home_dir}")
    typer.echo(f"  Plugins: {handler.user_plugins_dir}")
    typer.echo(f"  Marketplaces: {handler.marketplaces_dir}")
    typer.echo(f"  Settings: {handler.settings_file}")

    # Check status
    typer.echo(f"\n{Colors.CYAN}Status:{Colors.RESET}")

    home_exists = handler.home_dir.exists()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}"
        if home_exists
        else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} Home directory exists")

    plugins_exists = handler.user_plugins_dir.exists()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}"
        if plugins_exists
        else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} Plugins directory exists")

    cli_path = handler.get_cli_path()
    status = (
        f"{Colors.GREEN}✓{Colors.RESET}" if cli_path else f"{Colors.RED}✗{Colors.RESET}"
    )
    typer.echo(f"  {status} {app.capitalize()} CLI: {cli_path or 'Not found'}")

    # Get configured repos from CAM (only show once for all apps)
    all_repos = manager.get_all_repos()
    configured_marketplaces = {
        k: v for k, v in all_repos.items() if v.type == "marketplace"
    }
    configured_plugins = {k: v for k, v in all_repos.items() if v.type == "plugin"}

    # Show configured marketplaces (from CAM) - only when requested
    if show_cam_config and app == VALID_APP_TYPES[0]:  # Only show global config once
        typer.echo(
            f"\n{Colors.CYAN}Configured Marketplaces (CAM):{Colors.RESET} {len(configured_marketplaces)}"
        )
        for name, repo in sorted(configured_marketplaces.items()):
            if repo.repo_owner and repo.repo_name:
                typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
            else:
                typer.echo(f"  • {name}")

        # Show configured plugins (from CAM)
        if configured_plugins:
            typer.echo(
                f"\n{Colors.CYAN}Configured Plugins (CAM):{Colors.RESET} {len(configured_plugins)}"
            )
            for name, repo in sorted(configured_plugins.items()):
                if repo.repo_owner and repo.repo_name:
                    typer.echo(f"  • {name} ({repo.repo_owner}/{repo.repo_name})")
                else:
                    typer.echo(f"  • {name}")

    # Show installed marketplaces (from app)
    installed_marketplaces = handler.get_known_marketplaces()
    typer.echo(
        f"\n{Colors.CYAN}Installed Marketplaces ({app.capitalize()}):{Colors.RESET} {len(installed_marketplaces)}"
    )
    for name, info in sorted(installed_marketplaces.items()):
        source = info.get("source", {})
        source_url = source.get("url", "")
        # Extract repo from URL like https://github.com/owner/repo.git
        if "github.com" in source_url:
            repo_part = source_url.replace("https://github.com/", "").replace(
                ".git", ""
            )
            typer.echo(f"  • {name} ({repo_part})")
        else:
            typer.echo(f"  • {name}")

    # Show installed/enabled plugins with details
    enabled = handler.get_enabled_plugins()
    enabled_plugins = {k: v for k, v in enabled.items() if v}
    disabled_plugins = {k: v for k, v in enabled.items() if not v}

    typer.echo(
        f"\n{Colors.CYAN}Installed Plugins ({app.capitalize()}):{Colors.RESET} {len(enabled_plugins)} enabled, {len(disabled_plugins)} disabled"
    )

    if enabled_plugins:
        typer.echo(f"\n  {Colors.GREEN}Enabled:{Colors.RESET}")
        for plugin_key in sorted(enabled_plugins.keys()):
            # Parse plugin key (format: marketplace:plugin-name or plugin-name)
            if ":" in plugin_key:
                marketplace, plugin_name = plugin_key.split(":", 1)
                typer.echo(
                    f"    {Colors.GREEN}✓{Colors.RESET} {plugin_name} ({marketplace})"
                )
            elif "@" in plugin_key:
                # Legacy @ syntax support
                plugin_name, marketplace = plugin_key.split("@", 1)
                typer.echo(
                    f"    {Colors.GREEN}✓{Colors.RESET} {plugin_name} ({marketplace})"
                )
            else:
                typer.echo(f"    {Colors.GREEN}✓{Colors.RESET} {plugin_key}")

    if disabled_plugins:
        typer.echo(f"\n  {Colors.RED}Disabled:{Colors.RESET}")
        for plugin_key in sorted(disabled_plugins.keys()):
            # Parse plugin key (format: marketplace:plugin-name or plugin-name)
            if ":" in plugin_key:
                marketplace, plugin_name = plugin_key.split(":", 1)
                typer.echo(
                    f"    {Colors.RED}✗{Colors.RESET} {plugin_name} ({marketplace})"
                )
            elif "@" in plugin_key:
                # Legacy @ syntax support
                plugin_name, marketplace = plugin_key.split("@", 1)
                typer.echo(
                    f"    {Colors.RED}✗{Colors.RESET} {plugin_name} ({marketplace})"
                )
            else:
                typer.echo(f"    {Colors.RED}✗{Colors.RESET} {plugin_key}")

    typer.echo()
