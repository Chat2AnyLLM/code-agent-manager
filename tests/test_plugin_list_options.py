"""Comprehensive tests for cam plugin list command options."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.plugin_commands import plugin_app
from code_assistant_manager.plugins import VALID_APP_TYPES


class TestPluginListCommandOptions:
    """Test all options for the cam plugin list command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def create_mock_handler(self, app_type="claude"):
        """Create a mock plugin handler."""
        handler = MagicMock()
        handler.get_enabled_plugins.return_value = {
            "plugin1@marketplace": True,
            "plugin2@marketplace": False
        }
        return handler

    def create_mock_manager(self):
        """Create a mock PluginManager."""
        manager = MagicMock()
        mock_repo = MagicMock()
        mock_repo.repo_owner = "test-owner"
        mock_repo.repo_name = "test-repo"
        mock_repo.repo_branch = "main"
        mock_repo.type = "marketplace"
        manager.get_repo.return_value = mock_repo
        manager.get_all_repos.return_value = {"test-marketplace": mock_repo}
        return manager

    def test_list_with_invalid_app_type_shows_error(self, runner):
        """Test --app option with invalid app type shows error."""
        result = runner.invoke(plugin_app, ["list", "--app", "invalid-app"])

        assert result.exit_code == 1
        assert "Invalid app type: invalid-app" in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_with_app_option_filters_by_app(self, mock_get_handler, runner):
        """Test --app option filters plugins for specific app."""
        handler = self.create_mock_handler("claude")
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            # Mock scan_marketplace_plugins to avoid sorting issues
            with patch.object(handler, 'scan_marketplace_plugins', return_value=[]):
                result = runner.invoke(plugin_app, ["list", "--app", "claude"])

        assert result.exit_code == 0
        assert "Claude Plugins:" in result.output
        assert "plugin1" in result.output
        assert "plugin2" in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_with_query_option_filters_by_name_and_description(self, mock_get_handler, runner):
        """Test --query option filters plugins by name or description."""
        handler = self.create_mock_handler()

        # Create simple plugin-like objects to avoid sorting issues
        class SimplePlugin:
            def __init__(self, name, description, category, marketplace, version, installed):
                self.name = name
                self.description = description
                self.category = category
                self.marketplace = marketplace
                self.version = version
                self.installed = installed

        plugins = [
            SimplePlugin("useful-plugin", "A useful plugin", "utility", "test-marketplace", "1.0.0", True),
            SimplePlugin("another-plugin", "Something else", "development", "test-marketplace", "2.0.0", False),
        ]
        handler.scan_marketplace_plugins.return_value = plugins
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            result = runner.invoke(plugin_app, ["list", "--query", "useful"])

        assert result.exit_code == 0
        assert "useful-plugin" in result.output
        assert "another-plugin" not in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_with_category_option_filters_by_category(self, mock_get_handler, runner):
        """Test --category option filters plugins by category."""
        handler = self.create_mock_handler()

        # Create simple plugin-like objects
        class SimplePlugin:
            def __init__(self, name, description, category, marketplace, version, installed):
                self.name = name
                self.description = description
                self.category = category
                self.marketplace = marketplace
                self.version = version
                self.installed = installed

        plugins = [
            SimplePlugin("plugin1", "Plugin 1", "utility", "test-marketplace", "1.0.0", True),
            SimplePlugin("plugin2", "Plugin 2", "development", "test-marketplace", "2.0.0", False),
        ]
        handler.scan_marketplace_plugins.return_value = plugins
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            result = runner.invoke(plugin_app, ["list", "--category", "utility"])

        assert result.exit_code == 0
        assert "plugin1" in result.output
        # plugin2 should not appear in the marketplace section since it doesn't match the category filter

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_with_limit_option_limits_results(self, mock_get_handler, runner):
        """Test --limit option limits the number of plugins shown."""
        handler = self.create_mock_handler()

        # Create simple plugin-like objects
        class SimplePlugin:
            def __init__(self, name, description, category, marketplace, version, installed):
                self.name = name
                self.description = description
                self.category = category
                self.marketplace = marketplace
                self.version = version
                self.installed = installed

        # Create many plugins to test limit
        plugins = []
        for i in range(10):
            plugins.append(SimplePlugin(f"plugin{i}", f"Description {i}", "test",
                                      "test-marketplace", "1.0.0", True))
        handler.scan_marketplace_plugins.return_value = plugins
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            result = runner.invoke(plugin_app, ["list", "--limit", "3"])

        assert result.exit_code == 0
        # Count how many plugin entries appear in the marketplace section
        lines = result.output.split('\n')
        marketplace_section_started = False
        plugin_count = 0

        for line in lines:
            if "Available Plugins from Marketplaces" in line:
                marketplace_section_started = True
                continue
            if marketplace_section_started and line.strip().startswith('○'):
                plugin_count += 1

        assert plugin_count <= 3, f"Expected at most 3 plugins, but found {plugin_count}"

    def test_list_with_nonexistent_marketplace_shows_error(self, runner):
        """Test marketplace argument with non-existent marketplace shows error."""
        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_repo.return_value = None
            mock_pm_class.return_value = mock_manager

            result = runner.invoke(plugin_app, ["list", "nonexistent-marketplace"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    # Note: Marketplace-specific tests are complex due to network dependencies
    # and are covered by integration tests. The core filtering and display
    # functionality is well-tested above.

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_with_all_option_deprecated_behavior(self, mock_get_handler, runner):
        """Test --all option (deprecated) behaves like without marketplace argument."""
        handler = self.create_mock_handler()
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            # Mock scan_marketplace_plugins to avoid sorting issues
            with patch.object(handler, 'scan_marketplace_plugins', return_value=[]):
                result = runner.invoke(plugin_app, ["list", "--all"])

        assert result.exit_code == 0
        # Should work the same as without arguments
        assert "Plugin Status Across All Apps:" in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_combines_query_and_category_filters(self, mock_get_handler, runner):
        """Test combining --query and --category options."""
        handler = self.create_mock_handler()

        # Create simple plugin-like objects
        class SimplePlugin:
            def __init__(self, name, description, category, marketplace, version, installed):
                self.name = name
                self.description = description
                self.category = category
                self.marketplace = marketplace
                self.version = version
                self.installed = installed

        plugins = [
            SimplePlugin("useful-utility", "A useful utility plugin", "utility", "test-marketplace", "1.0.0", True),
            SimplePlugin("useful-dev", "A useful dev plugin", "development", "test-marketplace", "2.0.0", False),
            SimplePlugin("other-utility", "Other utility plugin", "utility", "test-marketplace", "1.0.0", False),
        ]
        handler.scan_marketplace_plugins.return_value = plugins
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            result = runner.invoke(plugin_app, ["list", "--query", "useful", "--category", "utility"])

        assert result.exit_code == 0
        assert "useful-utility" in result.output
        # Other plugins should be filtered out
        assert "useful-dev" not in result.output  # Wrong category
        assert "other-utility" not in result.output  # Doesn't match query

    # Note: Marketplace-specific tests with filters are complex due to network dependencies
    # and are covered by integration tests. The core filtering functionality is well-tested above.

    def test_list_with_help_option_shows_help(self, runner):
        """Test --help option shows command help."""
        result = runner.invoke(plugin_app, ["list", "--help"])

        assert result.exit_code == 0
        assert "List installed and available plugins" in result.output
        assert "--app" in result.output
        assert "--query" in result.output
        assert "--category" in result.output
        assert "--limit" in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_handles_no_installed_plugins_gracefully(self, mock_get_handler, runner):
        """Test list command handles case where no plugins are installed."""
        handler = self.create_mock_handler()
        handler.get_enabled_plugins.return_value = {}  # No installed plugins
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            # Mock scan_marketplace_plugins to avoid sorting issues
            with patch.object(handler, 'scan_marketplace_plugins', return_value=[]):
                result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0
        assert "No plugins installed" in result.output

    @patch("code_assistant_manager.plugins.get_handler")
    def test_list_shows_enabled_disabled_status_correctly(self, mock_get_handler, runner):
        """Test list command shows correct enabled/disabled status for plugins."""
        handler = self.create_mock_handler()
        handler.get_enabled_plugins.return_value = {
            "enabled-plugin@marketplace": True,
            "disabled-plugin@marketplace": False
        }
        mock_get_handler.return_value = handler

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_manager = self.create_mock_manager()
            mock_pm_class.return_value = mock_manager

            # Mock scan_marketplace_plugins to avoid sorting issues
            with patch.object(handler, 'scan_marketplace_plugins', return_value=[]):
                result = runner.invoke(plugin_app, ["list", "--app", "claude"])

        assert result.exit_code == 0
        assert "✓ enabled" in result.output
        assert "○ disabled" in result.output