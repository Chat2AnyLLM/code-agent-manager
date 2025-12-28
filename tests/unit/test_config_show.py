"""Tests for the config show command functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.app import config_app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.mark.skip(reason="Feature not implemented - integration tests for non-existent functionality")
class TestConfigShowCommand:
    """Tests for the config show command."""

    def test_config_show_help(self, runner):
        """config show command shows help."""
        result = runner.invoke(config_app, ["show", "--help"])
        assert result.exit_code == 0
        assert "Show configuration" in result.output
        assert "dotted notation format" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_claude_all(self, mock_load_config, runner):
        """config show displays all claude config."""
        mock_config = {
            "autoUpdates": False,
            "tipsHistory": {"config-thinking-mode": True}
        }
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "-a", "claude"])

        assert result.exit_code == 0
        assert "CLAUDE Configuration:" in result.output
        assert "File: /path/to/claude.json" in result.output
        assert "claude.autoUpdates = False" in result.output
        assert "claude.tipsHistory.config-thinking-mode = True" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_codex_all(self, mock_load_config, runner):
        """config show displays all codex config."""
        mock_config = {
            "profiles": {
                "default": {"model": "gpt-4", "temperature": 0.7}
            }
        }
        mock_load_config.return_value = (mock_config, "/path/to/codex.toml")

        result = runner.invoke(config_app, ["show", "-a", "codex"])

        assert result.exit_code == 0
        assert "CODEX Configuration:" in result.output
        assert "codex.profiles.default.model = gpt-4" in result.output
        assert "codex.profiles.default.temperature = 0.7" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_specific_key(self, mock_load_config, runner):
        """config show displays specific key value."""
        mock_config = {
            "autoUpdates": False,
            "tipsHistory": {"config-thinking-mode": True}
        }
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "claude.autoUpdates"])

        assert result.exit_code == 0
        assert "claude.autoUpdates = False" in result.output
        # Should not show other keys
        assert "tipsHistory" not in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_nested_key(self, mock_load_config, runner):
        """config show displays nested key value."""
        mock_config = {
            "tipsHistory": {"config-thinking-mode": True}
        }
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "claude.tipsHistory.config-thinking-mode"])

        assert result.exit_code == 0
        assert "claude.tipsHistory.config-thinking-mode = True" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_key_not_found(self, mock_load_config, runner):
        """config show handles key not found."""
        mock_config = {"autoUpdates": False}
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "claude.nonexistent.key"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
        assert "Available keys" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_no_config_found(self, mock_load_config, runner):
        """config show handles no config found."""
        mock_load_config.return_value = ({}, "No config file found")

        result = runner.invoke(config_app, ["show", "-a", "claude"])

        assert result.exit_code == 0
        assert "No configuration found for claude" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_list_values(self, mock_load_config, runner):
        """config show handles list values."""
        mock_config = {"allowedTools": ["bash", "grep", "read"]}
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "-a", "claude"])

        assert result.exit_code == 0
        assert "['bash', 'grep', 'read']" in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_default_app_claude(self, mock_load_config, runner):
        """config show defaults to claude app."""
        mock_config = {"autoUpdates": False}
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show"])

        assert result.exit_code == 0
        assert "CLAUDE Configuration:" in result.output
        mock_load_config.assert_called_with("claude")

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_prefix_matching(self, mock_load_config, runner):
        """config show displays all keys matching a prefix."""
        mock_config = {
            "profiles": {
                "default": {"model": "gpt-4", "temperature": 0.7},
                "fast": {"model": "gpt-3.5-turbo", "temperature": 0.5}
            },
            "other": {"setting": "value"}
        }
        mock_load_config.return_value = (mock_config, "/path/to/codex.toml")

        result = runner.invoke(config_app, ["show", "codex.profiles", "-a", "codex"])

        assert result.exit_code == 0
        assert "CODEX Configuration - Keys matching 'codex.profiles':" in result.output
        assert "codex.profiles.default.model = gpt-4" in result.output
        assert "codex.profiles.default.temperature = 0.7" in result.output
        assert "codex.profiles.fast.model = gpt-3.5-turbo" in result.output
        assert "codex.profiles.fast.temperature = 0.5" in result.output
        # Should not show keys outside the prefix
        assert "codex.other.setting" not in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_wildcard_matching(self, mock_load_config, runner):
        """config show displays all keys matching a wildcard pattern."""
        mock_config = {
            "tipsHistory": {
                "config-thinking-mode": {"lastToolDuration": 123, "enabled": True},
                "config-other-mode": {"lastToolDuration": 456, "enabled": False}
            },
            "other": {"setting": "value"}
        }
        mock_load_config.return_value = (mock_config, "/path/to/claude.json")

        result = runner.invoke(config_app, ["show", "claude.*.*.lastToolDuration"])

        assert result.exit_code == 0
        assert "CLAUDE Configuration - Keys matching pattern 'claude.*.*.lastToolDuration':" in result.output
        assert "claude.tipsHistory.config-thinking-mode.lastToolDuration = 123" in result.output
        assert "claude.tipsHistory.config-other-mode.lastToolDuration = 456" in result.output
        # Should not show keys outside the pattern
        assert "claude.other.setting" not in result.output
        assert "enabled" not in result.output

    @patch("code_assistant_manager.cli.app.load_app_config")
    def test_config_show_unknown_app(self, mock_load_config, runner):
        """config show handles unknown app."""
        from typer import Exit
        mock_load_config.side_effect = Exit("Unknown app: nonexistent")

        result = runner.invoke(config_app, ["show", "-a", "nonexistent"])

        assert result.exit_code == 1
        assert "Unknown app: nonexistent" in result.output