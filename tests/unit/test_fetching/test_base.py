"""Unit tests for code_assistant_manager.fetching.base module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from code_assistant_manager.fetching.base import BaseEntityFetcher, EntityParser, RepoConfig


class MockEntity:
    """Mock entity for testing."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description


class MockParser(EntityParser[MockEntity]):
    """Mock parser for testing."""

    def parse_from_file(self, file_path: Path, repo_config: RepoConfig) -> MockEntity:
        """Parse mock entity from file."""
        return MockEntity(file_path.name, "Mock description")

    def get_file_pattern(self) -> str:
        """Return file pattern."""
        return "*.mock"

    def create_entity_key(self, repo_config: RepoConfig, entity_name: str) -> str:
        """Create entity key."""
        return f"{repo_config.owner}/{repo_config.name}:{entity_name}"


class TestRepoConfig(unittest.TestCase):
    """Test RepoConfig dataclass."""

    def test_repo_config_creation(self):
        """Test RepoConfig can be created with required fields."""
        config = RepoConfig(owner="test-owner", name="test-repo")
        self.assertEqual(config.owner, "test-owner")
        self.assertEqual(config.name, "test-repo")
        self.assertEqual(config.branch, "main")  # default
        self.assertIsNone(config.path)  # default
        self.assertTrue(config.enabled)  # default

    def test_repo_config_with_all_fields(self):
        """Test RepoConfig with all fields specified."""
        config = RepoConfig(
            owner="test-owner",
            name="test-repo",
            branch="develop",
            path="sub/path",
            enabled=False
        )
        self.assertEqual(config.owner, "test-owner")
        self.assertEqual(config.name, "test-repo")
        self.assertEqual(config.branch, "develop")
        self.assertEqual(config.path, "sub/path")
        self.assertFalse(config.enabled)


class TestBaseEntityFetcher(unittest.TestCase):
    """Test BaseEntityFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = MockParser()
        self.fetcher = BaseEntityFetcher(parser=self.parser)

    def test_init(self):
        """Test BaseEntityFetcher initialization."""
        self.assertEqual(self.fetcher.parser, self.parser)
        self.assertEqual(self.fetcher.cache_ttl, 3600)  # default
        self.assertIsInstance(self.fetcher._cache, dict)

    def test_init_with_custom_ttl(self):
        """Test BaseEntityFetcher with custom cache TTL."""
        fetcher = BaseEntityFetcher(parser=self.parser, cache_ttl=1800)
        self.assertEqual(fetcher.cache_ttl, 1800)

    @patch('code_assistant_manager.fetching.parallel.ParallelFetcher')
    def test_fetch_from_repos_empty(self, mock_parallel_fetcher):
        """Test fetch_from_repos with empty repo list."""
        mock_parallel_fetcher.return_value.fetch_all.return_value = []

        result = self.fetcher.fetch_from_repos([])

        self.assertEqual(result, [])
        mock_parallel_fetcher.assert_not_called()

    @patch('code_assistant_manager.fetching.parallel.ParallelFetcher')
    def test_fetch_from_repos_disabled(self, mock_parallel_fetcher):
        """Test fetch_from_repos with disabled repos."""
        mock_parallel_fetcher.return_value.fetch_all.return_value = []

        repos = [
            RepoConfig(owner="test-owner", name="test-repo", enabled=False)
        ]

        result = self.fetcher.fetch_from_repos(repos)

        self.assertEqual(result, [])
        mock_parallel_fetcher.assert_not_called()

    @patch('code_assistant_manager.fetching.parallel.ParallelFetcher')
    def test_fetch_from_repos_success(self, mock_parallel_fetcher):
        """Test successful fetch_from_repos."""
        mock_entities = [MockEntity("entity1"), MockEntity("entity2")]
        mock_parallel_fetcher.return_value.fetch_all.return_value = [mock_entities]

        repos = [
            RepoConfig(owner="test-owner", name="test-repo", enabled=True)
        ]

        result = self.fetcher.fetch_from_repos(repos)

        self.assertEqual(result, mock_entities)
        mock_parallel_fetcher.assert_called_once()
        call_args = mock_parallel_fetcher.call_args
        self.assertEqual(call_args[1]['fetcher_func'], self.fetcher._fetch_from_single_repo)
        self.assertEqual(call_args[1]['max_workers'], 8)  # default

    @patch('code_assistant_manager.fetching.parallel.ParallelFetcher')
    def test_fetch_from_repos_custom_workers(self, mock_parallel_fetcher):
        """Test fetch_from_repos with custom max_workers."""
        mock_parallel_fetcher.return_value.fetch_all.return_value = []

        repos = [
            RepoConfig(owner="test-owner", name="test-repo", enabled=True)
        ]

        result = self.fetcher.fetch_from_repos(repos, max_workers=4)

        mock_parallel_fetcher.assert_called_once()
        call_args = mock_parallel_fetcher.call_args
        self.assertEqual(call_args[1]['max_workers'], 4)

    def test_fetch_from_single_repo_clone_unpacking(self):
        """Test that _fetch_from_single_repo correctly unpacks clone() tuple."""
        # This test verifies the fix for the tuple unpacking bug
        # where clone() returns (temp_dir, actual_branch) but was unpacked as just temp_dir

        from code_assistant_manager.fetching.repository import GitRepository

        with patch.object(GitRepository, 'clone') as mock_clone:
            # Mock the context manager to return proper tuple
            mock_temp_dir = Mock(spec=Path)
            mock_temp_dir.exists.return_value = True
            mock_temp_dir.rglob.return_value = []  # No files found

            mock_clone.return_value.__enter__.return_value = (mock_temp_dir, "main")
            mock_clone.return_value.__exit__.return_value = None

            repo = RepoConfig(owner="test-owner", name="test-repo")

            # This should not raise an exception about tuple unpacking
            result = self.fetcher._fetch_from_single_repo(repo)

            self.assertEqual(result, [])
            mock_clone.assert_called_once()


class TestEntityParser(unittest.TestCase):

    def test_abstract_methods(self):
        """Test that EntityParser defines required abstract methods."""
        # EntityParser is abstract, so we can't instantiate it directly
        # But we can check that our MockParser implements all required methods
        parser = MockParser()

        # Test that all abstract methods are implemented
        self.assertTrue(hasattr(parser, 'parse_from_file'))
        self.assertTrue(hasattr(parser, 'get_file_pattern'))
        self.assertTrue(hasattr(parser, 'create_entity_key'))

        # Test that methods can be called
        config = RepoConfig(owner="test", name="repo")
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.mock"
            test_file.write_text("test content")

            entity = parser.parse_from_file(test_file, config)
            self.assertIsInstance(entity, MockEntity)
            self.assertEqual(entity.name, "test.mock")

        pattern = parser.get_file_pattern()
        self.assertEqual(pattern, "*.mock")

        key = parser.create_entity_key(config, "test-entity")
        self.assertEqual(key, "test/repo:test-entity")


if __name__ == '__main__':
    unittest.main()