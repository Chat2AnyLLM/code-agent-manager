"""Repository configuration loader.

Loads repository configurations from multiple sources:
1. Local JSON files
2. Remote URLs (with caching)
3. Bundled defaults (fallback)
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import yaml

logger = logging.getLogger(__name__)


class RepoConfigLoader:
    """Loads repository configurations from config.yaml sources."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the repo config loader.

        Args:
            config_dir: Configuration directory (defaults to ~/.config/code-assistant-manager)
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "code-assistant-manager"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load config.yaml
        self.config = self._load_config()

        # Setup cache directory
        cache_config = self.config.get("cache", {})
        cache_dir = cache_config.get("directory", "~/.cache/code-assistant-manager/repos")
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_config.get("ttl_seconds", 3600)
        self.cache_enabled = cache_config.get("enabled", True)

    def _load_config(self) -> Dict:
        """Load config.yaml file.
        
        Tries user config first, then falls back to bundled config.
        """
        user_config_path = self.config_dir / "config.yaml"
        package_dir = Path(__file__).parent
        bundled_config_path = package_dir / "config.yaml"

        # Try to load user config first, fallback to bundled
        config_path = user_config_path if user_config_path.exists() else bundled_config_path

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {"repositories": {}}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded config from: {config_path}")
                return config or {}
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return {"repositories": {}}

    def get_repos(self, repo_type: str, bundled_fallback: Optional[Dict] = None) -> Dict:
        """Get repositories for a specific type (skills, agents, plugins).

        Args:
            repo_type: Type of repository ('skills', 'agents', or 'plugins')
            bundled_fallback: Bundled default repos to use if all sources fail

        Returns:
            Dictionary of repository configurations
        """
        repos = {}

        # Get sources from config
        repo_config = self.config.get("repositories", {}).get(repo_type, {})
        sources = repo_config.get("sources", [])

        if not sources:
            logger.warning(f"No sources configured for {repo_type}, using bundled defaults")
            return bundled_fallback or {}

        # Load from each source (in order)
        for source in sources:
            source_type = source.get("type")

            if source_type == "local":
                loaded = self._load_local_source(source)
                if loaded:
                    repos.update(loaded)
                    logger.debug(f"Loaded {len(loaded)} repos from local source")

            elif source_type == "remote":
                loaded = self._load_remote_source(source, repo_type)
                if loaded:
                    # Don't override local repos
                    for key, value in loaded.items():
                        if key not in repos:
                            repos[key] = value
                    logger.debug(f"Loaded {len(loaded)} repos from remote source")

        # If no repos loaded, use bundled fallback
        if not repos and bundled_fallback:
            logger.info(f"No repos loaded from configured sources, using bundled defaults for {repo_type}")
            repos = bundled_fallback

        return repos

    def _load_local_source(self, source: Dict) -> Optional[Dict]:
        """Load repositories from a local JSON file.

        Args:
            source: Source configuration dict

        Returns:
            Dictionary of repositories or None if failed
        """
        path_str = source.get("path", "")
        if not path_str:
            return None

        path = Path(path_str).expanduser()

        if not path.exists():
            logger.debug(f"Local repo file not found: {path}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded local repos from: {path}")
                return data
        except Exception as e:
            logger.error(f"Failed to load local repos from {path}: {e}")
            return None

    def _load_remote_source(self, source: Dict, repo_type: str) -> Optional[Dict]:
        """Load repositories from a remote URL.

        Args:
            source: Source configuration dict
            repo_type: Type of repository for cache key

        Returns:
            Dictionary of repositories or None if failed
        """
        url = source.get("url", "")
        if not url:
            return None

        # Check cache first
        if self.cache_enabled:
            cached = self._load_from_cache(url, repo_type)
            if cached:
                return cached

        # Fetch from remote
        try:
            logger.info(f"Fetching remote repos from: {url}")
            request = Request(url, headers={"User-Agent": "code-assistant-manager"})

            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Save to cache
            if self.cache_enabled:
                self._save_to_cache(url, repo_type, data)

            logger.info(f"Loaded remote repos from: {url}")
            return data

        except (URLError, HTTPError, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch remote repos from {url}: {e}")
            return None

    def _load_from_cache(self, url: str, repo_type: str) -> Optional[Dict]:
        """Load repositories from cache if not expired.

        Args:
            url: Remote URL
            repo_type: Type of repository

        Returns:
            Dictionary of repositories or None if cache miss/expired
        """
        cache_file = self._get_cache_file(url, repo_type)

        if not cache_file.exists():
            return None

        # Check if expired
        try:
            mtime = cache_file.stat().st_mtime
            age = time.time() - mtime

            if age > self.cache_ttl:
                logger.debug(f"Cache expired for {url}")
                return None

            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.debug(f"Loaded from cache: {cache_file.name}")
            return data

        except Exception as e:
            logger.debug(f"Failed to load from cache: {e}")
            return None

    def _save_to_cache(self, url: str, repo_type: str, data: Dict):
        """Save repositories to cache.

        Args:
            url: Remote URL
            repo_type: Type of repository
            data: Repository data to cache
        """
        cache_file = self._get_cache_file(url, repo_type)

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved to cache: {cache_file.name}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_cache_file(self, url: str, repo_type: str) -> Path:
        """Get cache file path for a URL.

        Args:
            url: Remote URL
            repo_type: Type of repository

        Returns:
            Path to cache file
        """
        # Create a safe filename from URL
        safe_name = url.replace("https://", "").replace("http://", "")
        safe_name = safe_name.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{repo_type}_{safe_name}.json"

    def clear_cache(self, repo_type: Optional[str] = None):
        """Clear cache files.

        Args:
            repo_type: Specific type to clear, or None for all
        """
        if repo_type:
            pattern = f"{repo_type}_*.json"
        else:
            pattern = "*.json"

        for cache_file in self.cache_dir.glob(pattern):
            try:
                cache_file.unlink()
                logger.info(f"Cleared cache: {cache_file.name}")
            except Exception as e:
                logger.warning(f"Failed to clear cache {cache_file.name}: {e}")
