"""Default prompt management operations."""

import logging
from typing import Optional

import typer

from code_assistant_manager.cli.option_utils import ensure_project_dir

logger = logging.getLogger(__name__)

# Valid app types - copilot is special (project-level only with different structure)
VALID_APP_TYPES = ["claude", "codex", "gemini", "copilot", "codebuddy"]
VALID_LEVELS = ["user", "project"]


def set_default_prompt(
    app: str = typer.Option(..., "--app", "-a", help="App type"),
    level: str = typer.Option("user", "--level", "-l", help="Level (user, project)"),
    prompt_id: str = typer.Option(
        ..., "--prompt-id", "-p", help="Prompt ID to set as default"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
):
    """Set a prompt as the default for an app and level."""
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

        # Verify prompt exists
        prompt = manager.get_prompt(prompt_id)
        if not prompt:
            typer.echo(f"Error: Prompt '{prompt_id}' not found.")
            raise typer.Exit(1)

        # Set as default
        manager.set_default_prompt(app, level, prompt_id, project_dir)
        typer.echo(f"Set '{prompt_id}' as default for {app} ({level})")

    except Exception as e:
        logger.error(f"Error setting default prompt: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def clear_default_prompt(
    app: str = typer.Option(..., "--app", "-a", help="App type"),
    level: str = typer.Option("user", "--level", "-l", help="Level (user, project)"),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
):
    """Clear the default prompt for an app and level."""
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
        manager.clear_default_prompt(app, level, project_dir)
        typer.echo(f"Cleared default prompt for {app} ({level})")

    except Exception as e:
        logger.error(f"Error clearing default prompt: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
