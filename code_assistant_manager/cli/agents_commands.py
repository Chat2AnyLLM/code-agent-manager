"""CLI commands for agent management."""

import logging
from typing import Optional

import typer

from code_assistant_manager.agents import VALID_APP_TYPES, AgentManager, AgentRepo
from code_assistant_manager.cli.option_utils import resolve_app_targets
from code_assistant_manager.menu.base import Colors

# Module-level variables for typer defaults to avoid B008 violations
URL_ARGUMENT = typer.Argument(
    None,
    help="GitHub URL or owner/repo to fetch and save (e.g., https://github.com/owner/repo or owner/repo)",
)
SAVE_OPTION = typer.Option(
    False,
    "--save",
    "-s",
    help="Save the fetched repo to config (only used with URL argument)",
)
AGENTS_PATH_OPTION = typer.Option(
    None,
    "--agents-path",
    help="Agents subdirectory path in the repo (only used with URL argument)",
)
AGENT_KEY_ARGUMENT = typer.Argument(..., help="Agent identifier")
APP_TYPE_OPTION = typer.Option(
    "claude",
    "--app",
    "-a",
    help="App type(s) to install to (claude, codex, gemini, droid, codebuddy, opencode, all). Comma-separated.",
)
FORCE_OPTION = typer.Option(False, "--force", "-f", help="Skip confirmation")
OWNER_OPTION = typer.Option(..., "--owner", "-o", help="Repository owner")
NAME_OPTION = typer.Option(..., "--name", "-n", help="Repository name")
BRANCH_OPTION = typer.Option("main", "--branch", "-b", help="Repository branch")
AGENTS_PATH_OPTION_REPO = typer.Option(
    None, "--agents-path", help="Agents subdirectory path"
)
APP_TYPE_OPTION_ALL = typer.Option(
    None,
    "--app",
    "-a",
    help="App type(s) to show (claude, codex, gemini, droid, codebuddy, opencode, all). Default shows all.",
)
APP_TYPE_OPTION_UNINSTALL = typer.Option(
    ...,
    "--app",
    "-a",
    help="App type(s) to uninstall all agents from (claude, codex, gemini, droid, codebuddy, opencode, all). Comma-separated.",
)
from code_assistant_manager.plugins.fetch import parse_github_url

logger = logging.getLogger(__name__)

agent_app = typer.Typer(
    help="Manage agents for AI assistants (Claude, Codex, Gemini, Droid, CodeBuddy, OpenCode)",
    no_args_is_help=True,
)


def _get_agent_manager() -> AgentManager:
    """Get agent manager instance."""
    return AgentManager()


@agent_app.command("list")
def list_agents():
    """List all agents."""
    manager = _get_agent_manager()
    manager.sync_installed_status()

    agents = manager.get_all()

    if not agents:
        typer.echo(
            f"{Colors.YELLOW}No agents found. Run 'cam agent fetch' to discover agents from repositories.{Colors.RESET}"
        )
        return

    typer.echo(f"\n{Colors.BOLD}Agents:{Colors.RESET}\n")
    for agent_key, agent in sorted(agents.items()):
        status = (
            f"{Colors.GREEN}✓{Colors.RESET}"
            if agent.installed
            else f"{Colors.RED}✗{Colors.RESET}"
        )
        color_badge = f" [{agent.color}]" if agent.color else ""
        typer.echo(
            f"{status} {Colors.BOLD}{agent.name}{Colors.RESET}{Colors.CYAN}{color_badge}{Colors.RESET} ({agent_key})"
        )
        if agent.description:
            # Truncate long descriptions
            desc = agent.description
            if len(desc) > 100:
                desc = desc[:97] + "..."
            typer.echo(f"  {Colors.CYAN}Description:{Colors.RESET} {desc}")
        if agent.tools:
            typer.echo(f"  {Colors.CYAN}Tools:{Colors.RESET} {', '.join(agent.tools)}")
        typer.echo()


