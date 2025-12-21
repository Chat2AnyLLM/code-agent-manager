"""Copilot plugin handler."""

from pathlib import Path

from .base import BasePluginHandler


class CopilotPluginHandler(BasePluginHandler):
    """Plugin handler for GitHub Copilot CLI.

    Copilot CLI does not currently provide a native `plugin` subcommand like Claude.
    We support plugin installation by copying plugin directories into:
      ~/.copilot/plugins/
    and tracking enabled state in ~/.copilot/settings.json.
    """

    @property
    def app_name(self) -> str:
        return "copilot"

    @property
    def _default_home_dir(self) -> Path:
        return Path.home() / ".copilot"

    @property
    def _default_user_plugins_dir(self) -> Path:
        return self._default_home_dir / "plugins"

    @property
    def _default_settings_file(self) -> Path:
        return self._default_home_dir / "settings.json"

    @property
    def plugin_manifest_path(self) -> str:
        # Most community marketplaces today use Claude plugin manifests
        return ".claude-plugin/plugin.json"

    @property
    def manifest_name_field(self) -> str:
        return "name"
