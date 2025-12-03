"""Prompt installation and synchronization operations."""

import logging
from pathlib import Path
from typing import Optional

import typer

from code_assistant_manager.cli.option_utils import ensure_project_dir
from code_assistant_manager.prompts import PromptManager

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


def install_prompts(
    source: str = typer.Option(..., "--source", "-s", help="Source to install from"),
    app: Optional[str] = typer.Option(
        None, "--app", "-a", help="Specific app to install prompts for"
    ),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to install at (user, project)"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing prompts"
    ),
):
    """Install prompts from a source."""
    # Validate inputs
    if app and app not in VALID_APP_TYPES:
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

        if source.startswith("http"):
            # Install from URL
            typer.echo(f"Installing prompts from URL: {source}")
            count = manager.install_from_url(
                url=source,
                app=app,
                level=level,
                project_dir=project_dir,
                force=force,
            )
        elif Path(source).exists():
            # Install from local file
            typer.echo(f"Installing prompts from file: {source}")
            count = manager.install_from_file(
                file_path=Path(source),
                app=app,
                level=level,
                project_dir=project_dir,
                force=force,
            )
        else:
            typer.echo(f"Error: Source '{source}' not found or invalid.")
            raise typer.Exit(1)

        typer.echo(f"Successfully installed {count} prompt(s)")

    except Exception as e:
        logger.error(f"Error installing prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def sync_prompts_alias(
    source_app: str = typer.Option(..., "--from", "-s", help="Source app"),
    target_app: str = typer.Option(..., "--to", "-t", help="Target app"),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to sync at (user, project)"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing prompts in target"
    ),
):
    """Sync prompts from one app to another as aliases."""
    # Validate inputs
    for app_name in [source_app, target_app]:
        if app_name not in VALID_APP_TYPES:
            typer.echo(
                f"Error: Invalid app type '{app_name}'. Valid types: {', '.join(VALID_APP_TYPES)}"
            )
            raise typer.Exit(1)

    if level not in VALID_LEVELS:
        typer.echo(
            f"Error: Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}"
        )
        raise typer.Exit(1)

    if level == "project":
        project_dir = ensure_project_dir(project_dir)

    try:
        manager = PromptManager()
        count = manager.sync_prompts_as_aliases(
            source_app=source_app,
            target_app=target_app,
            level=level,
            project_dir=project_dir,
            force=force,
        )
        typer.echo(
            f"Successfully synced {count} prompt(s) from {source_app} to {target_app}"
        )

    except Exception as e:
        logger.error(f"Error syncing prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def import_live_prompt(
    app: str = typer.Option(..., "--app", "-a", help="App type to import from"),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to import at (user, project)"
    ),
    prompt_id: str = typer.Option(..., "--id", "-i", help="ID for the imported prompt"),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-desc", help="Description for the imported prompt"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing prompt with same ID"
    ),
):
    """Import a live prompt from an app's interface."""
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

        if app == "copilot":
            content = _import_copilot(manager, project_dir)
        else:
            content = _import_from_app_interface(app)

        if not content:
            typer.echo("Error: Failed to import prompt content.")
            raise typer.Exit(1)

        # Check if prompt already exists
        existing = manager.get_prompt(prompt_id)
        if existing and not force:
            typer.echo(
                f"Error: Prompt '{prompt_id}' already exists. Use --force to overwrite."
            )
            raise typer.Exit(1)

        # Create or update prompt
        if existing:
            prompt = manager.update_prompt(
                prompt_id=prompt_id,
                content=content,
                description=description,
            )
            typer.echo(f"Updated existing prompt: {prompt_id}")
        else:
            prompt = manager.create_prompt(
                prompt_id=prompt_id,
                app=app,
                level=level,
                content=content,
                description=description,
                project_dir=project_dir,
            )
            typer.echo(f"Created new prompt: {prompt_id}")

    except Exception as e:
        logger.error(f"Error importing live prompt: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def _import_copilot(
    manager: PromptManager, project_dir: Optional[Path]
) -> Optional[str]:
    """Import prompt from Copilot interface."""
    try:
        # This would interact with Copilot's interface
        # For now, return a placeholder
        return "Imported content from Copilot interface"
    except Exception:
        return None


def _import_from_app_interface(app: str) -> Optional[str]:
    """Import prompt from app interface."""
    try:
        # This would interact with the app's interface
        # For now, return a placeholder
        return f"Imported content from {app} interface"
    except Exception:
        return None


def show_live_prompt(
    app: str = typer.Option(
        ..., "--app", "-a", help="App type to show live prompt for"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (for project-level prompts)",
    ),
):
    """Show the current live prompt from an app's interface."""
    # Validate inputs
    if app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    try:
        manager = PromptManager()

        if app == "copilot":
            _show_copilot_live_prompt(manager, project_dir)
        elif app == "codebuddy":
            _show_codebuddy_live_prompt(manager, project_dir)
        else:
            _show_regular_live_prompt(manager, app, project_dir)

    except Exception as e:
        logger.error(f"Error showing live prompt: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def _show_copilot_live_prompt(manager: PromptManager, project_dir: Optional[Path]):
    """Show Copilot live prompt."""
    # Implementation for Copilot
    typer.echo("Copilot live prompt content would be shown here")


def _show_codebuddy_live_prompt(manager: PromptManager, project_dir: Optional[Path]):
    """Show CodeBuddy live prompt."""
    # Implementation for CodeBuddy
    typer.echo("CodeBuddy live prompt content would be shown here")


def _show_regular_live_prompt(
    manager: PromptManager, app: str, project_dir: Optional[Path]
):
    """Show live prompt for regular apps."""
    # Implementation for other apps
    typer.echo(f"{app} live prompt content would be shown here")


def import_prompts(
    source: str = typer.Option(
        ..., "--source", "-s", help="Source file to import from"
    ),
    app: Optional[str] = typer.Option(
        None, "--app", "-a", help="Specific app to import prompts for"
    ),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to import at (user, project)"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing prompts"
    ),
):
    """Import prompts from a JSON file."""
    # Validate inputs
    if app and app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    if level not in VALID_LEVELS:
        typer.echo(
            f"Error: Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}"
        )
        raise typer.Exit(1)

    if level == "project":
        project_dir = ensure_project_dir(project_dir)

    try:
        manager = PromptManager()
        count = manager.import_prompts_from_file(
            file_path=Path(source),
            app=app,
            level=level,
            project_dir=project_dir,
            force=force,
        )
        typer.echo(f"Successfully imported {count} prompt(s) from {source}")

    except Exception as e:
        logger.error(f"Error importing prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def export_prompts(
    target: str = typer.Option(..., "--target", "-t", help="Target file to export to"),
    app: Optional[str] = typer.Option(
        None, "--app", "-a", help="Specific app to export prompts for"
    ),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to export from (user, project)"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
):
    """Export prompts to a JSON file."""
    # Validate inputs
    if app and app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    if level not in VALID_LEVELS:
        typer.echo(
            f"Error: Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}"
        )
        raise typer.Exit(1)

    if level == "project":
        project_dir = ensure_project_dir(project_dir)

    try:
        manager = PromptManager()
        count = manager.export_prompts_to_file(
            file_path=Path(target),
            app=app,
            level=level,
            project_dir=project_dir,
        )
        typer.echo(f"Successfully exported {count} prompt(s) to {target}")

    except Exception as e:
        logger.error(f"Error exporting prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
