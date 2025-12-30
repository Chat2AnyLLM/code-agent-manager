"""CLI commands for extension management.

Supports managing extensions for AI assistants (currently Gemini).
"""

import json
import logging
import sys
from typing import List, Optional

import typer
from typer import Context

logger = logging.getLogger(__name__)

# Create the main extension app
extension_app = typer.Typer(
    help="Manage extensions for AI assistants (currently supports Gemini).\n\n"
    "CAM provides extension management capabilities for compatible assistants.\n"
    "Use 'cam extension browse' to discover available extensions, or use\n"
    "other subcommands to manage installed extensions.",
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


@extension_app.command("browse")
def browse_extensions(
    ctx: Context,
):
    """Browse available Gemini extensions from geminicli.com."""
    try:
        import urllib.request
        
        # Fetch extensions from geminicli.com
        url = "https://geminicli.com/extensions.json"
        logger.debug(f"Fetching extensions from {url}")
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            typer.echo(f"Error: Failed to fetch extensions from {url}", err=True)
            typer.echo(f"Details: {str(e)}", err=True)
            raise typer.Exit(1)
        
        # Display extensions in a flat format (one per line)
        # The API returns either a list directly or a dict with 'extensions' key
        if isinstance(data, list):
            extensions = data
        else:
            extensions = data.get('extensions', [])
        
        if not extensions:
            typer.echo("No extensions found.")
            return
        
        typer.echo(f"\nAvailable Gemini Extensions ({len(extensions)}):\n")
        
        for ext in extensions:
            name = ext.get('extensionName', 'Unknown')
            description = ext.get('extensionDescription', '') or ext.get('repoDescription', 'No description')
            full_name = ext.get('fullName', '')
            url = ext.get('url', '')
            stars = ext.get('stars', 0)
            
            # Format: name - description [author/repo] (⭐ stars)
            line = f"• {name}"
            if description:
                line += f" - {description}"
            if full_name:
                line += f" [{full_name}]"
            if stars > 0:
                line += f" (⭐ {stars})"
            
            typer.echo(line)
        
        typer.echo("")  # Empty line at the end
        
    except ImportError:
        typer.echo("Error: urllib is required but not available", err=True)
        raise typer.Exit(1)


@extension_app.command("install", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def install_extension(
    ctx: Context,
    source: str = typer.Argument(None, help="Extension source (git URL or local path)"),
):
    """Install a Gemini extension from a git repository URL or local path."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions install
    args = ["extensions", "install"]
    
    # Add source if provided
    if source:
        args.append(source)
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("uninstall", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def uninstall_extension(
    ctx: Context,
    names: List[str] = typer.Argument(None, help="Extension name(s) to uninstall"),
):
    """Uninstall one or more Gemini extensions."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions uninstall
    args = ["extensions", "uninstall"]
    
    # Add extension names if provided
    if names:
        args.extend(names)
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("list", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def list_extensions(
    ctx: Context,
):
    """List installed Gemini extensions."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions list
    args = ["extensions", "list"]
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("update", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def update_extension(
    ctx: Context,
    name: Optional[str] = typer.Argument(None, help="Extension name to update (leave empty to update all with --all flag)"),
):
    """Update all extensions or a named extension to the latest version."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions update
    args = ["extensions", "update"]
    
    # Add extension name if provided
    if name:
        args.append(name)
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("disable", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def disable_extension(
    ctx: Context,
    name: str = typer.Argument(..., help="Extension name to disable"),
):
    """Disable a Gemini extension."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions disable
    args = ["extensions", "disable", name]
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("enable", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def enable_extension(
    ctx: Context,
    name: str = typer.Argument(..., help="Extension name to enable"),
):
    """Enable a Gemini extension."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions enable
    args = ["extensions", "enable", name]
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("link", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def link_extension(
    ctx: Context,
    path: str = typer.Argument(..., help="Local path to extension"),
):
    """Link a Gemini extension from a local path."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions link
    args = ["extensions", "link", path]
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("new", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def new_extension(
    ctx: Context,
    path: str = typer.Argument(..., help="Path where to create the extension"),
    template: Optional[str] = typer.Argument(None, help="Template to use"),
):
    """Create a new Gemini extension from a boilerplate example."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions new
    args = ["extensions", "new", path]
    
    # Add template if provided
    if template:
        args.append(template)
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("validate", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def validate_extension(
    ctx: Context,
    path: str = typer.Argument(..., help="Path to extension to validate"),
):
    """Validate a Gemini extension from a local path."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions validate
    args = ["extensions", "validate", path]
    
    # Add any extra flags from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@extension_app.command("settings", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def settings_extension(
    ctx: Context,
):
    """Manage Gemini extension settings."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools.gemini import GeminiTool
    
    # Prepare arguments for gemini extensions settings
    args = ["extensions", "settings"]
    
    # Add any extra arguments from context
    if ctx.args:
        args.extend(ctx.args)
    
    # Initialize config and run gemini command
    try:
        config = ConfigManager()
        tool = GeminiTool(config)
        sys.exit(tool.run(args))
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)
