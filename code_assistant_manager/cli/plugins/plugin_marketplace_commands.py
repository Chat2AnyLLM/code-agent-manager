"""Marketplace commands.

Handles marketplace update operations.
"""

from typing import Optional

import typer

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.plugins import VALID_APP_TYPES, get_handler

plugin_app = typer.Typer(
    help="Manage plugins and marketplaces for AI assistants (Claude, CodeBuddy)",
    no_args_is_help=True,
)

# ==================== Marketplace Subcommand ====================

marketplace_app = typer.Typer(
    help="Manage marketplaces for AI assistant plugins.\n\n"
    "Marketplaces are collections of plugins that can be installed to Claude or CodeBuddy.\n"
    "Use 'add' to configure new marketplaces, 'install' to add them to your app,\n"
    "'update' to refresh from source, and 'list'/'remove' for management.",
    no_args_is_help=True,
)


@marketplace_app.command("add")
def marketplace_add(
    source: str = typer.Argument(
        ...,
        help="Marketplace source (URL, path, or GitHub repo) or 'fetch' to fetch and add from GitHub",
    ),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
    save: bool = typer.Option(
        False,
        "--save",
        "-s",
        help="Save the fetched repo to user config (only used with URL argument)",
    ),
):
    """Add a marketplace from a URL, path, or GitHub repo, or fetch and add from GitHub.

    This adds a marketplace to CAM's configuration. After adding, use
    'cam plugin marketplace install <name>' to install it to Claude/CodeBuddy.

    Examples:
        cam plugin marketplace add https://github.com/owner/repo
        cam plugin marketplace add owner/repo --save
        cam plugin marketplace add /path/to/local/marketplace
    """
    from code_assistant_manager.cli.option_utils import resolve_single_app

    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")

    # Handle special 'fetch' command - redirect to fetch functionality
    if source.lower() == "fetch":
        typer.echo(
            f"{Colors.YELLOW}Use 'cam plugin marketplace add <url> --save' instead of 'cam plugin fetch <url> --save'{Colors.RESET}"
        )
        typer.echo("Fetching functionality has been moved to marketplace add command.")
        raise typer.Exit(1)

    # If source looks like a GitHub URL or repo, and --save is specified, use fetch logic
    if save and ("/" in source or "github.com" in source):
        from code_assistant_manager.plugins import (
            PluginManager,
            fetch_repo_info_from_url,
            parse_github_url,
        )
        from code_assistant_manager.plugins.models import PluginRepo

        manager = PluginManager()
        parsed = parse_github_url(source)
        if not parsed:
            typer.echo(f"{Colors.RED}✗ Invalid GitHub URL: {source}{Colors.RESET}")
            raise typer.Exit(1)

        owner, repo, branch = parsed
        typer.echo(f"  Repository: {Colors.BOLD}{owner}/{repo}{Colors.RESET}")

        # Fetch repo info
        info = fetch_repo_info_from_url(source)
        if not info:
            typer.echo(
                f"{Colors.RED}✗ Could not fetch repository info. "
                f"Make sure the repo has .claude-plugin/marketplace.json{Colors.RESET}"
            )
            raise typer.Exit(1)

        # Display results
        typer.echo(f"\n{Colors.BOLD}Repository Information:{Colors.RESET}\n")
        typer.echo(f"  {Colors.CYAN}Name:{Colors.RESET} {info.name}")
        typer.echo(f"  {Colors.CYAN}Type:{Colors.RESET} {info.type}")
        typer.echo(
            f"  {Colors.CYAN}Description:{Colors.RESET} {info.description or 'N/A'}"
        )
        typer.echo(f"  {Colors.CYAN}Branch:{Colors.RESET} {info.branch}")

        if info.version:
            typer.echo(f"  {Colors.CYAN}Version:{Colors.RESET} {info.version}")

        if info.type == "marketplace":
            typer.echo(
                f"  {Colors.CYAN}Plugin Count:{Colors.RESET} {info.plugin_count}"
            )
            if info.plugins and len(info.plugins) <= 10:
                typer.echo(f"\n  {Colors.CYAN}Plugins:{Colors.RESET}")
                for p in info.plugins[:10]:
                    typer.echo(f"    • {p.get('name', 'unknown')}")
            elif info.plugins:
                typer.echo(
                    f"\n  {Colors.CYAN}Plugins:{Colors.RESET} (showing first 10)"
                )
                for p in info.plugins[:10]:
                    typer.echo(f"    • {p.get('name', 'unknown')}")
                typer.echo(f"    ... and {len(info.plugins) - 10} more")
        else:
            if info.plugin_path:
                typer.echo(
                    f"  {Colors.CYAN}Plugin Path:{Colors.RESET} {info.plugin_path}"
                )

        # Check if already exists
        existing = manager.get_repo(info.name)
        if existing:
            typer.echo(
                f"\n{Colors.YELLOW}Repository '{info.name}' already exists in config.{Colors.RESET}"
            )
            if not typer.confirm("Overwrite?"):
                raise typer.Exit(0)

        # Create PluginRepo and save
        plugin_repo = PluginRepo(
            name=info.name,
            description=info.description,
            repo_owner=info.owner,
            repo_name=info.repo,
            repo_branch=info.branch,
            plugin_path=info.plugin_path,
            type=info.type,
            enabled=True,
        )
        manager.add_user_repo(plugin_repo)
        typer.echo(
            f"\n{Colors.GREEN}✓ Saved '{info.name}' to user config as {info.type}{Colors.RESET}"
        )
        typer.echo(f"  Config file: {manager.plugin_repos_file}")

        # Show next steps
        if info.type == "marketplace":
            typer.echo(
                f"\n{Colors.CYAN}Next:{Colors.RESET} cam plugin marketplace install {info.name}"
            )
        else:
            typer.echo(
                f"\n{Colors.CYAN}Next:{Colors.RESET} cam plugin install {info.name}"
            )
        return

    # Original marketplace add functionality
    handler = get_handler(app)

    typer.echo(f"{Colors.CYAN}Adding marketplace: {source}...{Colors.RESET}")
    success, msg = handler.marketplace_add(source)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
    else:
        typer.echo(f"{Colors.RED}✗ {msg}{Colors.RESET}")
        raise typer.Exit(1)


