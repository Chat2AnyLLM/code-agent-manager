"""Prompt status display operations."""

import logging
from pathlib import Path
from typing import Optional

import typer

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


def show_prompt_status(
    app: Optional[str] = typer.Option(
        None, "--app", "-a", help="Show status for specific app only"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory for project-level prompts",
    ),
):
    """Show comprehensive prompt status across all apps and levels."""
    # Validate inputs
    if app and app not in VALID_APP_TYPES:
        typer.echo(
            f"Error: Invalid app type '{app}'. Valid types: {', '.join(VALID_APP_TYPES)}"
        )
        raise typer.Exit(1)

    try:
        manager = PromptManager()

        if app:
            # Show status for specific app
            _show_app_status(manager, app, project_dir)
        else:
            # Show comprehensive status
            typer.echo(f"\n{COLORS.BOLD}Prompt Status Overview{COLORS.RESET}\n")

            # Show default prompts section
            _show_default_prompt_section(manager)

            # Show per-app status
            apps_to_show = VALID_APP_TYPES
            for app_name in apps_to_show:
                _show_app_status(manager, app_name, project_dir)

    except Exception as e:
        logger.error(f"Error showing prompt status: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def _show_default_prompt_section(manager: PromptManager):
    """Show default prompt information."""
    typer.echo(f"{COLORS.BOLD}Default Prompts:{COLORS.RESET}")

    # Check for defaults at user level
    user_defaults = {}
    for app in USER_LEVEL_APPS:
        default_id = manager.get_default_prompt(app, "user")
        if default_id:
            user_defaults[app] = default_id

    if user_defaults:
        typer.echo("  User Level:")
        for app, prompt_id in user_defaults.items():
            typer.echo(f"    {app}: {prompt_id}")
    else:
        typer.echo("  User Level: None set")

    # Check for defaults at project level (if project_dir available)
    # This would need project_dir context, so we'll skip for now
    typer.echo("  Project Level: Check individual project directories\n")


def _show_level_section(
    manager: PromptManager,
    level: str,
    project_dir: Optional[Path],
):
    """Show prompts for a specific level."""
    prompts = manager.list_prompts(level=level, project_dir=project_dir)
    default_count = sum(1 for p in prompts if p.is_default)
    total_count = len(prompts)

    typer.echo(f"    {level.capitalize()}: {default_count}/{total_count} default")

    if prompts:
        default_id = manager.get_default_prompt(None, level, project_dir)
        if default_id:
            typer.echo(f"      Default: {default_id}")

        # Show recent prompts
        recent = sorted(prompts, key=lambda p: p.id, reverse=True)[:3]
        for prompt in recent:
            status = "✓" if prompt.is_default else "✗"
            default = " (default)" if prompt.id == default_id else ""
            typer.echo(f"      {status} {prompt.id}{default}")


def _show_app_status(manager: PromptManager, app: str, project_dir: Optional[Path]):
    """Show status for a specific app."""
    typer.echo(f"{COLORS.BOLD}{app.upper()}:{COLORS.RESET}")

    if app == "copilot":
        # Copilot is project-level only
        _show_copilot_status(manager, project_dir)
    elif app == "codebuddy":
        _show_codebuddy_status(manager, project_dir)
    else:
        _show_regular_app_status(manager, app, project_dir)


def _show_copilot_status(manager: PromptManager, project_dir: Optional[Path]):
    """Show Copilot-specific status."""
    # Copilot is project-level only
    if project_dir:
        prompts = manager.list_prompts(
            app="copilot", level="project", project_dir=project_dir
        )
        default_count = sum(1 for p in prompts if p.is_default)
        total_count = len(prompts)

        typer.echo(
            f"  Project ({project_dir.name}): {default_count}/{total_count} default"
        )
        if prompts:
            default_id = manager.get_default_prompt("copilot", "project", project_dir)
            if default_id:
                typer.echo(f"    Default: {default_id}")
    else:
        typer.echo("  Project: Requires --project-dir")


def _show_codebuddy_status(manager: PromptManager, project_dir: Optional[Path]):
    """Show CodeBuddy-specific status."""
    # CodeBuddy supports both user and project levels
    typer.echo("  User Level:")
    _show_level_section(manager, "user", None)

    if project_dir:
        typer.echo(f"  Project ({project_dir.name}):")
        _show_level_section(manager, "project", project_dir)
    else:
        typer.echo("  Project: Requires --project-dir")


def _show_regular_app_status(
    manager: PromptManager, app: str, project_dir: Optional[Path]
):
    """Show status for regular apps (user-level only)."""
    _show_level_section(manager, "user", None)


# Import COLORS at the end to avoid circular imports
from code_assistant_manager.menu.base import Colors as COLORS
