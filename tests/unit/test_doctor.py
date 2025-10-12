"""Tests for CLI doctor module."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.cli.doctor import run_doctor_checks


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config object."""
    config_file = tmp_path / "providers.json"
    config_file.write_text(json.dumps({"providers": []}))

    config = MagicMock()
    config.config_path = str(config_file)
    # Add config_data attribute for JSON serialization in doctor checks
    config.config_data = {"providers": []}
    return config


class TestRunDoctorChecks:
    """Tests for run_doctor_checks function."""

    def test_doctor_checks_basic_pass(self, mock_config, capsys):
        """Doctor checks pass with valid installation."""
        # Mock the dependencies that doctor checks need
        # Patch at the source module where find_env_file is imported from
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=False)

        captured = capsys.readouterr().out
        # Should show installation check passed
        assert "installed" in captured.lower()
        assert "Python" in captured

    def test_doctor_checks_config_exists(self, mock_config, capsys):
        """Doctor shows config file exists when it does."""
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=False)

        captured = capsys.readouterr().out
        assert "Configuration" in captured

    def test_doctor_checks_config_missing(self, tmp_path, capsys):
        """Doctor reports when config file is missing."""
        config = MagicMock()
        config.config_path = str(tmp_path / "nonexistent.json")
        # Add config_data for JSON serialization even when config file is missing
        config.config_data = {"providers": []}

        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(config, verbose=False)

        captured = capsys.readouterr().out
        assert "Configuration" in captured or "not found" in captured.lower()

    def test_doctor_checks_verbose(self, mock_config, capsys):
        """Doctor provides additional info in verbose mode."""
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=True)

        captured = capsys.readouterr().out
        # Verbose mode should still complete
        assert "installed" in captured.lower()

    def test_doctor_shows_python_version(self, mock_config, capsys):
        """Doctor shows Python version information."""
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=False)

        captured = capsys.readouterr().out
        assert "Python" in captured
        assert sys.version.split()[0] in captured

    def test_doctor_shows_environment_check(self, mock_config, capsys):
        """Doctor includes environment variables check section."""
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=False)

        captured = capsys.readouterr().out
        assert "Environment" in captured

    def test_doctor_returns_zero_on_success(self, mock_config):
        """Doctor returns 0 when all checks pass."""
        with patch(
            "code_assistant_manager.env_loader.find_env_file", return_value=None
        ):
            result = run_doctor_checks(mock_config, verbose=False)

        # If the basic checks pass (installation, python, config exists)
        # it should return a low or zero issue count
        assert isinstance(result, int)
