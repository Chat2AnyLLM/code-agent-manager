"""Base fetching framework for skills, agents, and plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

# Generic type for entity (Skill, Agent, Plugin, etc.)
T = TypeVar('T')

@dataclass
class RepoConfig:
    """Generic repository configuration."""
    owner: str
    name: str
    branch: str = "main"
    path: Optional[str] = None  # Subdirectory path (skills_path, agents_path, etc.)
    enabled: bool = True


class EntityParser(ABC, Generic[T]):
    """Abstract parser for converting raw data to entities."""

    @abstractmethod
    def parse_from_file(
        self,
        file_path: Path,
        repo_config: RepoConfig
    ) -> Optional[T]:
        """Parse entity from a file.

        Args:
            file_path: Path to the file to parse
            repo_config: Repository configuration

        Returns:
            Parsed entity or None if invalid
        """
        pass

    @abstractmethod
    def get_file_pattern(self) -> str:
        """Get glob pattern for entity files (e.g., 'SKILL.md', '*.md')."""
        pass

    @abstractmethod
    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create unique key for entity."""
        pass


class BaseEntityFetcher(ABC, Generic[T]):
    """Base class for fetching entities from repositories.

    This provides a unified interface for fetching skills, agents, plugins, etc.
    """

    def __init__(self, parser: EntityParser[T], cache_ttl: int = 3600):
        """Initialize fetcher.

        Args:
            parser: Parser for converting files to entities
            cache_ttl: Cache time-to-live in seconds
        """
        self.parser = parser
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}

    def fetch_from_repos(
        self,
        repos: List[RepoConfig],
        max_workers: int = 8,
        use_cache: bool = True
    ) -> List[T]:
        """Fetch entities from multiple repositories in parallel.

        Args:
            repos: List of repository configurations
            max_workers: Maximum number of concurrent fetchers
            use_cache: Whether to use caching

        Returns:
            List of discovered entities
        """
        from code_assistant_manager.fetching.parallel import ParallelFetcher

        # Filter enabled repos
        enabled_repos = [r for r in repos if r.enabled]

        if not enabled_repos:
            logger.warning("No enabled repositories found")
            return []

        logger.info(f"Fetching from {len(enabled_repos)} repositories in parallel")

        # Use parallel fetcher
        parallel_fetcher = ParallelFetcher(
            fetcher_func=self._fetch_from_single_repo,
            max_workers=max_workers
        )

        results = parallel_fetcher.fetch_all(enabled_repos)

        # Flatten results
        all_entities = []
        for entities in results:
            all_entities.extend(entities)

        logger.info(f"Total entities fetched: {len(all_entities)}")
        return all_entities

    def _fetch_from_single_repo(self, repo: RepoConfig) -> List[T]:
        """Fetch entities from a single repository.

        Args:
            repo: Repository configuration

        Returns:
            List of entities found in the repository
        """
        from code_assistant_manager.fetching.repository import GitRepository

        git_repo = GitRepository(
            owner=repo.owner,
            name=repo.name,
            branch=repo.branch
        )

        entities = []

        try:
            # Clone/download repository
            with git_repo.clone() as (temp_dir, actual_branch):
                # Determine scan directory
                scan_dir = temp_dir
                if repo.path:
                    scan_dir = temp_dir / repo.path.strip("/")

                if not scan_dir.exists():
                    logger.warning(f"Path not found: {scan_dir}")
                    return entities

                # Find entity files
                file_pattern = self.parser.get_file_pattern()
                for entity_file in scan_dir.rglob(file_pattern):
                    try:
                        entity = self.parser.parse_from_file(entity_file, repo)
                        if entity:
                            entities.append(entity)
                            logger.debug(f"Found entity: {entity}")
                    except Exception as e:
                        logger.warning(f"Failed to parse {entity_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch from {repo.owner}/{repo.name}: {e}")

        return entities