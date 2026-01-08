"""Skill manager for Code Assistant Manager.

This module provides the SkillManager class that orchestrates skill operations
across different AI tool handlers.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from ..repo_loader import RepoConfigLoader
from ..fetching.base import BaseEntityFetcher, RepoConfig
from .base import BaseSkillHandler
from .claude import ClaudeSkillHandler
from .codebuddy import CodebuddySkillHandler
from .codex import CodexSkillHandler
from .copilot import CopilotSkillHandler
from .droid import DroidSkillHandler
from .gemini import GeminiSkillHandler
from .qwen import QwenSkillHandler
from .models import Skill, SkillRepo

logger = logging.getLogger(__name__)


def _load_builtin_skill_repos() -> Dict:
    """Load built-in skill repos from the bundled skill_repos.json file.

    Returns bundled repos as a dictionary for fallback.
    """
    package_dir = Path(__file__).parent.parent
    repos_file = package_dir / "skill_repos.json"

    if repos_file.exists():
        try:
            with open(repos_file, "r", encoding="utf-8") as f:
                repos_data = json.load(f)
                return repos_data
        except Exception as e:
            logger.warning(f"Failed to load builtin skill repos: {e}")

    # Fallback defaults
    return {
        "ComposioHQ/awesome-claude-skills": {
            "owner": "ComposioHQ",
            "name": "awesome-claude-skills",
            "branch": "main",
            "enabled": True,
            "skillsPath": None,
        },
        "obra/superpowers": {
            "owner": "obra",
            "name": "superpowers",
            "branch": "main",
            "enabled": True,
            "skillsPath": "skills",
        },
    }


def _load_skill_repos_from_config(config_dir: Optional[Path] = None) -> List[Dict]:
    """Load skill repos from config.yaml sources.

    Args:
        config_dir: Configuration directory

    Returns:
        List of repository configurations
    """
    loader = RepoConfigLoader(config_dir)
    bundled_fallback = _load_builtin_skill_repos()

    # Get repos from all configured sources
    repos_dict = loader.get_repos("skills", bundled_fallback)

    # Convert to list format for backward compatibility
    return [
        {
            "owner": repo.get("owner"),
            "name": repo.get("name"),
            "branch": repo.get("branch", "main"),
            "enabled": repo.get("enabled", True),
            "skillsPath": repo.get("skillsPath"),
            "exclude": repo.get("exclude"),
        }
        for repo in repos_dict.values()
    ]


DEFAULT_SKILL_REPOS = _load_skill_repos_from_config()

# Registry of available handlers
SKILL_HANDLERS: Dict[str, Type[BaseSkillHandler]] = {
    "claude": ClaudeSkillHandler,
    "codex": CodexSkillHandler,
    "copilot": CopilotSkillHandler,
    "gemini": GeminiSkillHandler,
    "droid": DroidSkillHandler,
    "codebuddy": CodebuddySkillHandler,
    "qwen": QwenSkillHandler,
}

# Valid app types for skills
VALID_APP_TYPES = list(SKILL_HANDLERS.keys())


class SkillManager:
    """Manages skills storage, retrieval, and operations across different tools."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize skill manager.

        Args:
            config_dir: Configuration directory (defaults to ~/.config/code-assistant-manager)
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "code-assistant-manager"
        self.config_dir = Path(config_dir)
        self.skills_file = self.config_dir / "skills.json"
        self.repos_file = self.config_dir / "skill_repos.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize fetcher with skill parser
        from ..fetching.parsers import SkillParser
        self.fetcher = BaseEntityFetcher(parser=SkillParser())

        # Initialize handlers
        self._handlers: Dict[str, BaseSkillHandler] = {}
        for app_name, handler_class in SKILL_HANDLERS.items():
            self._handlers[app_name] = handler_class()

    def get_handler(self, app_type: str) -> BaseSkillHandler:
        """Get the handler for a specific app type.

        Args:
            app_type: The app type (e.g., 'claude', 'codex')

        Returns:
            The handler instance

        Raises:
            ValueError: If app_type is not supported
        """
        if app_type not in self._handlers:
            raise ValueError(
                f"Unknown app type: {app_type}. Supported: {list(self._handlers.keys())}"
            )
        return self._handlers[app_type]

    def _load_skills(self) -> Dict[str, Skill]:
        """Load skills from file."""
        if not self.skills_file.exists():
            return {}

        try:
            with open(self.skills_file, "r") as f:
                data = json.load(f)
            return {
                skill_key: Skill.from_dict(skill_data)
                for skill_key, skill_data in data.items()
            }
        except Exception as e:
            logger.warning(f"Failed to load skills: {e}")
            return {}

    def _save_skills(self, skills: Dict[str, Skill]) -> None:
        """Save skills to file."""
        try:
            data = {skill_key: skill.to_dict() for skill_key, skill in skills.items()}
            with open(self.skills_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(skills)} skills to {self.skills_file}")
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")
            raise

    def _load_repos(self) -> Dict[str, SkillRepo]:
        """Load skill repos from config sources (local + remote).
        
        Uses RepoConfigLoader to dynamically load from all configured sources,
        ensuring we always get the latest repository list from remote sources.
        """
        bundled_fallback = _load_builtin_skill_repos()
        repos_data_list = _load_skill_repos_from_config(self.config_dir)
        
        # Convert list format to dict format with SkillRepo objects
        repos = {}
        for repo_data in repos_data_list:
            repo = SkillRepo(
                owner=repo_data["owner"],
                name=repo_data["name"],
                branch=repo_data.get("branch", "main"),
                enabled=repo_data.get("enabled", True),
                skills_path=repo_data.get("skillsPath"),
                exclude=repo_data.get("exclude"),
            )
            repo_id = f"{repo.owner}/{repo.name}"
            repos[repo_id] = repo
        
        return repos

    def _init_default_repos_file(self) -> None:
        """Initialize the repos file with default skill repos."""
        repos = {}
        for repo_data in DEFAULT_SKILL_REPOS:
            repo = SkillRepo(
                owner=repo_data["owner"],
                name=repo_data["name"],
                branch=repo_data.get("branch", "main"),
                enabled=repo_data.get("enabled", True),
                skills_path=repo_data.get("skillsPath"),
                exclude=repo_data.get("exclude"),
            )
            repo_id = f"{repo.owner}/{repo.name}"
            repos[repo_id] = repo

        self._save_repos(repos)
        logger.info(f"Initialized {len(repos)} default skill repos")

    def _save_repos(self, repos: Dict[str, SkillRepo]) -> None:
        """Save skill repos to file."""
        try:
            data = {repo_id: repo.to_dict() for repo_id, repo in repos.items()}
            with open(self.repos_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(repos)} skill repos to {self.repos_file}")
        except Exception as e:
            logger.error(f"Failed to save skill repos: {e}")
            raise

    def get_all(self) -> Dict[str, Skill]:
        """Get all skills."""
        return self._load_skills()

    def get(self, skill_key: str) -> Optional[Skill]:
        """Get a specific skill by key (can be actual key or install key format repo:directory)."""
        skills = self._load_skills()

        # First try direct lookup with the provided key
        skill = skills.get(skill_key)
        if skill:
            return skill

        # If not found, try to find by install key format (repo:directory)
        if ":" in skill_key:
            repo_part, directory_part = skill_key.rsplit(":", 1)
            # Look for skills that match this repo and directory
            for stored_skill in skills.values():
                if (stored_skill.repo_owner and stored_skill.repo_name and
                    f"{stored_skill.repo_owner}/{stored_skill.repo_name}" == repo_part and
                    stored_skill.directory == directory_part):
                    return stored_skill

        return None

    def create(self, skill: Skill) -> None:
        """Create a new skill."""
        skills = self._load_skills()
        if skill.key in skills:
            raise ValueError(f"Skill with key '{skill.key}' already exists")
        skills[skill.key] = skill
        self._save_skills(skills)
        logger.info(f"Created skill: {skill.key}")

    def update(self, skill: Skill) -> None:
        """Update an existing skill."""
        skills = self._load_skills()
        if skill.key not in skills:
            raise ValueError(f"Skill with key '{skill.key}' not found")
        skills[skill.key] = skill
        self._save_skills(skills)
        logger.info(f"Updated skill: {skill.key}")

    def upsert(self, skill: Skill) -> None:
        """Create or update a skill."""
        skills = self._load_skills()
        skills[skill.key] = skill
        self._save_skills(skills)
        logger.info(f"Upserted skill: {skill.key}")

    def delete(self, skill_key: str) -> None:
        """Delete a skill by key (can be actual key or install key format repo:directory)."""
        skills = self._load_skills()

        # First try direct lookup with the provided key
        if skill_key not in skills:
            # If not found, try to find by install key format (repo:directory)
            if ":" in skill_key:
                repo_part, directory_part = skill_key.rsplit(":", 1)
                # Look for skills that match this repo and directory
                for stored_key, skill in skills.items():
                    if (skill.repo_owner and skill.repo_name and
                        f"{skill.repo_owner}/{skill.repo_name}" == repo_part and
                        skill.directory == directory_part):
                        skill_key = stored_key
                        break
                else:
                    raise ValueError(f"Skill with key '{skill_key}' not found")

        del skills[skill_key]
        self._save_skills(skills)
        logger.info(f"Deleted skill: {skill_key}")

    def get_repos(self) -> List[SkillRepo]:
        """Get all skill repos."""
        repos = self._load_repos()
        return list(repos.values())

    def add_repo(self, repo: SkillRepo) -> None:
        """Add a skill repo."""
        repos = self._load_repos()
        repo_id = f"{repo.owner}/{repo.name}"
        repos[repo_id] = repo
        self._save_repos(repos)
        logger.info(f"Added skill repo: {repo_id}")

    def remove_repo(self, owner: str, name: str) -> None:
        """Remove a skill repo."""
        repos = self._load_repos()
        repo_id = f"{owner}/{name}"
        if repo_id not in repos:
            raise ValueError(f"Skill repo '{repo_id}' not found")
        del repos[repo_id]
        self._save_repos(repos)
        logger.info(f"Removed skill repo: {repo_id}")

    def install(self, skill_key: str, app_type: str = "claude") -> Path:
        """Install a skill for a specific app.

        Args:
            skill_key: The skill identifier (can be actual key or install key format repo:directory)
            app_type: The app type to install to

        Returns:
            Path to the installed skill directory

        Raises:
            ValueError: If skill_key is not found
        """
        skills = self._load_skills()

        # First try direct lookup with the provided key
        if skill_key not in skills:
            # If not found, try to find by install key format (repo:directory)
            if ":" in skill_key:
                repo_part, directory_part = skill_key.rsplit(":", 1)
                # Look for skills that match this repo and directory
                for stored_key, skill in skills.items():
                    if (skill.repo_owner and skill.repo_name and
                        f"{skill.repo_owner}/{skill.repo_name}" == repo_part and
                        skill.directory == directory_part):
                        skill_key = stored_key
                        break
                else:
                    raise ValueError(f"Skill with key '{skill_key}' not found")

        if skill_key not in skills:
            raise ValueError(f"Skill with key '{skill_key}' not found")

        skill = skills[skill_key]
        handler = self.get_handler(app_type)

        dest_path = handler.install(skill)

        # Update installed status
        skill.installed = True
        self._save_skills(skills)
        logger.info(f"Installed skill: {skill_key} to {app_type}")

        return dest_path

    def uninstall(self, skill_key: str, app_type: str = "claude") -> None:
        """Uninstall a skill from a specific app.

        Args:
            skill_key: The skill identifier (can be actual key or install key format repo:directory)
            app_type: The app type to uninstall from
        """
        skills = self._load_skills()

        # First try direct lookup with the provided key
        if skill_key not in skills:
            # If not found, try to find by install key format (repo:directory)
            if ":" in skill_key:
                repo_part, directory_part = skill_key.rsplit(":", 1)
                # Look for skills that match this repo and directory
                for stored_key, skill in skills.items():
                    if (skill.repo_owner and skill.repo_name and
                        f"{skill.repo_owner}/{skill.repo_name}" == repo_part and
                        skill.directory == directory_part):
                        skill_key = stored_key
                        break
                else:
                    raise ValueError(f"Skill with key '{skill_key}' not found")

        if skill_key not in skills:
            raise ValueError(f"Skill with key '{skill_key}' not found")

        skill = skills[skill_key]
        handler = self.get_handler(app_type)

        handler.uninstall(skill)

        # Update installed status
        skill.installed = False
        self._save_skills(skills)
        logger.info(f"Uninstalled skill: {skill_key} from {app_type}")

    def fetch_skills_from_repos(self, max_workers: int = 8) -> List[Skill]:
        """Fetch all skills from configured repositories in parallel.

        Args:
            max_workers: Maximum number of concurrent repository fetchers

        Returns:
            List of discovered skills
        """
        repos = self._load_repos()
        if not repos:
            self._init_default_repos_file()
            repos = self._load_repos()

        # Convert SkillRepo objects to RepoConfig objects for the fetcher
        repo_configs = [
            RepoConfig(
                owner=repo.owner,
                name=repo.name,
                branch=repo.branch,
                path=repo.skills_path,
                exclude=repo.exclude,
                enabled=repo.enabled
            )
            for repo in repos.values()
        ]

        # Fetch using unified fetcher
        skills = self.fetcher.fetch_from_repos(
            repos=repo_configs,
            max_workers=max_workers
        )

        # Deduplicate skills based on key - if the same skill appears multiple times
        # (e.g., from different repository configurations), keep only the first occurrence
        unique_skills = []
        seen_keys = set()
        for skill in skills:
            if skill.key not in seen_keys:
                unique_skills.append(skill)
                seen_keys.add(skill.key)

        # Update installed status from existing skills
        existing_skills = self._load_skills()
        for skill in unique_skills:
            if skill.key in existing_skills:
                skill.installed = existing_skills[skill.key].installed
            existing_skills[skill.key] = skill

        # Save updated skills
        self._save_skills(existing_skills)

        logger.info(f"Total skills fetched: {len(skills)}")
        return skills

    def sync_installed_status(self, app_type: str = "claude") -> None:
        """Sync the installed status of all skills.

        Args:
            app_type: The app type to check
        """
        handler = self.get_handler(app_type)
        installed_dirs = set()

        for skill_dir in handler.get_installed_dirs():
            try:
                rel_path = skill_dir.relative_to(handler.skills_dir)
                installed_dirs.add(str(rel_path).replace("\\", "/").lower())
            except ValueError:
                continue

        skills = self._load_skills()
        for skill in skills.values():
            skill.installed = skill.directory.lower() in installed_dirs
        self._save_skills(skills)
        logger.debug(f"Synced installed status for {len(skills)} skills")

    def get_installed_skills(self, app_type: str = "claude") -> List[Skill]:
        """Get all installed skills for a specific app.

        Args:
            app_type: The app type to check

        Returns:
            List of installed skills
        """
        handler = self.get_handler(app_type)
        installed_dirs = handler.get_installed_dirs()

        if not installed_dirs:
            return []

        installed_skills = []
        existing_skills = self._load_skills()

        for skill_dir in installed_dirs:
            try:
                rel_path = skill_dir.relative_to(handler.skills_dir)
                directory = str(rel_path).replace("\\", "/")
            except ValueError:
                continue

            # Find matching skill in database
            matching_skill = None
            for skill in existing_skills.values():
                if skill.directory.lower() == directory.lower():
                    matching_skill = skill
                    break

            if matching_skill:
                matching_skill.installed = True
                installed_skills.append(matching_skill)
            else:
                # Local skill not in database
                skill_md = skill_dir / "SKILL.md"
                meta = (
                    handler.parse_skill_metadata(skill_md) if skill_md.exists() else {}
                )
                skill = Skill(
                    key=f"local:{directory}",
                    name=meta.get("name", directory.split("/")[-1]),
                    description=meta.get("description", ""),
                    directory=directory,
                    installed=True,
                )
                installed_skills.append(skill)

        return installed_skills

    def import_from_file(self, file_path: Path) -> None:
        """Import skills from a JSON file."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            skills = self._load_skills()
            imported_count = 0

            if isinstance(data, dict):
                for skill_key, skill_data in data.items():
                    if isinstance(skill_data, dict):
                        skill = Skill.from_dict(skill_data)
                        skills[skill.key] = skill
                        imported_count += 1
            elif isinstance(data, list):
                for skill_data in data:
                    if isinstance(skill_data, dict):
                        skill = Skill.from_dict(skill_data)
                        skills[skill.key] = skill
                        imported_count += 1

            self._save_skills(skills)
            logger.info(f"Imported {imported_count} skills from {file_path}")
        except Exception as e:
            logger.error(f"Failed to import skills: {e}")
            raise

    def export_to_file(self, file_path: Path) -> None:
        """Export skills to a JSON file."""
        try:
            skills = self._load_skills()
            data = {skill_key: skill.to_dict() for skill_key, skill in skills.items()}
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported {len(skills)} skills to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export skills: {e}")
            raise
