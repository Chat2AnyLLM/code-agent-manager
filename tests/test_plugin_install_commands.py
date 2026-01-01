"""Unit tests for plugin install commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from code_assistant_manager.cli.plugins.plugin_install_commands import (
    plugin_app, _resolve_plugin_conflict, _get_handler
)


class TestPluginInstallCommands:
    """Test plugin installation commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict")
    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_install_plugin_success(self, mock_get_handler, mock_resolve, runner):
        """Test successful plugin installation."""
        mock_resolve.return_value = "resolved-marketplace"
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed successfully")
        mock_get_handler.return_value = mock_handler

        result = runner.invoke(plugin_app, ["install", "test-plugin"])
        assert result.exit_code == 0
        assert "installed successfully" in result.output

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_install_plugin_with_marketplace(self, mock_get_handler, runner):
        """Test plugin installation with marketplace specification."""
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed")
        mock_get_handler.return_value = mock_handler

        result = runner.invoke(plugin_app, ["install", "test-marketplace:test-plugin"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_install_plugin_failure(self, mock_get_handler, runner):
        """Test plugin installation failure."""
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (False, "Installation failed")
        mock_get_handler.return_value = mock_handler

        result = runner.invoke(plugin_app, ["install", "test-marketplace:failing-plugin"])
        assert result.exit_code != 0
        assert "failed" in result.output.lower()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict")
    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_install_plugin_conflict_resolution(self, mock_get_handler, mock_resolve, runner):
        """Test plugin installation with conflict resolution."""
        mock_resolve.return_value = "resolved-marketplace"

        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed")
        mock_get_handler.return_value = mock_handler

        result = runner.invoke(plugin_app, ["install", "conflicting-plugin"])
        assert result.exit_code == 0
        mock_resolve.assert_called_once()


class TestPluginConflictResolution:
    """Test plugin conflict resolution logic."""

    @patch("code_assistant_manager.plugins.PluginManager")
    def test_resolve_plugin_conflict_single_marketplace(self, mock_pm_class):
        """Test conflict resolution when plugin exists in one marketplace."""
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm

        # Mock single marketplace with plugin
        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.name = "test-marketplace"
        mock_pm.get_all_repos.return_value = {"test-marketplace": mock_repo}

        with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
            mock_info = MagicMock()
            mock_info.plugins = [{"name": "test-plugin", "version": "1.0.0"}]
            mock_fetch.return_value = mock_info

            with patch("builtins.input", return_value="1"):
                result = _resolve_plugin_conflict("test-plugin", "claude")
                assert result == "test-marketplace"

    @patch("code_assistant_manager.plugins.PluginManager")
    def test_resolve_plugin_conflict_multiple_marketplaces(self, mock_pm_class):
        """Test conflict resolution when plugin exists in multiple marketplaces."""
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm

        # Mock multiple marketplaces
        mock_repo1 = MagicMock()
        mock_repo1.type = "marketplace"
        mock_repo1.name = "marketplace1"
        mock_repo2 = MagicMock()
        mock_repo2.type = "marketplace"
        mock_repo2.name = "marketplace2"

        mock_pm.get_all_repos.return_value = {
            "marketplace1": mock_repo1,
            "marketplace2": mock_repo2
        }

        with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
            mock_info = MagicMock()
            mock_info.plugins = [{"name": "test-plugin", "version": "1.0.0"}]
            mock_fetch.return_value = mock_info

            with patch("typer.prompt", return_value="1"):
                result = _resolve_plugin_conflict("test-plugin", "claude")
                assert result in ["marketplace1", "marketplace2"]

    @patch("code_assistant_manager.plugins.PluginManager")
    def test_resolve_plugin_conflict_no_conflicts(self, mock_pm_class):
        """Test conflict resolution when no conflicts exist."""
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm

        # Mock single marketplace
        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.name = "test-marketplace"
        mock_pm.get_all_repos.return_value = {"test-marketplace": mock_repo}

        with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
            mock_info = MagicMock()
            mock_info.plugins = [{"name": "unique-plugin", "version": "1.0.0"}]
            mock_fetch.return_value = mock_info

            # Should return marketplace directly without prompting
            result = _resolve_plugin_conflict("unique-plugin", "claude")
            assert result == "test-marketplace"

    @patch("code_assistant_manager.plugins.PluginManager")
    def test_resolve_plugin_conflict_plugin_not_found(self, mock_pm_class):
        """Test conflict resolution when plugin is not found."""
        import typer
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm

        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.name = "test-marketplace"
        mock_pm.get_all_repos.return_value = {"test-marketplace": mock_repo}

        with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
            mock_info = MagicMock()
            mock_info.plugins = []  # No plugins
            mock_fetch.return_value = mock_info

            with pytest.raises(typer.Exit):
                _resolve_plugin_conflict("nonexistent-plugin", "claude")


class TestHandlerIntegration:
    """Test handler integration."""

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.get_handler")
    def test_get_handler_claude(self, mock_get_handler):
        """Test getting Claude handler."""
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler

        result = _get_handler("claude")
        assert result == mock_handler

    def test_get_handler_invalid_app(self):
        """Test getting handler for invalid app."""
        with pytest.raises(ValueError):
            _get_handler("invalid-app")

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.get_handler")
    def test_handler_uses_cli_commands(self, mock_get_handler):
        """Test that Claude handler uses CLI commands."""
        mock_handler = MagicMock()
        mock_handler.uses_cli_plugin_commands = True
        mock_get_handler.return_value = mock_handler

        handler = _get_handler("claude")
        assert handler.uses_cli_plugin_commands is True