@marketplace_app.command("list")
def marketplace_list(
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
    show_installed: bool = typer.Option(
        False,
        "--installed",
        help="Show only marketplaces installed in the app (not configured in CAM)",
    ),
):
    """List all configured marketplaces.

    By default, shows marketplaces configured in CAM. Use --installed to show
    marketplaces actually installed in the target app.
    """
    from code_assistant_manager.cli.option_utils import resolve_single_app
    from code_assistant_manager.plugins import PluginManager

    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")

    if show_installed:
        # Show marketplaces installed in the app
        handler = get_handler(app)
        success, installed_output = handler.marketplace_list()
        if success:
            # Parse the installed marketplaces and format consistently
            typer.echo(f"Installed marketplaces in {app}:")
            typer.echo()

            # Parse and standardize the format from different app handlers
            # Different apps may return different formats, so we standardize here
            lines = installed_output.strip().split("\n")
            marketplace_list = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Handle different formats:
                # - CodeBuddy: "❯ marketplace-name"
                # - Claude: "1. ✓ marketplace-name" or similar
                # Extract marketplace name from various formats
                if line.startswith("❯ "):
                    # CodeBuddy format: "❯ marketplace-name"
                    marketplace_name = line[2:].strip()
                elif ". " in line and ("✓" in line or "✗" in line):
                    # Claude format: "1. ✓ marketplace-name" or "1. ✗ marketplace-name"
                    parts = line.split(". ", 1)
                    if len(parts) == 2:
                        marketplace_name = parts[1].strip()
                        # Remove status indicators
                        if marketplace_name.startswith(("✓ ", "✗ ")):
                            marketplace_name = marketplace_name[2:].strip()
                        # Skip non-marketplace lines (like source URLs)
                        if marketplace_name.startswith(
                            "Source:"
                        ) or marketplace_name.startswith("Git ("):
                            continue
                else:
                    # Fallback: skip lines that don't match expected patterns
                    continue

                if marketplace_name and not marketplace_name.startswith(
                    ("Source:", "Git (")
                ):
                    marketplace_list.append(marketplace_name)

            # Display in consistent numbered format
            for i, marketplace_name in enumerate(sorted(marketplace_list), 1):
                typer.echo(f"  {i}. ✓ {marketplace_name}")

        else:
            typer.echo(f"{Colors.RED}✗ {installed_output}{Colors.RESET}")
            raise typer.Exit(1)
    else:
        # Show CAM configured marketplaces
        manager = PluginManager()
        all_repos = manager.get_all_repos()
        configured_marketplaces = {
            k: v for k, v in all_repos.items() if v.type == "marketplace"
        }

        if not configured_marketplaces:
            typer.echo(
                f"{Colors.YELLOW}No marketplaces configured in CAM.{Colors.RESET}"
            )
            typer.echo(
                f"Use 'cam plugin add-repo --type marketplace <owner>/<repo>' to add one."
            )
            return

        typer.echo("Configured marketplaces:")
        typer.echo()

        for i, (name, repo) in enumerate(sorted(configured_marketplaces.items()), 1):
            # Show status indicator
            status = (
                f"{Colors.GREEN}✓{Colors.RESET}"
                if repo.enabled
                else f"{Colors.RED}✗{Colors.RESET}"
            )
            typer.echo(f"  {i}. {status} {name}")

            # Show aliases if any
            if hasattr(repo, "aliases") and repo.aliases:
                aliases_str = ", ".join(repo.aliases)
                typer.echo(f"    Aliases: {aliases_str}")

            # Show description
            if repo.description:
                typer.echo(f"    {repo.description}")

            # Show source
            if repo.repo_owner and repo.repo_name:
                source_url = (
                    f"https://github.com/{repo.repo_owner}/{repo.repo_name}.git"
                )
                typer.echo(f"    Source: Git ({source_url})")
            else:
                typer.echo(
                    f"    Source: {Colors.YELLOW}No GitHub source configured{Colors.RESET}"
                )

            typer.echo()


