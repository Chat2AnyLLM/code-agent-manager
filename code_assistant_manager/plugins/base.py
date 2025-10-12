"""Base class for app-specific plugin handlers."""

import io
import json
import logging
import shutil
import subprocess
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Plugin

logger = logging.getLogger(__name__)


class BasePluginHandler(ABC):
    """Abstract base class for app-specific plugin handlers.

    Each AI tool (Claude, Codex, Gemini, etc.) can have its own implementation
    that defines how plugins are stored, installed, and managed.
    """

    def __init__(
        self,
        user_plugins_override: Optional[Path] = None,
        project_plugins_override: Optional[Path] = None,
        settings_override: Optional[Path] = None,
    ):
        """Initialize the handler with optional path overrides for testing.

        Args:
            user_plugins_override: Override the user-level plugins directory
            project_plugins_override: Override the project-level plugins directory
            settings_override: Override the settings file path
        """
        self._user_plugins_override = user_plugins_override
        self._project_plugins_override = project_plugins_override
        self._settings_override = settings_override

    @property
    @abstractmethod
    def app_name(self) -> str:
        """Return the name of the app (e.g., 'claude', 'codex')."""

    @property
    @abstractmethod
    def _default_home_dir(self) -> Path:
        """Return the default home directory for this app."""

    @property
    @abstractmethod
    def _default_user_plugins_dir(self) -> Path:
        """Return the default user-level plugins directory."""

    @property
    def _default_project_plugins_dir(self) -> Path:
        """Return the default project-level plugins directory."""
        return Path(f".{self.app_name}") / "plugins"

    @property
    @abstractmethod
    def _default_settings_file(self) -> Path:
        """Return the default settings file path."""

    @property
    @abstractmethod
    def plugin_manifest_path(self) -> str:
        """Return the relative path to the plugin manifest file within a plugin."""

    @property
    @abstractmethod
    def manifest_name_field(self) -> str:
        """Return the field name for plugin name in the manifest."""

    @property
    def home_dir(self) -> Path:
        """Return the home directory for this app."""
        return self._default_home_dir

    @property
    def user_plugins_dir(self) -> Path:
        """Return the user-level plugins directory."""
        if self._user_plugins_override is not None:
            return self._user_plugins_override
        return self._default_user_plugins_dir

    @property
    def project_plugins_dir(self) -> Path:
        """Return the project-level plugins directory."""
        if self._project_plugins_override is not None:
            return self._project_plugins_override
        return self._default_project_plugins_dir

    @property
    def settings_file(self) -> Path:
        """Return the settings file path."""
        if self._settings_override is not None:
            return self._settings_override
        return self._default_settings_file

    def get_plugins_dir(self, scope: str = "user") -> Path:
        """Get the plugins directory for the given scope.

        Args:
            scope: Either "user" or "project"

        Returns:
            Path to the plugins directory
        """
        if scope == "project":
            return self.project_plugins_dir
        return self.user_plugins_dir

    def validate_plugin_structure(
        self, path: Path
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate plugin directory structure and return manifest if valid.

        Args:
            path: Path to the plugin directory

        Returns:
            Tuple of (is_valid, manifest_dict or None)
        """
        manifest_path = path / self.plugin_manifest_path
        if not manifest_path.exists():
            return False, None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if self.manifest_name_field not in manifest:
                return False, None
            return True, manifest
        except Exception as e:
            logger.warning(f"Failed to read plugin manifest: {e}")
            return False, None

    def install_from_local(
        self,
        source_path: Path,
        scope: str = "user",
        marketplace_name: Optional[str] = None,
    ) -> Plugin:
        """Install a plugin from a local directory.

        Args:
            source_path: Path to the plugin source directory
            scope: Installation scope ("user" or "project")
            marketplace_name: Optional marketplace name to associate with

        Returns:
            The installed Plugin object

        Raises:
            ValueError: If the plugin structure is invalid
        """
        source_path = Path(source_path).expanduser().resolve()
        if not source_path.exists():
            raise ValueError(f"Path does not exist: {source_path}")

        valid, manifest = self.validate_plugin_structure(source_path)
        if not valid or manifest is None:
            raise ValueError(
                f"Invalid plugin structure. Expected {self.plugin_manifest_path} in {source_path}"
            )

        plugin_name = manifest[self.manifest_name_field]
        install_dir = self.get_plugins_dir(scope)
        install_dir.mkdir(parents=True, exist_ok=True)

        dest_path = install_dir / plugin_name
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(source_path, dest_path)

        plugin = Plugin(
            name=plugin_name,
            version=manifest.get("version", "1.0.0"),
            description=manifest.get("description", ""),
            local_path=str(source_path),
            marketplace=marketplace_name,
            installed=True,
            enabled=True,
        )

        self.update_settings(plugin, enabled=True)
        logger.info(f"Installed plugin: {plugin_name} to {dest_path}")
        return plugin

    def install_from_github(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        scope: str = "user",
        plugin_path: Optional[str] = None,
        marketplace_name: Optional[str] = None,
    ) -> Plugin:
        """Install a plugin from a GitHub repository.

        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            branch: Git branch name
            scope: Installation scope ("user" or "project")
            plugin_path: Path to plugin within the repository
            marketplace_name: Optional marketplace name to associate with

        Returns:
            The installed Plugin object
        """
        temp_dir, actual_branch = self._download_repo(owner, repo, branch)

        try:
            source_path = temp_dir / plugin_path if plugin_path else temp_dir

            valid, manifest = self.validate_plugin_structure(source_path)
            if not valid or manifest is None:
                raise ValueError(
                    f"Invalid plugin structure in {owner}/{repo}. "
                    f"Expected {self.plugin_manifest_path}"
                )

            plugin_name = manifest[self.manifest_name_field]
            install_dir = self.get_plugins_dir(scope)
            install_dir.mkdir(parents=True, exist_ok=True)

            dest_path = install_dir / plugin_name
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)

            plugin = Plugin(
                name=plugin_name,
                version=manifest.get("version", "1.0.0"),
                description=manifest.get("description", ""),
                repo_owner=owner,
                repo_name=repo,
                repo_branch=actual_branch,
                plugin_path=plugin_path,
                marketplace=marketplace_name,
                installed=True,
                enabled=True,
            )

            self.update_settings(plugin, enabled=True)
            logger.info(f"Installed plugin: {plugin_name} from {owner}/{repo}")
            return plugin
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def uninstall(self, plugin_name: str, scope: str = "user") -> bool:
        """Uninstall a plugin.

        Args:
            plugin_name: Name of the plugin to uninstall
            scope: Installation scope ("user" or "project")

        Returns:
            True if successful, False otherwise
        """
        install_dir = self.get_plugins_dir(scope) / plugin_name

        if install_dir.exists():
            shutil.rmtree(install_dir)
            logger.info(f"Removed plugin directory: {install_dir}")
            return True
        return False

    def scan_installed(self, scope: str = "user") -> List[Plugin]:
        """Scan for installed plugins in the plugins directory.

        Args:
            scope: Installation scope ("user" or "project")

        Returns:
            List of installed Plugin objects
        """
        plugins_dir = self.get_plugins_dir(scope)
        if not plugins_dir.exists():
            return []

        installed = []
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            valid, manifest = self.validate_plugin_structure(plugin_dir)
            if not valid or manifest is None:
                continue

            plugin = Plugin(
                name=manifest[self.manifest_name_field],
                version=manifest.get("version", "1.0.0"),
                description=manifest.get("description", ""),
                local_path=str(plugin_dir),
                installed=True,
            )
            installed.append(plugin)

        return installed

    def update_settings(self, plugin: Plugin, enabled: bool) -> None:
        """Update the app's settings to enable/disable a plugin.

        Args:
            plugin: The plugin to update
            enabled: Whether to enable or disable the plugin
        """
        settings: Dict[str, Any] = {}
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read settings: {e}")

        if "enabledPlugins" not in settings:
            settings["enabledPlugins"] = {}

        settings["enabledPlugins"][plugin.key] = enabled

        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        logger.debug(f"Updated settings: {plugin.key} = {enabled}")

    def _download_repo(
        self, owner: str, name: str, branch: str = "main"
    ) -> Tuple[Path, str]:
        """Download a GitHub repository as a zip file and extract it.

        Args:
            owner: Repository owner
            name: Repository name
            branch: Branch name

        Returns:
            Tuple of (Path to extracted directory, actual branch name used)
        """
        branches = [branch]
        if branch == "main":
            branches = ["main", "master"]
        elif branch == "master":
            branches = ["master", "main"]
        else:
            branches = [branch, "main", "master"]

        for try_branch in branches:
            url = (
                f"https://github.com/{owner}/{name}/archive/refs/heads/{try_branch}.zip"
            )
            logger.debug(f"Trying to download: {url}")

            try:
                req = Request(url, headers={"User-Agent": "code-assistant-manager"})
                with urlopen(req, timeout=60) as response:
                    zip_data = response.read()

                temp_dir = Path(tempfile.mkdtemp(prefix="cam-plugin-"))

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    root_dir = None
                    for name_in_zip in zf.namelist():
                        parts = name_in_zip.split("/")
                        if len(parts) > 1 and not root_dir:
                            root_dir = parts[0]

                        if root_dir and name_in_zip.startswith(root_dir + "/"):
                            rel_path = name_in_zip[len(root_dir) + 1 :]
                            if not rel_path:
                                continue

                            target_path = temp_dir / rel_path
                            if name_in_zip.endswith("/"):
                                target_path.mkdir(parents=True, exist_ok=True)
                            else:
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                with (
                                    zf.open(name_in_zip) as src,
                                    open(target_path, "wb") as dst,
                                ):
                                    dst.write(src.read())

                logger.info(f"Downloaded repository {owner}/{name}@{try_branch}")
                return temp_dir, try_branch

            except HTTPError as e:
                if e.code == 404:
                    logger.debug(f"Branch {try_branch} not found, trying next")
                    continue
                raise
            except URLError as e:
                logger.error(f"Failed to download repository: {e}")
                raise

        raise ValueError(f"Could not download repository {owner}/{name}")

    def use_cli(self, command: str, *args: str) -> Tuple[int, str, str]:
        """Execute a CLI command for this app.

        Args:
            command: The subcommand to run
            *args: Additional arguments

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [self.app_name, "plugin", command, *args]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", f"{self.app_name} CLI not found"

    def get_cli_path(self) -> Optional[str]:
        """Get the path to the app's CLI executable.

        Returns:
            Path to CLI executable, or None if not found
        """
        return shutil.which(self.app_name)
