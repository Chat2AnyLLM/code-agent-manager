"""Uninstall command helpers and context for Code Assistant Manager.

This module contains all uninstall-related functionality:
- UninstallContext dataclass for operation state
- Tool configuration directory mappings
- NPM package name mappings
- Helper functions for uninstall operations
"""

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import typer
from typer import Context

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.menu.base import Colors
from code_assistant_manager.tools import get_registered_tools


@dataclass
class UninstallContext:
    """Context for uninstall operation."""

    tools_to_uninstall: List[str]
    installed_tools: List[str]
    config_dirs: Dict[str, Path]
    tools_with_config: List[str]
    keep_config: bool
    force: bool


# Tool configuration directories mapping
TOOL_CONFIG_DIRS: Dict[str, Path] = {
    "claude": Path.home() / ".claude",
    "crush": Path.home() / ".config" / "crush",
    "codex": Path.home() / ".codex",
    "gemini": Path.home() / ".gemini",
    "codebuddy": Path.home() / ".codebuddy",
    "droid": Path.home() / ".droid",
    "iflow": Path.home() / ".iflow",
    "neovate": Path.home() / ".neovate",
    "qodercli": Path.home() / ".qodercli",
    "qwen": Path.home() / ".qwen",
    "zed": Path.home() / ".zed",
    "copilot": Path.home() / ".copilot",
    "cursor-agent": Path.home() / ".cursor-agent",
}

# NPM package name mapping
NPM_PACKAGE_MAP: Dict[str, str] = {
    "claude": "@anthropic-ai/claude-code",
    "crush": "@charmland/crush",
    "codex": "@openai/codex",
    "gemini": "@google/genai",
    "qwen": "@qwen-code/qwen-code",
    "codebuddy": "@tencent-ai/codebuddy-code",
    "droid": "@factory-ai/droid",
    "iflow": "@iflytek/iflow",
    "neovate": "@neovate/cli",
    "qodercli": "@qoder/qodercli",
    "copilot": "@githubnext/copilot-cli",
    "cursor-agent": "@cursor/agent",
    "zed": "zed",
}


def get_config_manager(ctx: Context) -> ConfigManager:
    """Get or create ConfigManager from context."""
    try:
        config_path = None
        if ctx and ctx.obj and hasattr(ctx.obj, "get"):
            config_path = ctx.obj.get("config_path")
        return ConfigManager(config_path) if config_path else ConfigManager()
    except Exception:
        return ConfigManager()


def get_installed_tools(
    target: str, config: ConfigManager
) -> tuple[List[str], Optional[int]]:
    """Get list of installed tools based on target.

    Returns:
        Tuple of (installed_tools, error_code or None)
    """
    upgradeable_tools = get_registered_tools()

    # Validate target
    if target != "all" and target not in upgradeable_tools:
        typer.echo(f"{Colors.RED}Error: Unknown tool {target!r}{Colors.RESET}")
        return [], 1

    # Determine which tools to check
    tools_to_check = [target] if target != "all" else list(upgradeable_tools.keys())

    # Filter to only installed tools
    installed_tools = []
    for tool_name in tools_to_check:
        try:
            tool = upgradeable_tools[tool_name](config)
            if tool._check_command_available(tool.command_name):
                installed_tools.append(tool_name)
        except Exception:
            pass

    return installed_tools, None


def display_uninstall_plan(ctx: UninstallContext) -> None:
    """Display what will be uninstalled."""
    typer.echo(f"\n{Colors.BOLD}Tools to uninstall:{Colors.RESET}")
    for tool_name in ctx.installed_tools:
        typer.echo(f"  • {tool_name}")

    if ctx.tools_with_config and not ctx.keep_config:
        typer.echo(f"\n{Colors.BOLD}Configuration directories to backup:{Colors.RESET}")
        for tool in ctx.tools_with_config:
            config_dir = ctx.config_dirs.get(tool)
            typer.echo(f"  • {config_dir}")


def confirm_uninstall(ctx: UninstallContext) -> bool:
    """Prompt for confirmation if not forced."""
    if ctx.force:
        return True

    if ctx.tools_with_config and not ctx.keep_config:
        typer.echo(
            f"\n{Colors.YELLOW}⚠️  Configuration files will be backed up{Colors.RESET}"
        )
    else:
        typer.echo(
            f"\n{Colors.YELLOW}⚠️  Configuration files will be deleted{Colors.RESET}"
        )

    return typer.confirm(
        f"Continue with uninstalling {len(ctx.installed_tools)} tool(s)?"
    )


