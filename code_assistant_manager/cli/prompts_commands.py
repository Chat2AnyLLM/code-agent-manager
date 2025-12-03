"""CLI commands for prompt management."""

import logging

import typer

# Import functions from refactored modules
from code_assistant_manager.cli.prompt_crud import (
    add_prompt,
    list_prompts,
    remove_prompt,
    update_prompt,
    view_prompt,
)
from code_assistant_manager.cli.prompt_defaults import (
    clear_default_prompt,
    set_default_prompt,
)
from code_assistant_manager.cli.prompt_install_sync import (
    export_prompts,
    import_live_prompt,
    import_prompts,
    install_prompts,
    show_live_prompt,
    sync_prompts_alias,
)
from code_assistant_manager.cli.prompt_status import show_prompt_status
from code_assistant_manager.cli.prompt_uninstall import (
    uninstall_prompt,
    unsync_prompt_alias,
)

logger = logging.getLogger(__name__)

prompt_app = typer.Typer(
    help="Manage prompts for AI assistants (Claude, Codex, Gemini, Copilot, CodeBuddy)",
    no_args_is_help=True,
)

# Register commands
prompt_app.command("list")(list_prompts)
prompt_app.command("ls", hidden=True)(list_prompts)
prompt_app.command("view")(view_prompt)
prompt_app.command("add")(add_prompt)
prompt_app.command("update")(update_prompt)
prompt_app.command("remove")(remove_prompt)
prompt_app.command("rm", hidden=True)(remove_prompt)
prompt_app.command("install")(install_prompts)
prompt_app.command("uninstall")(uninstall_prompt)
prompt_app.command("sync")(sync_prompts_alias)
prompt_app.command("unsync")(unsync_prompt_alias)
prompt_app.command("import")(import_prompts)
prompt_app.command("export")(export_prompts)
prompt_app.command("import-live")(import_live_prompt)
prompt_app.command("show-live")(show_live_prompt)
prompt_app.command("status")(show_prompt_status)
prompt_app.command("set-default")(set_default_prompt)
prompt_app.command("clear-default")(clear_default_prompt)
