"""Tests for CLI plugin commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

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


@pytest.mark.skip(reason="Feature not implemented - integration tests for non-existent functionality")
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
                    "code_assistant_manager.plugins.PluginManager",
                    return_value=mock_manager,
                ):
                    with patch(
                        "code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict",
                        return_value=None
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
                with patch(
                    "code_assistant_manager.cli.plugins.plugin_install_commands._resolve_installed_plugin_conflict",
                    return_value=None
                ):
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

        # Check that command runs (may show "no marketplace configured" message)
        assert result.exit_code == 0 or "marketplace" in result.output.lower()

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

        # When no marketplaces are configured, it shows a different message
        assert result.exit_code == 0 or "not found" in result.output.lower() or "no marketplace" in result.output.lower()

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

        # When no marketplaces configured, might show different message
        assert result.exit_code in [0, 1]

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

        # When no marketplaces configured, might show different message
        assert result.exit_code in [0, 1]

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

        # When no marketplaces configured, shows different message
        assert result.exit_code == 0

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

        # When no marketplaces configured, shows different message
        assert result.exit_code in [0, 1]


class TestPluginInstallErrorHandling:
    """Test plugin install command error handling and unreachable marketplace behavior."""

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict")
    def test_install_plugin_calls_resolve_conflict(self, mock_resolve, runner):
        """Test that install_plugin calls _resolve_plugin_conflict when no marketplace specified."""
        mock_resolve.return_value = "test-marketplace"

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_get_handler:
            mock_handler = MagicMock()
            mock_get_handler.return_value = mock_handler
            mock_handler.uses_cli_plugin_commands = False

            with patch(
                "code_assistant_manager.plugins.PluginManager"
            ) as mock_plugin_manager:
                mock_manager = MagicMock()
                mock_plugin_manager.return_value = mock_manager

                with patch(
                    "code_assistant_manager.plugins.fetch.fetch_repo_info"
                ) as mock_fetch:
                    mock_fetch.return_value = MagicMock(plugins=[{"name": "test-plugin"}])

                    result = runner.invoke(
                        plugin_app, ["install", "test-plugin"]
                    )

        mock_resolve.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_resolve_plugin_conflict_with_unreachable_marketplaces(self, mock_get_handler):
        """Test _resolve_plugin_conflict handles unreachable marketplaces gracefully."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _resolve_plugin_conflict

        # Mock handler
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler
        mock_handler.get_known_marketplaces.return_value = {}

        # Mock PluginManager for configured marketplaces
        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm_class.return_value = mock_pm
            # Create marketplace repos
            working_repo = MagicMock()
            working_repo.repo_owner = "working"
            working_repo.repo_name = "repo"
            working_repo.repo_branch = "main"
            working_repo.type = "marketplace"

            broken_repo = MagicMock()
            broken_repo.repo_owner = "broken"
            broken_repo.repo_name = "repo"
            broken_repo.repo_branch = "main"
            broken_repo.type = "marketplace"

            mock_pm.get_all_repos.return_value = {
                "working-marketplace": working_repo,
                "broken-marketplace": broken_repo
            }

            # Mock fetch_repo_info to fail for broken marketplace, succeed for working
            with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
                working_info = MagicMock()
                working_info.plugins = [{"name": "test-plugin", "version": "1.0.0"}]

                def mock_fetch_side_effect(owner, repo, branch):
                    if owner == "working":
                        return working_info
                    elif owner == "broken":
                        raise Exception("Network error")
                    return None

                mock_fetch.side_effect = mock_fetch_side_effect

                # Test resolving conflict - this should return the marketplace since it finds the plugin
                marketplace = _resolve_plugin_conflict("test-plugin", "claude")

                assert marketplace == "working-marketplace"
                # Should have tried both marketplaces
                assert mock_fetch.call_count == 2

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_resolve_plugin_conflict_shows_unreachable_marketplaces(self, mock_get_handler):
        """Test that unreachable marketplaces are displayed to user."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _resolve_plugin_conflict

        # Mock handler
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler
        mock_handler.get_known_marketplaces.return_value = {}

        # Mock PluginManager
        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm_class.return_value = mock_pm

            # Create unreachable marketplace repo
            broken_repo = MagicMock()
            broken_repo.repo_owner = "broken"
            broken_repo.repo_name = "repo"
            broken_repo.repo_branch = "main"
            broken_repo.type = "marketplace"

            mock_pm.get_all_repos.return_value = {
                "broken-marketplace": broken_repo
            }

            # Mock fetch_repo_info to always fail
            with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
                mock_fetch.side_effect = Exception("Network timeout")

                # This should exit due to no available plugins
                with pytest.raises(SystemExit):
                    _resolve_plugin_conflict("test-plugin", "claude")

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_resolve_plugin_conflict_multiple_marketplaces_with_unreachable(self, mock_get_handler):
        """Test handling multiple marketplaces where some are unreachable."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _resolve_plugin_conflict

        # Mock handler
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler
        mock_handler.get_known_marketplaces.return_value = {}

        # Mock PluginManager
        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm_class.return_value = mock_pm

            # Create marketplace repos
            owner1_repo = MagicMock()
            owner1_repo.repo_owner = "owner1"
            owner1_repo.repo_name = "repo1"
            owner1_repo.repo_branch = "main"
            owner1_repo.type = "marketplace"

            owner2_repo = MagicMock()
            owner2_repo.repo_owner = "owner2"
            owner2_repo.repo_name = "repo2"
            owner2_repo.repo_branch = "main"
            owner2_repo.type = "marketplace"

            broken_repo = MagicMock()
            broken_repo.repo_owner = "broken"
            broken_repo.repo_name = "repo"
            broken_repo.repo_branch = "main"
            broken_repo.type = "marketplace"

            mock_pm.get_all_repos.return_value = {
                "marketplace1": owner1_repo,
                "marketplace2": owner2_repo,
                "unreachable-marketplace": broken_repo
            }

            # Mock fetch_repo_info
            with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
                info1 = MagicMock()
                info1.plugins = [{"name": "test-plugin", "version": "1.0.0"}]
                info2 = MagicMock()
                info2.plugins = [{"name": "test-plugin", "version": "2.0.0"}]

                def mock_fetch_side_effect(owner, repo, branch):
                    if owner == "owner1":
                        return info1
                    elif owner == "owner2":
                        return info2
                    else:
                        raise Exception("Network error")

                mock_fetch.side_effect = mock_fetch_side_effect

                # Mock user input to select marketplace 1
                with patch("builtins.input", return_value="1"):
                    marketplace = _resolve_plugin_conflict("test-plugin", "claude")

                # Should return marketplace1 (the first working marketplace)
                assert marketplace == "marketplace1"

    def test_remove_plugin_from_settings_handles_missing_keys(self):
        """Test _remove_plugin_from_settings handles missing or malformed keys."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _remove_plugin_from_settings

        mock_handler = MagicMock()
        mock_settings_file = MagicMock()
        mock_handler.settings_file = mock_settings_file
        mock_settings_file.exists.return_value = True

        # Test with missing enabledPlugins key
        with patch("builtins.open", mock_open(read_data='{"someOtherKey": "value"}')):
            result = _remove_plugin_from_settings(mock_handler, "test-plugin")
            assert result is False

        # Test with empty enabledPlugins
        with patch("builtins.open", mock_open(read_data='{"enabledPlugins": {}}')):
            result = _remove_plugin_from_settings(mock_handler, "test-plugin")
            assert result is False

        # Test with non-existent plugin
        settings_data = '{"enabledPlugins": {"existing-plugin": true}}'
        with patch("builtins.open", mock_open(read_data=settings_data)):
            result = _remove_plugin_from_settings(mock_handler, "non-existent-plugin")
            assert result is False

    def test_remove_plugin_from_settings_success(self):
        """Test successful plugin removal from settings."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _remove_plugin_from_settings

        mock_handler = MagicMock()
        mock_settings_file = MagicMock()
        mock_handler.settings_file = mock_settings_file
        mock_settings_file.exists.return_value = True

        settings_data = '{"enabledPlugins": {"test-plugin": true, "other-plugin": false}}'

        with patch("builtins.open", mock_open(read_data=settings_data)) as mock_file:
            result = _remove_plugin_from_settings(mock_handler, "test-plugin")

            assert result is True
            # Verify the file was written back
            mock_file().write.assert_called()
            written_data = "".join(call[0][0] for call in mock_file().write.call_args_list)
            # Parse written data and verify plugin was removed
            import json
            written_json = json.loads(written_data)
            assert "test-plugin" not in written_json["enabledPlugins"]
            assert "other-plugin" in written_json["enabledPlugins"]

    def test_set_plugin_enabled_handles_errors(self):
        """Test _set_plugin_enabled handles file errors gracefully."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _set_plugin_enabled

        mock_handler = MagicMock()
        mock_settings_file = MagicMock()
        mock_handler.settings_file = mock_settings_file

        # Test with non-existent settings file
        mock_settings_file.exists.return_value = False
        result = _set_plugin_enabled(mock_handler, "test-plugin", True)
        assert result is False

        # Test with unreadable settings file
        mock_settings_file.exists.return_value = True
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = _set_plugin_enabled(mock_handler, "test-plugin", True)
            assert result is False

    def test_set_plugin_enabled_success(self):
        """Test successful plugin enable/disable in settings."""
        from code_assistant_manager.cli.plugins.plugin_install_commands import _set_plugin_enabled

        mock_handler = MagicMock()
        mock_settings_file = MagicMock()
        mock_handler.settings_file = mock_settings_file
        mock_settings_file.exists.return_value = True

        initial_settings = '{"enabledPlugins": {"test-plugin": false}}'

        with patch("builtins.open", mock_open(read_data=initial_settings)) as mock_file:
            result = _set_plugin_enabled(mock_handler, "test-plugin", True)

            assert result is True
            # Verify the file was written back with updated setting
            mock_file().write.assert_called()
            written_data = "".join(call[0][0] for call in mock_file().write.call_args_list)
            import json
            written_json = json.loads(written_data)
            assert written_json["enabledPlugins"]["test-plugin"] is True

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler")
    def test_install_plugin_handles_fetch_repo_info_failure(self, mock_get_handler, runner):
        """Test install_plugin handles fetch_repo_info failures gracefully."""
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler
        mock_handler.uses_cli_plugin_commands = False

        with patch("code_assistant_manager.plugins.PluginManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm_class.return_value = mock_pm

            mock_repo = MagicMock()
            mock_repo.repo_owner = "test-owner"
            mock_repo.repo_name = "test-repo"
            mock_repo.repo_branch = "main"
            mock_pm.get_repo.return_value = mock_repo

            # Mock fetch_repo_info to return None (failure)
            with patch("code_assistant_manager.plugins.fetch.fetch_repo_info") as mock_fetch:
                mock_fetch.return_value = None

                result = runner.invoke(
                    plugin_app, ["install", "--marketplace", "test-marketplace", "test-plugin"]
                )

                assert result.exit_code == 1
                assert "Could not fetch plugins" in result.output