@agent_app.command("fetch")
def fetch_agents(
    url: Optional[str] = URL_ARGUMENT,
    save: bool = SAVE_OPTION,
    agents_path: Optional[str] = AGENTS_PATH_OPTION,
):
    """Fetch agents from configured repositories or a specific GitHub URL.

    Without URL: Fetches agents from all configured repositories.
    With URL: Fetches info from a specific GitHub repo and optionally saves it.

    Examples:
        cam agent fetch                     # Fetch from all configured repos
        cam agent fetch owner/repo --save   # Fetch and save a new repo
        cam agent fetch https://github.com/owner/repo --save --agents-path agents
    """
    manager = _get_agent_manager()

    # If URL provided, fetch from that specific repo
    if url:
        typer.echo(f"{Colors.CYAN}Fetching repository info...{Colors.RESET}")

        # Parse and validate URL
        parsed = parse_github_url(url)
        if not parsed:
            typer.echo(f"{Colors.RED}✗ Invalid GitHub URL: {url}{Colors.RESET}")
            raise typer.Exit(1)

        owner, repo, branch = parsed
        typer.echo(f"  Repository: {Colors.BOLD}{owner}/{repo}{Colors.RESET}")

        # Display results
        typer.echo(f"\n{Colors.BOLD}Repository Information:{Colors.RESET}\n")
        typer.echo(f"  {Colors.CYAN}Owner:{Colors.RESET} {owner}")
        typer.echo(f"  {Colors.CYAN}Repo:{Colors.RESET} {repo}")
        typer.echo(f"  {Colors.CYAN}Branch:{Colors.RESET} {branch}")
        if agents_path:
            typer.echo(f"  {Colors.CYAN}Agents Path:{Colors.RESET} {agents_path}")

        # Save if requested
        if save:
            # Check if already exists
            existing_repos = manager.get_repos()
            repo_id = f"{owner}/{repo}"
            existing = next(
                (r for r in existing_repos if f"{r.owner}/{r.name}" == repo_id), None
            )
            if existing:
                typer.echo(
                    f"\n{Colors.YELLOW}Repository '{repo_id}' already exists in config.{Colors.RESET}"
                )
                if not typer.confirm("Overwrite?"):
                    raise typer.Exit(0)

            # Create AgentRepo and save
            agent_repo = AgentRepo(
                owner=owner,
                name=repo,
                branch=branch,
                enabled=True,
                agents_path=agents_path,
            )
            manager.add_repo(agent_repo)
            typer.echo(
                f"\n{Colors.GREEN}✓ Saved '{repo_id}' to user config{Colors.RESET}"
            )
            typer.echo(f"  Config file: {manager.repos_file}")

            # Show next steps
            typer.echo(
                f"\n{Colors.CYAN}Next:{Colors.RESET} cam agent fetch  # to fetch agents from all repos"
            )
        else:
            typer.echo(
                f"\n{Colors.CYAN}To save:{Colors.RESET} cam agent fetch '{url}' --save"
            )

        typer.echo()
        return

    # No URL provided - fetch from all configured repos
    typer.echo(f"{Colors.CYAN}Fetching agents from repositories...{Colors.RESET}")

    try:
        agents = manager.fetch_agents_from_repos()
        typer.echo(f"{Colors.GREEN}✓ Found {len(agents)} agents{Colors.RESET}")

        for agent in agents[:10]:  # Show first 10
            status = (
                f"{Colors.GREEN}✓{Colors.RESET}"
                if agent.installed
                else f"{Colors.RED}✗{Colors.RESET}"
            )
            typer.echo(f"  {status} {agent.name} ({agent.key})")

        if len(agents) > 10:
            typer.echo(f"  ... and {len(agents) - 10} more")

        typer.echo(
            f"\n{Colors.CYAN}Run 'cam agent list' to see all agents{Colors.RESET}"
        )
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Error fetching agents: {e}{Colors.RESET}")
        raise typer.Exit(1)


