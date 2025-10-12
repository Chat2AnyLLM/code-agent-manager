"""Tests for CLI app module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.app import app, config_app, list_config, validate_config


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestValidateConfig:
    """Tests for config validation command."""

    def test_validate_config_success(self, runner, tmp_path):
        """validate_config passes with valid configuration."""
        config_file = tmp_path / "providers.json"
        config_file.write_text(json.dumps({"providers": []}))

        mock_cm = MagicMock()
        mock_cm.validate_config.return_value = (True, [])

        with patch("code_assistant_manager.config.ConfigManager", return_value=mock_cm):
            result = runner.invoke(
                config_app, ["validate", "--config", str(config_file)]
            )

        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_validate_config_failure(self, runner, tmp_path):
        """validate_config reports errors with invalid configuration."""
        config_file = tmp_path / "providers.json"
        config_file.write_text(json.dumps({"providers": []}))

        mock_cm = MagicMock()
        mock_cm.validate_config.return_value = (False, ["Missing required field"])

        with patch("code_assistant_manager.config.ConfigManager", return_value=mock_cm):
            result = runner.invoke(
                config_app, ["validate", "--config", str(config_file)]
            )

        assert "failed" in result.output.lower()
        assert "Missing required field" in result.output

    def test_validate_config_file_not_found(self, runner, tmp_path):
        """validate_config handles missing file gracefully."""
        config_file = tmp_path / "nonexistent.json"

        with patch(
            "code_assistant_manager.config.ConfigManager",
            side_effect=FileNotFoundError("Config not found"),
        ):
            result = runner.invoke(
                config_app, ["validate", "--config", str(config_file)]
            )

        assert "not found" in result.output.lower()


class TestListConfig:
    """Tests for config list command."""

    def test_list_config_shows_locations(self, runner):
        """list_config shows configuration file locations."""
        result = runner.invoke(config_app, ["list"])

        assert result.exit_code == 0
        assert "Configuration Files" in result.output
        # Should mention some standard locations
        assert "providers.json" in result.output

    def test_list_config_shows_editor_configs(self, runner):
        """list_config shows editor configuration locations."""
        result = runner.invoke(config_app, ["list"])

        assert result.exit_code == 0
        # Should show editor configurations section
        assert "Editor" in result.output or "claude" in result.output.lower()


class TestMainApp:
    """Tests for main app commands."""

    def test_app_help(self, runner):
        """app shows help message."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Code Assistant Manager" in result.output

    def test_app_subcommands_available(self, runner):
        """app has expected subcommands."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Check for main subcommands
        assert "mcp" in result.output
        assert "prompt" in result.output
        assert "skill" in result.output
        assert "plugin" in result.output


class TestGlobalOptions:
    """Tests for global CLI options."""

    def test_debug_option(self, runner):
        """--debug option enables debug logging."""
        with patch("code_assistant_manager.cli.app.logging") as mock_logging:
            result = runner.invoke(app, ["--debug", "--help"])

        # The debug option should be recognized
        assert result.exit_code == 0
