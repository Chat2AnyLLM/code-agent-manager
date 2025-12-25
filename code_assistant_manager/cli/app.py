import logging
import sys
from typing import List, Optional

import typer
from typer import Context

try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
                home / ".factory" / "settings.json",
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


def parse_toml_key_path(key_path):
    """Parse a dotted key path that may contain TOML quoted keys.

    Examples:
        codex.profiles.myprofile.model -> ['codex', 'profiles', 'myprofile', 'model']
        codex.profiles."alibaba/glm-4.5".model -> ['codex', 'profiles', 'alibaba/glm-4.5', 'model']
        codex.profiles."alibaba/deepseek-v3.2-exp" -> ['codex', 'profiles', 'alibaba/deepseek-v3.2-exp']
    """
    import re

    # First, split by dots but preserve quoted strings
    # Use a regex that matches quoted strings OR unquoted parts
    parts = re.split(r'(?<!\\)"(?:\\.|[^"\\])*"(?:\s*\.\s*|\s*$)|\s*\.\s*', key_path.strip())

    # Clean up the parts - remove empty strings and whitespace
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if part and part not in ['.', '']:
            # Remove surrounding quotes if present
            if part.startswith('"') and part.endswith('"'):
                part = part[1:-1].replace('\\"', '"')
            cleaned_parts.append(part)

    return cleaned_parts


@config_app.command("set", short_help="Set a configuration value for code assistants")
def set_config(
    key_value: str = typer.Argument(
        ..., help="Configuration key=value pair (e.g., codex.profiles.grok-code-fast-1.model=qwen3-coder-plus)"
    ),
):
    """Set a configuration value for code assistants.

    Supports dotted key notation for nested configuration values.
    Examples:
        cam config set codex.model=gpt-4
        cam config set codex.profiles.my-profile.model=qwen3-coder-plus
        cam config set codex.model_provider=openai
    """
    from pathlib import Path
    import tomli_w
    import tomllib

    from code_assistant_manager.menu.base import Colors

    try:
        # Parse key=value
        if "=" not in key_value:
            typer.echo(f"{Colors.RED}✗ Invalid format. Use key=value syntax{Colors.RESET}")
            raise typer.Exit(1)

        key_path, value = key_value.split("=", 1)
        key_path = key_path.strip()
        value = value.strip()

        # Parse dotted key path using TOML-aware parser
        parts = parse_toml_key_path(key_path)
        if len(parts) < 2:
            typer.echo(f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}")
            raise typer.Exit(1)

        prefix = parts[0]  # e.g., "codex"
        config_key_parts = parts[1:]  # e.g., ["profiles", "alibaba/glm-4.5", "model"]

        # Determine config file based on prefix
        if prefix == "codex":
            config_path = Path.home() / ".codex" / "config.toml"
        else:
            typer.echo(f"{Colors.RED}✗ Unsupported config prefix: {prefix}{Colors.RESET}")
            typer.echo(f"  Supported prefixes: codex")
            raise typer.Exit(1)

        # Load existing config
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, 'rb') as f:
                    config_data = tomllib.load(f)
            except Exception as e:
                typer.echo(f"{Colors.YELLOW}! Could not load existing config: {e}{Colors.RESET}")
                typer.echo(f"  Creating new config file")

        # Set the nested value
        def set_nested_value(data, key_parts, val):
            if len(key_parts) == 1:
                data[key_parts[0]] = val
                return data

            current_key = key_parts[0]
            if current_key not in data or not isinstance(data[current_key], dict):
                data[current_key] = {}

            data[current_key] = set_nested_value(data[current_key], key_parts[1:], val)
            return data

        config_data = set_nested_value(config_data, config_key_parts, value)

        # Write back to file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'wb') as f:
            tomli_w.dump(config_data, f)

        typer.echo(f"{Colors.GREEN}✓ Set {key_path} = {value}{Colors.RESET}")
        typer.echo(f"  Config: {config_path}")

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Failed to set config value: {e}{Colors.RESET}")
        raise typer.Exit(1)


