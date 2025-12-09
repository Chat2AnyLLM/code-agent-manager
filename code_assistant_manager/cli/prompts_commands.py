import logging
import sys
from pathlib import Path
from typing import Optional
import random

import typer

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.prompts import PromptManager, Prompt, VALID_APP_TYPES

logger = logging.getLogger(__name__)

prompt_app = typer.Typer(
    help="Manage prompts for AI assistants (Claude, Codex, Gemini, Copilot, CodeBuddy)",
    no_args_is_help=True,
)


def _get_manager() -> PromptManager:
    """Get a PromptManager instance."""
    return PromptManager()


def _find_prompt_by_name(manager: PromptManager, name: str) -> Optional[Prompt]:
    """Find a prompt by name."""
    for p in manager.get_all().values():
        if p.name == name:
            return p
    return None


def _strip_metadata_from_content(content: str) -> str:
    """
    Strip metadata headers from content that shouldn't be part of the prompt.

    This includes:
    - YAML front matter (--- ... ---)
    - Existing metadata headers from show command output
    - CAM prompt ID markers
    """
    import re

    # First strip CAM prompt ID markers
    from code_assistant_manager.prompts.base import PROMPT_ID_PATTERN
    content = PROMPT_ID_PATTERN.sub("", content).strip()

    # Strip YAML front matter
    yaml_pattern = r'^---\s*\n.*?\n---\s*\n'
    content = re.sub(yaml_pattern, '', content, flags=re.DOTALL).strip()

    # Strip metadata headers that look like the show command output
    # Look for patterns like "Prompt: ..." or "ID: ..." at the beginning
    lines = content.splitlines()

    # Find where actual content starts (after metadata headers)
    content_start_idx = 0
    for i, line in enumerate(lines):
        # Stop at the first line that doesn't look like metadata
        if not re.match(r'^(Prompt|ID|Description|Status|Default|Content|Imported from):\s*', line, re.IGNORECASE):
            # Also skip empty lines at the beginning
            if line.strip():
                content_start_idx = i
                break
        content_start_idx = i + 1

    # If we found metadata headers, return content starting after them
    if content_start_idx > 0 and content_start_idx < len(lines):
        return '\n'.join(lines[content_start_idx:]).strip()

    return content.strip()


def _generate_fancy_name() -> str:
    """Generate a fancy, creative name for a prompt."""
    adjectives = [
        "Cosmic", "Digital", "Quantum", "Cyber", "Neural", "Pixel", "Binary",
        "Virtual", "Synthetic", "Logic", "Code", "Syntax", "Algorithm", "Byte",
        "Data", "Matrix", "Circuit", "Pulse", "Wave", "Stream", "Flux", "Nexus",
        "Aether", "Zenith", "Prism", "Echo", "Nova", "Aura", "Spark", "Bloom",
        "Whisper", "Dream", "Vision", "Harmony", "Pulse", "Radiant", "Ethereal",
        "Luminous", "Mystic", "Phantom", "Sapphire", "Crimson", "Amber", "Azure"
    ]

    nouns = [
        "Coder", "Assistant", "Wizard", "Sage", "Oracle", "Companion", "Guide",
        "Mentor", "Architect", "Scribe", "Alchemist", "Artisan", "Craftsman",
        "Navigator", "Explorer", "Pioneer", "Trailblazer", "Pathfinder", "Seeker",
        "Dreamer", "Visionary", "Innovator", "Creator", "Builder", "Weaver",
        "Sorcerer", "Enchanter", "Luminary", "Beacon", "Guardian", "Sentinel",
        "Whisperer", "Harmonizer", "Illuminator", "Transformer", "Catalyst"
    ]

    # Generate 2-3 word combinations
    name_parts = []
    name_parts.append(random.choice(adjectives))
    name_parts.append(random.choice(nouns))

    # Sometimes add a second adjective for variety (30% chance)
    if random.random() < 0.3:
        name_parts.insert(0, random.choice(adjectives))

    return "_".join(name_parts)


