"""Base CLI command classes with common functionality.

Provides standardized patterns for CLI commands including error handling,
logging, parameter validation, and common app resolution logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

import typer

from code_assistant_manager.menu.base import Colors

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """Base class for CLI commands providing common functionality."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize command with optional config path."""
        self.config_path = config_path

    def log_command_start(self, command_name: str, **kwargs):
        """Log the start of a command execution."""
        logger.debug(f"Starting command: {command_name}", extra=kwargs)

    def log_command_end(self, command_name: str, success: bool, **kwargs):
        """Log the end of a command execution."""
        level = logging.INFO if success else logging.ERROR
        logger.log(
            level,
            f"Command completed: {command_name} (success={success})",
            extra=kwargs,
        )

    def handle_error(
        self, error: Exception, message: str = "An error occurred"
    ) -> None:
        """Handle and display errors consistently."""
        logger.error(f"{message}: {error}")
        typer.echo(f"{Colors.RED}✗ {message}: {error}{Colors.RESET}", err=True)
        raise typer.Exit(1)

    def show_success(self, message: str) -> None:
        """Display success messages consistently."""
        logger.info(message)
        typer.echo(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

    def show_warning(self, message: str) -> None:
        """Display warning messages consistently."""
        logger.warning(message)
        typer.echo(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

    def show_info(self, message: str) -> None:
        """Display info messages consistently."""
        logger.info(message)
        typer.echo(f"{Colors.CYAN}{message}{Colors.RESET}")

    def validate_required(self, value: Any, name: str) -> Any:
        """Validate that a required parameter is provided."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self.handle_error(
                ValueError(f"{name} is required"), f"Missing required parameter: {name}"
            )
        return value

    def validate_choice(self, value: Any, choices: List[Any], name: str) -> Any:
        """Validate that a value is one of the allowed choices."""
        if value not in choices:
            self.handle_error(
                ValueError(
                    f"{name} must be one of: {', '.join(str(c) for c in choices)}"
                ),
                f"Invalid {name}: {value}",
            )
        return value

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Prompt user for confirmation with consistent styling."""
        return typer.confirm(f"{Colors.YELLOW}{message}{Colors.RESET}", default=default)

    @abstractmethod
    def execute(self, *args, **kwargs) -> int:
        """Execute the command. Must be implemented by subclasses."""


class AppAwareCommand(BaseCommand):
    """Base command class for operations that work with specific AI apps."""

    VALID_APP_TYPES = ["claude", "codex", "gemini", "copilot", "codebuddy"]

    def resolve_app_type(self, app_type: Optional[str], default: str = "claude") -> str:
        """Resolve and validate app type."""
        if app_type is None:
            app_type = default

        return self.validate_choice(app_type.lower(), self.VALID_APP_TYPES, "app type")

    def get_app_handler(self, app_type: str):
        """Get the handler for a specific app type."""
        try:
            from code_assistant_manager.prompts import get_handler

            return get_handler(app_type)
        except Exception as e:
            self.handle_error(e, f"Failed to get handler for app: {app_type}")

    def validate_app_installed(self, app_type: str) -> None:
        """Validate that the specified app is installed."""
        handler = self.get_app_handler(app_type)
        cli_path = handler.get_cli_path()
        if not cli_path:
            self.handle_error(
                RuntimeError(f"{app_type} CLI not found"),
                f"{app_type.capitalize()} is not installed or not in PATH",
            )


class PluginCommand(AppAwareCommand):
    """Base command class for plugin-related operations."""

    def get_plugin_manager(self):
        """Get the plugin manager instance."""
        try:
            from code_assistant_manager.plugins import PluginManager

            return PluginManager()
        except Exception as e:
            self.handle_error(e, "Failed to initialize plugin manager")

    def validate_marketplace_exists(self, marketplace: str) -> None:
        """Validate that a marketplace exists in configuration."""
        manager = self.get_plugin_manager()
        repo = manager.get_repo(marketplace)
        if not repo:
            self.handle_error(
                ValueError(f"Marketplace '{marketplace}' not found in configuration"),
                f"Marketplace '{marketplace}' not configured. Use 'cam plugin add-repo' first.",
            )

    def parse_plugin_reference(self, plugin_ref: str) -> Tuple[str, Optional[str]]:
        """Parse plugin reference in format 'plugin' or 'plugin@marketplace'."""
        parts = plugin_ref.split("@", 1)
        plugin_name = parts[0]
        marketplace = parts[1] if len(parts) > 1 else None
        return plugin_name, marketplace


class PromptCommand(BaseCommand):
    """Base command class for prompt-related operations."""

    def get_prompt_manager(self):
        """Get the prompt manager instance."""
        try:
            from code_assistant_manager.prompts import PromptManager

            return PromptManager()
        except Exception as e:
            self.handle_error(e, "Failed to initialize prompt manager")

    def validate_prompt_exists(self, prompt_id: str) -> None:
        """Validate that a prompt exists."""
        manager = self.get_prompt_manager()
        prompt = manager.get(prompt_id)
        if not prompt:
            self.handle_error(
                ValueError(f"Prompt '{prompt_id}' not found"),
                f"Prompt '{prompt_id}' does not exist",
            )


def create_command_handler(command_class: type, *args, **kwargs) -> int:
    """Factory function to create and execute a command handler."""
    try:
        command = command_class(*args, **kwargs)
        return command.execute()
    except typer.Exit:
        # Re-raise typer exits to maintain expected behavior
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {e}", exc_info=True)
        typer.echo(f"{Colors.RED}✗ Command failed: {e}{Colors.RESET}", err=True)
        return 1
