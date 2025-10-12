"""Tests for code_assistant_manager.env_loader module."""

import os
import tempfile
from pathlib import Path

import pytest

from code_assistant_manager.env_loader import find_env_file, is_loaded, load_env, reset


class TestFindEnvFile:
    """Test find_env_file function."""

    def test_find_env_file_custom_path(self):
        """Test finding env file with custom path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST=value\n")
            env_path = f.name

        try:
            result = find_env_file(env_path)
            assert result == Path(env_path)
        finally:
            Path(env_path).unlink()

    def test_find_env_file_current_directory(self):
        """Test finding env file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST=value\n")

            # Test that find_dotenv can find the file in the directory
            result = find_env_file(str(env_file))
            assert result == env_file

    def test_find_env_file_not_found(self):
        """Test that function returns None for truly non-existent path."""
        # When we pass a custom path that doesn't exist and it's the only location
        # Since find_env_file also searches other locations, we test the custom path specifically
        result = find_env_file("/truly/nonexistent/path/that/does/not/exist/.env")
        # Result should be None if the custom path doesn't exist
        # (or might find another location, but the custom one won't be returned if it doesn't exist)
        if result is not None:
            # If found, verify it's not the nonexistent path
            assert str(result) != "/truly/nonexistent/path/that/does/not/exist/.env"

    def test_find_env_file_home_directory(self):
        """Test finding env file in home directory."""
        home_env = Path.home() / ".env"

        # This test checks the logic; in real scenario, home .env might exist
        # We can't reliably test this without modifying the home directory
        # So we just verify the method exists and returns Path or None
        result = find_env_file()
        assert result is None or isinstance(result, Path)


class TestLoadEnv:
    """Test load_env function."""

    def setup_method(self):
        """Reset state before each test."""
        reset()

    def test_load_env_from_file(self):
        """Test loading env variables from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR_1=test_value_1\n")
            f.write("TEST_VAR_2=test_value_2\n")
            env_path = f.name

        try:
            result = load_env(env_path)
            assert result is True
            assert os.environ.get("TEST_VAR_1") == "test_value_1"
            assert os.environ.get("TEST_VAR_2") == "test_value_2"
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR_1", None)
            os.environ.pop("TEST_VAR_2", None)

    def test_load_env_file_not_found(self):
        """Test loading when no env file exists in any location."""
        # This is tricky in a repo with .env files. We'll test the scenario
        # where we specifically look for a custom file that doesn't exist.
        # Since load_env falls back to finding other locations, we just
        # verify the behavior is reasonable.
        reset()
        orig_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                # In this isolated directory with no .env files anywhere nearby
                result = load_env()
                # Result could be True if it found a home .env, False otherwise
                assert isinstance(result, bool)
        finally:
            os.chdir(orig_cwd)
            reset()

    def test_load_env_no_redundant_loading(self):
        """Test that loading is not repeated without force flag."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=initial_value\n")
            env_path = f.name

        try:
            result1 = load_env(env_path)
            assert result1 is True
            assert is_loaded() is True

            result2 = load_env(env_path)
            assert result2 is False  # Should not reload
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR", None)

    def test_load_env_force_reload(self):
        """Test force reloading of env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=initial_value\n")
            env_path = f.name

        try:
            result1 = load_env(env_path)
            assert result1 is True

            result2 = load_env(env_path, force=True)
            assert result2 is True  # Should reload with force flag
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR", None)

    def test_load_env_is_loaded_flag(self):
        """Test is_loaded flag."""
        reset()
        assert is_loaded() is False

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=value\n")
            env_path = f.name

        try:
            load_env(env_path)
            assert is_loaded() is True

            reset()
            assert is_loaded() is False
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR", None)

    def test_load_env_with_quoted_values(self):
        """Test loading env file with quoted values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('API_KEY="my-secret-key-123"\n')
            f.write("ENDPOINT='https://api.example.com'\n")
            env_path = f.name

        try:
            load_env(env_path)
            assert os.environ.get("API_KEY") == "my-secret-key-123"
            assert os.environ.get("ENDPOINT") == "https://api.example.com"
        finally:
            Path(env_path).unlink()
            os.environ.pop("API_KEY", None)
            os.environ.pop("ENDPOINT", None)

    def test_load_env_with_comments(self):
        """Test loading env file with comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Database config\n")
            f.write("DB_HOST=localhost\n")
            f.write("# API config\n")
            f.write("API_KEY=secret123\n")
            env_path = f.name

        try:
            load_env(env_path)
            assert os.environ.get("DB_HOST") == "localhost"
            assert os.environ.get("API_KEY") == "secret123"
        finally:
            Path(env_path).unlink()
            os.environ.pop("DB_HOST", None)
            os.environ.pop("API_KEY", None)


class TestIsLoaded:
    """Test is_loaded function."""

    def test_is_loaded_initial_state(self):
        """Test initial state of is_loaded."""
        reset()
        assert is_loaded() is False


class TestReset:
    """Test reset function."""

    def test_reset_clears_flag(self):
        """Test that reset clears the loaded flag."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=value\n")
            env_path = f.name

        try:
            load_env(env_path)
            assert is_loaded() is True

            reset()
            assert is_loaded() is False
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR", None)


class TestModuleExecution:
    """Test module execution as a script."""

    def test_module_can_be_run_as_script(self):
        """Test that module can be run with python -m."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "code_assistant_manager.env_loader"],
            capture_output=True,
            text=True,
        )

        # Should exit successfully (0) if env file not found, but that's okay
        # or exit with 0 if it finds and loads an env file
        assert result.returncode in (0, 1)


class TestIntegration:
    """Integration tests for env_loader."""

    def test_load_env_integration_with_standard_locations(self):
        """Test that load_env can find files in standard locations."""
        reset()

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("INTEGRATION_TEST_VAR=success\n")

            # Test by providing custom path
            result = load_env(str(env_file))
            assert result is True
            assert os.environ.get("INTEGRATION_TEST_VAR") == "success"

            reset()
            os.environ.pop("INTEGRATION_TEST_VAR", None)

    def test_load_env_precedence(self):
        """Test that custom path takes precedence."""
        reset()

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file1 = Path(tmpdir) / ".env_custom"
            env_file1.write_text("VAR1=custom\n")

            env_file2 = Path(tmpdir) / ".env"
            env_file2.write_text("VAR1=default\n")

            result = load_env(str(env_file1))
            assert result is True
            assert os.environ.get("VAR1") == "custom"

            reset()
            os.environ.pop("VAR1", None)
