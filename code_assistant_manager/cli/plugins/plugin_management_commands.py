"""Plugin management commands.

Handles list, repos, add-repo, and remove-repo operations.
"""

import logging
from typing import Optional

import typer

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.plugins import (
    BUILTIN_PLUGIN_REPOS,
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
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all plugins from marketplaces (not just enabled)",
    ),
    app_type: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help=f"App type to show plugins for ({', '.join(VALID_APP_TYPES)}). Shows all apps if not specified.",
    ),
):
    """List installed/enabled plugins."""
    from code_assistant_manager.plugins import VALID_APP_TYPES, get_handler

    if app_type:
        # Show plugins for specific app (original behavior)
        if app_type not in VALID_APP_TYPES:
            typer.echo(
                f"{Colors.RED}✗ Invalid app type: {app_type}. Valid: {', '.join(VALID_APP_TYPES)}{Colors.RESET}"
            )
            raise typer.Exit(1)

        handler = get_handler(app_type)
        _show_app_plugins(app_type, handler, show_all)
    else:
        # Show plugins for all apps
        typer.echo(f"{Colors.BOLD}Plugin Status Across All Apps:{Colors.RESET}\n")

        apps_with_plugins = []
        for current_app in VALID_APP_TYPES:
            handler = get_handler(current_app)
            enabled_plugins = handler.get_enabled_plugins()
            if enabled_plugins:
                apps_with_plugins.append(current_app)
                _show_app_plugins(current_app, handler, show_all, show_header=False)
                typer.echo()  # Add spacing between apps

        if not apps_with_plugins:
            typer.echo(f"{Colors.YELLOW}No plugins installed in any app.{Colors.RESET}")
            typer.echo(f"Use 'cam plugin install <plugin>' to install one.")

            # Show available built-in repos
            if BUILTIN_PLUGIN_REPOS:
                typer.echo(f"\n{Colors.CYAN}Available built-in plugins:{Colors.RESET}")
                for name, repo in BUILTIN_PLUGIN_REPOS.items():
                    typer.echo(f"  • {name}: {repo.description or 'No description'}")
                typer.echo(f"\nInstall with: cam plugin install <name>")


def _show_app_plugins(app_name: str, handler, show_all: bool, show_header: bool = True):
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
            f"{Colors.CYAN}Add marketplace with:{Colors.RESET} cam plugin install <marketplace-name>"
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