@prompt_app.command("list")
def list_prompts():
    """List all configured prompts."""
    manager = _get_manager()
    prompts = manager.get_all()

    if not prompts:
        typer.echo("No prompts configured. Use 'cam prompt add' to add one.")
        return

    typer.echo(f"\n{Colors.BOLD}Configured Prompts:{Colors.RESET}\n")
    for prompt_id, prompt in sorted(prompts.items(), key=lambda x: x[1].name):
        default_marker = f" {Colors.GREEN}(default){Colors.RESET}" if prompt.is_default else ""
        typer.echo(f"  {Colors.CYAN}{prompt.name}{Colors.RESET}{default_marker}")
        typer.echo(f"    ID: {Colors.DIM}{prompt_id}{Colors.RESET}")
        if prompt.description:
            typer.echo(f"    Description: {prompt.description}")
        # Show preview of content (first 60 chars)
        preview = prompt.content[:60].replace('\n', ' ')
        if len(prompt.content) > 60:
            preview += "..."
        typer.echo(f"    Content: {Colors.DIM}{preview}{Colors.RESET}")
        typer.echo()


@prompt_app.command("show")
def show_prompt(
    name: str = typer.Argument(..., help="Prompt name to show"),
):
    """Show the full content of a configured prompt."""
    manager = _get_manager()

    prompt = _find_prompt_by_name(manager, name)
    if not prompt:
        typer.echo(f"Error: Prompt '{name}' not found")
        raise typer.Exit(1)

    typer.echo(f"\n{Colors.BOLD}{prompt.name}{Colors.RESET}")
    typer.echo(f"ID: {Colors.DIM}{prompt.id}{Colors.RESET}")
    if prompt.description:
        typer.echo(f"Description: {prompt.description}")
    default_marker = f" {Colors.GREEN}(default){Colors.RESET}" if prompt.is_default else ""
    typer.echo(f"Default:{default_marker}")
    typer.echo(f"\n{Colors.BOLD}Content:{Colors.RESET}\n")
    typer.echo(prompt.content)
    typer.echo()


