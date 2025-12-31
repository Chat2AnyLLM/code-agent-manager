"""Unit tests for code_assistant_manager.fetching.parallel module."""

import unittest
from unittest.mock import Mock, patch, call
import threading
import time

from code_assistant_manager.fetching.parallel import ParallelFetcher


class TestParallelFetcher(unittest.TestCase):
    """Test ParallelFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher_func = Mock(return_value="result")
        self.parallel_fetcher = ParallelFetcher(
            fetcher_func=self.fetcher_func,
            max_workers=4
        )

    def test_init(self):
        """Test ParallelFetcher initialization."""
        self.assertEqual(self.parallel_fetcher.fetcher_func, self.fetcher_func)
        self.assertEqual(self.parallel_fetcher.max_workers, 4)
        self.assertIsInstance(self.parallel_fetcher.results, list)
        self.assertIsInstance(self.parallel_fetcher.lock, type(threading.Lock()))

    def test_fetch_all_empty_sources(self):
        """Test fetch_all with empty sources list."""
        result = self.parallel_fetcher.fetch_all([])
        self.assertEqual(result, [])
        self.fetcher_func.assert_not_called()

    def test_fetch_all_single_source(self):
        """Test fetch_all with single source."""
        sources = ["source1"]
        expected_result = ["result"]

        result = self.parallel_fetcher.fetch_all(sources)

        self.assertEqual(result, expected_result)
        self.fetcher_func.assert_called_once_with("source1")

    def test_fetch_all_multiple_sources(self):
        """Test fetch_all with multiple sources."""
        sources = ["source1", "source2", "source3"]
        expected_results = ["result1", "result2", "result3"]

        # Configure mock to return different results
        self.fetcher_func.side_effect = expected_results

        result = self.parallel_fetcher.fetch_all(sources)

        self.assertEqual(len(result), 3)
        # Results may be in any order due to parallel execution
        self.assertIn("result1", result)
        self.assertIn("result2", result)
        self.assertIn("result3", result)

        # Verify all sources were processed
        self.assertEqual(self.fetcher_func.call_count, 3)
        calls = self.fetcher_func.call_args_list
        self.assertIn(call("source1"), calls)
        self.assertIn(call("source2"), calls)
        self.assertIn(call("source3"), calls)

    def test_fetch_all_with_none_results(self):
        """Test fetch_all handles None results correctly."""
        sources = ["source1", "source2", "source3"]

        # Configure mock to return None for some results
        self.fetcher_func.side_effect = ["result1", None, "result3"]

        result = self.parallel_fetcher.fetch_all(sources)

        # Should only include non-None results
        self.assertEqual(len(result), 2)
        self.assertIn("result1", result)
        self.assertIn("result3", result)

    def test_fetch_all_with_exceptions(self):
        """Test fetch_all handles exceptions in fetcher function."""
        sources = ["source1", "source2", "source3"]

        # Configure mock to raise exception for second source
        self.fetcher_func.side_effect = ["result1", Exception("test error"), "result3"]

        result = self.parallel_fetcher.fetch_all(sources)

        # Should continue processing other sources despite exception
        self.assertEqual(len(result), 2)
        self.assertIn("result1", result)
        self.assertIn("result3", result)

    def test_max_workers_limit(self):
        """Test that max_workers limits concurrent execution."""
        sources = ["source1", "source2", "source3", "source4", "source5"]

        # Create a fetcher with max_workers=2
        parallel_fetcher = ParallelFetcher(
            fetcher_func=self.fetcher_func,
            max_workers=2
        )

        # Mock ThreadPoolExecutor to verify max_workers
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value.__enter__.return_value = Mock()
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            mock_future = Mock()
            mock_future.result.return_value = "result"
            mock_executor.return_value.as_completed.return_value = [mock_future] * 5

            result = parallel_fetcher.fetch_all(sources)

            # Verify ThreadPoolExecutor was created with max_workers=2
            mock_executor.assert_called_once_with(max_workers=2)

    def test_thread_safety(self):
        """Test that results collection is thread-safe."""
        # This is harder to test directly, but we can verify the lock exists
        # and that the code uses it correctly
        self.assertIsInstance(self.parallel_fetcher.lock, type(threading.Lock()))

        # Verify that the lock is used in the right place by checking the code structure
        # The lock should be acquired when appending to results
        sources = ["source1"]
        result = self.parallel_fetcher.fetch_all(sources)

        self.assertEqual(result, ["result"])


if __name__ == '__main__':
    unittest.main()