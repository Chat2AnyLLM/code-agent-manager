"""Unified caching layer for repository fetching."""

import time
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FetchCache:
    """Unified caching layer for fetch operations."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry['timestamp'] > entry['ttl']:
            # Expired
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for {key}")
        return entry['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        self._cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl
        }
        logger.debug(f"Cached {key} for {ttl}s")

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = []
        current_time = time.time()

        for key, entry in self._cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)