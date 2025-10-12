"""Base class for app-specific skill handlers."""

import io
import logging
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from .models import Skill

logger = logging.getLogger(__name__)


class BaseSkillHandler(ABC):
    """Abstract base class for app-specific skill handlers.

    Each AI tool (Claude, Codex, Gemini, Droid) can have its own implementation
    that defines how skills are stored and managed.
    """

    def __init__(
        self,
        skills_dir_override: Optional[Path] = None,
    ):
        """Initialize the handler with optional path overrides for testing.

        Args:
            skills_dir_override: Override the skills directory
        """
        self._skills_dir_override = skills_dir_override

    @property
    @abstractmethod
    def app_name(self) -> str:
        """Return the name of the app (e.g., 'claude', 'codex')."""

    @property
    @abstractmethod
    def _default_skills_dir(self) -> Path:
        """Return the default skills directory for this app."""

    @property
    def skills_dir(self) -> Path:
        """Return the skills directory."""
        if self._skills_dir_override is not None:
            return self._skills_dir_override
        return self._default_skills_dir

    def install(self, skill: Skill) -> Path:
        """Install a skill by downloading and copying to the skills directory.

        Args:
            skill: The skill to install

        Returns:
            Path to the installed skill directory

        Raises:
            ValueError: If skill has no repository information
        """
        if not skill.repo_owner or not skill.repo_name:
            raise ValueError(f"Skill '{skill.key}' has no repository information")

        # Ensure install directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Download and install
        temp_dir, _ = self._download_repo(
            skill.repo_owner, skill.repo_name, skill.repo_branch or "main"
        )

        try:
            # Determine source path
            source_dir = skill.source_directory or skill.directory
            if skill.skills_path:
                source_path = temp_dir / skill.skills_path.strip("/") / source_dir
            else:
                source_path = temp_dir / source_dir

            if not source_path.exists():
                raise ValueError(
                    f"Skill directory not found in repository: {source_path}"
                )

            # Copy to install directory using skill.directory as the folder name
            dest_path = self.skills_dir / skill.directory
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)
            logger.info(f"Installed skill to: {dest_path}")
            return dest_path
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def uninstall(self, skill: Skill) -> bool:
        """Uninstall a skill by removing its directory.

        Args:
            skill: The skill to uninstall

        Returns:
            True if directory was removed, False if it didn't exist
        """
        skill_dir = self.skills_dir / skill.directory
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            logger.info(f"Removed skill directory: {skill_dir}")
            return True
        return False

    def get_installed_dirs(self) -> List[Path]:
        """Get list of installed skill directories.

        Returns:
            List of paths to installed skill directories containing SKILL.md
        """
        if not self.skills_dir.exists():
            return []

        installed = []
        for skill_md in self.skills_dir.rglob("SKILL.md"):
            skill_dir = skill_md.parent
            if skill_dir.is_dir():
                installed.append(skill_dir)
        return installed

    def is_installed(self, skill: Skill) -> bool:
        """Check if a skill is installed.

        Args:
            skill: The skill to check

        Returns:
            True if the skill directory exists with SKILL.md
        """
        skill_dir = self.skills_dir / skill.directory
        return (skill_dir / "SKILL.md").exists()

    def parse_skill_metadata(self, skill_md_path: Path) -> Dict:
        """Parse skill metadata from SKILL.md file.

        Args:
            skill_md_path: Path to the SKILL.md file

        Returns:
            Dictionary with name and description
        """
        try:
            content = skill_md_path.read_text(encoding="utf-8")
            content = content.lstrip("\ufeff")  # Remove BOM

            parts = content.split("---", 2)
            if len(parts) >= 3:
                front_matter = parts[1].strip()
                try:
                    meta = yaml.safe_load(front_matter)
                    if isinstance(meta, dict):
                        return {
                            "name": meta.get("name"),
                            "description": meta.get("description", ""),
                        }
                except yaml.YAMLError as e:
                    logger.debug(f"Failed to parse YAML front matter: {e}")
        except Exception as e:
            logger.debug(f"Failed to read SKILL.md: {e}")

        return {}

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

                temp_dir = Path(tempfile.mkdtemp(prefix="cam-skill-"))

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
