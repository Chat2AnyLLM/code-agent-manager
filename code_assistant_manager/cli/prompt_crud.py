"""Basic CRUD operations for prompt management."""

import logging
from typing import List, Optional

import typer

from code_assistant_manager.cli.option_utils import ensure_project_dir
from code_assistant_manager.menu.base import Colors

logger = logging.getLogger(__name__)

# Valid app types - copilot is special (project-level only with different structure)
VALID_APP_TYPES = ["claude", "codex", "gemini", "copilot", "codebuddy"]
# Apps that support user-level prompts
USER_LEVEL_APPS = [
    "claude",
    "codex",
    "gemini",
    "codebuddy",
]  # codebuddy supports user and project levels
VALID_LEVELS = ["user", "project"]


def generate_prompt_id(prefix: str = "prompt") -> str:
    """Generate a unique prompt ID with a short UUID suffix."""
    import uuid

    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}-{short_uuid}"


def _parse_app_list(app_str: str) -> List[str]:
    """Parse comma-separated app list."""
    if not app_str:
        return []
    return [app.strip() for app in app_str.split(",") if app.strip()]


def list_prompts(
    app: str = typer.Option(
        None,
        "--app",
        "-a",
        help="Filter by app type (claude, codex, gemini, copilot, codebuddy)",
    ),
    level: str = typer.Option(
        None,
        "--level",
        "-l",
        help="Filter by level (user, project)",
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory for project-level prompts",
    ),
):
    """List all prompts, optionally filtered by app and level."""
    from code_assistant_manager.prompts import PromptManager

    # Validate inputs
    if app and app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    if level and level not in VALID_LEVELS:
        typer.echo(
            f"Error: Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}"
        )
        raise typer.Exit(1)

    # Handle project directory
    if level == "project":
        project_dir = ensure_project_dir(project_dir)

    try:
        manager = PromptManager()
        prompts = manager.list_prompts(app=app, level=level, project_dir=project_dir)

        if not prompts:
            typer.echo("No prompts found matching the criteria.")
            return

        typer.echo(f"\nFound {len(prompts)} prompt(s):\n")

        for prompt in prompts:
            status = "✓" if prompt.is_active else "✗"
            default = " (default)" if prompt.is_default else ""
            typer.echo(f"  {status} {prompt.prompt_id}{default}")
            if prompt.description:
                typer.echo(f"    {Colors.DIM}{prompt.description}{Colors.RESET}")
            typer.echo(
                f"    {Colors.DIM}App: {prompt.app}, Level: {prompt.level}{Colors.RESET}"
            )
            typer.echo()

    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def view_prompt(prompt_id: str):
    """View details of a specific prompt."""
    from code_assistant_manager.prompts import PromptManager

    try:
        manager = PromptManager()
        prompt = manager.get_prompt(prompt_id)

        if not prompt:
            typer.echo(f"Error: Prompt '{prompt_id}' not found.")
            raise typer.Exit(1)

        typer.echo(f"\nPrompt: {prompt.prompt_id}")
        typer.echo(f"App: {prompt.app}")
        typer.echo(f"Level: {prompt.level}")
        typer.echo(f"Active: {'Yes' if prompt.is_active else 'No'}")
        typer.echo(f"Default: {'Yes' if prompt.is_default else 'No'}")
        if prompt.description:
            typer.echo(f"Description: {prompt.description}")
        typer.echo(f"\nContent:\n{prompt.content}")

    except Exception as e:
        logger.error(f"Error viewing prompt '{prompt_id}': {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def add_prompt(
    app: str = typer.Option(..., "--app", "-a", help="App type for the prompt"),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level for the prompt (user, project)"
    ),
    name: str = typer.Option(
        ..., "--name", "-n", help="Name/identifier for the prompt"
    ),
    content: str = typer.Option(..., "--content", "-c", help="Content of the prompt"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Optional description"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-p",
        help="Project directory (required for project-level prompts)",
    ),
    set_default: bool = typer.Option(
        False, "--default", help="Set this prompt as the default for the app"
    ),
):
    """Add a new prompt."""
    from code_assistant_manager.prompts import PromptManager

    # Validate inputs
    if app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    if level not in VALID_LEVELS:
        typer.echo(
            f"Error: Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}"
        )
        raise typer.Exit(1)

    if app == "copilot" and level != "project":
        typer.echo("Error: Copilot prompts can only be project-level.")
        raise typer.Exit(1)

    if level == "project":
        project_dir = ensure_project_dir(project_dir)

    try:
        manager = PromptManager()

        # Generate prompt ID
        prompt_id = generate_prompt_id(f"{app}-{name}")

        # Create prompt
        prompt = manager.create_prompt(
            prompt_id=prompt_id,
            app=app,
            level=level,
            content=content,
            description=description,
            project_dir=project_dir,
        )

        typer.echo(f"Created prompt: {prompt.prompt_id}")

        # Set as default if requested
        if set_default:
            manager.set_default_prompt(app, level, prompt_id, project_dir)
            typer.echo(f"Set as default for {app} ({level})")

    except Exception as e:
        logger.error(f"Error adding prompt: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def update_prompt(
    prompt_id: str,
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="New description"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="New name/identifier"
    ),
):
    """Update an existing prompt."""
    from code_assistant_manager.prompts import PromptManager

    if not any([content, description, name]):
        typer.echo(
            "Error: Must specify at least one field to update (--content, --description, or --name)"
        )
        raise typer.Exit(1)

    try:
        manager = PromptManager()

        # Get current prompt
        current_prompt = manager.get_prompt(prompt_id)
        if not current_prompt:
            typer.echo(f"Error: Prompt '{prompt_id}' not found.")
            raise typer.Exit(1)

        # Update prompt
        updated_prompt = manager.update_prompt(
            prompt_id=prompt_id,
            content=content,
            description=description,
            name=name,
        )

        typer.echo(f"Updated prompt: {updated_prompt.prompt_id}")

    except Exception as e:
        logger.error(f"Error updating prompt '{prompt_id}': {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def remove_prompt(
    prompt_id: str,
    force: bool = typer.Option(
        False, "--force", "-f", help="Force removal without confirmation"
    ),
):
    """Remove a prompt."""
    from code_assistant_manager.prompts import PromptManager

    try:
        manager = PromptManager()

        # Check if prompt exists
        prompt = manager.get_prompt(prompt_id)
        if not prompt:
            typer.echo(f"Error: Prompt '{prompt_id}' not found.")
            raise typer.Exit(1)

        # Confirm removal unless forced
        if not force:
            typer.echo(
                f"Are you sure you want to remove prompt '{prompt_id}'? (y/N): ",
                nl=False,
            )
            confirmation = input().strip().lower()
            if confirmation not in ["y", "yes"]:
                typer.echo("Cancelled.")
                return

        # Remove prompt
        manager.remove_prompt(prompt_id)
        typer.echo(f"Removed prompt: {prompt_id}")

    except Exception as e:
        logger.error(f"Error removing prompt '{prompt_id}': {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
