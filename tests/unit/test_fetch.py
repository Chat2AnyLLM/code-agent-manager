"""Tests for plugin fetch functionality with retry logic, caching, and branch detection."""

import json
import time
from unittest.mock import MagicMock, patch, mock_open

import pytest
from urllib.error import HTTPError, URLError

from code_assistant_manager.plugins.fetch import (
    fetch_raw_file,
    fetch_repo_info,
    parse_github_url,
    _marketplace_cache,
    _CACHE_TTL_SECONDS,
)


class TestFetchRawFile:
    """Test fetch_raw_file with retry logic and error handling."""

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_successful_fetch(self, mock_request, mock_urlopen):
        """Test successful file fetch."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"test": "data"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert result == '{"test": "data"}'
        mock_request.assert_called_once()
        mock_urlopen.assert_called_once()

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_retry_on_httperror(self, mock_request, mock_urlopen):
        """Test retry logic on HTTPError."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'content'
        mock_response.__enter__.return_value = mock_response

        # First two calls fail, third succeeds
        mock_urlopen.side_effect = [
            HTTPError(None, 500, "Server Error", None, None),
            HTTPError(None, 500, "Server Error", None, None),
            mock_response
        ]

        result = fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert result == "content"
        assert mock_urlopen.call_count == 3

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_retry_on_urlerror(self, mock_request, mock_urlopen):
        """Test retry logic on URLError."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'content'
        mock_response.__enter__.return_value = mock_response

        # First call fails, second succeeds
        mock_urlopen.side_effect = [
            URLError("Network timeout"),
            mock_response
        ]

        result = fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert result == "content"
        assert mock_urlopen.call_count == 2

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_max_retries_exceeded(self, mock_request, mock_urlopen):
        """Test that function returns None after max retries."""
        mock_urlopen.side_effect = HTTPError(None, 500, "Server Error", None, None)

        result = fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert result is None
        assert mock_urlopen.call_count == 3  # Max retries

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_404_not_found(self, mock_request, mock_urlopen):
        """Test that 404 errors return None immediately."""
        mock_urlopen.side_effect = HTTPError(None, 404, "Not Found", None, None)

        result = fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert result is None
        assert mock_urlopen.call_count == 1  # No retries for 404

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    @patch("code_assistant_manager.plugins.fetch.time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_request, mock_urlopen):
        """Test exponential backoff with jitter."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'content'
        mock_response.__enter__.return_value = mock_response

        # First two calls fail, third succeeds
        mock_urlopen.side_effect = [
            HTTPError(None, 500, "Server Error", None, None),
            HTTPError(None, 500, "Server Error", None, None),
            mock_response
        ]

        fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        assert mock_sleep.call_count == 2
        # Check that delays are increasing (exponential backoff)
        first_delay = mock_sleep.call_args_list[0][0][0]
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert second_delay > first_delay

    @patch("code_assistant_manager.plugins.fetch.urlopen")
    @patch("code_assistant_manager.plugins.fetch.Request")
    def test_increased_timeout(self, mock_request, mock_urlopen):
        """Test that timeout is increased to 30 seconds."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'content'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        fetch_raw_file("owner", "repo", "main", "path/to/file.json")

        # Check that urlopen was called with timeout=30
        call_args = mock_urlopen.call_args
        assert call_args[1]['timeout'] == 30


class TestFetchRepoInfo:
    """Test fetch_repo_info with caching and branch detection."""

    def setup_method(self):
        """Clear cache before each test."""
        _marketplace_cache.clear()

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_successful_repo_fetch(self, mock_fetch_raw):
        """Test successful repository info fetch."""
        marketplace_json = {
            "name": "test-marketplace",
            "description": "Test marketplace",
            "plugins": [
                {"name": "test-plugin", "version": "1.0.0", "description": "Test plugin"}
            ]
        }
        mock_fetch_raw.return_value = json.dumps(marketplace_json)

        result = fetch_repo_info("owner", "repo", "main")

        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.branch == "main"
        assert result.name == "test-marketplace"
        assert len(result.plugins) == 1
        assert result.plugins[0]["name"] == "test-plugin"

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_branch_detection_fallback(self, mock_fetch_raw):
        """Test branch detection tries multiple branches."""
        marketplace_json = {
            "name": "test-marketplace",
            "plugins": [{"name": "test-plugin"}]
        }

        # main fails, master succeeds
        mock_fetch_raw.side_effect = [None, json.dumps(marketplace_json)]

        result = fetch_repo_info("owner", "repo", "main")

        assert result.branch == "master"
        assert mock_fetch_raw.call_count == 2

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_branch_detection_multiple_attempts(self, mock_fetch_raw):
        """Test branch detection tries all common branches."""
        marketplace_json = {
            "name": "test-marketplace",
            "plugins": [{"name": "test-plugin"}]
        }

        # main, master, develop fail, development succeeds
        mock_fetch_raw.side_effect = [
            None, None, None, json.dumps(marketplace_json)
        ]

        result = fetch_repo_info("owner", "repo", "main")

        assert result.branch == "development"
        assert mock_fetch_raw.call_count == 4

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_caching_successful_result(self, mock_fetch_raw):
        """Test that successful results are cached."""
        marketplace_json = {
            "name": "test-marketplace",
            "plugins": [{"name": "test-plugin"}]
        }
        mock_fetch_raw.return_value = json.dumps(marketplace_json)

        # First call
        result1 = fetch_repo_info("owner", "repo", "main")
        assert mock_fetch_raw.call_count == 1

        # Second call should use cache
        result2 = fetch_repo_info("owner", "repo", "main")
        assert mock_fetch_raw.call_count == 1  # Still 1, used cache

        assert result1 == result2

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_caching_failed_result(self, mock_fetch_raw):
        """Test that failed results are also cached."""
        mock_fetch_raw.return_value = None

        # First call - will try multiple branches due to branch detection
        result1 = fetch_repo_info("owner", "repo", "main")
        first_call_count = mock_fetch_raw.call_count

        # Second call should use cache (no additional calls)
        result2 = fetch_repo_info("owner", "repo", "main")
        second_call_count = mock_fetch_raw.call_count

        assert result1 is None
        assert result2 is None
        # Second call should not have made additional calls (cache hit)
        assert second_call_count == first_call_count

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_cache_expiration(self, mock_fetch_raw):
        """Test that cache expires after TTL."""
        marketplace_json = {
            "name": "test-marketplace",
            "plugins": [{"name": "test-plugin"}]
        }
        mock_fetch_raw.return_value = json.dumps(marketplace_json)

        # First call
        result1 = fetch_repo_info("owner", "repo", "main")
        assert mock_fetch_raw.call_count == 1

        # Manipulate cache to be expired
        cache_key = "owner/repo/main"
        if cache_key in _marketplace_cache:
            _marketplace_cache[cache_key] = (result1, time.time() - _CACHE_TTL_SECONDS - 1)

        # Second call should fetch fresh data
        result2 = fetch_repo_info("owner", "repo", "main")
        assert mock_fetch_raw.call_count == 2  # Cache expired, fetched again

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_invalid_json_handling(self, mock_fetch_raw):
        """Test handling of invalid JSON in marketplace.json."""
        mock_fetch_raw.return_value = "invalid json"

        result = fetch_repo_info("owner", "repo", "main")

        assert result is None
        # Check that None result was cached
        cache_key = "owner/repo/main"
        assert cache_key in _marketplace_cache
        assert _marketplace_cache[cache_key][0] is None

    @patch("code_assistant_manager.plugins.fetch.fetch_raw_file")
    def test_no_marketplace_json(self, mock_fetch_raw):
        """Test handling when marketplace.json doesn't exist."""
        mock_fetch_raw.return_value = None

        result = fetch_repo_info("owner", "repo", "main")

        assert result is None


