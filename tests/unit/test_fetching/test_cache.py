"""Unit tests for code_assistant_manager.fetching.cache module."""

import unittest
import time
from unittest.mock import Mock, patch

from code_assistant_manager.fetching.cache import FetchCache


class TestFetchCache(unittest.TestCase):
    """Test FetchCache class."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = FetchCache()

    def test_init_default_ttl(self):
        """Test FetchCache initialization with default TTL."""
        self.assertEqual(self.cache.default_ttl, 3600)
        self.assertIsInstance(self.cache._cache, dict)
        self.assertEqual(len(self.cache._cache), 0)

    def test_init_custom_ttl(self):
        """Test FetchCache initialization with custom TTL."""
        cache = FetchCache(default_ttl=1800)
        self.assertEqual(cache.default_ttl, 1800)

    def test_get_nonexistent_key(self):
        """Test get returns None for nonexistent key."""
        result = self.cache.get("nonexistent")
        self.assertIsNone(result)

    def test_set_and_get(self):
        """Test setting and getting a cache entry."""
        test_value = {"data": "test"}

        self.cache.set("test_key", test_value)
        result = self.cache.get("test_key")

        self.assertEqual(result, test_value)

    def test_set_with_custom_ttl(self):
        """Test setting cache entry with custom TTL."""
        test_value = "custom_ttl_value"

        self.cache.set("custom_key", test_value, ttl=120)
        result = self.cache.get("custom_key")

        self.assertEqual(result, test_value)

        # Verify the TTL was stored correctly
        entry = self.cache._cache["custom_key"]
        self.assertEqual(entry["ttl"], 120)

    def test_get_expired_entry(self):
        """Test get returns None for expired entries."""
        test_value = "expired_value"

        # Set an entry with very short TTL
        self.cache.set("expired_key", test_value, ttl=0.001)

        # Wait for expiration
        time.sleep(0.01)

        result = self.cache.get("expired_key")
        self.assertIsNone(result)

        # Entry should be removed from cache
        self.assertNotIn("expired_key", self.cache._cache)

    def test_get_non_expired_entry(self):
        """Test get returns value for non-expired entries."""
        test_value = "valid_value"

        self.cache.set("valid_key", test_value, ttl=1)
        result = self.cache.get("valid_key")

        self.assertEqual(result, test_value)

    def test_cleanup_expired(self):
        """Test cleanup_expired removes expired entries."""
        # Set multiple entries with different TTLs
        self.cache.set("valid_key", "valid", ttl=1)
        self.cache.set("expired_key1", "expired1", ttl=0.001)
        self.cache.set("expired_key2", "expired2", ttl=0.001)

        # Wait for expiration
        time.sleep(0.01)

        removed_count = self.cache.cleanup_expired()

        self.assertEqual(removed_count, 2)
        self.assertIn("valid_key", self.cache._cache)
        self.assertNotIn("expired_key1", self.cache._cache)
        self.assertNotIn("expired_key2", self.cache._cache)

    def test_clear(self):
        """Test clear removes all entries."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")

        self.assertEqual(len(self.cache._cache), 3)

        self.cache.clear()

        self.assertEqual(len(self.cache._cache), 0)

    def test_multiple_entries(self):
        """Test handling multiple cache entries."""
        entries = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }

        # Set all entries
        for key, value in entries.items():
            self.cache.set(key, value)

        # Verify all can be retrieved
        for key, expected_value in entries.items():
            result = self.cache.get(key)
            self.assertEqual(result, expected_value)

        # Verify cache has all entries
        self.assertEqual(len(self.cache._cache), 3)

    def test_overwrite_existing_key(self):
        """Test overwriting existing cache key."""
        self.cache.set("test_key", "original_value")
        result = self.cache.get("test_key")
        self.assertEqual(result, "original_value")

        # Overwrite with new value
        self.cache.set("test_key", "new_value")
        result = self.cache.get("test_key")
        self.assertEqual(result, "new_value")

    def test_different_ttl_values(self):
        """Test entries with different TTL values."""
        self.cache.set("short_ttl", "short", ttl=0.1)
        self.cache.set("long_ttl", "long", ttl=10)

        # Both should be valid initially
        self.assertEqual(self.cache.get("short_ttl"), "short")
        self.assertEqual(self.cache.get("long_ttl"), "long")

        # Wait for short TTL to expire
        time.sleep(0.2)

        # Short TTL should be gone, long TTL should remain
        self.assertIsNone(self.cache.get("short_ttl"))
        self.assertEqual(self.cache.get("long_ttl"), "long")


if __name__ == '__main__':
    unittest.main()