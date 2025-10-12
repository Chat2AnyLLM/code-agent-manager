#!/usr/bin/env python3
"""CLI app setup for Code Assistant Manager."""

import logging
import sys
from typing import List, Optional

import typer
from typer import Context

from code_assistant_manager.cli.agents_commands import agent_app
from code_assistant_manager.cli.plugin_commands import plugin_app
from code_assistant_manager.cli.prompts_commands import prompt_app
from code_assistant_manager.cli.skills_commands import skill_app
from code_assistant_manager.config import ConfigManager
from code_assistant_manager.mcp.cli import app as mcp_app
from code_assistant_manager.tools import (
    display_all_tool_endpoints,
    display_tool_endpoints,
    get_registered_tools,
)

# Module-level typer.Option constants to fix B008 linting errors
from .options import (
    CONFIG_FILE_OPTION,
    CONFIG_OPTION,
    DEBUG_OPTION,
    TOOL_ARGS_OPTION,
    VALIDATE_VERBOSE_OPTION,
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="cam",
    help="Code Assistant Manager - CLI utilities for working with AI coding assistants",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback(invoke_without_command=False)
def global_options(debug: bool = DEBUG_OPTION):
    """Global options for the CLI application."""
    if debug:
        # Configure debug logging for all modules
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.debug("Debug logging enabled")


# Import commands to register them with the app
from . import commands  # noqa: F401,E402

# Create a group for editor commands
editor_app = typer.Typer(
    help="Launch AI code editors: claude, codex, qwen, etc. (alias: l)",
    no_args_is_help=False,
)


@editor_app.callback(invoke_without_command=True)
def launch(ctx: Context):
    """Launch AI code editors."""
    # If no subcommand is provided, show interactive menu to select a tool
    if ctx.invoked_subcommand is None:
        from code_assistant_manager.menu.menus import display_centered_menu

        logger.debug("No subcommand provided, showing interactive menu")
        registered_tools = get_registered_tools()
        editor_tools = {k: v for k, v in registered_tools.items() if k not in ["mcp"]}
        tool_names = sorted(editor_tools.keys())

        logger.debug(f"Available tools for menu: {tool_names}")

        success, selected_idx = display_centered_menu(
            title="Select AI Code Editor", items=tool_names, cancel_text="Cancel"
        )

        if not success or selected_idx is None:
            logger.debug("User cancelled menu selection")
            raise typer.Exit(0)

        selected_tool = tool_names[selected_idx]
        logger.debug(f"User selected tool: {selected_tool}")

        # Initialize context object
        ctx.ensure_object(dict)
        ctx.obj["config_path"] = None
        ctx.obj["debug"] = False
        ctx.obj["endpoints"] = None

        # Get config and launch the selected tool
        config_path = ctx.obj.get("config_path")
        logger.debug(f"Using config path: {config_path}")

        try:
            config = ConfigManager(config_path)
            is_valid, errors = config.validate_config()
            if not is_valid:
                logger.error(f"Configuration validation errors: {errors}")
                typer.echo("Configuration validation errors:")
                for error in errors:
                    typer.echo(f"  - {error}")
                raise typer.Exit(1)
            logger.debug("Configuration loaded and validated successfully")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            typer.echo(f"Error: {e}")
            raise typer.Exit(1) from e

        tool_class = editor_tools[selected_tool]
        tool_instance = tool_class(config)
        sys.exit(tool_instance.run([]))


# Dynamically create subcommands for each editor tool
def create_editor_subcommands():
    """Create subcommands for each registered editor tool."""
    logger.debug("Creating editor subcommands")
    registered_tools = get_registered_tools()
    editor_tools = {k: v for k, v in registered_tools.items() if k not in ["mcp"]}
    logger.debug(f"Found {len(editor_tools)} editor tools: {list(editor_tools.keys())}")

    # Create a wrapper function with default parameters to avoid late binding issues
    def make_command(name, cls):
        def command(
            ctx: Context,
            config: Optional[str] = CONFIG_OPTION,
            tool_args: List[str] = TOOL_ARGS_OPTION,
        ):
            """Launch the specified AI code editor."""
            # Initialize context object
            ctx.ensure_object(dict)
            ctx.obj["config_path"] = config
            ctx.obj["debug"] = False
            ctx.obj["endpoints"] = None

            logger.debug(f"Executing command: {name} with args: {tool_args}")
            config_path = config
            logger.debug(f"Using config path: {config_path}")

            # Initialize config
            try:
                config_obj = ConfigManager(config_path)
                # Validate configuration
                is_valid, errors = config_obj.validate_config()
                if not is_valid:
                    logger.error(f"Configuration validation errors: {errors}")
                    typer.echo("Configuration validation errors:")
                    for error in errors:
                        typer.echo(f"  - {error}")
                    raise typer.Exit(1)
                logger.debug("Configuration loaded and validated successfully")
            except FileNotFoundError as e:
                logger.error(f"Configuration file not found: {e}")
                typer.echo(f"Error: {e}")
                raise typer.Exit(1) from e

            # Handle --endpoints option if specified
            endpoints = ctx.obj.get("endpoints") if ctx.obj else None
            if endpoints:
                logger.debug(f"Handling endpoints option: {endpoints}")
                if endpoints == "all":
                    display_all_tool_endpoints(config_obj)
                else:
                    display_tool_endpoints(config_obj, endpoints)
                raise typer.Exit()

            logger.debug(f"Launching tool: {name}")
            tool_instance = cls(config_obj)
            sys.exit(tool_instance.run(tool_args or []))

        # Set the command name and help text
        command.__name__ = name
        command.__doc__ = f"Launch {name} editor"
        return command

    for tool_name, tool_class in editor_tools.items():
        # Add the command to the editor app
        editor_app.command(name=tool_name)(make_command(tool_name, tool_class))
        logger.debug(f"Added command: {tool_name}")


# Create the editor subcommands
create_editor_subcommands()

# Create a group for config commands
config_app = typer.Typer(
    help="Configuration management commands",
    no_args_is_help=True,
)

# Add the editor app as a subcommand to the main app
app.add_typer(editor_app, name="launch")
app.add_typer(editor_app, name="l", hidden=True)
# Add the config app as a subcommand to the main app
app.add_typer(config_app, name="config")
app.add_typer(config_app, name="cf", hidden=True)
# Add the MCP app as a subcommand to the main app
app.add_typer(mcp_app, name="mcp")
app.add_typer(mcp_app, name="m", hidden=True)
# Add the prompt app as a subcommand to the main app
app.add_typer(prompt_app, name="prompt")
app.add_typer(prompt_app, name="p", hidden=True)
# Add the skill app as a subcommand to the main app
app.add_typer(skill_app, name="skill")
app.add_typer(skill_app, name="s", hidden=True)
# Add the plugin app as a subcommand to the main app (Claude Code plugins)
app.add_typer(plugin_app, name="plugin")
app.add_typer(plugin_app, name="pl", hidden=True)
# Add the agent app as a subcommand to the main app (Claude Code agents)
app.add_typer(agent_app, name="agent")
app.add_typer(agent_app, name="ag", hidden=True)


@config_app.command("validate")
def validate_config(
    config: Optional[str] = CONFIG_FILE_OPTION,
    verbose: bool = VALIDATE_VERBOSE_OPTION,
):
    """Validate the configuration file for syntax and semantic errors."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.menu.base import Colors

    try:
        cm = ConfigManager(config)
        typer.echo(
            f"{Colors.GREEN}✓ Configuration file loaded successfully{Colors.RESET}"
        )

        # Run full validation
        is_valid, errors = cm.validate_config()

        if is_valid:
            typer.echo(f"{Colors.GREEN}✓ Configuration validation passed{Colors.RESET}")
            return 0
        else:
            typer.echo(f"{Colors.RED}✗ Configuration validation failed:{Colors.RESET}")
            for error in errors:
                typer.echo(f"  - {error}")
            return 1

    except FileNotFoundError as e:
        typer.echo(f"{Colors.RED}✗ Configuration file not found: {e}{Colors.RESET}")
        return 1
    except ValueError as e:
        typer.echo(f"{Colors.RED}✗ Configuration validation failed: {e}{Colors.RESET}")
        return 1
    except Exception as e:
        typer.echo(
            f"{Colors.RED}✗ Unexpected error during validation: {e}{Colors.RESET}"
        )
        return 1


@config_app.command("list", short_help="List all configuration file locations")
def list_config():
    """List all configuration file locations including CAM config and editor client configs."""
    from pathlib import Path

    from code_assistant_manager.menu.base import Colors

    typer.echo(f"\n{Colors.BOLD}Configuration Files:{Colors.RESET}\n")

    # CAM's own configuration
    typer.echo(f"{Colors.CYAN}Code Assistant Manager (CAM):{Colors.RESET}")
    home = Path.home()
    cam_config_locations = [
        home / ".config" / "code-assistant-manager" / "providers.json",
        Path.cwd() / "providers.json",
        home / "providers.json",
    ]
    for path in cam_config_locations:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if path.exists() else " "
        typer.echo(f"  {status} {path}")

    # Editor client configurations
    typer.echo(f"\n{Colors.CYAN}Editor Client Configurations:{Colors.RESET}")

    # Define config locations for each editor with descriptions
    editor_configs = {
        "claude": {
            "description": "Claude Code Editor",
            "paths": [
                home / ".claude.json",
                home / ".claude" / "settings.json",
                home / ".claude" / "settings.local.json",
                Path.cwd() / ".claude" / "settings.json",
                Path.cwd() / ".claude" / "settings.local.json",
                Path.cwd() / ".claude" / "mcp.json",
                Path.cwd() / ".claude" / "mcp.local.json",
            ],
        },
        "cursor-agent": {
            "description": "Cursor AI Code Editor",
            "paths": [
                home / ".cursor" / "mcp.json",
                home / ".cursor" / "settings.json",
                Path.cwd() / ".cursor" / "mcp.json",
            ],
        },
        "gemini": {
            "description": "Google Gemini CLI",
            "paths": [
                home / ".gemini" / "settings.json",
                Path.cwd() / ".gemini" / "settings.json",
            ],
        },
        "copilot": {
            "description": "GitHub Copilot CLI",
            "paths": [
                home / ".copilot" / "mcp-config.json",
                home / ".copilot" / "mcp.json",
            ],
        },
        "codex": {
            "description": "OpenAI Codex CLI",
            "paths": [
                home / ".codex" / "config.toml",
            ],
        },
        "qwen": {
            "description": "Qwen Code CLI",
            "paths": [
                home / ".qwen" / "settings.json",
            ],
        },
        "codebuddy": {
            "description": "Tencent CodeBuddy CLI",
            "paths": [
                home / ".codebuddy.json",
                Path.cwd() / ".codebuddy" / "mcp.json",
            ],
        },
        "crush": {
            "description": "Charmland Crush CLI",
            "paths": [
                home / ".config" / "crush" / "crush.json",
            ],
        },
        "droid": {
            "description": "Factory.ai Droid CLI",
            "paths": [
                home / ".factory" / "mcp.json",
                home / ".factory" / "config.json",
            ],
        },
        "iflow": {
            "description": "iFlow CLI",
            "paths": [
                home / ".iflow" / "settings.json",
                home / ".iflow" / "config.json",
            ],
        },
        "neovate": {
            "description": "Neovate Code CLI",
            "paths": [
                home / ".neovate" / "config.json",
            ],
        },
        "qodercli": {
            "description": "Qoder CLI",
            "paths": [
                home / ".qodercli" / "config.json",
            ],
        },
        "zed": {
            "description": "Zed Editor",
            "paths": [
                home / ".config" / "zed" / "settings.json",
            ],
        },
    }

    for editor, config_info in editor_configs.items():
        description = config_info.get("description", editor.capitalize())
        paths = config_info.get("paths", [])
        typer.echo(f"\n  {Colors.BOLD}{description} ({editor}):{Colors.RESET}")
        for path in paths:
            status = f"{Colors.GREEN}✓{Colors.RESET}" if path.exists() else " "
            typer.echo(f"    {status} {path}")

    typer.echo()


# Add list as shorthand commands
config_app.command(name="ls", hidden=True)(list_config)
config_app.command(name="l", hidden=True)(list_config)
