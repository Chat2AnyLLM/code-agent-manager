"""Plugin management commands.

Handles list, repos, add-repo, and remove-repo operations.
"""

import logging
from typing import Optional

import typer

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.plugins import (
    VALID_APP_TYPES,
    PluginManager,
    PluginRepo,
)

logger = logging.getLogger(__name__)

plugin_app = typer.Typer(
    help="Manage plugins and marketplaces for AI assistants (Claude, CodeBuddy)",
    no_args_is_help=True,
)


@plugin_app.command("list")
def list_plugins(
    marketplace: Optional[str] = typer.Argument(
        None,
        help="Marketplace name to browse (from 'cam plugin repos'). If not specified, shows all plugins from all marketplaces.",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all plugins from marketplaces (not just enabled). Deprecated: use without marketplace argument instead.",
    ),
    app_type: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help=f"App type to show plugins for ({', '.join(VALID_APP_TYPES)}). Shows all apps if not specified.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Filter plugins by name or description",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter plugins by category",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of plugins to show",
    ),
):
    """List installed and available plugins from configured marketplaces.

    Without arguments: Shows installed plugins for all apps plus available plugins from all marketplaces.
    With marketplace name: Shows plugins from the specified marketplace.
    Use --query to search by name/description, --category to filter by category.
    """
    from code_assistant_manager.plugins import VALID_APP_TYPES, get_handler
    from code_assistant_manager.plugins.fetch import fetch_repo_info
    from code_assistant_manager.cli.plugins.plugin_discovery_commands import (
        _filter_plugins,
        _display_plugin,
        _display_marketplace_header,
        _display_marketplace_footer,
        _resolve_marketplace_repo,
        _display_marketplace_not_found,
    )

    # Handle marketplace-specific browsing (replaces browse functionality)
    if marketplace:
        from code_assistant_manager.cli.option_utils import resolve_single_app

        app = resolve_single_app(app_type or "claude", VALID_APP_TYPES, default="claude")
        manager = PluginManager()
        handler = get_handler(app)

        # Resolve marketplace to repo info
        repo_owner, repo_name, repo_branch = _resolve_marketplace_repo(
            manager, handler, marketplace
        )

        if not repo_owner or not repo_name:
            _display_marketplace_not_found(manager, handler, marketplace)
            raise typer.Exit(1)

        # Fetch plugins
        typer.echo(f"{Colors.CYAN}Fetching plugins from {marketplace}...{Colors.RESET}")
        info = fetch_repo_info(repo_owner, repo_name, repo_branch)

        if not info or not info.plugins:
            typer.echo(f"{Colors.RED}✗ Could not fetch plugins from repo.{Colors.RESET}")
            raise typer.Exit(1)

        # Filter and display
        plugins = _filter_plugins(info.plugins, query, category)
        total = len(plugins)
        plugins = plugins[:limit]

        _display_marketplace_header(info, query, category, total)
        typer.echo(f"\n{Colors.BOLD}Plugins:{Colors.RESET}\n")

        for plugin in plugins:
            _display_plugin(plugin)

        _display_marketplace_footer(info, marketplace, total, limit)
        return

    # Show both installed and available plugins (default behavior)
    if app_type:
        # Show plugins for specific app
        if app_type not in VALID_APP_TYPES:
            typer.echo(
                f"{Colors.RED}✗ Invalid app type: {app_type}. Valid: {', '.join(VALID_APP_TYPES)}{Colors.RESET}"
            )
            raise typer.Exit(1)

        handler = get_handler(app_type)
        _show_app_plugins(app_type, handler, True, query, category, limit)  # Always show available now
    else:
        # Show plugins for all apps plus available plugins
        manager = PluginManager()

        typer.echo(f"{Colors.BOLD}Plugin Status Across All Apps:{Colors.RESET}\n")

        apps_with_plugins = []
        for current_app in VALID_APP_TYPES:
            handler = get_handler(current_app)
            enabled_plugins = handler.get_enabled_plugins()
            if enabled_plugins:
                apps_with_plugins.append(current_app)
                _show_app_plugins(current_app, handler, True, query, category, limit, show_header=False)
                typer.echo()  # Add spacing between apps

        if not apps_with_plugins:
            typer.echo(f"{Colors.YELLOW}No plugins installed in any app.{Colors.RESET}")
            typer.echo(f"Use 'cam plugin install <plugin>' to install one.")

        # Show available plugins from all marketplaces
        _show_available_plugins(manager, query, category, limit)


