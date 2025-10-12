"""Tests for CLI plugin commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.plugin_commands import plugin_app
from code_assistant_manager.cli.plugins.plugin_install_commands import (
    _get_handler,
    _remove_plugin_from_settings,
    _set_plugin_enabled,
)


def create_mock_handler():
    """Create a mock ClaudePluginHandler for tests."""
    handler = MagicMock()
    handler.get_cli_path.return_value = "/usr/bin/claude"
    return handler


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestHelperFunctions:
    """Test helper functions in plugin_commands."""

    def test_get_handler_returns_handler(self):
        """Test _get_handler returns a plugin handler for the specified app."""
        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands.get_handler"
        ) as mock_get_handler:
            mock_get_handler.return_value = MagicMock()
            handler = _get_handler("claude")
            assert handler is not None
            mock_get_handler.assert_called_once_with("claude")

    def test_get_handler_default_is_claude(self):
        """Test _get_handler defaults to claude."""
        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands.get_handler"
        ) as mock_get_handler:
            mock_get_handler.return_value = MagicMock()
            handler = _get_handler()
            assert handler is not None
            mock_get_handler.assert_called_once_with("claude")

    def test_remove_plugin_from_settings_success(self, tmp_path):
        """Test removing plugin from settings.json."""
        mock_handler = create_mock_handler()
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        # Create settings with a plugin in enabledPlugins
        settings = {"enabledPlugins": {"test-plugin@marketplace": {"enabled": True}}}
        with open(settings_path, "w") as f:
            json.dump(settings, f)

        mock_handler.settings_file = settings_path

        result = _remove_plugin_from_settings(mock_handler, "test-plugin")

        assert result is True
        with open(settings_path) as f:
            updated = json.load(f)
        assert "test-plugin@marketplace" not in updated.get("enabledPlugins", {})

    def test_remove_plugin_from_settings_not_found(self, tmp_path):
        """Test removing plugin that doesn't exist."""
        mock_handler = create_mock_handler()
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        settings = {"enabledPlugins": {}}
        with open(settings_path, "w") as f:
            json.dump(settings, f)

        mock_handler.settings_file = settings_path

        result = _remove_plugin_from_settings(mock_handler, "nonexistent")

        assert result is False

    def test_set_plugin_enabled_enable(self, tmp_path):
        """Test enabling a plugin."""
        mock_handler = create_mock_handler()
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        settings = {"enabledPlugins": {"test-plugin@marketplace": False}}
        with open(settings_path, "w") as f:
            json.dump(settings, f)

        mock_handler.settings_file = settings_path

        result = _set_plugin_enabled(mock_handler, "test-plugin", enabled=True)

        assert result is True
        with open(settings_path) as f:
            updated = json.load(f)
        assert updated["enabledPlugins"]["test-plugin@marketplace"] is True

    def test_set_plugin_enabled_disable(self, tmp_path):
        """Test disabling a plugin."""
        mock_handler = create_mock_handler()
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        settings = {"enabledPlugins": {"test-plugin@marketplace": True}}
        with open(settings_path, "w") as f:
            json.dump(settings, f)

        mock_handler.settings_file = settings_path

        result = _set_plugin_enabled(mock_handler, "test-plugin", enabled=False)

        assert result is True
        with open(settings_path) as f:
            updated = json.load(f)
        assert updated["enabledPlugins"]["test-plugin@marketplace"] is False

    def test_set_plugin_enabled_settings_not_found(self, tmp_path):
        """Test enabling plugin when settings file doesn't exist."""
        mock_handler = create_mock_handler()
        mock_handler.settings_file = tmp_path / "nonexistent.json"

        result = _set_plugin_enabled(mock_handler, "test-plugin", enabled=True)

        assert result is False


class TestPluginCommands:
    """Test plugin subcommands."""

    def test_plugin_install_success(self, runner):
        """Test successful plugin installation."""
        mock_handler = create_mock_handler()
        # The install command uses install_plugin which returns (success, msg)
        mock_handler.install_plugin.return_value = (True, "Plugin installed")
        # Also need to set up get_known_marketplaces for the flow
        mock_handler.get_known_marketplaces.return_value = []

        # Mock PluginManager to return no repo (triggering plugin install flow)
        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = None

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch(
                    "code_assistant_manager.cli.plugins.plugin_install_commands.PluginManager",
                    return_value=mock_manager,
                ):
                    result = runner.invoke(plugin_app, ["install", "test-plugin"])

        assert result.exit_code == 0
        assert "installed" in result.output.lower()

    def test_plugin_uninstall_success(self, runner):
        """Test successful plugin uninstallation."""
        mock_handler = create_mock_handler()
        # The uninstall command uses uninstall_plugin which returns (success, msg)
        mock_handler.uninstall_plugin.return_value = (True, "Plugin uninstalled")

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                # Use input="y\n" to confirm the prompt (workaround for Python 3.14-nogil issue with --force flag)
                result = runner.invoke(
                    plugin_app, ["uninstall", "test-plugin"], input="y\n"
                )

        assert result.exit_code == 0

    def test_plugin_list(self, runner):
        """Test plugin list command."""
        mock_handler = create_mock_handler()
        # The list command uses get_enabled_plugins which returns a dict of plugin_key -> enabled
        mock_handler.get_enabled_plugins.return_value = {"plugin1@marketplace": True}

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0

    def test_plugin_enable(self, runner):
        """Test plugin enable command."""
        mock_handler = create_mock_handler()
        # The enable command uses enable_plugin which returns (success, msg)
        mock_handler.enable_plugin.return_value = (True, "Plugin enabled")

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch(
                    "code_assistant_manager.cli.plugins.plugin_install_commands._set_plugin_enabled",
                    return_value=True,
                ):
                    result = runner.invoke(plugin_app, ["enable", "test-plugin"])

        assert result.exit_code == 0

    def test_plugin_disable(self, runner):
        """Test plugin disable command."""
        mock_handler = create_mock_handler()
        # The disable command uses disable_plugin which returns (success, msg)
        mock_handler.disable_plugin.return_value = (True, "Plugin disabled")

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch(
                    "code_assistant_manager.cli.plugins.plugin_install_commands._set_plugin_enabled",
                    return_value=True,
                ):
                    result = runner.invoke(plugin_app, ["disable", "test-plugin"])

        assert result.exit_code == 0

    def test_plugin_validate(self, runner):
        """Test plugin validate command."""
        mock_handler = create_mock_handler()
        # The validate command uses validate_plugin which returns (success, msg)
        mock_handler.validate_plugin.return_value = (True, "Plugin is valid")

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                result = runner.invoke(plugin_app, ["validate", "test-plugin"])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()