@agent_app.command("view")
def view_agent(agent_key: str = typer.Argument(..., help="Agent identifier")):
    """View a specific agent."""
    manager = _get_agent_manager()
    agent = manager.get(agent_key)

    if not agent:
        typer.echo(f"{Colors.RED}✗ Agent '{agent_key}' not found{Colors.RESET}")
        raise typer.Exit(1)

    typer.echo(f"\n{Colors.BOLD}Agent: {agent.name}{Colors.RESET}")
    typer.echo(f"{Colors.CYAN}Description:{Colors.RESET} {agent.description}")
    typer.echo(f"{Colors.CYAN}Key:{Colors.RESET} {agent_key}")
    typer.echo(f"{Colors.CYAN}Filename:{Colors.RESET} {agent.filename}")
    status = (
        f"{Colors.GREEN}installed{Colors.RESET}"
        if agent.installed
        else f"{Colors.RED}not installed{Colors.RESET}"
    )
    typer.echo(f"{Colors.CYAN}Status:{Colors.RESET} {status}")

    if agent.tools:
        typer.echo(f"{Colors.CYAN}Tools:{Colors.RESET} {', '.join(agent.tools)}")

    if agent.color:
        typer.echo(f"{Colors.CYAN}Color:{Colors.RESET} {agent.color}")

    if agent.repo_owner and agent.repo_name:
        typer.echo(
            f"{Colors.CYAN}Repository:{Colors.RESET} {agent.repo_owner}/{agent.repo_name}"
        )
        typer.echo(f"{Colors.CYAN}Branch:{Colors.RESET} {agent.repo_branch or 'main'}")

    if agent.agents_path:
        typer.echo(f"{Colors.CYAN}Agents Path:{Colors.RESET} {agent.agents_path}")

    if agent.readme_url:
        typer.echo(f"{Colors.CYAN}URL:{Colors.RESET} {agent.readme_url}")

    typer.echo()


# Alias 'show' to 'view' for consistency with other commands
@agent_app.command("show")
def show_agent(agent_key: str = typer.Argument(..., help="Agent identifier")):
    """Show details about a specific agent (alias for view)."""
    return view_agent(agent_key)


@agent_app.command("install")
def install_agent(
    agent_key: str = AGENT_KEY_ARGUMENT,
    app_type: str = APP_TYPE_OPTION,
):
    """Install an agent to one or more app's agents directories.
    
    Can accept either a registered agent key or a GitHub specification:
    - Registered key: 'security-auditor'
    - GitHub spec: 'owner/repo:agent-name' or 'owner/repo:agent-name@branch'
    """
    target_apps = resolve_app_targets(app_type, VALID_APP_TYPES, default="claude")
    
    manager = _get_agent_manager()
    
    # First check if agent_key matches a registered agent (most common case)
    all_agents = manager.get_all()
    if agent_key in all_agents:
        # Use registered agent configuration
        for app in target_apps:
            try:
                handler = manager.get_handler(app)
                dest_path = manager.install(agent_key, app)
                typer.echo(
                    f"{Colors.GREEN}✓ Agent installed to {app}: {agent_key}{Colors.RESET}"
                )
                typer.echo(f"  {Colors.CYAN}Location:{Colors.RESET} {handler.agents_dir}")
            except ValueError as e:
                typer.echo(f"{Colors.RED}✗ Error installing to {app}: {e}{Colors.RESET}")
                raise typer.Exit(1)
        return
    
    # Check if agent_key is a GitHub specification (contains / or :)
    if "/" in agent_key and ":" in agent_key:
        # Parse GitHub specification: owner/repo:agent-name[@branch]
        try:
            parts = agent_key.split(":")
            branch = "main"
            
            if len(parts) == 2:
                repo_part, agent_name = parts
                owner, repo = repo_part.split("/")
            elif len(parts) == 3:
                repo_part, agent_name, branch = parts
                owner, repo = repo_part.split("/")
            else:
                typer.echo(
                    f"{Colors.RED}✗ Invalid agent specification: {agent_key}{Colors.RESET}"
                )
                typer.echo(
                    f"  {Colors.CYAN}Use format: owner/repo:agent-name or owner/repo:agent-name@branch{Colors.RESET}"
                )
                raise typer.Exit(1)
            
            # Check if this exact GitHub spec is registered in agents.json
            if agent_key in all_agents:
                agent = all_agents[agent_key]
            else:
                # Create a temporary agent object for installation
                from code_assistant_manager.agents.models import Agent
                
                # Determine filename from agent name
                filename = f"{agent_name}.md"
                agent = Agent(
                    key=agent_key,
                    name=agent_name,
                    description=f"Installed from {owner}/{repo}",
                    filename=filename,
                    repo_owner=owner,
                    repo_name=repo,
                    repo_branch=branch,
                    agents_path=None,  # Try common paths
                )
            
            for app in target_apps:
                try:
                    handler = manager.get_handler(app)
                    dest_path = handler.install(agent)
                    typer.echo(
                        f"{Colors.GREEN}✓ Agent installed to {app}: {agent_name}{Colors.RESET}"
                    )
                    typer.echo(f"  {Colors.CYAN}Location:{Colors.RESET} {dest_path}")
                except ValueError as e:
                    # If agent not found in configured path, try common paths
                    error_msg = str(e)
                    if "not found" in error_msg and agent.agents_path is None:
                        # Try plugins directory
                        agent.agents_path = "plugins"
                        try:
                            dest_path = handler.install(agent)
                            typer.echo(
                                f"{Colors.GREEN}✓ Agent installed to {app}: {agent_name}{Colors.RESET}"
                            )
                            typer.echo(f"  {Colors.CYAN}Location:{Colors.RESET} {dest_path}")
                        except ValueError:
                            # Try agents directory
                            agent.agents_path = "agents"
                            try:
                                dest_path = handler.install(agent)
                                typer.echo(
                                    f"{Colors.GREEN}✓ Agent installed to {app}: {agent_name}{Colors.RESET}"
                                )
                                typer.echo(f"  {Colors.CYAN}Location:{Colors.RESET} {dest_path}")
                            except ValueError as e2:
                                typer.echo(f"{Colors.RED}✗ Error installing to {app}: {e2}{Colors.RESET}")
                                raise typer.Exit(1)
                    else:
                        typer.echo(f"{Colors.RED}✗ Error installing to {app}: {e}{Colors.RESET}")
                        raise typer.Exit(1)
        except (ValueError, IndexError) as e:
            typer.echo(
                f"{Colors.RED}✗ Invalid agent specification format: {agent_key}{Colors.RESET}"
            )
            typer.echo(
                f"  {Colors.CYAN}Use format: owner/repo:agent-name or owner/repo:agent-name@branch{Colors.RESET}"
            )
            raise typer.Exit(1)
    else:
        # Not found as registered key and not in GitHub format
        typer.echo(
            f"{Colors.RED}✗ Agent '{agent_key}' not found{Colors.RESET}"
        )
        typer.echo(
            f"  {Colors.CYAN}Try one of:{Colors.RESET}"
        )
        typer.echo(
            f"    • cam agent list  (to see available agents)"
        )
        typer.echo(
            f"    • cam agent fetch (to discover agents from repositories)"
        )
        raise typer.Exit(1)


