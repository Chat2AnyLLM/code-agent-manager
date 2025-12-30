"""Repository pattern for data access.

Abstracts data storage and retrieval.
"""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .domain_models import EndpointConfig, ProxySettings
from .value_objects import APIKey, ClientName, EndpointName, EndpointURL, ModelID


class ConfigRepository(ABC):
    """Abstract repository for configuration data."""

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[EndpointConfig]:
        """Find endpoint configuration by name."""

    @abstractmethod
    def find_all(self) -> List[EndpointConfig]:
        """Find all endpoint configurations."""

    @abstractmethod
    def get_common_config(self) -> Dict[str, str]:
        """Get common configuration settings."""


class JsonConfigRepository(ConfigRepository):
    """JSON file-based configuration repository."""

    def __init__(
        self,
        file_path: Path,
        env_resolver: Optional[Callable[[str, Dict], Optional[str]]] = None,
    ):
        """
        Initialize repository.

        Args:
            file_path: Path to JSON configuration file
            env_resolver: Optional function to resolve API keys from environment
        """
        self.file_path = file_path
        self.env_resolver = env_resolver
        self._cache: Optional[Dict[str, EndpointConfig]] = None
        self._common_cache: Optional[Dict[str, str]] = None
        self._last_load_time: float = 0
        self._cache_ttl: float = 60.0  # Cache for 60 seconds

    def find_by_name(self, name: str) -> Optional[EndpointConfig]:
        """Find endpoint configuration by name."""
        self._ensure_loaded()
        if self._cache is None:
            return None
        return self._cache.get(name)

    def find_all(self) -> List[EndpointConfig]:
        """Find all endpoint configurations."""
        self._ensure_loaded()
        if self._cache is None:
            return []
        return list(self._cache.values())

    def get_common_config(self) -> Dict[str, str]:
        """Get common configuration settings."""
        self._ensure_loaded()
        if self._common_cache is None:
            return {}
        return self._common_cache.copy()

    def reload(self):
        """Force reload from disk."""
        self._cache = None
        self._common_cache = None
        self._last_load_time = 0

    def _ensure_loaded(self):
        """Ensure data is loaded with caching."""
        current_time = time.time()
        if (
            self._cache is None
            or (current_time - self._last_load_time) > self._cache_ttl
        ):
            self._load()
            self._last_load_time = current_time

    def _load(self):
        """Load configuration from JSON file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load common config
        self._common_cache = {}
        common_data = data.get("common", {})
        for key, value in common_data.items():
            if isinstance(value, (bool, int, float)):
                self._common_cache[key] = str(value)
            else:
                self._common_cache[key] = str(value).strip()

        # Load endpoints
        self._cache = {}
        endpoints_data = data.get("endpoints", {})

        for name, endpoint_data in endpoints_data.items():
            try:
                config = self._parse_endpoint(name, endpoint_data)
                self._cache[name] = config
            except (ValueError, KeyError) as e:
                # Log error but continue loading other endpoints
                print(f"Warning: Failed to load endpoint '{name}': {e}")

    def _parse_endpoint(self, name: str, data: Dict) -> EndpointConfig:
        """Parse endpoint configuration from dictionary."""
        # Parse basic fields
        endpoint_name = EndpointName(name)
        url = EndpointURL(data["endpoint"])
        description = data.get("description", "")

        # Parse API key
        api_key = None
        api_key_value = self._resolve_api_key(name, data)
        if api_key_value:
            api_key = APIKey(api_key_value)

        # Parse supported clients
        supported_clients = []
        supported_str = data.get("supported_client", "")
        if supported_str:
            for client in supported_str.split(","):
                client = client.strip()
                if client:
                    try:
                        supported_clients.append(ClientName(client))
                    except ValueError:
                        pass  # Skip invalid client names

        # Parse proxy settings
        proxy_settings = None
        use_proxy = str(data.get("use_proxy", "false")).lower() == "true"
        if use_proxy and self._common_cache is not None:
            proxy_settings = ProxySettings(
                http_proxy=self._common_cache.get("http_proxy"),
                https_proxy=self._common_cache.get("https_proxy"),
                no_proxy=self._common_cache.get("no_proxy"),
            )

        # Parse other fields
        keep_proxy = str(data.get("keep_proxy_config", "false")).lower() == "true"
        list_models_cmd = data.get("list_models_cmd", "")
        list_of_models = data.get("list_of_models", None)
        if list_of_models is not None and not isinstance(list_of_models, list):
            list_of_models = None
        cache_ttl = 86400
        if self._common_cache is not None:
            cache_ttl = int(self._common_cache.get("cache_ttl_seconds", "86400"))

        return EndpointConfig(
            name=endpoint_name,
            url=url,
            description=description,
            supported_clients=supported_clients,
            api_key=api_key,
            proxy_settings=proxy_settings,
            use_proxy=use_proxy,
            keep_proxy_config=keep_proxy,
            list_models_cmd=list_models_cmd,
            list_of_models=list_of_models,
            cache_ttl_seconds=cache_ttl,
        )

    def _resolve_api_key(
        self, endpoint_name: str, endpoint_data: Dict
    ) -> Optional[str]:
        """Resolve API key from environment or configuration."""
        if self.env_resolver:
            return self.env_resolver(endpoint_name, endpoint_data)

        # Fallback to direct value from config
        return endpoint_data.get("api_key", "")


class CacheRepository(ABC):
    """Abstract repository for cache data."""

    @abstractmethod
    def get_models(self, endpoint_name: str) -> Optional[List[ModelID]]:
        """Get cached models for an endpoint."""

    @abstractmethod
    def save_models(self, endpoint_name: str, models: List[ModelID]) -> None:
        """Save models to cache."""

    @abstractmethod
    def clear(self, endpoint_name: Optional[str] = None) -> None:
        """Clear cache (all or specific endpoint)."""

    @abstractmethod
    def is_expired(self, endpoint_name: str) -> bool:
        """Check if cache for endpoint is expired."""


class FileCacheRepository(CacheRepository):
    """File-based cache repository."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400):
        """
        Initialize cache repository.

        Args:
            cache_dir: Directory for cache files
            ttl_seconds: Time-to-live for cache in seconds
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_models(self, endpoint_name: str) -> Optional[List[ModelID]]:
        """Get cached models for an endpoint."""
        cache_file = self._get_cache_file(endpoint_name)

        if not cache_file.exists():
            return None

        if self.is_expired(endpoint_name):
            return None

        return self._read_cache(cache_file)

    def save_models(self, endpoint_name: str, models: List[ModelID]) -> None:
        """Save models to cache."""
        cache_file = self._get_cache_file(endpoint_name)
        self._write_cache(cache_file, models)

    def clear(self, endpoint_name: Optional[str] = None) -> None:
        """Clear cache (all or specific endpoint)."""
        if endpoint_name:
            cache_file = self._get_cache_file(endpoint_name)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob(
                "code_assistant_manager_models_cache_*.txt"
            ):
                cache_file.unlink()

    def is_expired(self, endpoint_name: str) -> bool:
        """Check if cache for endpoint is expired."""
        cache_file = self._get_cache_file(endpoint_name)

        if not cache_file.exists():
            return True

        try:
            with open(cache_file, "r") as f:
                timestamp_line = f.readline().strip()

            if not timestamp_line.isdigit():
                return True

            cache_time = int(timestamp_line)
            current_time = int(time.time())

            return (current_time - cache_time) >= self.ttl_seconds
        except Exception:
            return True

    def _get_cache_file(self, endpoint_name: str) -> Path:
        """Get cache file path for endpoint."""
        return (
            self.cache_dir / f"code_assistant_manager_models_cache_{endpoint_name}.txt"
        )

    def _read_cache(self, cache_file: Path) -> List[ModelID]:
        """Read models from cache file."""
        models = []

        with open(cache_file, "r") as f:
            lines = f.readlines()

        # Skip first line (timestamp)
        for line in lines[1:]:
            line = line.strip()
            if line:
                try:
                    models.append(ModelID(line))
                except ValueError:
                    pass  # Skip invalid model IDs

        return models

    def _write_cache(self, cache_file: Path, models: List[ModelID]) -> None:
        """Write models to cache file."""
        # Write atomically using temp file
        temp_file = cache_file.with_suffix(".tmp")

        with open(temp_file, "w") as f:
            # Write timestamp on first line
            f.write(f"{int(time.time())}\n")

            # Write model IDs
            for model in models:
                f.write(f"{model}\n")

        # Atomic rename
        temp_file.replace(cache_file)

        # Set restrictive permissions
        cache_file.chmod(0o600)


class InMemoryCacheRepository(CacheRepository):
    """In-memory cache repository (for testing)."""

    def __init__(self, ttl_seconds: int = 86400):
        """Initialize in-memory cache."""
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # endpoint_name -> (timestamp, models)

    def get_models(self, endpoint_name: str) -> Optional[List[ModelID]]:
        """Get cached models for an endpoint."""
        if endpoint_name not in self._cache:
            return None

        if self.is_expired(endpoint_name):
            return None

        timestamp, models = self._cache[endpoint_name]
        return models

    def save_models(self, endpoint_name: str, models: List[ModelID]) -> None:
        """Save models to cache."""
        self._cache[endpoint_name] = (int(time.time()), models)

    def clear(self, endpoint_name: Optional[str] = None) -> None:
        """Clear cache."""
        if endpoint_name:
            self._cache.pop(endpoint_name, None)
        else:
            self._cache.clear()

    def is_expired(self, endpoint_name: str) -> bool:
        """Check if cache is expired."""
        if endpoint_name not in self._cache:
            return True

        timestamp, _ = self._cache[endpoint_name]
        current_time = int(time.time())
        return (current_time - timestamp) >= self.ttl_seconds
