"""Prompt uninstallation operations."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

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


def _build_targets(
    app: Optional[str],
    level: Optional[str],
    project_dir: Optional[Path],
) -> List[Dict]:
    """Build target list for uninstallation."""
    targets = []
    apps = [app] if app else VALID_APP_TYPES
    levels = [level] if level else VALID_LEVELS

    for a in apps:
        for l in levels:
            targets.append({"app": a, "level": l, "project_dir": project_dir})

    return targets


def uninstall_prompt(
    target: str = typer.Option(
        ...,
        "--target",
        "-t",
        help="What to uninstall (app, level, or 'all')",
    ),
    app: Optional[str] = typer.Option(
        None, "--app", "-a", help="Specific app to uninstall prompts for"
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l", help="Specific level to uninstall from"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation prompts"
    ),
):
    """Uninstall prompts by target criteria."""
    # Validate inputs
    if target not in ["app", "level", "all"]:
        typer.echo("Error: Target must be 'app', 'level', or 'all'")
        raise typer.Exit(1)

    if target == "app" and not app:
        typer.echo("Error: --app is required when target is 'app'")
        raise typer.Exit(1)

    if target == "level" and not level:
        typer.echo("Error: --level is required when target is 'level'")
        raise typer.Exit(1)

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

    # Determine what to uninstall
    if target == "all":
        targets = _build_targets(None, None, project_dir)
    elif target == "app":
        targets = _build_targets(app, None, project_dir)
    elif target == "level":
        targets = _build_targets(None, level, project_dir)

    if not targets:
        typer.echo("No targets found to uninstall.")
        return

    # Collect all prompts to be removed
    all_targets = _collect_uninstall_targets(targets)

    if not all_targets:
        typer.echo("No prompts found to uninstall.")
        return

    # Show what will be removed and confirm (skip if force)
    if not force and not _confirm_uninstall(all_targets):
        typer.echo("Uninstall cancelled.")
        return

    # Perform the uninstall
    _perform_uninstall(all_targets)
    typer.echo("Uninstall completed.")


def _collect_uninstall_targets(targets: List[Dict]) -> List[Dict]:
    """Collect all prompts that would be removed by the uninstall operation."""
    all_targets = []

    for target in targets:
        app = target["app"]
        level = target["level"]
        project_dir = target.get("project_dir")

        manager = PromptManager()
        prompts = manager.list_prompts(app=app, level=level, project_dir=project_dir)

        for prompt in prompts:
            all_targets.append(
                {
                    "prompt_id": prompt.id,
                    "app": app,
                    "level": level,
                    "project_dir": project_dir,
                    "description": prompt.description,
                }
            )

    return all_targets


def _collect_codebuddy_targets(project_dir: Optional[Path]) -> List[Dict]:
    """Collect CodeBuddy-specific targets for uninstall."""
    # This would handle CodeBuddy-specific logic
    # For now, return empty list
    return []


def _confirm_uninstall(all_targets: List[Dict]) -> bool:
    """Show uninstall summary and get user confirmation."""
    typer.echo(f"\nThis will remove {len(all_targets)} prompt(s):")

    # Group by app/level
    by_target = {}
    for target in all_targets:
        key = f"{target['app']}/{target['level']}"
        if key not in by_target:
            by_target[key] = []
        by_target[key].append(target)

    for target_key, prompts in by_target.items():
        typer.echo(f"\n{target_key} ({len(prompts)} prompts):")
        for prompt in prompts[:5]:  # Show first 5
            desc = f" - {prompt['description']}" if prompt["description"] else ""
            typer.echo(f"  • {prompt['prompt_id']}{desc}")

        if len(prompts) > 5:
            typer.echo(f"  ... and {len(prompts) - 5} more")

    if len(all_targets) > 10:
        typer.echo(f"\nTotal: {len(all_targets)} prompts will be removed.")

    if len(all_targets) == 0:
        return True

    typer.echo("\nAre you sure you want to proceed? (y/N): ", nl=False)
    confirmation = input().strip().lower()
    return confirmation in ["y", "yes"]


def _perform_uninstall(all_targets: List[Dict]):
    """Execute the uninstall operation."""
    manager = PromptManager()

    for target in all_targets:
        try:
            manager.remove_prompt(target["prompt_id"])
            typer.echo(f"Removed: {target['prompt_id']}")
        except Exception as e:
            logger.error(f"Error removing prompt '{target['prompt_id']}': {e}")
            typer.echo(f"Failed to remove: {target['prompt_id']} ({e})")


def unsync_prompt_alias(
    app: str = typer.Option(..., "--app", "-a", help="App type to unsync"),
    level: str = typer.Option(
        "user", "--level", "-l", help="Level to unsync (user, project)"
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (required for project-level)",
    ),
):
    """Remove synced prompt aliases for an app."""
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
        count = manager.unsync_prompt_aliases(app, level, project_dir)
        typer.echo(f"Removed {count} synced prompt alias(es) for {app} ({level})")

    except Exception as e:
        logger.error(f"Error unsyncing prompts: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
