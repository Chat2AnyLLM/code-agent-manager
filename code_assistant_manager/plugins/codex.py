"""Codex plugin handler."""

from pathlib import Path

from .base import BasePluginHandler


class CodexPluginHandler(BasePluginHandler):
    """Plugin handler for OpenAI Codex CLI."""

    @property
    def app_name(self) -> str:
        return "codex"

    @property
    def _default_home_dir(self) -> Path:
        return Path.home() / ".codex"

    @property
    def _default_user_plugins_dir(self) -> Path:
        return self._default_home_dir / "plugins"

    @property
    def _default_settings_file(self) -> Path:
        return self._default_home_dir / "settings.json"

    @property
    def plugin_manifest_path(self) -> str:
        return ".codex-plugin/plugin.json"

    @property
    def manifest_name_field(self) -> str:
        return "name"