def _show_app_plugins(app_name: str, handler, show_all: bool, query: Optional[str] = None, category: Optional[str] = None, limit: int = 50, show_header: bool = True):
    """Show plugins for a specific app."""
    # Get enabled plugins from settings
    enabled_plugins = handler.get_enabled_plugins()

    if show_header:
        typer.echo(f"{Colors.BOLD}{app_name.capitalize()} Plugins:{Colors.RESET}\n")

    if not enabled_plugins and not show_all:
        typer.echo(
            f"{Colors.YELLOW}No plugins installed for {app_name}. "
            f"Use 'cam plugin install <plugin> --app {app_name}' to install one.{Colors.RESET}"
        )
        return

    if enabled_plugins:
        if not show_header:
            typer.echo(f"{Colors.BOLD}{app_name.capitalize()}:{Colors.RESET}")
        for plugin_key, enabled in sorted(enabled_plugins.items()):
            # Extract plugin name from key (format: owner/repo:name or name@marketplace)
            if ":" in plugin_key:
                plugin_name = plugin_key.split(":")[-1]
            elif "@" in plugin_key:
                plugin_name = plugin_key.split("@")[0]
            else:
                plugin_name = plugin_key

            if enabled:
                status = f"{Colors.GREEN}✓ enabled{Colors.RESET}"
            else:
                status = f"{Colors.YELLOW}○ disabled{Colors.RESET}"

            typer.echo(f"  {status} {Colors.BOLD}{plugin_name}{Colors.RESET}")
            typer.echo(f"         {Colors.CYAN}Key:{Colors.RESET} {plugin_key}")
        typer.echo()

    if show_all:
        # Scan plugins from marketplaces
        plugins = handler.scan_marketplace_plugins()
        if plugins:
            # Apply filtering if specified
            if query or category:
                filtered_plugins = []
                for p in plugins:
                    # Convert Plugin object to dict for consistent filtering
                    plugin_dict = {
                        "name": p.name,
                        "description": p.description or "",
                        "category": getattr(p, 'category', '') if hasattr(p, 'category') else "",
                        "version": p.version,
                        "marketplace": p.marketplace,
                    }
                    # Apply filters
                    matches_query = (not query or
                                   query.lower() in plugin_dict["name"].lower() or
                                   query.lower() in plugin_dict["description"].lower())
                    matches_category = (not category or
                                      category.lower() in plugin_dict["category"].lower())

                    if matches_query and matches_category:
                        filtered_plugins.append(p)
                plugins = filtered_plugins

            # Apply limit
            plugins = plugins[:limit]

            typer.echo(
                f"{Colors.BOLD}Available Plugins from Marketplaces ({app_name}):{Colors.RESET}\n"
            )
            for plugin in sorted(plugins, key=lambda p: p.name):
                if plugin.installed:
                    status = f"{Colors.GREEN}✓{Colors.RESET}"
                else:
                    status = f"{Colors.CYAN}○{Colors.RESET}"

                typer.echo(
                    f"  {status} {Colors.BOLD}{plugin.name}{Colors.RESET} v{plugin.version}"
                )
                if plugin.description:
                    typer.echo(f"      {plugin.description[:80]}...")
                typer.echo(
                    f"      {Colors.CYAN}Marketplace:{Colors.RESET} {plugin.marketplace}"
                )
            typer.echo()


