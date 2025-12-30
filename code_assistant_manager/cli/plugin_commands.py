"""CLI commands for plugin management.

Uses the app-specific CLI (e.g., `claude`) to manage plugins and marketplaces.
"""

import logging

import typer

from code_assistant_manager.cli.plugins import (
    plugin_discovery_commands,
    plugin_install_commands,
    plugin_management_commands,
    plugin_marketplace_commands,
)

logger = logging.getLogger(__name__)

# Combine all plugin subcommands into the main plugin app
plugin_app = typer.Typer(
    help="Manage plugins and marketplaces for AI assistants (Claude, CodeBuddy).\n\n"
    "CAM supports plugin management for compatible assistants. Plugins are distributed\n"
    "through marketplaces that can be browsed and installed. Use 'cam plugin marketplace'\n"
    "subcommands to manage marketplaces themselves, and 'cam plugin install' for plugins.",
    no_args_is_help=True,
)

# Register sub-apps as subcommands
plugin_app.add_typer(plugin_marketplace_commands.marketplace_app, name="marketplace")

# Register individual commands
# Management commands
plugin_app.command("list")(plugin_management_commands.list_plugins)
plugin_app.command("repos")(plugin_management_commands.list_repos)
plugin_app.command("add-repo")(plugin_management_commands.add_repo)
plugin_app.command("remove-repo")(plugin_management_commands.remove_repo)

# Install commands
plugin_app.command("install")(plugin_install_commands.install_plugin)
plugin_app.command("uninstall")(plugin_install_commands.uninstall_plugin)
plugin_app.command("enable")(plugin_install_commands.enable_plugin)
plugin_app.command("disable")(plugin_install_commands.disable_plugin)
plugin_app.command("validate")(plugin_install_commands.validate_plugin)

# Discovery commands
plugin_app.command("view")(plugin_discovery_commands.view_plugin)
plugin_app.command("status")(plugin_discovery_commands.plugin_status)
