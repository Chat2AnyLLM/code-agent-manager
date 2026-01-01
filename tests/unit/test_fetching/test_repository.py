"""Unit tests for code_assistant_manager.fetching.repository module."""

import unittest
from unittest.mock import Mock, patch, call
from pathlib import Path
import tempfile
import shutil
import subprocess

from code_assistant_manager.fetching.repository import GitRepository


class TestGitRepository(unittest.TestCase):
    """Test GitRepository class."""

    def setUp(self):
        """Set up test fixtures."""
        self.owner = "test-owner"
        self.name = "test-repo"
        self.branch = "main"
        self.repo = GitRepository(self.owner, self.name, self.branch)

    def test_init(self):
        """Test GitRepository initialization."""
        self.assertEqual(self.repo.owner, self.owner)
        self.assertEqual(self.repo.name, self.name)
        self.assertEqual(self.repo.branch, self.branch)
        expected_url = f"https://github.com/{self.owner}/{self.name}.git"
        self.assertEqual(self.repo.url, expected_url)

    def test_init_default_branch(self):
        """Test GitRepository with default branch."""
        repo = GitRepository(self.owner, self.name)
        self.assertEqual(repo.branch, "main")

    def test_init_different_branch(self):
        """Test GitRepository with different branch."""
        repo = GitRepository(self.owner, self.name, "develop")
        self.assertEqual(repo.branch, "develop")

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_success_main_branch(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test successful clone with main branch."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = Mock(returncode=0)

        with self.repo.clone() as (actual_temp_dir, actual_branch):
            self.assertEqual(actual_temp_dir, Path(temp_dir))
            self.assertEqual(actual_branch, self.branch)

        # Verify git clone was called correctly
        mock_run.assert_called_once_with(
            ["git", "clone", "--depth", "1", "--branch", self.branch, self.repo.url, str(Path(temp_dir))],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Verify cleanup was called
        mock_rmtree.assert_called_once_with(Path(temp_dir), ignore_errors=True)

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_success_fallback_branch(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test successful clone with branch fallback."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir

        # Simulate main branch failing, master succeeding
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, 'git', "branch not found"),
            Mock(returncode=0)  # master succeeds
        ]

        with self.repo.clone() as (actual_temp_dir, actual_branch):
            self.assertEqual(actual_temp_dir, Path(temp_dir))
            self.assertEqual(actual_branch, "master")  # Should be master

        # Verify both branches were tried
        self.assertEqual(mock_run.call_count, 2)
        calls = mock_run.call_args_list
        # Check that main was tried first
        main_call = calls[0][0][0]  # Get the command list
        self.assertIn("--branch", main_call)
        self.assertIn("main", main_call)
        # Check that master was tried second
        master_call = calls[1][0][0]  # Get the command list
        self.assertIn("--branch", master_call)
        self.assertIn("master", master_call)

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_all_branches_fail(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test clone when all branch attempts fail."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir

        # All branches fail
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', "branch not found")

        with self.assertRaises(RuntimeError) as cm:
            with self.repo.clone():
                pass

        self.assertIn("Failed to clone repository from any branch", str(cm.exception))

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_timeout(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test clone with timeout."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir

        # Simulate timeout
        mock_run.side_effect = subprocess.TimeoutExpired('git', 60)

        with self.assertRaises(subprocess.TimeoutExpired):
            with self.repo.clone():
                pass

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_cleanup_on_exception(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test that cleanup happens even when exception occurs."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir
        mock_run.side_effect = Exception("Test exception")

        with self.assertRaises(Exception):
            with self.repo.clone():
                pass

        # Verify cleanup was still called
        mock_rmtree.assert_called_once_with(Path(temp_dir), ignore_errors=True)

    def test_clone_returns_correct_tuple(self):
        """Test that clone method returns the correct tuple structure."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.mkdtemp', return_value='/tmp/test'), \
             patch('shutil.rmtree') as mock_rmtree:

            mock_run.return_value = Mock(returncode=0)

            # Test that clone returns (Path, str) tuple
            with self.repo.clone() as result:
                self.assertIsInstance(result, tuple)
                self.assertEqual(len(result), 2)
                temp_dir, actual_branch = result
                self.assertIsInstance(temp_dir, Path)
                self.assertIsInstance(actual_branch, str)
                self.assertEqual(actual_branch, self.branch)

            mock_rmtree.assert_called_once()

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_clone_with_context_manager(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test that clone works as a proper context manager."""
        temp_dir = "/tmp/test_clone"
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = Mock(returncode=0)

        # Test normal usage
        with self.repo.clone() as (temp_path, branch):
            self.assertIsInstance(temp_path, Path)
            self.assertEqual(branch, self.branch)

        # Verify cleanup
        mock_rmtree.assert_called_once_with(Path(temp_dir), ignore_errors=True)


if __name__ == '__main__':
    unittest.main()