@agent_app.command("uninstall")
def uninstall_agent(
    agent_key: str = AGENT_KEY_ARGUMENT,
    app_type: str = APP_TYPE_OPTION,
    force: bool = FORCE_OPTION,
):
    """Uninstall an agent from one or more app's agents directories."""
    target_apps = resolve_app_targets(app_type, VALID_APP_TYPES, default="claude")

    manager = _get_agent_manager()
    agent = manager.get(agent_key)

    if not agent:
        typer.echo(f"{Colors.RED}✗ Agent '{agent_key}' not found{Colors.RESET}")
        raise typer.Exit(1)

    if not force:
        typer.confirm(f"Uninstall agent '{agent.name}' ({agent_key})?", abort=True)

    for app in target_apps:
        try:
            manager.uninstall(agent_key, app)
            typer.echo(
                f"{Colors.GREEN}✓ Agent uninstalled from {app}: {agent_key}{Colors.RESET}"
            )
        except ValueError as e:
            typer.echo(
                f"{Colors.RED}✗ Error uninstalling from {app}: {e}{Colors.RESET}"
            )
            raise typer.Exit(1)


@agent_app.command("repos")
def list_repos():
    """List all agent repositories."""
    manager = _get_agent_manager()
    repos = manager.get_repos()

    if not repos:
        typer.echo(f"{Colors.YELLOW}No agent repositories configured{Colors.RESET}")
        return

    typer.echo(f"\n{Colors.BOLD}Agent Repositories:{Colors.RESET}\n")
    for repo in repos:
        status = (
            f"{Colors.GREEN}✓{Colors.RESET}"
            if repo.enabled
            else f"{Colors.RED}✗{Colors.RESET}"
        )
        typer.echo(f"{status} {Colors.BOLD}{repo.owner}/{repo.name}{Colors.RESET}")
        typer.echo(f"  {Colors.CYAN}Branch:{Colors.RESET} {repo.branch}")
        if repo.agents_path:
            typer.echo(f"  {Colors.CYAN}Agents Path:{Colors.RESET} {repo.agents_path}")
        typer.echo()


