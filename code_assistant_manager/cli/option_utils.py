"""Shared helpers for CLI option validation and normalization."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import typer

from code_assistant_manager.menu.base import Colors


def _emit_error(message: str) -> None:
    """Print a formatted error message and exit."""
    typer.echo(f"{Colors.RED}✗ {message}{Colors.RESET}")
    raise typer.Exit(1)


def _split_values(raw: str) -> List[str]:
    """Split a comma-delimited option string into individual values."""
    parts = [part.strip() for part in raw.split(",")]
    values = [part for part in parts if part]
    return values or ([raw.strip()] if raw.strip() else [])


def resolve_app_targets(
    value: Optional[str],
    valid_apps: Sequence[str],
    *,
    option_label: str = "--app",
    default: Optional[str] = None,
    allow_all: bool = True,
    fallback_to_all_if_none: bool = False,
) -> List[str]:
    """Resolve an app option into a list of normalized app identifiers."""
    selection = value if value is not None else default
    if selection is None and fallback_to_all_if_none:
        selection = "all"
    if selection is None:
        _emit_error(f"{option_label} is required")

    tokens = _split_values(selection)
    if not tokens:
        _emit_error(f"{option_label} cannot be empty")

    resolved: List[str] = []
    for token in tokens:
        normalized = token.lower()
        if allow_all and normalized == "all":
            return list(valid_apps)
        if normalized not in valid_apps:
            valid_list = ", ".join(valid_apps)
            all_hint = " or 'all'" if allow_all else ""
            _emit_error(
                f"Invalid value '{token}' for {option_label}. Valid: {valid_list}{all_hint}"
            )
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def resolve_single_app(
    value: Optional[str],
    valid_apps: Sequence[str],
    *,
    option_label: str = "--app",
    default: Optional[str] = None,
) -> str:
    """Resolve an app option that must target exactly one app."""
    apps = resolve_app_targets(
        value,
        valid_apps,
        option_label=option_label,
        default=default,
        allow_all=False,
    )
    if len(apps) != 1:
        _emit_error(f"{option_label} accepts a single app value")
    return apps[0]


def resolve_level_targets(
    value: Optional[str],
    valid_levels: Sequence[str],
    *,
    option_label: str = "--level",
    default: Optional[str] = None,
    allow_all: bool = True,
) -> List[str]:
    """Resolve a level option into one or more levels."""
    selection = value if value is not None else default
    if selection is None:
        _emit_error(f"{option_label} is required")

    tokens = _split_values(selection)
    if not tokens:
        _emit_error(f"{option_label} cannot be empty")

    resolved: List[str] = []
    for token in tokens:
        normalized = token.lower()
        if allow_all and normalized == "all":
            return list(valid_levels)
        if normalized not in valid_levels:
            valid_list = ", ".join(valid_levels)
            all_hint = " or 'all'" if allow_all else ""
            _emit_error(
                f"Invalid value '{token}' for {option_label}. Valid: {valid_list}{all_hint}"
            )
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def resolve_single_level(
    value: Optional[str],
    valid_levels: Sequence[str],
    *,
    option_label: str = "--level",
    default: Optional[str] = None,
) -> str:
    """Resolve a level option that must target exactly one level."""
    levels = resolve_level_targets(
        value,
        valid_levels,
        option_label=option_label,
        default=default,
        allow_all=False,
    )
    if len(levels) != 1:
        _emit_error(f"{option_label} accepts a single level value")
    return levels[0]


def ensure_project_dir(level: str, project_dir: Optional[Path]) -> Optional[Path]:
    """Ensure a project directory exists when required for the provided level."""
    if level == "project" and project_dir is None:
        return Path.cwd()
    return project_dir