@config_app.command("unset", short_help="Unset a configuration value for code assistants")
def unset_config(
    key_path: str = typer.Argument(
        ..., help="Configuration key path (e.g., codex.profiles.grok-code-fast-1.model)"
    ),
):
    """Unset a configuration value for code assistants.

    Supports dotted key notation for nested configuration values.
    Examples:
        cam config unset codex.model
        cam config unset codex.profiles.my-profile.model
        cam config unset codex.model_provider
    """
    from pathlib import Path
    import tomli_w
    import tomllib

    from code_assistant_manager.menu.base import Colors

    try:
        key_path = key_path.strip()

        # Parse dotted key path using TOML-aware parser
        parts = parse_toml_key_path(key_path)
        if len(parts) < 2:
            typer.echo(f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}")
            raise typer.Exit(1)

        prefix = parts[0]  # e.g., "codex"
        config_key_parts = parts[1:]  # e.g., ["profiles", "alibaba/deepseek-v3", "2-exp"]

        # Special handling for unset: if the key parts seem to be incorrectly split,
        # try to reconstruct the key name
        if len(config_key_parts) > 2:
            # Check if the last parts look like they should be joined
            # This handles cases like ['profiles', 'alibaba/deepseek-v3', '2-exp']
            # where it should be ['profiles', 'alibaba/deepseek-v3.2-exp']
            table_name = config_key_parts[0]
            key_parts_to_join = config_key_parts[1:]
            reconstructed_key = '.'.join(key_parts_to_join)
            config_key_parts = [table_name, reconstructed_key]

        # Determine config file based on prefix
        if prefix == "codex":
            config_path = Path.home() / ".codex" / "config.toml"
        else:
            typer.echo(f"{Colors.RED}✗ Unsupported config prefix: {prefix}{Colors.RESET}")
            typer.echo(f"  Supported prefixes: codex")
            raise typer.Exit(1)

        # Check if config file exists
        if not config_path.exists():
            typer.echo(f"{Colors.YELLOW}! Config file not found: {config_path}{Colors.RESET}")
            raise typer.Exit(0)

        # Load existing config
        config_data = {}
        try:
            with open(config_path, 'rb') as f:
                config_data = tomllib.load(f)
        except Exception as e:
            typer.echo(f"{Colors.RED}✗ Could not load config file: {e}{Colors.RESET}")
            raise typer.Exit(1)

        # Unset the nested value
        def unset_nested_value(data, key_parts):
            if len(key_parts) == 1:
                key = key_parts[0]

                # Try multiple variations of the key
                candidates = [key]  # exact match first

                # If key contains special characters, try quoted version
                if '/' in key or any(c in key for c in '.-'):
                    candidates.append(f'"{key}"')

                # If key looks like it might have been split incorrectly, try reconstructing
                # For example, if we have ['alibaba/deepseek-v3', '2-exp'], try 'alibaba/deepseek-v3.2-exp'
                if len(key_parts) > 1 and len(key_parts) == 1:  # This is the leaf key
                    # Check if there are more parts that should be joined
                    pass  # This logic is complex, let's try the candidates approach first

                for candidate in candidates:
                    if candidate in data:
                        del data[candidate]
                        return data, True

                return data, False

            current_key = key_parts[0]
            if current_key not in data or not isinstance(data[current_key], dict):
                return data, False

            data[current_key], found = unset_nested_value(data[current_key], key_parts[1:])
            return data, found

        config_data, found = unset_nested_value(config_data, config_key_parts)

        if not found:
            typer.echo(f"{Colors.YELLOW}! Key '{key_path}' not found in config{Colors.RESET}")
            raise typer.Exit(0)

        # Write back to file
        with open(config_path, 'wb') as f:
            tomli_w.dump(config_data, f)

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Failed to unset config value: {e}{Colors.RESET}")
        raise typer.Exit(1)


def flatten_config(data: dict, prefix: str = "") -> dict:
    """Flatten nested dictionary into dotted notation."""
    result = {}

    def _flatten(obj, current_prefix):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{current_prefix}.{key}" if current_prefix else key
                _flatten(value, new_prefix)
        elif isinstance(obj, list):
            # For lists, convert to string representation
            result[current_prefix] = str(obj)
        else:
            # Convert all values to strings
            result[current_prefix] = str(obj)

    _flatten(data, prefix)
    return result


def load_app_config(app_name: str) -> tuple[dict, str]:
    """Load configuration for a specific app.

    Returns:
        Tuple of (config_dict, config_file_path)
    """
    from pathlib import Path

    # Define config file mappings for each app
    config_mappings = {
        "claude": [
            Path.home() / ".claude" / "settings.json",
            Path.home() / ".claude.json",
            Path.home() / ".claude" / "settings.local.json",
            Path.cwd() / ".claude" / "settings.json",
            Path.cwd() / ".claude" / "settings.local.json",
        ],
        "codex": [
            Path.home() / ".codex" / "config.toml",
        ],
        "cursor-agent": [
            Path.home() / ".cursor" / "mcp.json",
            Path.home() / ".cursor" / "settings.json",
            Path.cwd() / ".cursor" / "mcp.json",
        ],
        "gemini": [
            Path.home() / ".gemini" / "settings.json",
            Path.cwd() / ".gemini" / "settings.json",
        ],
        "copilot": [
            Path.home() / ".copilot" / "mcp-config.json",
            Path.home() / ".copilot" / "mcp.json",
        ],
        "qwen": [
            Path.home() / ".qwen" / "settings.json",
        ],
        "codebuddy": [
            Path.home() / ".codebuddy.json",
            Path.cwd() / ".codebuddy" / "mcp.json",
        ],
        "crush": [
            Path.home() / ".config" / "crush" / "crush.json",
        ],
        "droid": [
            Path.home() / ".factory" / "mcp.json",
            Path.home() / ".factory" / "settings.json",
        ],
        "iflow": [
            Path.home() / ".iflow" / "settings.json",
            Path.home() / ".iflow" / "config.json",
        ],
        "neovate": [
            Path.home() / ".neovate" / "config.json",
        ],
        "qodercli": [
            Path.home() / ".qodercli" / "config.json",
        ],
        "zed": [
            Path.home() / ".config" / "zed" / "settings.json",
        ],
    }

    if app_name not in config_mappings:
        raise typer.Exit(f"Unknown app: {app_name}. Supported apps: {', '.join(config_mappings.keys())}")

    # Try to load config from the first available file
    for config_path in config_mappings[app_name]:
        if config_path.exists():
            try:
                if config_path.suffix == ".toml":
                    with open(config_path, 'rb') as f:
                        config_data = tomllib.load(f)
                else:  # JSON files
                    import json
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)

                return config_data, str(config_path)
            except Exception as e:
                logger.warning(f"Failed to load {config_path}: {e}")
                continue

    # If no config file found, return empty dict
    return {}, "No config file found"