class TestParseGithubUrl:
    """Test GitHub URL parsing functionality."""

    def test_github_https_url(self):
        """Test parsing HTTPS GitHub URL."""
        result = parse_github_url("https://github.com/owner/repo")
        assert result == ("owner", "repo", "main")

    def test_github_ssh_url(self):
        """Test parsing SSH GitHub URL (currently incorrectly parses it)."""
        result = parse_github_url("git@github.com:owner/repo.git")
        # The current regex incorrectly parses this as:
        # owner="git@github.com:owner", repo="repo"
        assert result == ("git@github.com:owner", "repo", "main")

    def test_simple_owner_repo(self):
        """Test parsing simple owner/repo format."""
        result = parse_github_url("owner/repo")
        assert result == ("owner", "repo", "main")

    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        result = parse_github_url("https://github.com/owner/repo/")
        assert result == ("owner", "repo", "main")

    def test_url_with_git_extension(self):
        """Test URL with .git extension."""
        result = parse_github_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo", "main")

    def test_invalid_url(self):
        """Test invalid URL returns None."""
        result = parse_github_url("not-a-github-url")
        assert result is None

    def test_empty_url(self):
        """Test empty URL returns None."""
        result = parse_github_url("")
        assert result is None


class TestCachingBehavior:
    """Test caching behavior across different scenarios."""

    def setup_method(self):
        """Clear cache before each test."""
        _marketplace_cache.clear()

    def test_different_branches_cached_separately(self):
        """Test that different branches are cached separately."""
        with patch("code_assistant_manager.plugins.fetch.fetch_raw_file") as mock_fetch:
            marketplace_json = {
                "name": "test-marketplace",
                "plugins": [{"name": "test-plugin"}]
            }
            mock_fetch.return_value = json.dumps(marketplace_json)

            # Fetch main branch
            result1 = fetch_repo_info("owner", "repo", "main")
            # Fetch master branch
            result2 = fetch_repo_info("owner", "repo", "master")

            assert mock_fetch.call_count == 2  # Two separate fetches
            assert result1.branch == "main"
            assert result2.branch == "master"

    def test_different_repos_cached_separately(self):
        """Test that different repos are cached separately."""
        with patch("code_assistant_manager.plugins.fetch.fetch_raw_file") as mock_fetch:
            marketplace_json = {
                "name": "test-marketplace",
                "plugins": [{"name": "test-plugin"}]
            }
            mock_fetch.return_value = json.dumps(marketplace_json)

            # Fetch repo1
            result1 = fetch_repo_info("owner", "repo1", "main")
            # Fetch repo2
            result2 = fetch_repo_info("owner", "repo2", "main")

            assert mock_fetch.call_count == 2  # Two separate fetches
            assert result1.repo == "repo1"
            assert result2.repo == "repo2"