"""CLI commands for prompt management."""

import logging

import typer

# Import functions from refactored modules

logger = logging.getLogger(__name__)

prompt_app = typer.Typer(
    help="Manage prompts for AI assistants (Claude, Codex, Gemini, Copilot, CodeBuddy)",
    no_args_is_help=True,
)
