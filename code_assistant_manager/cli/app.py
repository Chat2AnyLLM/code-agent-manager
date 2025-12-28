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
    SCOPE_OPTION,
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


        ...,


        help="Configuration key=value pair (e.g., codex.profiles.grok-code-fast-1.model=qwen3-coder-plus)",


    ),


    scope: str = SCOPE_OPTION,


):


    """Set a configuration value for code assistants.





    Supports dotted key notation for nested configuration values.


    Examples:


        cam config set codex.model=gpt-4


        cam config set --scope project claude.theme=dark


        cam config set codex.profiles.my-profile.model=qwen3-coder-plus


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        # Parse key=value


        if "=" not in key_value:


            typer.echo(


                f"{Colors.RED}✗ Invalid format. Use key=value syntax{Colors.RESET}"


            )


            raise typer.Exit(1)





        key_path, value = key_value.split("=", 1)


        key_path = key_path.strip()


        value = value.strip()





        # Parse dotted key path using TOML-aware parser


        # We need to extract the prefix (tool name) first


        # But wait, BaseToolConfig._parse_key_path does splitting too.


        # However, we need to know WHICH tool to load first.


        # So we reuse the parse_toml_key_path helper here for now or duplicate logic.


        parts = parse_toml_key_path(key_path)


        if len(parts) < 2:


            typer.echo(


                f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}"


            )


            raise typer.Exit(1)





        prefix = parts[0]  # e.g., "codex"


        config_key = ".".join(parts[1:])  # Reconstruct the key without prefix





        # Get tool config


        tool_config = get_tool_config(prefix)


        if not tool_config:


            typer.echo(


                f"{Colors.RED}✗ Unsupported config prefix (tool): {prefix}{Colors.RESET}"


            )


            raise typer.Exit(1)





        # Set value


        saved_path = tool_config.set_value(config_key, value, scope)





        typer.echo(


            f"{Colors.GREEN}✓ Set {key_path} = {value} ({scope} scope){Colors.RESET}"


        )


        typer.echo(f"  Config: {saved_path}")





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


    scope: str = SCOPE_OPTION,


):


    """Unset a configuration value for code assistants.





    Supports dotted key notation for nested configuration values.


    Examples:


        cam config unset codex.model


        cam config unset --scope project claude.theme


        cam config unset codex.profiles.my-profile.model


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        key_path = key_path.strip()





        # Parse dotted key path


        parts = parse_toml_key_path(key_path)


        if len(parts) < 2:


            typer.echo(


                f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}"


            )


            raise typer.Exit(1)





        prefix = parts[0]


        config_key = ".".join(parts[1:])





        # Get tool config


        tool_config = get_tool_config(prefix)


        if not tool_config:


            typer.echo(


                f"{Colors.RED}✗ Unsupported config prefix (tool): {prefix}{Colors.RESET}"


            )


            raise typer.Exit(1)





        found = tool_config.unset_value(config_key, scope)





        if not found:


            typer.echo(


                f"{Colors.YELLOW}! Key '{key_path}' not found in {scope} config{Colors.RESET}"


            )


            raise typer.Exit(0)





        typer.echo(


            f"{Colors.GREEN}✓ Unset {key_path} from {scope} scope{Colors.RESET}"


        )





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








@config_app.command("show", short_help="Show configuration in dotted format")


def show_config(


    key_path: Optional[str] = typer.Argument(


        None, help="Specific config key path to show (optional)"


    ),


    app: str = typer.Option(


        "claude", "-a", "--app", help="App to show config for (default: claude)"


    ),


    scope: Optional[str] = typer.Option(


        None, "--scope", "-s", help="Filter by scope (user, project)"


    ),


):


    """Show configuration for an AI editor app in dotted notation format.





    Examples:


        cam config show                    # Show all claude config


        cam config show -a codex          # Show all codex config


        cam config show --scope project    # Show only project config


        cam config show claude.tipsHistory.config-thinking-mode  # Show specific key


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        tool_config = get_tool_config(app)


        if not tool_config:


            typer.echo(f"{Colors.RED}✗ Unknown app: {app}{Colors.RESET}")


            raise typer.Exit(1)





        # Load configs


        # If specific scope requested, we get a dict with just that scope (BaseToolConfig returns same structure if scope arg is passed? No, check implementation)


        # BaseToolConfig.load_config(scope) returns JUST the data dict for that scope if scope is provided.


        # But existing logic expects a structure mapping scope -> {data, path}.


        # So I need to adapt the usage or the BaseToolConfig.load_config behavior.


        # BaseToolConfig.load_config(None) returns scope mapping. That fits.


        


        if scope:


             # Just load all and filter here to keep consistent structure for display logic below


             all_configs = tool_config.load_config()


             if scope not in all_configs:


                typer.echo(


                    f"{Colors.YELLOW}No configuration found for {app} in scope '{scope}'{Colors.RESET}"


                )


                return


             configs_to_show = {scope: all_configs[scope]}


        else:


             all_configs = tool_config.load_config()


             configs_to_show = all_configs





        if not configs_to_show:


            typer.echo(f"{Colors.YELLOW}No configuration found for {app}{Colors.RESET}")


            return





        # Collect and flatten all requested configs


        merged_flattened = {}


        key_sources = {}





        # Sort scopes so that project overrides user in the merged view


        for s_name in ["user", "project"]:


            if s_name in configs_to_show:


                s_data = configs_to_show[s_name]["data"]


                s_path = configs_to_show[s_name]["path"]


                flattened = flatten_config(s_data, app)


                for k, v in flattened.items():


                    merged_flattened[k] = v


                    key_sources[k] = (s_name, s_path)





        if not merged_flattened:


            typer.echo(f"{Colors.YELLOW}No keys found in requested scope(s){Colors.RESET}")


            return





        # Header


        typer.echo(f"{Colors.CYAN}{app.upper()} Configuration:{Colors.RESET}")


        for s_name, s_info in configs_to_show.items():


            typer.echo(f"  {Colors.BOLD}[{s_name}]{Colors.RESET} {s_info['path']}")


        typer.echo()





        # Filter by key_path if provided


        keys_to_show = sorted(merged_flattened.keys())


        if key_path:


            import re





            if "*" in key_path:


                pattern = re.escape(key_path).replace(r"\*", "[^.]+")


                regex = re.compile(f"^{pattern}$")


                keys_to_show = [k for k in keys_to_show if regex.match(k)]


            else:


                # Direct match or prefix match


                keys_to_show = [


                    k


                    for k in keys_to_show


                    if k == key_path or k.startswith(key_path + ".")


                ]





            if not keys_to_show:


                typer.echo(


                    f"{Colors.RED}✗ Key '{key_path}' not found in {app} configuration{Colors.RESET}"


                )


                raise typer.Exit(1)





        # Display keys


        for key in keys_to_show:


            value = merged_flattened[key]


            s_name, s_path = key_sources[key]


            scope_tag = f" {Colors.DIM}({s_name}){Colors.RESET}" if not scope else ""


            typer.echo(f"{Colors.GREEN}{key}{Colors.RESET} = {value}{scope_tag}")





    except Exception as e:


        typer.echo(f"{Colors.RED}✗ Failed to show config: {e}{Colors.RESET}")


        raise typer.Exit(1)