def _show_available_plugins(manager: PluginManager, query: Optional[str] = None, category: Optional[str] = None, limit: int = 50):
    """Show available plugins from all configured marketplaces."""
    from code_assistant_manager.plugins.fetch import fetch_repo_info
    from code_assistant_manager.cli.plugins.plugin_discovery_commands import _filter_plugins, _display_plugin
    import concurrent.futures
    import threading

    all_repos = manager.get_all_repos()
    if not all_repos:
        return

    typer.echo(f"{Colors.BOLD}Available Plugins from All Marketplaces:{Colors.RESET}")

    all_plugins = []
    repo_sources = {}  # Track which repo each plugin comes from

    # Thread-safe storage for results
    results_lock = threading.Lock()
    fetch_results = []

    def fetch_single_repo(repo_name: str, repo):
        """Fetch plugins from a single repository."""
        try:
            # Fetch repo info
            info = fetch_repo_info(
                repo.repo_owner, repo.repo_name, repo.repo_branch or "main"
            )
            if not info:
                return None

            result_data = {"repo_name": repo_name, "repo": repo, "info": info}
            return result_data
        except Exception as e:
            logger.warning(f"Failed to fetch from {repo_name}: {e}")
            return None

    # Use ThreadPoolExecutor for parallel fetching (5-10x speedup!)
    actual_workers = min(8, len(all_repos))  # Max 8 concurrent requests
    logger.debug(f"Fetching from {len(all_repos)} repositories with {actual_workers} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # Submit all fetch tasks
        future_to_repo = {
            executor.submit(fetch_single_repo, repo_name, repo): repo_name
            for repo_name, repo in all_repos.items()
            if repo.repo_owner and repo.repo_name
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_repo):
            result = future.result()
            if result:
                with results_lock:
                    fetch_results.append(result)

    # Process the results
    for result_data in fetch_results:
        repo_name = result_data["repo_name"]
        repo = result_data["repo"]
        info = result_data["info"]

        if info.type == "marketplace":
            # Add plugins from marketplace with their source
            for plugin in info.plugins:
                plugin["marketplace"] = repo_name
                repo_sources[f"{plugin.get('name', '')}@{repo_name}"] = repo_name
            all_plugins.extend(info.plugins)
        else:
            # Single plugin repository
            plugin_name = info.name
            all_plugins.append(
                {
                    "name": plugin_name,
                    "version": info.version or "",
                    "description": info.description or "",
                    "category": "",
                    "marketplace": repo_name,
                }
            )
            repo_sources[f"{plugin_name}@{repo_name}"] = repo_name

    if not all_plugins:
        typer.echo(f"  {Colors.YELLOW}No plugins found in configured repositories{Colors.RESET}")
        return

    # Filter and display
    plugins = _filter_plugins(all_plugins, query, category)
    total = len(plugins)
    plugins = plugins[:limit]

    if query or category:
        typer.echo(f"  Showing {len(plugins)} of {total} matching plugins\n")
    else:
        typer.echo(f"  Showing {len(plugins)} plugins\n")

    # Organize plugins by marketplace
    plugins_by_marketplace = {}
    for plugin in plugins:
        marketplace_name = plugin.get("marketplace", "Unknown")
        if marketplace_name not in plugins_by_marketplace:
            plugins_by_marketplace[marketplace_name] = []
        plugins_by_marketplace[marketplace_name].append(plugin)

    # Display plugins organized by marketplace
    displayed_count = 0
    for marketplace_name in sorted(plugins_by_marketplace.keys()):
        marketplace_plugins = plugins_by_marketplace[marketplace_name]
        typer.echo(f"{Colors.BOLD}{marketplace_name}:{Colors.RESET}")

        for plugin in marketplace_plugins:
            if displayed_count >= limit:
                break
            _display_plugin(plugin)
            displayed_count += 1

        if displayed_count >= limit:
            break

    if total > limit:
        typer.echo(f"\n  ... and {total - limit} more plugins")

    categories = {p.get("category") for p in all_plugins if p.get("category")}
    if categories:
        typer.echo(
            f"\n{Colors.CYAN}Categories:{Colors.RESET} {', '.join(sorted(categories))}"
        )

    typer.echo(
        f"\n{Colors.CYAN}Install with:{Colors.RESET} cam plugin install <marketplace>:<plugin-name>"
    )
    typer.echo()


@plugin_app.command("repos")
def list_repos():
    """List available plugin repositories and marketplaces (built-in + user)."""
    manager = PluginManager()

    # Get all repos (builtin + user)
    all_repos = manager.get_all_repos()
    user_repos = manager.get_user_repos()

    if not all_repos:
        typer.echo(f"{Colors.YELLOW}No plugin repositories available.{Colors.RESET}")
        typer.echo(
            f"\n{Colors.CYAN}Add a repo with:{Colors.RESET} cam plugin fetch <github-url> --save"
        )
        return

    # Separate plugins and marketplaces
    plugins = {k: v for k, v in all_repos.items() if v.type == "plugin"}
    marketplaces = {k: v for k, v in all_repos.items() if v.type == "marketplace"}

    def _print_repo(name: str, repo: PluginRepo, is_user: bool = False):
        status = (
            f"{Colors.GREEN}✓{Colors.RESET}"
            if repo.enabled
            else f"{Colors.RED}✗{Colors.RESET}"
        )
        user_tag = f" {Colors.YELLOW}(user){Colors.RESET}" if is_user else ""
        typer.echo(f"{status} {Colors.BOLD}{name}{Colors.RESET}{user_tag}")
        if repo.description:
            typer.echo(f"  {Colors.CYAN}Description:{Colors.RESET} {repo.description}")
        if repo.repo_owner and repo.repo_name:
            typer.echo(
                f"  {Colors.CYAN}Source:{Colors.RESET} github.com/{repo.repo_owner}/{repo.repo_name}"
            )
        typer.echo()

    if plugins:
        typer.echo(f"\n{Colors.BOLD}Plugins:{Colors.RESET}\n")
        for name, repo in sorted(plugins.items()):
            _print_repo(name, repo, name in user_repos)
        typer.echo(
            f"{Colors.CYAN}Install with:{Colors.RESET} cam plugin install <name>"
        )

    if marketplaces:
        typer.echo(f"\n{Colors.BOLD}Marketplaces:{Colors.RESET}\n")
        for name, repo in sorted(marketplaces.items()):
            _print_repo(name, repo, name in user_repos)
        typer.echo(
            f"{Colors.CYAN}Install marketplace with:{Colors.RESET} cam plugin marketplace install <marketplace-name>"
        )

    typer.echo(
        f"\n{Colors.CYAN}Add new repo:{Colors.RESET} cam plugin add-repo --owner <owner> --name <repo>"
    )
    typer.echo()


@plugin_app.command("add-repo")
def add_repo(
    owner: str = typer.Option(..., "--owner", "-o", help="Repository owner"),
    name: str = typer.Option(..., "--name", "-n", help="Repository name"),
    branch: str = typer.Option("main", "--branch", "-b", help="Repository branch"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Repository description"
    ),
    repo_type: str = typer.Option(
        "marketplace",
        "--type",
        "-t",
        help="Repository type (plugin or marketplace)",
    ),
    plugin_path: Optional[str] = typer.Option(
        None, "--plugin-path", help="Plugin path within the repository"
    ),
):
    """Add a plugin repository to CAM config."""
    manager = PluginManager()

    repo_id = f"{owner}/{name}"

    # Check if already exists
    existing = manager.get_repo(name)
    if existing:
        typer.echo(
            f"{Colors.YELLOW}Repository '{name}' already exists in config.{Colors.RESET}"
        )
        if not typer.confirm("Overwrite?"):
            raise typer.Exit(0)

    try:
        repo = PluginRepo(
            name=name,
            description=description,
            repo_owner=owner,
            repo_name=name,
            repo_branch=branch,
            type=repo_type,
            plugin_path=plugin_path,
            enabled=True,
        )
        manager.add_user_repo(repo)
        typer.echo(f"{Colors.GREEN}✓ Repository added: {repo_id}{Colors.RESET}")
        typer.echo(f"  Config file: {manager.plugin_repos_file}")
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        raise typer.Exit(1)


@plugin_app.command("remove-repo")
def remove_repo(
    name: str = typer.Argument(..., help="Repository name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a plugin repository from CAM config."""
    manager = PluginManager()

    # Check if exists
    existing = manager.get_repo(name)
    if not existing:
        typer.echo(f"{Colors.RED}✗ Repository '{name}' not found{Colors.RESET}")
        raise typer.Exit(1)

    # Check if it's a user repo (can't remove built-in)
    user_repos = manager.get_user_repos()
    if name not in user_repos:
        typer.echo(
            f"{Colors.RED}✗ Cannot remove built-in repository '{name}'{Colors.RESET}"
        )
        raise typer.Exit(1)

    if not force:
        typer.confirm(f"Remove repository '{name}'?", abort=True)

    try:
        if manager.remove_user_repo(name):
            typer.echo(f"{Colors.GREEN}✓ Repository removed: {name}{Colors.RESET}")
        else:
            typer.echo(f"{Colors.RED}✗ Failed to remove repository{Colors.RESET}")
            raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        raise typer.Exit(1)