@prompt_app.command("add")
def add_prompt(
    name: Optional[str] = typer.Argument(None, help="Name for the prompt (auto-generated if not provided)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description of the prompt"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read content from file"),
    default: bool = typer.Option(False, "--default", help="Set as default prompt"),
):
    """Add a new prompt from file, stdin, or interactive input.

    Examples:
        cam prompt add "My Custom Prompt" -f prompt.md
        cam prompt add -f prompt.md  # Auto-generates a fancy name
        cat prompt.md | cam prompt add
        cam prompt add  # Interactive mode with fancy name
    """
    manager = _get_manager()

    # Read content from file, stdin, or interactive input
    if file:
        if not file.exists():
            typer.echo(f"Error: File not found: {file}")
            raise typer.Exit(1)
        content = file.read_text()
        # Strip metadata headers that shouldn't be part of the prompt content
        content = _strip_metadata_from_content(content)
    elif not sys.stdin.isatty():
        # Read from stdin (piped input)
        content = sys.stdin.read()
    else:
        # Interactive input mode
        typer.echo()  # Enter a newline as requested
        typer.echo("Enter prompt content (press Ctrl+C when finished):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except KeyboardInterrupt:
            typer.echo("\n")  # New line after Ctrl+C
            content = "\n".join(lines)

    if not content.strip():
        typer.echo("Error: Content cannot be empty")
        raise typer.Exit(1)

    # Generate or validate name
    if not name:
        # Generate a fancy name and ensure it's unique
        while True:
            name = _generate_fancy_name()
            if not _find_prompt_by_name(manager, name):
                break
        typer.echo(f"✨ Generated fancy name: {Colors.CYAN}{name}{Colors.RESET}")
    else:
        # Check if prompt with same name already exists
        existing_prompt = _find_prompt_by_name(manager, name)
        if existing_prompt:
            typer.echo(f"Error: Prompt with name '{name}' already exists. Use a different name or remove it first.")
            raise typer.Exit(1)

    # Create the prompt (ID is auto-generated)
    prompt = Prompt(
        name=name,
        content=content,
        description=description or "",
        is_default=default,
    )

    # If setting as default, clear other defaults first
    if default:
        manager.clear_default()

    manager.create(prompt)
    typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Added prompt: {name} (id: {prompt.id})")

    if default:
        typer.echo(f"  Set as default prompt")


@prompt_app.command("update")
def update_prompt(
    name: str = typer.Argument(..., help="Name of the prompt to update"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Update the description"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read new content from file"),
    new_name: Optional[str] = typer.Option(None, "--name", "-n", help="Rename the prompt"),
    default: Optional[bool] = typer.Option(None, "--default/--no-default", help="Set or unset as default prompt"),
):
    """Update a configured prompt's content, description, name, or default status.

    Examples:
        cam prompt update my-prompt -f updated-prompt.md
        cam prompt update my-prompt --description "Updated description"
        cam prompt update my-prompt --name "New Prompt Name" --default
        cam prompt update my-prompt -f prompt.md -d "New description" --default
    """
    manager = _get_manager()

    # Find the prompt by name
    prompt = _find_prompt_by_name(manager, name)
    if not prompt:
        typer.echo(f"Error: Prompt '{name}' not found")
        raise typer.Exit(1)

    # Read content from file if provided
    content = None
    if file:
        if not file.exists():
            typer.echo(f"Error: File not found: {file}")
            raise typer.Exit(1)
        content = file.read_text()
        if not content.strip():
            typer.echo("Error: File is empty")
            raise typer.Exit(1)

        # Strip metadata headers that shouldn't be part of the prompt content
        content = _strip_metadata_from_content(content)

    # Check if new name conflicts with existing prompt
    if new_name and new_name != name:
        existing_prompt = _find_prompt_by_name(manager, new_name)
        if existing_prompt:
            typer.echo(f"Error: Prompt with name '{new_name}' already exists")
            raise typer.Exit(1)

    # Update the prompt
    try:
        updated_prompt = manager.update_prompt(
            prompt_id=prompt.id,
            content=content,
            description=description,
            name=new_name,
        )

        # Handle default status change
        if default is True:
            manager.clear_default()  # Clear any existing default
            manager.set_default(prompt.id)
            typer.echo(f"  Set as default prompt")
        elif default is False and prompt.is_default:
            manager.clear_default()
            typer.echo(f"  Unset as default prompt")

        typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Updated prompt: {updated_prompt.name}")

        if content:
            typer.echo(f"  Content updated from file: {file}")

        if description:
            typer.echo(f"  Description updated")

        if new_name and new_name != name:
            typer.echo(f"  Renamed from '{name}' to '{new_name}'")

    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


@prompt_app.command("remove")
def remove_prompt(
    name: str = typer.Argument(..., help="Prompt name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a configured prompt."""
    manager = _get_manager()

    prompt = _find_prompt_by_name(manager, name)
    if not prompt:
        typer.echo(f"Error: Prompt '{name}' not found")
        raise typer.Exit(1)

    if not force:
        typer.confirm(f"Remove prompt '{name}'?", abort=True)

    manager.delete(prompt.id)
    typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Removed prompt: {name}")


@prompt_app.command("import")
def import_prompt(
    name: Optional[str] = typer.Argument(None, help="Name for the imported prompt (auto-generated if not provided)"),
    app: str = typer.Option(..., "--app", "-a", help=f"App to import from ({', '.join(VALID_APP_TYPES)})"),
    level: str = typer.Option("user", "--level", "-l", help="Level: user or project"),
    project_dir: Optional[Path] = typer.Option(None, "--project-dir", "-d", help="Project directory (for project level)"),
    description: Optional[str] = typer.Option(None, "--description", help="Description of the prompt"),
):
    """Import a prompt from an app's live prompt file.

    Examples:
        cam prompt import "My Claude Prompt" --app claude
        cam prompt import --app claude  # Auto-generates a fancy name
        cam prompt import project-prompt --app claude --level project -d .
    """
    if app not in VALID_APP_TYPES:
        typer.echo(f"Error: Invalid app '{app}'. Valid: {', '.join(VALID_APP_TYPES)}")
        raise typer.Exit(1)

    if level not in ("user", "project"):
        typer.echo("Error: Level must be 'user' or 'project'")
        raise typer.Exit(1)

    if level == "project" and not project_dir:
        project_dir = Path.cwd()

    manager = _get_manager()

    # Get the live content
    handler = manager.get_handler(app)
    file_path = handler.get_prompt_file_path(level, project_dir)

    if not file_path:
        typer.echo(f"Error: {app} does not support {level} level prompts")
        raise typer.Exit(1)

    if not file_path.exists():
        typer.echo(f"Error: No prompt file found at: {file_path}")
        raise typer.Exit(1)

    content = file_path.read_text()
    if not content.strip():
        typer.echo(f"Error: Prompt file is empty: {file_path}")
        raise typer.Exit(1)

    # Strip any existing ID marker from the content
    from code_assistant_manager.prompts.base import PROMPT_ID_PATTERN
    content = PROMPT_ID_PATTERN.sub("", content).strip()

    # Strip metadata headers that shouldn't be part of the prompt content
    content = _strip_metadata_from_content(content)

    # Generate or validate name
    if not name:
        # Generate a fancy name with app context and ensure it's unique
        while True:
            base_name = _generate_fancy_name()
            # Add app context to make it more specific
            app_prefixes = {
                "claude": "Claude",
                "codex": "Codex",
                "gemini": "Gemini",
                "copilot": "Copilot",
                "codebuddy": "CodeBuddy"
            }
            prefix = app_prefixes.get(app, app.capitalize())
            name = f"{prefix}_{base_name}"  # Use underscore instead of space
            if not _find_prompt_by_name(manager, name):
                break
        typer.echo(f"✨ Generated fancy name: {Colors.CYAN}{name}{Colors.RESET}")
    else:
        # Check if prompt with same name already exists
        if _find_prompt_by_name(manager, name):
            typer.echo(f"Error: Prompt '{name}' already exists. Use a different name.")
            raise typer.Exit(1)

    # Create the prompt (ID is auto-generated)
    prompt = Prompt(
        name=name,
        content=content,
        description=description or f"Imported from {app} ({level})",
    )

    manager.create(prompt)
    typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Imported prompt: {name} (id: {prompt.id})")
    typer.echo(f"  From: {file_path}")


@prompt_app.command("install")
def install_prompt(
    name: str = typer.Argument(..., help="Prompt name to install"),
    app: str = typer.Option(..., "--app", "-a", help=f"Target app ({', '.join(VALID_APP_TYPES)})"),
    level: str = typer.Option("user", "--level", "-l", help="Level: user or project"),
    project_dir: Optional[Path] = typer.Option(None, "--project-dir", "-d", help="Project directory (for project level)"),
):
    """Install a prompt to an app's prompt file.
    
    Examples:
        cam prompt install my-prompt --app claude
        cam prompt install my-prompt --app codex --level project -d .
    """
    if app not in VALID_APP_TYPES:
        typer.echo(f"Error: Invalid app '{app}'. Valid: {', '.join(VALID_APP_TYPES)}")
        raise typer.Exit(1)

    if level not in ("user", "project"):
        typer.echo("Error: Level must be 'user' or 'project'")
        raise typer.Exit(1)

    if level == "project" and not project_dir:
        project_dir = Path.cwd()

    manager = _get_manager()
    prompt = _find_prompt_by_name(manager, name)

    if not prompt:
        typer.echo(f"Error: Prompt '{name}' not found")
        raise typer.Exit(1)

    try:
        target_file = manager.sync_to_app(prompt.id, app, level, project_dir)
        typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Installed '{name}' to {app}")
        typer.echo(f"  File: {target_file}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


@prompt_app.command("uninstall")
def uninstall_prompt(
    app: str = typer.Option(..., "--app", "-a", help=f"Target app ({', '.join(VALID_APP_TYPES)})"),
    level: str = typer.Option("user", "--level", "-l", help="Level: user or project"),
    project_dir: Optional[Path] = typer.Option(None, "--project-dir", "-d", help="Project directory (for project level)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Uninstall/clear the prompt file for an app.
    
    Examples:
        cam prompt uninstall --app claude
        cam prompt uninstall --app codex --level project -d .
    """
    if app not in VALID_APP_TYPES:
        typer.echo(f"Error: Invalid app '{app}'. Valid: {', '.join(VALID_APP_TYPES)}")
        raise typer.Exit(1)

    if level not in ("user", "project"):
        typer.echo("Error: Level must be 'user' or 'project'")
        raise typer.Exit(1)

    if level == "project" and not project_dir:
        project_dir = Path.cwd()

    manager = _get_manager()
    handler = manager.get_handler(app)
    target_file = handler.get_prompt_file_path(level, project_dir)

    if not target_file:
        typer.echo(f"Error: {app} does not support {level} level prompts")
        raise typer.Exit(1)

    if not target_file.exists():
        typer.echo(f"No prompt file found at: {target_file}")
        return

    if not force:
        typer.confirm(f"Clear prompt file: {target_file}?", abort=True)

    # Clear the file content
    target_file.write_text("")
    typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Uninstalled prompt from {app}")
    typer.echo(f"  Cleared: {target_file}")


@prompt_app.command("status")
def status(
    project_dir: Optional[Path] = typer.Option(None, "--project-dir", "-d", help="Project directory for project-level status"),
):
    """Show configured and installed prompts for all apps."""
    manager = _get_manager()
    prompts = manager.get_all()

    if project_dir is None:
        project_dir = Path.cwd()

    # Build installation map: prompt_id -> [(app, level, file_path), ...]
    install_map = {}  # prompt_id -> list of (app, level, file_path) tuples
    untracked = []    # list of (app, level, preview) for untracked installs

    for app in VALID_APP_TYPES:
        handler = manager.get_handler(app)

        for level in ["user", "project"]:
            proj = project_dir if level == "project" else None
            file_path = handler.get_prompt_file_path(level, proj)

            if not file_path or not file_path.exists():
                continue

            content = file_path.read_text().strip()
            if not content:
                continue

            # Check if any configured prompt matches this content
            matched_prompt_id = None
            for prompt_id, prompt in prompts.items():
                if handler.get_matching_prompt_id(prompt.content, level, proj):
                    matched_prompt_id = prompt_id
                    break

            if matched_prompt_id:
                if matched_prompt_id not in install_map:
                    install_map[matched_prompt_id] = []
                install_map[matched_prompt_id].append((app, level, file_path))
            else:
                preview = content[:30].replace('\n', ' ')
                if len(content) > 30:
                    preview += "..."
                untracked.append((app, level, preview))

    # Show configured prompts with their installations
    typer.echo(f"\n{Colors.BOLD}Configured Prompts:{Colors.RESET}\n")
    
    if prompts:
        for prompt_id, prompt in sorted(prompts.items(), key=lambda x: x[1].name):
            default_marker = f" {Colors.GREEN}(default){Colors.RESET}" if prompt.is_default else ""
            typer.echo(f"  {Colors.CYAN}{prompt.name}{Colors.RESET}{default_marker}")
            typer.echo(f"    ID: {Colors.DIM}{prompt_id}{Colors.RESET}")
            
            # Show where this prompt is installed
            if prompt_id in install_map:
                locations = install_map[prompt_id]
                loc_strs = [f"{app}:{level} ({file_path})" for app, level, file_path in locations]
                typer.echo(f"    Installed: {Colors.GREEN}{', '.join(loc_strs)}{Colors.RESET}")
            else:
                typer.echo(f"    Installed: {Colors.DIM}nowhere{Colors.RESET}")
            typer.echo()
    else:
        typer.echo(f"  {Colors.DIM}No prompts configured. Use 'cam prompt add' to add one.{Colors.RESET}\n")

    # Show untracked installations
    if untracked:
        typer.echo(f"{Colors.BOLD}Untracked Installations:{Colors.RESET}\n")
        for app, level, preview in untracked:
            typer.echo(f"  {Colors.YELLOW}{app}:{level}{Colors.RESET} - {Colors.DIM}{preview}{Colors.RESET}")
        typer.echo()
    
    # Show prompts that were deleted but still installed
    orphaned = [pid for pid in install_map if pid not in prompts]
    if orphaned:
        typer.echo(f"{Colors.BOLD}Orphaned Installations (prompt deleted):{Colors.RESET}\n")
        for pid in orphaned:
            locations = install_map[pid]
            loc_strs = [f"{app}:{level} ({file_path})" for app, level, file_path in locations]
            typer.echo(f"  {Colors.RED}{pid}{Colors.RESET} - installed at: {', '.join(loc_strs)}")
        typer.echo()


# Hidden aliases
prompt_app.command("ls", hidden=True)(list_prompts)
prompt_app.command("rm", hidden=True)(remove_prompt)
prompt_app.command("edit", hidden=True)(update_prompt)


@prompt_app.command("rename")
def rename_prompt(
    old_name: str = typer.Argument(..., help="Current name of the prompt to rename"),
    new_name: str = typer.Argument(..., help="New name for the prompt"),
):
    """Rename an existing prompt.

    Examples:
        cam prompt rename "Old Name" "New Name"
    """
    manager = _get_manager()

    # Find the prompt by old name
    prompt = _find_prompt_by_name(manager, old_name)
    if not prompt:
        typer.echo(f"Error: Prompt '{old_name}' not found")
        raise typer.Exit(1)

    # Check if new name conflicts with existing prompt
    if new_name != old_name:
        existing_prompt = _find_prompt_by_name(manager, new_name)
        if existing_prompt:
            typer.echo(f"Error: Prompt with name '{new_name}' already exists")
            raise typer.Exit(1)

    # Rename the prompt
    try:
        updated_prompt = manager.update_prompt(
            prompt_id=prompt.id,
            name=new_name,
        )
        typer.echo(f"{Colors.GREEN}✓{Colors.RESET} Renamed prompt: '{old_name}' → '{new_name}'")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