@config_app.command("show", short_help="Show configuration in dotted format")
def show_config(
    key_path: Optional[str] = typer.Argument(None, help="Specific config key path to show (optional)"),
    app: str = typer.Option("claude", "-a", "--app", help="App to show config for (default: claude)"),
):
    """Show configuration for an AI editor app in dotted notation format.

    Examples:
        cam config show                    # Show all claude config
        cam config show -a codex          # Show all codex config
        cam config show --app cursor-agent # Show all cursor config
        cam config show claude.tipsHistory.config-thinking-mode  # Show specific key
    """
    from code_assistant_manager.menu.base import Colors

    try:
        config_data, config_path = load_app_config(app)

        if not config_data:
            typer.echo(f"{Colors.YELLOW}No configuration found for {app}{Colors.RESET}")
            typer.echo(f"Config path: {config_path}")
            return

        # Flatten the config
        flattened = flatten_config(config_data, app)

        # If a specific key path is requested
        if key_path:
            if key_path in flattened:
                value = flattened[key_path]
                typer.echo(f"{Colors.GREEN}{key_path}{Colors.RESET} = {value}")
            else:
                matching_keys = []

                # Check for wildcard patterns (containing '*')
                if "*" in key_path:
                    import re
                    # Convert wildcard pattern to regex: * becomes [^.]+
                    # Escape regex special characters and replace * with [^.]+
                    pattern = re.escape(key_path).replace(r"\*", "[^.]+")
                    regex = re.compile(f"^{pattern}$")

                    matching_keys = [k for k in flattened.keys() if regex.match(k)]
                    match_type = "pattern"
                else:
                    # Check for prefix matches (e.g., 'codex.profiles' should show all profiles)
                    prefix = key_path + "."
                    matching_keys = [k for k in flattened.keys() if k.startswith(prefix)]
                    match_type = "prefix"

                if matching_keys:
                    if match_type == "pattern":
                        typer.echo(f"{Colors.CYAN}{app.upper()} Configuration - Keys matching pattern '{key_path}':{Colors.RESET}")
                    else:
                        typer.echo(f"{Colors.CYAN}{app.upper()} Configuration - Keys matching '{key_path}':{Colors.RESET}")
                    typer.echo(f"Config file: {config_path}")
                    typer.echo()

                    # Sort matching keys for consistent output
                    for key in sorted(matching_keys):
                        value = flattened[key]
                        typer.echo(f"{Colors.GREEN}{key}{Colors.RESET} = {value}")
                else:
                    typer.echo(f"{Colors.RED}✗ Key '{key_path}' not found in {app} configuration{Colors.RESET}")
                    typer.echo(f"Config file: {config_path}")
                    available_keys = sorted(flattened.keys())
                    if available_keys:
                        typer.echo(f"\nAvailable keys ({len(available_keys)}):")
                        for key in available_keys[:10]:  # Show first 10 keys
                            typer.echo(f"  {key}")
                        if len(available_keys) > 10:
                            typer.echo(f"  ... and {len(available_keys) - 10} more")
                    raise typer.Exit(1)
            return

        # Display all config (original behavior)
        typer.echo(f"{Colors.CYAN}{app.upper()} Configuration:{Colors.RESET}")
        typer.echo(f"File: {config_path}")
        typer.echo()

        # Sort keys for consistent output
        for key in sorted(flattened.keys()):
            value = flattened[key]
            typer.echo(f"{Colors.GREEN}{key}{Colors.RESET} = {value}")

    except Exception as e:
        typer.echo(f"{Colors.RED}✗ Failed to show config: {e}{Colors.RESET}")
        raise typer.Exit(1)
