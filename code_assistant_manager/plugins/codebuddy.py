"""CodeBuddy plugin handler."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BasePluginHandler
from .models import Plugin

logger = logging.getLogger(__name__)


class CodebuddyPluginHandler(BasePluginHandler):
    @property
    def uses_cli_plugin_commands(self) -> bool:
        return True

    """Plugin handler for CodeBuddy CLI.

    Uses the `codebuddy` CLI to manage plugins and marketplaces.

    User-level plugins: ~/.codebuddy/plugins/
    Marketplaces: ~/.codebuddy/plugins/marketplaces/
    Settings file: ~/.codebuddy/settings.json
    """

    @property
    def app_name(self) -> str:
        return "codebuddy"

    @property
    def _default_home_dir(self) -> Path:
        return Path.home() / ".codebuddy"

    @property
    def _default_user_plugins_dir(self) -> Path:
        return self._default_home_dir / "plugins"

    @property
    def _default_settings_file(self) -> Path:
        return self._default_home_dir / "settings.json"

    @property
    def plugin_manifest_path(self) -> str:
        return ".codebuddy-plugin/plugin.json"

    @property
    def manifest_name_field(self) -> str:
        return "name"

    @property
    def marketplaces_dir(self) -> Path:
        """Return the marketplaces directory."""
        return self.user_plugins_dir / "marketplaces"

    @property
    def known_marketplaces_file(self) -> Path:
        """Return the known marketplaces file."""
        return self.user_plugins_dir / "known_marketplaces.json"

    def _run_codebuddy_cli(self, *args: str) -> Tuple[int, str, str]:
        """Run a codebuddy CLI command.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = ["codebuddy", "plugin", *args]
        logger.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return (
                -1,
                "",
                "CodeBuddy CLI not found. Please install CodeBuddy first.",
            )
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"

    # ==================== Marketplace Operations ====================

    def marketplace_add(self, source: str) -> Tuple[bool, str]:
        """Add a marketplace using CodeBuddy CLI.

        Args:
            source: URL, path, or GitHub repo (e.g., "owner/repo")

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("marketplace", "add", source)
        if code == 0:
            return True, stdout.strip() or f"Marketplace added: {source}"
        return False, stderr.strip() or stdout.strip() or "Failed to add marketplace"

    def marketplace_remove(self, name: str) -> Tuple[bool, str]:
        """Remove a marketplace using CodeBuddy CLI.

        Args:
            name: Marketplace name

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("marketplace", "remove", name)
        if code == 0:
            return True, stdout.strip() or f"Marketplace removed: {name}"
        return False, stderr.strip() or stdout.strip() or "Failed to remove marketplace"

    def marketplace_list(self) -> Tuple[bool, str]:
        """List all marketplaces using CodeBuddy CLI.

        Returns:
            Tuple of (success, output)
        """
        code, stdout, stderr = self._run_codebuddy_cli("marketplace", "list")
        if code == 0:
            return True, stdout.strip()
        return False, stderr.strip() or stdout.strip() or "Failed to list marketplaces"

    def marketplace_update(self, name: Optional[str] = None) -> Tuple[bool, str]:
        """Update marketplace(s) using CodeBuddy CLI.

        Args:
            name: Marketplace name (updates all if None)

        Returns:
            Tuple of (success, message)
        """
        if name:
            # Update specific marketplace
            args = ["marketplace", "update", name]
            code, stdout, stderr = self._run_codebuddy_cli(*args)
            if code == 0:
                return True, stdout.strip() or f"Marketplace '{name}' updated"
            return (
                False,
                stderr.strip()
                or stdout.strip()
                or f"Failed to update marketplace '{name}'",
            )
        else:
            # Update all marketplaces
            marketplaces = self.get_known_marketplaces()
            if not marketplaces:
                return True, "No marketplaces to update"

            failed = []
            for marketplace_name in marketplaces.keys():
                args = ["marketplace", "update", marketplace_name]
                code, stdout, stderr = self._run_codebuddy_cli(*args)
                if code != 0:
                    failed.append(marketplace_name)
                    logger.warning(
                        f"Failed to update marketplace '{marketplace_name}': {stderr}"
                    )

            if failed:
                return (
                    False,
                    f"Updated {len(marketplaces) - len(failed)}/{len(marketplaces)} marketplaces. Failed: {', '.join(failed)}",
                )
            return True, f"Updated all {len(marketplaces)} marketplace(s)"

    def get_known_marketplaces(self) -> Dict[str, Any]:
        """Get known marketplaces from the JSON file.

        Returns:
            Dict of marketplace name -> marketplace info
        """
        if not self.known_marketplaces_file.exists():
            return {}

        try:
            with open(self.known_marketplaces_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read known marketplaces: {e}")
            return {}

    # ==================== Plugin Operations ====================

    def install_plugin(
        self, plugin: str, marketplace: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Install a plugin using CodeBuddy CLI.

        Args:
            plugin: Plugin name
            marketplace: Optional marketplace name (use plugin@marketplace format)

        Returns:
            Tuple of (success, message)
        """
        plugin_ref = f"{plugin}@{marketplace}" if marketplace else plugin
        code, stdout, stderr = self._run_codebuddy_cli("install", plugin_ref)
        if code == 0:
            return True, stdout.strip() or f"Plugin installed: {plugin_ref}"
        return False, stderr.strip() or stdout.strip() or "Failed to install plugin"

    def uninstall_plugin(self, plugin: str) -> Tuple[bool, str]:
        """Uninstall a plugin using CodeBuddy CLI.

        Args:
            plugin: Plugin name

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("uninstall", plugin)
        if code == 0:
            return True, stdout.strip() or f"Plugin uninstalled: {plugin}"
        return False, stderr.strip() or stdout.strip() or "Failed to uninstall plugin"

    def enable_plugin(self, plugin: str) -> Tuple[bool, str]:
        """Enable a plugin using CodeBuddy CLI.

        Args:
            plugin: Plugin name

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("enable", plugin)
        if code == 0:
            return True, stdout.strip() or f"Plugin enabled: {plugin}"
        return False, stderr.strip() or stdout.strip() or "Failed to enable plugin"

    def disable_plugin(self, plugin: str) -> Tuple[bool, str]:
        """Disable a plugin using CodeBuddy CLI.

        Args:
            plugin: Plugin name

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("disable", plugin)
        if code == 0:
            return True, stdout.strip() or f"Plugin disabled: {plugin}"
        return False, stderr.strip() or stdout.strip() or "Failed to disable plugin"

    def validate_plugin(self, path: str) -> Tuple[bool, str]:
        """Validate a plugin or marketplace manifest.

        Args:
            path: Path to plugin or marketplace

        Returns:
            Tuple of (success, message)
        """
        code, stdout, stderr = self._run_codebuddy_cli("validate", path)
        if code == 0:
            return True, stdout.strip() or "Plugin is valid"
        return False, stderr.strip() or stdout.strip() or "Validation failed"

    def get_enabled_plugins(self) -> Dict[str, bool]:
        """Get enabled plugins from settings.

        Returns:
            Dict of plugin key -> enabled status
        """
        if not self.settings_file.exists():
            return {}

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            return settings.get("enabledPlugins", {})
        except Exception as e:
            logger.warning(f"Failed to read settings: {e}")
            return {}

    def scan_marketplace_plugins(self) -> List[Plugin]:
        """Scan for plugins in all marketplaces.

        Returns:
            List of Plugin objects found in marketplaces
        """
        plugins = []

        if not self.marketplaces_dir.exists():
            return plugins

        for marketplace_dir in self.marketplaces_dir.iterdir():
            if not marketplace_dir.is_dir():
                continue

            marketplace_name = marketplace_dir.name
            plugins_dir = marketplace_dir / "plugins"

            if not plugins_dir.exists():
                continue

            # Recursively find all plugin directories (they contain .codebuddy-plugin/)
            def scan_dir(directory: Path):
                for item in directory.iterdir():
                    if not item.is_dir():
                        continue

                    # Check if this directory is a plugin
                    valid, manifest = self.validate_plugin_structure(item)
                    if valid and manifest is not None:
                        plugin = Plugin(
                            name=manifest[self.manifest_name_field],
                            version=manifest.get("version", "1.0.0"),
                            description=manifest.get("description", ""),
                            marketplace=marketplace_name,
                            local_path=str(item),
                            installed=False,
                        )
                        plugins.append(plugin)
                    else:
                        # Not a plugin, might be a category directory - scan deeper
                        scan_dir(item)

            scan_dir(plugins_dir)

        # Check which plugins are enabled
        enabled = self.get_enabled_plugins()
        for plugin in plugins:
            plugin.installed = any(
                plugin.name in key and enabled.get(key, False) for key in enabled
            )
            plugin.enabled = plugin.installed

        return plugins
