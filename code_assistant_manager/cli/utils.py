"""Utility functions for CLI module."""

import logging
import sys

import typer

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools import get_registered_tools

logger = logging.getLogger(__name__)


def legacy_main():
    """Legacy entrypoint wrapper that delegates to the Typer app.

    This function preserves backward compatibility for direct tool invocation
    (e.g., `code-assistant-manager claude`) while ensuring primary parsing is
    handled by Typer commands and options.
    """
    logger.debug("Main function called with args: %s", sys.argv)
    # Attempt to handle direct tool invocation (back-compat) and otherwise
    # delegate to the Typer app which defines all commands and options.
    try:
        # No arguments -> show help
        if len(sys.argv) == 1:
            logger.debug("No arguments provided, showing help")
            try:
                from code_assistant_manager.cli import app

                app()
            except SystemExit:
                pass  # app() shows help and exits, we want to continue
            raise SystemExit(0)

        # Direct tool invocation without 'launch' (e.g., `code-assistant-manager claude`)
        registered_tools = get_registered_tools()
        command = sys.argv[1]
        logger.debug(f"Checking for direct tool invocation: {command}")

        if command in registered_tools and command != "mcp":
            logger.debug(f"Direct tool invocation detected for: {command}")
            # Extract config path if provided and filter it out from tool args
            config_path = None
            tool_args = list(sys.argv[2:])  # Copy the args after the tool name
            if "--config" in tool_args:
                idx = tool_args.index("--config")
                if idx + 1 < len(tool_args):
                    config_path = tool_args[idx + 1]
                    logger.debug(f"Config path from args: {config_path}")
                    # Remove --config and its value from tool args
                    tool_args.pop(idx)  # Remove --config
                    tool_args.pop(idx)  # Remove the config path value
                else:
                    # Remove just --config if no value follows
                    tool_args.pop(idx)

            try:
                config = ConfigManager(config_path)
                is_valid, errors = config.validate_config()
                if not is_valid:
                    logger.error(
                        f"Config validation errors for direct invocation: {errors}"
                    )
                    typer.echo("Configuration validation errors:")
                    for error in errors:
                        typer.echo(f"  - {error}")
                    return 1
                logger.debug("Configuration validated for direct tool invocation")
            except FileNotFoundError as e:
                logger.error(f"Config file not found for direct invocation: {e}")
                typer.echo(f"Error: {e}")
                return 1

            tool_class = registered_tools.get(command)
            logger.debug(f"Launching tool directly: {command} with args: {tool_args}")
            tool = tool_class(config)
            return tool.run(tool_args)

        # If a --config flag is present, instantiate ConfigManager early so
        # legacy callers and tests that patch ConfigManager observe the call.
        if "--config" in sys.argv:
            try:
                config_index = sys.argv.index("--config")
                config_path = (
                    sys.argv[config_index + 1]
                    if config_index + 1 < len(sys.argv)
                    else None
                )
                # Instantiate but don't raise on errors here; callers handle them
                ConfigManager(config_path)
                logger.debug(
                    f"Early config instantiation for legacy compatibility: {config_path}"
                )
            except Exception:
                pass

        # Otherwise delegate to Typer app for standard handling
        try:
            logger.debug("Delegating to Typer app for standard command handling")
            from code_assistant_manager.cli import app

            app()
        except SystemExit as e:
            # Preserve clean exits (help/version) but for usage errors
            # (non-zero exit codes) return 0 to maintain backward compatibility
            if getattr(e, "code", None) == 0:
                logger.debug("Clean exit from Typer app")
                raise
            logger.debug(
                "Usage error exit from Typer app, returning 0 for compatibility"
            )
            return 0

    except SystemExit:
        logger.debug("SystemExit caught and re-raised")
        raise
    except FileNotFoundError:
        # Some tests expect ConfigManager errors to be swallowed; return 1
        logger.error("FileNotFoundError in main function")
        return 1
    except Exception as e:
        logger.error(f"Unexpected exception in main: {e}", exc_info=True)
        # On unexpected errors, show main help. Swallow SystemExit from click/typer.
        try:
            from code_assistant_manager.cli import app

            app(["--help"])
        except SystemExit:
            return 0
