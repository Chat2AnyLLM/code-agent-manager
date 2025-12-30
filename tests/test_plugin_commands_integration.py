"""Test the refactored plugin commands integration."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.plugins.plugin_discovery_commands import (
    plugin_app as discovery_app,
)
from code_assistant_manager.plugins.fetch import FetchedRepoInfo
from code_assistant_manager.cli.plugins.plugin_install_commands import (
    plugin_app as install_app,
)
from code_assistant_manager.cli.plugins.plugin_management_commands import (
    plugin_app as management_app,
)
from code_assistant_manager.cli.plugins.plugin_marketplace_commands import (
    marketplace_app,
)


class TestPluginCommandIntegration:
    """Test that the refactored plugin commands work together."""

    def test_plugin_apps_exist(self):
        """Test that all plugin sub-apps are properly defined."""
        assert install_app is not None
        assert management_app is not None
        assert discovery_app is not None
        assert marketplace_app is not None

    def test_install_commands_available(self):
        """Test that install commands are available."""
        runner = CliRunner()
        result = runner.invoke(install_app, ["--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output
        assert "enable" in result.output
        assert "disable" in result.output
        assert "validate" in result.output

    def test_management_commands_available(self):
        """Test that management commands are available."""
        runner = CliRunner()
        result = runner.invoke(management_app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "repos" in result.output
        assert "add-repo" in result.output
        assert "remove-repo" in result.output

    def test_discovery_commands_available(self):
        """Test that discovery commands are available."""
        runner = CliRunner()
        result = runner.invoke(discovery_app, ["--help"])
        assert result.exit_code == 0
        assert "view" in result.output
        assert "status" in result.output
        # browse was deprecated and removed, list was enhanced instead
        # fetch was moved to marketplace add --save, so it's no longer here

    def test_marketplace_commands_available(self):
        """Test that marketplace commands are available."""
        runner = CliRunner()
        result = runner.invoke(marketplace_app, ["--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output
        assert "update" in result.output

    @patch(
        "code_assistant_manager.cli.plugins.plugin_management_commands.PluginManager"
    )
    def test_list_command_basic(self, mock_plugin_manager):
        """Test that the list command can be called without errors."""
        mock_manager = MagicMock()
        mock_manager.get_all_repos.return_value = {}
        mock_plugin_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(management_app, ["list"])
        # Just verify it doesn't crash - the actual output depends on the mock setup
        assert result.exit_code in [
            0,
            1,
        ]  # 0 for success, 1 for expected errors with empty repos

    @patch("code_assistant_manager.cli.plugins.plugin_discovery_commands.PluginManager")
    @patch("code_assistant_manager.plugins.fetch.fetch_repo_info")
    def test_view_plugin_python_expert(self, mock_fetch, mock_plugin_manager):
        """CLI view can locate python-expert from awesome-claude-code-plugins."""
        mock_repo = MagicMock(
            repo_owner="ccplugins",
            repo_name="awesome-claude-code-plugins",
            repo_branch="main",
        )

        mock_manager = MagicMock()
        mock_manager.get_all_repos.return_value = {"awesome-claude-code-plugins": mock_repo}
        mock_plugin_manager.return_value = mock_manager

        mock_fetch.return_value = FetchedRepoInfo(
            owner="ccplugins",
            repo="awesome-claude-code-plugins",
            branch="main",
            name="awesome-claude-code-plugins",
            description="Awesome Claude Code plugins collection",
            type="marketplace",
            plugin_count=1,
            plugins=[
                {
                    "name": "python-expert",
                    "version": "0.1.0",
                    "description": "Python expert plugin",
                    "category": "python",
                }
            ],
        )

        runner = CliRunner()
        result = runner.invoke(discovery_app, ["view", "python-expert"])
        assert result.exit_code == 0
        assert "python-expert" in result.output
        assert "awesome-claude-code-plugins" in result.output
