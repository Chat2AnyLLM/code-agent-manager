"""Plugin manager that coordinates all app-specific handlers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..repo_loader import RepoConfigLoader
from .base import BasePluginHandler
from .claude import ClaudePluginHandler
from .codebuddy import CodebuddyPluginHandler
from .codex import CodexPluginHandler
from .copilot import CopilotPluginHandler
from .models import Marketplace, Plugin, PluginRepo

logger = logging.getLogger(__name__)


def _load_builtin_plugin_repos() -> Dict[str, PluginRepo]:
    """Load built-in plugin repos from the bundled plugin_repos.json file.

    Returns bundled repos as PluginRepo objects for fallback.
    """
    package_dir = Path(__file__).parent.parent
    repos_file = package_dir / "plugin_repos.json"

    repos: Dict[str, PluginRepo] = {}
    if repos_file.exists():
        try:
            with open(repos_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, repo_data in data.items():
                repos[key] = PluginRepo(
                    name=repo_data.get("name", key),
                    description=repo_data.get("description", ""),
                    repo_owner=repo_data.get("repoOwner"),
                    repo_name=repo_data.get("repoName"),
                    repo_branch=repo_data.get("repoBranch", "main"),
                    plugin_path=repo_data.get("pluginPath"),
                    enabled=repo_data.get("enabled", True),
                    type=repo_data.get("type", "plugin"),
                    aliases=repo_data.get("aliases", []),
                )
            logger.debug(f"Loaded {len(repos)} builtin plugin repos")
        except Exception as e:
            logger.warning(f"Failed to load builtin plugin repos: {e}")

    return repos


def _load_plugin_repos_from_config(config_dir: Optional[Path] = None) -> Dict[str, PluginRepo]:
    """Load plugin repos from config.yaml sources.

    Args:
        config_dir: Configuration directory

    Returns:
        Dictionary of PluginRepo objects
    """
    loader = RepoConfigLoader(config_dir)
    bundled_fallback_dict = _load_builtin_plugin_repos()

    # Convert PluginRepo objects to dict for loader
    bundled_data = {}
    for key, repo in bundled_fallback_dict.items():
        bundled_data[key] = {
            "name": repo.name,
            "description": repo.description,
            "repoOwner": repo.repo_owner,
            "repoName": repo.repo_name,
            "repoBranch": repo.repo_branch,
            "pluginPath": repo.plugin_path,
            "enabled": repo.enabled,
            "type": repo.type,
            "aliases": repo.aliases,
        }

    # Get repos from all configured sources
    repos_dict = loader.get_repos("plugins", bundled_data)

    # Convert back to PluginRepo objects
    repos: Dict[str, PluginRepo] = {}
    for key, repo_data in repos_dict.items():
        repos[key] = PluginRepo(
            name=repo_data.get("name", key),
            description=repo_data.get("description", ""),
            repo_owner=repo_data.get("repoOwner"),
            repo_name=repo_data.get("repoName"),
            repo_branch=repo_data.get("repoBranch", "main"),
            plugin_path=repo_data.get("pluginPath"),
            enabled=repo_data.get("enabled", True),
            type=repo_data.get("type", "plugin"),
            aliases=repo_data.get("aliases", []),
        )

    return repos


# Registry of all available plugin handlers
PLUGIN_HANDLERS: Dict[str, Type[BasePluginHandler]] = {
    "claude": ClaudePluginHandler,
    "codebuddy": CodebuddyPluginHandler,
    "codex": CodexPluginHandler,
    "copilot": CopilotPluginHandler,
}

# Valid app types that support plugins
VALID_APP_TYPES = list(PLUGIN_HANDLERS.keys())

# Built-in plugin repositories
BUILTIN_PLUGIN_REPOS = _load_plugin_repos_from_config()


def get_handler(app_type: str) -> BasePluginHandler:
    """Get a plugin handler instance for the specified app type.

    Args:
        app_type: The app type (e.g., "claude")

    Returns:
        Plugin handler instance

    Raises:
        ValueError: If app_type is not supported
    """
    handler_class = PLUGIN_HANDLERS.get(app_type)
    if not handler_class:
        raise ValueError(f"Unknown app type: {app_type}. Valid: {VALID_APP_TYPES}")
    return handler_class()


class PluginManager:
    """Manages plugins storage and retrieval across all apps."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        handler_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """Initialize plugin manager.

        Args:
            config_dir: Configuration directory for plugin storage
            handler_overrides: Dict of app_type -> {'user_plugins': Path, 'project_plugins': Path, 'settings': Path}
                              for testing purposes
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "code-assistant-manager"
        self.config_dir = Path(config_dir)
        self.plugins_file = self.config_dir / "plugins.json"
        self.marketplaces_file = self.config_dir / "marketplaces.json"
        self.plugin_repos_file = self.config_dir / "plugin_repos.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize handlers with optional overrides
        self._handlers: Dict[str, BasePluginHandler] = {}
        for name, cls in PLUGIN_HANDLERS.items():
            overrides = (handler_overrides or {}).get(name, {})
            self._handlers[name] = cls(
                user_plugins_override=overrides.get("user_plugins"),
                project_plugins_override=overrides.get("project_plugins"),
                settings_override=overrides.get("settings"),
            )

    def get_handler(self, app_type: str) -> BasePluginHandler:
        """Get the handler for a specific app type."""
        handler = self._handlers.get(app_type)
        if not handler:
            raise ValueError(f"Unknown app type: {app_type}. Valid: {VALID_APP_TYPES}")
        return handler

    @property
    def claude(self) -> ClaudePluginHandler:
        """Get the Claude handler for Claude-specific operations."""
        return self._handlers["claude"]  # type: ignore

    # ==================== Plugin Storage Operations ====================

    def _load_plugins(self) -> Dict[str, Plugin]:
        """Load plugins from config file."""
        if not self.plugins_file.exists():
            return {}

        try:
            with open(self.plugins_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {key: Plugin.from_dict(val) for key, val in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load plugins: {e}")
            return {}

    def _save_plugins(self, plugins: Dict[str, Plugin]) -> None:
        """Save plugins to config file."""
        try:
            data = {key: plugin.to_dict() for key, plugin in plugins.items()}
            with open(self.plugins_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(plugins)} plugins to {self.plugins_file}")
        except Exception as e:
            logger.error(f"Failed to save plugins: {e}")
            raise

    def get_all(self) -> Dict[str, Plugin]:
        """Get all known plugins."""
        return self._load_plugins()

    def get(self, plugin_key: str) -> Optional[Plugin]:
        """Get a specific plugin by key."""
        plugins = self._load_plugins()
        return plugins.get(plugin_key)

    def get_by_name(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name."""
        plugins = self._load_plugins()
        for plugin in plugins.values():
            if plugin.name == name:
                return plugin
        return None

    def add(self, plugin: Plugin) -> None:
        """Add a plugin to the registry."""
        plugins = self._load_plugins()
        plugins[plugin.key] = plugin
        self._save_plugins(plugins)
        logger.info(f"Added plugin: {plugin.key}")

    def remove(self, plugin_key: str) -> None:
        """Remove a plugin from the registry."""
        plugins = self._load_plugins()
        if plugin_key not in plugins:
            raise ValueError(f"Plugin '{plugin_key}' not found")
        del plugins[plugin_key]
        self._save_plugins(plugins)
        logger.info(f"Removed plugin from registry: {plugin_key}")

    def update(self, plugin: Plugin) -> None:
        """Update a plugin in the registry."""
        plugins = self._load_plugins()
        plugins[plugin.key] = plugin
        self._save_plugins(plugins)
        logger.info(f"Updated plugin: {plugin.key}")

    # ==================== Marketplace Operations ====================

    def _load_marketplaces(self) -> Dict[str, Marketplace]:
        """Load marketplaces from config file."""
        if not self.marketplaces_file.exists():
            return {}

        try:
            with open(self.marketplaces_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {key: Marketplace.from_dict(val) for key, val in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load marketplaces: {e}")
            return {}

    def _save_marketplaces(self, marketplaces: Dict[str, Marketplace]) -> None:
        """Save marketplaces to config file."""
        try:
            data = {key: mp.to_dict() for key, mp in marketplaces.items()}
            with open(self.marketplaces_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(marketplaces)} marketplaces")
        except Exception as e:
            logger.error(f"Failed to save marketplaces: {e}")
            raise

    def get_all_marketplaces(self) -> Dict[str, Marketplace]:
        """Get all marketplaces."""
        return self._load_marketplaces()

    def add_marketplace(self, marketplace: Marketplace) -> None:
        """Add a marketplace."""
        marketplaces = self._load_marketplaces()
        marketplaces[marketplace.name] = marketplace
        self._save_marketplaces(marketplaces)
        logger.info(f"Added marketplace: {marketplace.name}")

    def remove_marketplace(self, name: str) -> None:
        """Remove a marketplace."""
        marketplaces = self._load_marketplaces()
        if name not in marketplaces:
            raise ValueError(f"Marketplace '{name}' not found")
        del marketplaces[name]
        self._save_marketplaces(marketplaces)
        logger.info(f"Removed marketplace: {name}")

    # ==================== Pre-registered Plugin Repos ====================

    def get_builtin_repos(self) -> Dict[str, PluginRepo]:
        """Get all built-in plugin repositories."""
        return BUILTIN_PLUGIN_REPOS.copy()

    def get_builtin_repo(self, name: str) -> Optional[PluginRepo]:
        """Get a built-in plugin repository by name (supports aliases)."""
        resolved = self._resolve_repo_name(name, self.get_builtin_repos())
        if resolved:
            return BUILTIN_PLUGIN_REPOS.get(resolved)
        return None

    # ==================== User Plugin Repos ====================

    def _load_user_repos(self) -> Dict[str, PluginRepo]:
        """Load user-configured plugin repos from config file."""
        if not self.plugin_repos_file.exists():
            return {}

        try:
            with open(self.plugin_repos_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            repos: Dict[str, PluginRepo] = {}
            for key, repo_data in data.items():
                repos[key] = PluginRepo(
                    name=repo_data.get("name", key),
                    description=repo_data.get("description", ""),
                    repo_owner=repo_data.get("repoOwner"),
                    repo_name=repo_data.get("repoName"),
                    repo_branch=repo_data.get("repoBranch", "main"),
                    plugin_path=repo_data.get("pluginPath"),
                    enabled=repo_data.get("enabled", True),
                    type=repo_data.get("type", "plugin"),
                    aliases=repo_data.get("aliases", []),
                )
            return repos
        except Exception as e:
            logger.warning(f"Failed to load user plugin repos: {e}")
            return {}

    def _save_user_repos(self, repos: Dict[str, PluginRepo]) -> None:
        """Save user plugin repos to config file."""
        data = {key: repo.to_dict() for key, repo in repos.items()}
        with open(self.plugin_repos_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_user_repos(self) -> Dict[str, PluginRepo]:
        """Get all user-configured plugin repositories."""
        return self._load_user_repos()

    def get_user_repo(self, name: str) -> Optional[PluginRepo]:
        """Get a user plugin repository by name (supports aliases)."""
        user_repos = self._load_user_repos()
        resolved = self._resolve_repo_name(name, user_repos)
        if resolved:
            return user_repos.get(resolved)
        return None

    def add_user_repo(self, repo: PluginRepo) -> None:
        """Add or update a user plugin repository."""
        repos = self._load_user_repos()
        repos[repo.name] = repo
        self._save_user_repos(repos)
        logger.info(f"Added/updated user repo: {repo.name}")

    def remove_user_repo(self, name: str) -> bool:
        """Remove a user plugin repository."""
        repos = self._load_user_repos()
        if name not in repos:
            return False
        del repos[name]
        self._save_user_repos(repos)
        logger.info(f"Removed user repo: {name}")
        return True

    def get_all_repos(self) -> Dict[str, PluginRepo]:
        """Get all plugin repos (builtin + user), user repos override builtin."""
        repos = self.get_builtin_repos()
        repos.update(self._load_user_repos())
        return repos

    def _resolve_repo_name(
        self, name: str, repos: Dict[str, PluginRepo]
    ) -> Optional[str]:
        """Resolve a repo name, checking for aliases. Returns the canonical name or None."""
        # First check if it's a direct match
        if name in repos:
            return name

        # Check if it's an alias
        for canonical_name, repo in repos.items():
            if name in repo.aliases:
                return canonical_name

        return None

    def get_repo(self, name: str) -> Optional[PluginRepo]:
        """Get a plugin repo by name, supporting aliases (user repos take precedence)."""
        all_repos = self.get_all_repos()
        resolved = self._resolve_repo_name(name, all_repos)
        if resolved:
            return all_repos.get(resolved)
        return None

    # ==================== Installation Operations ====================

    def install(
        self,
        source: str,
        app_type: str = "claude",
        scope: str = "user",
        branch: str = "main",
        plugin_path: Optional[str] = None,
        marketplace: Optional[str] = None,
    ) -> Plugin:
        """Install a plugin from a source (local path or GitHub repo).

        Args:
            source: Local path or GitHub repo in format "owner/repo"
            app_type: Target app type (default: "claude")
            scope: Installation scope ("user" or "project")
            branch: Git branch for GitHub repos
            plugin_path: Path to plugin within the repository
            marketplace: Optional marketplace name to associate with

        Returns:
            The installed Plugin object
        """
        handler = self.get_handler(app_type)
        source_path = Path(source).expanduser()

        # Check if source is a built-in repo name
        builtin = self.get_builtin_repo(source)
        if builtin and builtin.repo_owner and builtin.repo_name:
            plugin = handler.install_from_github(
                owner=builtin.repo_owner,
                repo=builtin.repo_name,
                branch=builtin.repo_branch,
                scope=scope,
                plugin_path=builtin.plugin_path,
                marketplace_name=marketplace,
            )
        elif source_path.exists():
            # Local path
            plugin = handler.install_from_local(
                source_path=source_path,
                scope=scope,
                marketplace_name=marketplace,
            )
        elif "/" in source and not source_path.exists():
            # GitHub repo format: owner/repo
            parts = source.split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid GitHub repo format. Use: owner/repo")
            owner, repo = parts
            plugin = handler.install_from_github(
                owner=owner,
                repo=repo,
                branch=branch,
                scope=scope,
                plugin_path=plugin_path,
                marketplace_name=marketplace,
            )
        else:
            raise ValueError(
                f"Invalid source: {source}. Must be a local path, GitHub repo (owner/repo), "
                f"or built-in repo name: {list(BUILTIN_PLUGIN_REPOS.keys())}"
            )

        # Save to registry
        self.add(plugin)
        return plugin

    def uninstall(
        self,
        plugin_key: str,
        app_type: str = "claude",
        scope: str = "user",
    ) -> None:
        """Uninstall a plugin.

        Args:
            plugin_key: Plugin key or name
            app_type: Target app type (default: "claude")
            scope: Installation scope ("user" or "project")
        """
        plugins = self._load_plugins()

        # Try to find by key or name
        plugin = plugins.get(plugin_key)
        if not plugin:
            plugin = self.get_by_name(plugin_key)
            if plugin:
                plugin_key = plugin.key

        if not plugin:
            raise ValueError(f"Plugin '{plugin_key}' not found")

        handler = self.get_handler(app_type)
        handler.uninstall(plugin.name, scope)
        handler.update_settings(plugin, enabled=False)

        plugin.installed = False
        self.update(plugin)
        logger.info(f"Uninstalled plugin: {plugin_key}")

    def enable(self, plugin_key: str, app_type: str = "claude") -> None:
        """Enable a plugin.

        Args:
            plugin_key: Plugin key or name
            app_type: Target app type (default: "claude")
        """
        plugins = self._load_plugins()
        plugin = plugins.get(plugin_key) or self.get_by_name(plugin_key)

        if not plugin:
            raise ValueError(f"Plugin '{plugin_key}' not found")

        handler = self.get_handler(app_type)
        handler.update_settings(plugin, enabled=True)

        plugin.enabled = True
        self.update(plugin)
        logger.info(f"Enabled plugin: {plugin_key}")

    def disable(self, plugin_key: str, app_type: str = "claude") -> None:
        """Disable a plugin.

        Args:
            plugin_key: Plugin key or name
            app_type: Target app type (default: "claude")
        """
        plugins = self._load_plugins()
        plugin = plugins.get(plugin_key) or self.get_by_name(plugin_key)

        if not plugin:
            raise ValueError(f"Plugin '{plugin_key}' not found")

        handler = self.get_handler(app_type)
        handler.update_settings(plugin, enabled=False)

        plugin.enabled = False
        self.update(plugin)
        logger.info(f"Disabled plugin: {plugin_key}")

    def scan_installed(
        self,
        app_type: str = "claude",
        scope: str = "user",
    ) -> List[Plugin]:
        """Scan for installed plugins.

        Args:
            app_type: Target app type (default: "claude")
            scope: Scope to scan ("user" or "project")

        Returns:
            List of installed Plugin objects
        """
        handler = self.get_handler(app_type)
        return handler.scan_installed(scope)

    def sync_installed_status(self, app_type: str = "claude") -> None:
        """Sync the installed status of all plugins.

        Args:
            app_type: Target app type (default: "claude")
        """
        plugins = self._load_plugins()

        # Scan both user and project scopes
        user_installed = {p.name for p in self.scan_installed(app_type, "user")}
        project_installed = {p.name for p in self.scan_installed(app_type, "project")}
        all_installed = user_installed | project_installed

        for plugin in plugins.values():
            plugin.installed = plugin.name in all_installed

        self._save_plugins(plugins)
        logger.debug(f"Synced installed status for {len(plugins)} plugins")

    # ==================== Import/Export Operations ====================

    def export_to_file(self, file_path: Path) -> None:
        """Export plugins to a JSON file."""
        plugins = self._load_plugins()
        data = {key: plugin.to_dict() for key, plugin in plugins.items()}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported {len(plugins)} plugins to {file_path}")

    def import_from_file(self, file_path: Path) -> int:
        """Import plugins from a JSON file.

        Returns:
            Number of plugins imported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        plugins = self._load_plugins()
        imported = 0

        for key, val in data.items():
            plugin = Plugin.from_dict(val)
            plugins[plugin.key] = plugin
            imported += 1

        self._save_plugins(plugins)
        logger.info(f"Imported {imported} plugins from {file_path}")
        return imported