@marketplace_app.command("remove")
@marketplace_app.command("rm", hidden=True)
def marketplace_remove(
    name: str = typer.Argument(
        ...,
        help="Marketplace name to remove",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Remove a configured marketplace."""
    from code_assistant_manager.cli.option_utils import resolve_single_app

    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    handler = get_handler(app)

    if not force:
        typer.confirm(f"Remove marketplace '{name}'?", abort=True)

    typer.echo(f"{Colors.CYAN}Removing marketplace: {name}...{Colors.RESET}")
    success, msg = handler.marketplace_remove(name)

    if success:
        typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
    else:
        typer.echo(f"{Colors.RED}✗ {msg}{Colors.RESET}")
        raise typer.Exit(1)


@marketplace_app.command("update")
def marketplace_update(
    name: Optional[str] = typer.Argument(
        None,
        help="Marketplace name to update (updates all if not specified)",
    ),
    app_type: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help=f"App type to update marketplaces for ({', '.join(VALID_APP_TYPES)}). Updates all apps if not specified.",
    ),
):
    """Update installed marketplace(s) from their source.

    This command updates installed marketplaces by pulling the latest changes
    from their source repositories. If no name is specified, all marketplaces
    are updated. If no app is specified, marketplaces are updated for all apps.

    Examples:
        cam plugin marketplace update                    # Update all marketplaces for all apps
        cam plugin marketplace update my-marketplace     # Update specific marketplace for all apps
        cam plugin marketplace update --app claude       # Update all marketplaces for Claude
        cam plugin marketplace update my-marketplace --app claude  # Update specific marketplace for Claude
    """
    from code_assistant_manager.plugins import VALID_APP_TYPES, get_handler

    if app_type:
        # Update for specific app
        if app_type not in VALID_APP_TYPES:
            typer.echo(
                f"{Colors.RED}✗ Invalid app type: {app_type}. Valid: {', '.join(VALID_APP_TYPES)}{Colors.RESET}"
            )
            raise typer.Exit(1)

        handler = get_handler(app_type)

        if name:
            typer.echo(
                f"{Colors.CYAN}Updating marketplace '{name}' for {app_type}...{Colors.RESET}"
            )
        else:
            typer.echo(
                f"{Colors.CYAN}Updating all marketplaces for {app_type}...{Colors.RESET}"
            )

        success, msg = handler.marketplace_update(name)

        if success:
            typer.echo(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        else:
            typer.echo(f"{Colors.RED}✗ {msg}{Colors.RESET}")
            raise typer.Exit(1)
    else:
        # Update for all apps
        if name:
            typer.echo(
                f"{Colors.CYAN}Updating marketplace '{name}' for all apps...{Colors.RESET}"
            )
        else:
            typer.echo(
                f"{Colors.CYAN}Updating all marketplaces for all apps...{Colors.RESET}"
            )

        all_success = True
        results = []

        for current_app in VALID_APP_TYPES:
            try:
                handler = get_handler(current_app)

                if name:
                    typer.echo(
                        f"  {Colors.CYAN}Updating '{name}' for {current_app}...{Colors.RESET}"
                    )
                else:
                    typer.echo(
                        f"  {Colors.CYAN}Updating all marketplaces for {current_app}...{Colors.RESET}"
                    )

                success, msg = handler.marketplace_update(name)

                if success:
                    typer.echo(f"  {Colors.GREEN}✓ {current_app}: {msg}{Colors.RESET}")
                    results.append(f"{current_app}: {msg}")
                else:
                    typer.echo(f"  {Colors.RED}✗ {current_app}: {msg}{Colors.RESET}")
                    results.append(f"{current_app}: {msg}")
                    all_success = False

            except Exception as e:
                error_msg = f"Failed to update {current_app}: {e}"
                typer.echo(f"  {Colors.RED}✗ {error_msg}{Colors.RESET}")
                results.append(error_msg)
                all_success = False

        if all_success:
            typer.echo(
                f"\n{Colors.GREEN}✓ All marketplace updates completed successfully{Colors.RESET}"
            )
        else:
            typer.echo(
                f"\n{Colors.YELLOW}⚠ Some marketplace updates failed{Colors.RESET}"
            )
            if not all_success:
                raise typer.Exit(1)


# Add marketplace subcommand to plugin app
plugin_app.add_typer(marketplace_app, name="marketplace")


@marketplace_app.command("install")
def marketplace_install(
    marketplace: Optional[str] = typer.Argument(
        None,
        help="Marketplace name to install (must be configured with 'cam plugin marketplace add' first)",
    ),
    all_marketplaces: bool = typer.Option(
        False,
        "--all",
        help="Install all configured marketplaces",
    ),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type(s) to install marketplace to ({', '.join(VALID_APP_TYPES)}, all). Comma-separated.",
    ),
):
    """Install a configured marketplace or all marketplaces to Claude or CodeBuddy.

    This installs a marketplace that has been previously configured in CAM
    to the target AI assistant app(s). The marketplace must already be configured
    using 'cam plugin marketplace add' before it can be installed.

    After installation, you can browse plugins with 'cam plugin list <marketplace>'
    and install them with 'cam plugin install <plugin>@<marketplace>'.

    Examples:
        cam plugin marketplace install awesome-claude-code-plugins
        cam plugin marketplace install my-marketplace --app codebuddy
        cam plugin marketplace install --all
        cam plugin marketplace install --all --app claude,codebuddy
    """
    from code_assistant_manager.cli.option_utils import resolve_app_targets
    from code_assistant_manager.plugins import PluginManager

    target_apps = resolve_app_targets(app_type, VALID_APP_TYPES, default="claude")
    manager = PluginManager()

    # Get all configured marketplaces
    all_repos = manager.get_all_repos()
    configured_marketplaces = {
        k: v for k, v in all_repos.items() if v.type == "marketplace"
    }

    if not configured_marketplaces:
        typer.echo(f"{Colors.YELLOW}No marketplaces configured in CAM.{Colors.RESET}")
        typer.echo(
            f"Use 'cam plugin add-repo --type marketplace <owner>/<repo>' to add one."
        )
        return

    # Determine which marketplaces to install
    if all_marketplaces:
        marketplaces_to_install = configured_marketplaces
    elif marketplace:
        # Install single marketplace
        if marketplace not in configured_marketplaces:
            typer.echo(
                f"{Colors.RED}✗ Marketplace '{marketplace}' not found in CAM configuration.{Colors.RESET}"
            )
            typer.echo(
                f"{Colors.YELLOW}Use 'cam plugin add-repo --type marketplace <owner>/<repo>' to add it first.{Colors.RESET}"
            )
            typer.echo(f"\n{Colors.CYAN}Configured marketplaces:{Colors.RESET}")
            for name in sorted(configured_marketplaces.keys()):
                typer.echo(f"  • {name}")
            raise typer.Exit(1)
        marketplaces_to_install = {marketplace: configured_marketplaces[marketplace]}
    else:
        typer.echo(
            f"{Colors.RED}✗ Either specify a marketplace name or use --all to install all marketplaces.{Colors.RESET}"
        )
        typer.echo(f"\n{Colors.CYAN}Configured marketplaces:{Colors.RESET}")
        for name in sorted(configured_marketplaces.keys()):
            typer.echo(f"  • {name}")
        raise typer.Exit(1)

    # Install the marketplaces to each target app
    for app in target_apps:
        typer.echo(f"\n{Colors.BOLD}Installing to {app}...{Colors.RESET}")
        handler = get_handler(app)

        installed_count = 0
        failed_count = 0
        already_installed_count = 0

        for name, repo in marketplaces_to_install.items():
            if repo.type != "marketplace":
                continue

            if not repo.repo_owner or not repo.repo_name:
                typer.echo(
                    f"{Colors.YELLOW}⚠ Skipping '{name}' (no GitHub source configured){Colors.RESET}"
                )
                continue

            repo_url = f"https://github.com/{repo.repo_owner}/{repo.repo_name}"

            typer.echo(f"{Colors.CYAN}Installing marketplace: {name}...{Colors.RESET}")
            success, msg = handler.marketplace_add(repo_url)

            if success:
                typer.echo(f"{Colors.GREEN}✓ Marketplace installed: {name}{Colors.RESET}")
                installed_count += 1
            elif "already installed" in msg.lower():
                typer.echo(
                    f"{Colors.YELLOW}Marketplace '{name}' is already installed.{Colors.RESET}"
                )
                already_installed_count += 1
            else:
                typer.echo(f"{Colors.RED}✗ Failed to install '{name}': {msg}{Colors.RESET}")
                failed_count += 1

        # Summary for current app
        total_attempted = len(marketplaces_to_install)
        typer.echo(f"  {Colors.BOLD}Summary for {app}:{Colors.RESET}")
        typer.echo(f"    Installed: {installed_count}")
        typer.echo(f"    Already installed: {already_installed_count}")
        typer.echo(f"    Failed: {failed_count}")

    if len(target_apps) == 1:
        if installed_count > 0 or already_installed_count > 0:
            typer.echo(
                f"\n{Colors.CYAN}Browse plugins with:{Colors.RESET} cam plugin list <marketplace>"
            )
            typer.echo(
                f"{Colors.CYAN}Install plugins with:{Colors.RESET} cam plugin install <plugin-name>@<marketplace>"
            )



@marketplace_app.command("uninstall")
def marketplace_uninstall(
    marketplace: Optional[str] = typer.Argument(
        None,
        help="Marketplace name to uninstall",
    ),
    all_marketplaces: bool = typer.Option(
        False,
        "--all",
        help="Uninstall all installed marketplaces",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    app_type: str = typer.Option(
        "claude",
        "--app",
        "-a",
        help=f"App type to uninstall marketplace from ({', '.join(VALID_APP_TYPES)})",
    ),
):
    """Uninstall a marketplace or all marketplaces from Claude or CodeBuddy.

    This removes a marketplace from the target AI assistant app. The marketplace
    remains configured in CAM but is no longer available in the app.

    Examples:
        cam plugin marketplace uninstall awesome-claude-code-plugins
        cam plugin marketplace uninstall my-marketplace --app codebuddy
        cam plugin marketplace uninstall --all
        cam plugin marketplace uninstall --all --force
    """
    from code_assistant_manager.cli.option_utils import resolve_single_app
    from code_assistant_manager.plugins import PluginManager

    app = resolve_single_app(app_type, VALID_APP_TYPES, default="claude")
    handler = get_handler(app)
    manager = PluginManager()

    # Get all configured marketplaces
    all_repos = manager.get_all_repos()
    configured_marketplaces = {
        k: v for k, v in all_repos.items() if v.type == "marketplace"
    }

    if not configured_marketplaces:
        typer.echo(f"{Colors.YELLOW}No marketplaces configured in CAM.{Colors.RESET}")
        return

    # Determine which marketplaces to uninstall
    if all_marketplaces:
        marketplaces_to_uninstall = configured_marketplaces
        typer.echo(
            f"{Colors.CYAN}Uninstalling all configured marketplaces from {app}...{Colors.RESET}"
        )
    elif marketplace:
        # Uninstall single marketplace
        if marketplace not in configured_marketplaces:
            typer.echo(
                f"{Colors.RED}✗ Marketplace '{marketplace}' not found in CAM configuration.{Colors.RESET}"
            )
            typer.echo(f"\n{Colors.CYAN}Configured marketplaces:{Colors.RESET}")
            for name in sorted(configured_marketplaces.keys()):
                typer.echo(f"  • {name}")
            raise typer.Exit(1)
        marketplaces_to_uninstall = {marketplace: configured_marketplaces[marketplace]}
    else:
        typer.echo(
            f"{Colors.RED}✗ Either specify a marketplace name or use --all to uninstall all marketplaces.{Colors.RESET}"
        )
        typer.echo(f"\n{Colors.CYAN}Configured marketplaces:{Colors.RESET}")
        for name in sorted(configured_marketplaces.keys()):
            typer.echo(f"  • {name}")
        raise typer.Exit(1)

    # Check if we need confirmation for multiple uninstalls
    if len(marketplaces_to_uninstall) > 1 and not force:
        names_list = ", ".join(sorted(marketplaces_to_uninstall.keys()))
        if not typer.confirm(
            f"Uninstall {len(marketplaces_to_uninstall)} marketplaces ({names_list})?",
            abort=True,
        ):
            raise typer.Exit(0)

    # Uninstall the marketplaces
    uninstalled_count = 0
    failed_count = 0
    not_installed_count = 0

    for name, repo in marketplaces_to_uninstall.items():
        if repo.type != "marketplace":
            typer.echo(
                f"{Colors.YELLOW}⚠ Skipping '{name}' (not a marketplace, type: {repo.type}){Colors.RESET}"
            )
            continue

        # For single marketplace, show confirmation unless forced
        if len(marketplaces_to_uninstall) == 1 and not force:
            if not typer.confirm(f"Uninstall marketplace '{name}'?", abort=True):
                continue

        typer.echo(f"{Colors.CYAN}Uninstalling marketplace: {name}...{Colors.RESET}")
        success, msg = handler.marketplace_remove(name)

        if success:
            typer.echo(f"{Colors.GREEN}✓ Marketplace uninstalled: {name}{Colors.RESET}")
            uninstalled_count += 1
        elif "not installed" in msg.lower() or "not found" in msg.lower():
            typer.echo(
                f"{Colors.YELLOW}Marketplace '{name}' is not installed.{Colors.RESET}"
            )
            not_installed_count += 1
        else:
            typer.echo(
                f"{Colors.RED}✗ Failed to uninstall '{name}': {msg}{Colors.RESET}"
            )
            failed_count += 1

    # Summary
    total_attempted = len(marketplaces_to_uninstall)
    typer.echo(f"\n{Colors.BOLD}Uninstallation Summary:{Colors.RESET}")
    typer.echo(f"  Uninstalled: {uninstalled_count}")
    typer.echo(f"  Not installed: {not_installed_count}")
    typer.echo(f"  Failed: {failed_count}")
    typer.echo(
        f"  Skipped: {total_attempted - uninstalled_count - failed_count - not_installed_count}"
    )

    if failed_count > 0:
        typer.echo(
            f"\n{Colors.YELLOW}⚠ {failed_count} marketplace(s) failed to uninstall.{Colors.RESET}"
        )
        raise typer.Exit(1)