@agent_app.command("add-repo")
def add_repo(
    owner: str = OWNER_OPTION,
    name: str = NAME_OPTION,
    branch: str = BRANCH_OPTION,
    agents_path: Optional[str] = AGENTS_PATH_OPTION_REPO,
):
    """Add an agent repository."""
    manager = _get_agent_manager()

    try:
        repo = AgentRepo(
            owner=owner,
            name=name,
            branch=branch,
            enabled=True,
            agents_path=agents_path,
        )
        manager.add_repo(repo)
        typer.echo(f"{Colors.GREEN}✓ Repository added: {owner}/{name}{Colors.RESET}")
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        raise typer.Exit(1)


@agent_app.command("remove-repo")
def remove_repo(
    owner: str = OWNER_OPTION,
    name: str = NAME_OPTION,
    force: bool = FORCE_OPTION,
):
    """Remove an agent repository."""
    manager = _get_agent_manager()

    if not force:
        typer.confirm(f"Remove repository '{owner}/{name}'?", abort=True)

    try:
        manager.remove_repo(owner, name)
        typer.echo(f"{Colors.GREEN}✓ Repository removed: {owner}/{name}{Colors.RESET}")
    except ValueError as e:
        typer.echo(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        raise typer.Exit(1)


@agent_app.command("status")
def agent_status(
    app_type: Optional[str] = APP_TYPE_OPTION_ALL,
):
    """Show agent installation status across apps (alias: installed)."""
    return list_installed_agents(app_type)


@agent_app.command("installed")
def list_installed_agents(
    app_type: Optional[str] = APP_TYPE_OPTION_ALL,
):
    """Show installed agents for each app."""
    manager = _get_agent_manager()
    all_agents = manager.get_all()

    target_apps = resolve_app_targets(
        app_type,
        VALID_APP_TYPES,
        default=None,
        fallback_to_all_if_none=True,
    )

    for app in target_apps:
        try:
            handler = manager.get_handler(app)
        except ValueError:
            continue

        agents_dir = handler.agents_dir
        typer.echo(f"\n{Colors.BOLD}{app.capitalize()} ({agents_dir}):{Colors.RESET}")

        if not agents_dir.exists():
            typer.echo(f"  {Colors.YELLOW}No agents installed{Colors.RESET}")
            continue

        installed = list(agents_dir.glob("*.md"))
        if not installed:
            typer.echo(f"  {Colors.YELLOW}No agents installed{Colors.RESET}")
            continue

        for agent_file in sorted(installed):
            filename = agent_file.name

            # Find matching agent in database
            agent_key = None
            for key, agent in all_agents.items():
                if agent.filename.lower() == filename.lower():
                    agent_key = key
                    break

            if agent_key:
                agent = all_agents[agent_key]
                typer.echo(
                    f"  {Colors.GREEN}✓{Colors.RESET} {agent.name} ({Colors.CYAN}{agent_key}{Colors.RESET})"
                )
            else:
                typer.echo(f"  {Colors.GREEN}✓{Colors.RESET} {filename}")


@agent_app.command("uninstall-all")
def uninstall_all_agents(
    app_type: str = APP_TYPE_OPTION_UNINSTALL,
    force: bool = FORCE_OPTION,
):
    """Uninstall all agents from one or more apps."""
    target_apps = resolve_app_targets(app_type, VALID_APP_TYPES)
    manager = _get_agent_manager()

    for app in target_apps:
        try:
            handler = manager.get_handler(app)
        except ValueError as e:
            typer.echo(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
            continue

        agents_dir = handler.agents_dir
        if not agents_dir.exists():
            typer.echo(
                f"{Colors.YELLOW}No agents directory found for {app}{Colors.RESET}"
            )
            continue

        agent_files = list(agents_dir.glob("*.md"))
        if not agent_files:
            typer.echo(f"{Colors.YELLOW}No agents installed for {app}{Colors.RESET}")
            continue

        if not force:
            typer.confirm(
                f"Uninstall all {len(agent_files)} agents from {app}?", abort=True
            )

        removed_count = 0
        for agent_file in agent_files:
            try:
                agent_file.unlink()
                typer.echo(
                    f"  {Colors.GREEN}✓{Colors.RESET} Removed: {agent_file.name}"
                )
                removed_count += 1
            except Exception as e:
                typer.echo(
                    f"  {Colors.RED}✗{Colors.RESET} Failed to remove {agent_file.name}: {e}"
                )

        manager.sync_installed_status(app)
        typer.echo(
            f"\n{Colors.GREEN}✓ Removed {removed_count} agents from {app}{Colors.RESET}"
        )


# Add list shorthand
agent_app.command(name="ls", hidden=True)(list_agents)
