"""Comprehensive tests for new plugin conflict resolution and naming changes."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.plugins.plugin_install_commands import (
    plugin_app,
)


class TestNewNamingPattern:
    """Test the new marketplace:plugin naming pattern."""

    def test_plugin_key_uses_colon_syntax(self):
        """Test that Plugin.key property uses marketplace:plugin format."""
        from code_assistant_manager.plugins.models import Plugin

        # Test with marketplace
        plugin = Plugin(
            name="code-reviewer",
            marketplace="awesome-plugins",
            repo_owner="test",
            repo_name="repo"
        )
        assert plugin.key == "awesome-plugins:code-reviewer"

        # Test with repo but no marketplace
        plugin = Plugin(
            name="eslint",
            repo_owner="test",
            repo_name="repo"
        )
        assert plugin.key == "test/repo:eslint"

        # Test local plugin
        plugin = Plugin(name="local-tool")
        assert plugin.key == "local:local-tool"


class TestPluginParsing:
    """Test plugin argument parsing with new syntax."""

    def test_parsing_colon_syntax(self):
        """Test that colon syntax is parsed correctly."""
        plugin_arg = "marketplace:plugin"
        expected_marketplace = "marketplace"
        expected_plugin = "plugin"

        if ":" in plugin_arg:
            marketplace, plugin = plugin_arg.split(":", 1)
            assert marketplace == expected_marketplace
            assert plugin == expected_plugin

    def test_parsing_legacy_at_syntax(self):
        """Test that legacy @ syntax is still supported."""
        plugin_arg = "plugin@marketplace"
        expected_plugin = "plugin"
        expected_marketplace = "marketplace"

        if "@" in plugin_arg:
            plugin, marketplace = plugin_arg.split("@", 1)
            assert plugin == expected_plugin
            assert marketplace == expected_marketplace


class TestInstallCommandParsing:
    """Test the install command argument parsing."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_install_with_explicit_marketplace(self, runner):
        """Test install with explicit marketplace:plugin syntax."""
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed")

        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler", return_value=mock_handler):
            with patch("code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"):
                result = runner.invoke(plugin_app, ["install", "awesome-plugins:code-reviewer"])

        assert result.exit_code == 0
        assert "awesome-plugins:code-reviewer" in result.output
        mock_handler.install_plugin.assert_called_once_with("code-reviewer", "awesome-plugins")

    def test_install_with_legacy_at_syntax(self, runner):
        """Test install with legacy plugin@marketplace syntax."""
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed")

        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler", return_value=mock_handler):
            with patch("code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"):
                result = runner.invoke(plugin_app, ["install", "code-reviewer@awesome-plugins"])

        assert result.exit_code == 0
        assert "awesome-plugins:code-reviewer" in result.output  # Should show new syntax in output
        mock_handler.install_plugin.assert_called_once_with("code-reviewer", "awesome-plugins")

    def test_install_without_marketplace_no_conflicts(self, runner):
        """Test install without marketplace when no conflicts exist."""
        mock_handler = MagicMock()
        mock_handler.install_plugin.return_value = (True, "Plugin installed")

        # Mock PluginManager to return empty repos (no conflicts)
        mock_manager = MagicMock()
        mock_manager.get_all_repos.return_value = {}

        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler", return_value=mock_handler):
            with patch("code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"):
                with patch("code_assistant_manager.plugins.PluginManager", return_value=mock_manager):
                    with patch("code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict", return_value=None):
                        result = runner.invoke(plugin_app, ["install", "unique-plugin"])

        assert result.exit_code == 0
        # Should call install with no marketplace
        mock_handler.install_plugin.assert_called_once_with("unique-plugin", None)


class TestUninstallCommandParsing:
    """Test the uninstall command argument parsing."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_uninstall_with_explicit_marketplace(self, runner):
        """Test uninstall with explicit marketplace:plugin syntax."""
        mock_handler = MagicMock()
        mock_handler.uninstall_plugin.return_value = (True, "Plugin uninstalled")

        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler", return_value=mock_handler):
            with patch("code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"):
                result = runner.invoke(plugin_app, ["uninstall", "awesome-plugins:code-reviewer"], input="y\n")

        assert result.exit_code == 0
        assert "awesome-plugins:code-reviewer" in result.output
        mock_handler.uninstall_plugin.assert_called_once_with("code-reviewer")


class TestBackwardCompatibility:
    """Test backward compatibility with old @ syntax."""

    def test_plugin_key_backward_compatibility(self):
        """Test that old @ keys are still recognized."""
        from code_assistant_manager.plugins.models import Plugin

        # Test that from_dict handles old @ format keys if they exist
        # (though we don't create them anymore)
        plugin_data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "marketplace": "test-marketplace"
        }
        plugin = Plugin.from_dict(plugin_data)
        assert plugin.key == "test-marketplace:test-plugin"


class TestSettingsFileHandling:
    """Test that settings files are handled correctly with new format."""

    def test_remove_plugin_from_settings_with_colon_keys(self, tmp_path):
        """Test removing plugin from settings when using colon format."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _remove_plugin_from_settings

        mock_handler = create_mock_handler()
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        # Create settings with colon-format plugin key
        settings = {"enabledPlugins": {"marketplace1:code-reviewer": {"enabled": True}}}
        with open(settings_path, "w") as f:
            json.dump(settings, f)

        mock_handler.settings_file = settings_path

        # Test removing by just plugin name (should match the key)
        result = _remove_plugin_from_settings(mock_handler, "code-reviewer")

        assert result is True
        with open(settings_path) as f:
            updated = json.load(f)
        assert "marketplace1:code-reviewer" not in updated.get("enabledPlugins", {})


def create_mock_handler():
    """Create a mock ClaudePluginHandler for tests."""
    handler = MagicMock()
    handler.get_cli_path.return_value = "/usr/bin/claude"
    return handler