class TestRepoCommands:
    """Test plugin repository commands."""

    def test_repos_list(self, runner):
        """Test repos list command."""
        result = runner.invoke(plugin_app, ["repos"])

        assert result.exit_code == 0

    def test_plugin_status(self, runner):
        """Test plugin status command."""
        mock_handler = create_mock_handler()
        with patch(
            "code_assistant_manager.plugins.get_handler",
            return_value=mock_handler,
        ):
            result = runner.invoke(plugin_app, ["status"])

        assert result.exit_code == 0


class TestMarketplaceCommands:
    """Test marketplace subcommands."""

    def test_marketplace_install_success(self, runner):
        """Test successful marketplace installation."""
        mock_handler = create_mock_handler()
        mock_handler.marketplace_add.return_value = (True, "Marketplace installed")

        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.repo_owner = "test-owner"
        mock_repo.repo_name = "test-repo"

        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = mock_repo

        with (
            patch(
                "code_assistant_manager.cli.plugins.plugin_marketplace_commands.get_handler",
                return_value=mock_handler,
            ),
            patch(
                "code_assistant_manager.plugins.PluginManager",
                return_value=mock_manager,
            ),
        ):
            result = runner.invoke(
                plugin_app, ["marketplace", "install", "test-marketplace"]
            )

        assert result.exit_code == 0
        assert "installed" in result.output.lower()
        mock_handler.marketplace_add.assert_called_once()

    def test_marketplace_install_not_configured(self, runner):
        """Test marketplace install when marketplace is not configured."""
        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = None

        with patch(
            "code_assistant_manager.plugins.PluginManager",
            return_value=mock_manager,
        ):
            result = runner.invoke(
                plugin_app, ["marketplace", "install", "nonexistent-marketplace"]
            )

        assert result.exit_code == 1
        assert "not found in CAM configuration" in result.output

    def test_marketplace_install_wrong_type(self, runner):
        """Test marketplace install when repo is not a marketplace."""
        mock_repo = MagicMock()
        mock_repo.type = "plugin"  # Wrong type
        mock_repo.repo_owner = "test-owner"
        mock_repo.repo_name = "test-repo"

        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = mock_repo

        with patch(
            "code_assistant_manager.plugins.PluginManager",
            return_value=mock_manager,
        ):
            result = runner.invoke(
                plugin_app, ["marketplace", "install", "wrong-type-repo"]
            )

        assert result.exit_code == 1
        assert "not a marketplace" in result.output

    def test_marketplace_install_no_github_source(self, runner):
        """Test marketplace install when repo has no GitHub source."""
        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.repo_owner = None  # No GitHub source
        mock_repo.repo_name = None

        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = mock_repo

        with patch(
            "code_assistant_manager.plugins.PluginManager",
            return_value=mock_manager,
        ):
            result = runner.invoke(
                plugin_app, ["marketplace", "install", "no-source-marketplace"]
            )

        assert result.exit_code == 1
        assert "no GitHub source configured" in result.output

    def test_marketplace_install_already_installed(self, runner):
        """Test marketplace install when already installed."""
        mock_handler = create_mock_handler()
        mock_handler.marketplace_add.return_value = (
            False,
            "Marketplace already installed",
        )

        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.repo_owner = "test-owner"
        mock_repo.repo_name = "test-repo"

        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = mock_repo

        with patch(
            "code_assistant_manager.cli.plugins.plugin_marketplace_commands.get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.plugins.PluginManager",
                return_value=mock_manager,
            ):
                result = runner.invoke(
                    plugin_app,
                    ["marketplace", "install", "already-installed-marketplace"],
                )

        assert result.exit_code == 0
        assert "already installed" in result.output.lower()

    def test_marketplace_install_failure(self, runner):
        """Test marketplace install failure."""
        mock_handler = create_mock_handler()
        mock_handler.marketplace_add.return_value = (False, "Installation failed")

        mock_repo = MagicMock()
        mock_repo.type = "marketplace"
        mock_repo.repo_owner = "test-owner"
        mock_repo.repo_name = "test-repo"

        mock_manager = MagicMock()
        mock_manager.get_repo.return_value = mock_repo

        with patch(
            "code_assistant_manager.cli.plugins.plugin_marketplace_commands.get_handler",
            return_value=mock_handler,
        ):
            with patch(
                "code_assistant_manager.plugins.PluginManager",
                return_value=mock_manager,
            ):
                result = runner.invoke(
                    plugin_app, ["marketplace", "install", "failing-marketplace"]
                )

        assert result.exit_code == 1
        assert "failed" in result.output.lower()
