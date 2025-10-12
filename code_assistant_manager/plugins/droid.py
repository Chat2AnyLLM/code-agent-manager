"""Droid plugin handler."""

from pathlib import Path

from .base import BasePluginHandler


class DroidPluginHandler(BasePluginHandler):
    """Plugin handler for Factory.ai Droid CLI."""

    @property
    def app_name(self) -> str:
        return "droid"

    @property
    def _default_home_dir(self) -> Path:
        return Path.home() / ".factory"

    @property
    def _default_user_plugins_dir(self) -> Path:
        return self._default_home_dir / "plugins"

    @property
    def _default_settings_file(self) -> Path:
        return self._default_home_dir / "settings.json"

    @property
    def plugin_manifest_path(self) -> str:
        return ".droid-plugin/plugin.json"

    @property
    def manifest_name_field(self) -> str:
        return "name"