def backup_configs(ctx: UninstallContext) -> Optional[Path]:
    """Backup configuration directories.

    Returns:
        Backup directory path or None if no backup was made
    """
    if not ctx.tools_with_config or ctx.keep_config:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = (
        Path.home() / f".config/code-assistant-manager/backup/uninstall_{timestamp}"
    )
    backup_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"\n{Colors.BOLD}Backing up configuration files...{Colors.RESET}")
    for tool in ctx.tools_with_config:
        config_dir = ctx.config_dirs.get(tool)
        try:
            backup_path = backup_dir / tool
            shutil.copytree(config_dir, backup_path)
            typer.echo(
                f"  {Colors.GREEN}✓{Colors.RESET} {tool}: {config_dir} → {backup_path}"
            )
        except Exception as e:
            typer.echo(f"  {Colors.RED}✗{Colors.RESET} {tool}: Failed to backup - {e}")

    return backup_dir


def uninstall_tools(installed_tools: List[str]) -> List[str]:
    """Uninstall tools using npm.

    Returns:
        List of failed tool names
    """
    typer.echo(f"\n{Colors.BOLD}Uninstalling tools...{Colors.RESET}")
    failed_uninstalls = []

    for tool_name in installed_tools:
        try:
            npm_package = NPM_PACKAGE_MAP.get(tool_name, tool_name)
            uninstall_cmd = f"npm uninstall -g {npm_package}"

            result = subprocess.run(
                shlex.split(uninstall_cmd), shell=False, capture_output=True, text=True
            )

            if result.returncode == 0:
                typer.echo(f"  {Colors.GREEN}✓{Colors.RESET} {tool_name}")
            else:
                typer.echo(
                    f"  {Colors.RED}✗{Colors.RESET} {tool_name}: {result.stderr.strip()}"
                )
                failed_uninstalls.append(tool_name)
        except Exception as e:
            typer.echo(f"  {Colors.RED}✗{Colors.RESET} {tool_name}: {e}")
            failed_uninstalls.append(tool_name)

    return failed_uninstalls


def remove_configs(ctx: UninstallContext) -> None:
    """Remove configuration directories."""
    if ctx.keep_config:
        return

    typer.echo(f"\n{Colors.BOLD}Removing configuration files...{Colors.RESET}")
    for tool in ctx.tools_with_config:
        config_dir = ctx.config_dirs.get(tool)
        try:
            shutil.rmtree(config_dir)
            typer.echo(f"  {Colors.GREEN}✓{Colors.RESET} {tool}: {config_dir}")
        except Exception as e:
            typer.echo(f"  {Colors.YELLOW}⚠️  {tool}: {e}{Colors.RESET}")


def display_summary(
    installed_tools: List[str],
    failed_uninstalls: List[str],
    backup_dir: Optional[Path],
) -> int:
    """Display uninstall summary and return exit code."""
    successful_uninstalls = len(installed_tools) - len(failed_uninstalls)
    typer.echo(f"\n{Colors.BOLD}Uninstall Summary:{Colors.RESET}")
    typer.echo(f"  Successful: {successful_uninstalls}/{len(installed_tools)}")

    if backup_dir:
        typer.echo(f"  Backup location: {backup_dir}")

    if failed_uninstalls:
        typer.echo(
            f"  {Colors.RED}Failed:{Colors.RESET} {', '.join(failed_uninstalls)}"
        )
        return 1

    return 0


def uninstall(
    ctx: Context,
    target: str,
    force: bool,
    keep_config: bool,
) -> int:
    """Uninstall CLI tools and backup their configuration files.

    Args:
        ctx: Typer context
        target: Tool name or "all"
        force: Skip confirmation prompt
        keep_config: Keep configuration files

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config = get_config_manager(ctx)

    # Get installed tools
    installed_tools, error_code = get_installed_tools(target, config)
    if error_code is not None:
        return error_code

    if not installed_tools:
        typer.echo(f"{Colors.YELLOW}No tools found to uninstall{Colors.RESET}")
        return 0

    # Build uninstall context
    tools_with_config = [
        tool for tool in installed_tools if TOOL_CONFIG_DIRS.get(tool, Path()).exists()
    ]

    uninstall_ctx = UninstallContext(
        tools_to_uninstall=[target] if target != "all" else installed_tools,
        installed_tools=installed_tools,
        config_dirs=TOOL_CONFIG_DIRS,
        tools_with_config=tools_with_config,
        keep_config=keep_config,
        force=force,
    )

    # Display plan and confirm
    display_uninstall_plan(uninstall_ctx)

    if not confirm_uninstall(uninstall_ctx):
        typer.echo("Uninstall cancelled")
        return 0

    # Execute uninstall
    backup_dir = backup_configs(uninstall_ctx)
    failed_uninstalls = uninstall_tools(installed_tools)
    remove_configs(uninstall_ctx)

    return display_summary(installed_tools, failed_uninstalls, backup_dir)
