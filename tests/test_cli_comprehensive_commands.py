"""Comprehensive CLI command and subcommand parameter/option tests.

This test suite covers all CLI commands, subcommands, parameters, and options
to ensure the CLI interface is properly tested and prevent regressions.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

# Mock tomli_w if missing to allow tests to run
try:
    import tomli_w
except ImportError:
    sys.modules["tomli_w"] = MagicMock()

import code_assistant_manager.configs  # Ensure configs module is loaded for patching
from code_assistant_manager.cli.app import app, config_app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        "providers": [
            {
                "name": "test-provider",
                "type": "anthropic",
                "api_key": "test-key",
                "model": "claude-3-sonnet-20240229"
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)


class TestMainCommands:
    """Test main CLI commands and their parameters/options."""

    def test_version_command(self, runner):
        """Test version command works."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "code-assistant-manager version" in result.output

    def test_version_alias(self, runner):
        """Test version alias 'v' works."""
        result = runner.invoke(app, ["v"])
        assert result.exit_code == 0
        assert "code-assistant-manager version" in result.output

    def test_doctor_command_basic(self, runner):
        """Test doctor command with basic options."""
        with patch("code_assistant_manager.cli.doctor.run_doctor_checks") as mock_doctor:
            mock_doctor.return_value = 0

            result = runner.invoke(app, ["doctor"])
            assert result.exit_code == 0
            mock_doctor.assert_called_once()

    def test_doctor_command_with_config(self, runner, temp_config_file):
        """Test doctor command with config file option."""
        with patch("code_assistant_manager.cli.doctor.run_doctor_checks") as mock_doctor:
            mock_doctor.return_value = 0

            result = runner.invoke(app, ["doctor", "--config", temp_config_file])
            assert result.exit_code == 0
            mock_doctor.assert_called_once()

    def test_doctor_command_verbose(self, runner):
        """Test doctor command with verbose option."""
        with patch("code_assistant_manager.cli.doctor.run_doctor_checks") as mock_doctor:
            mock_doctor.return_value = 0

            result = runner.invoke(app, ["doctor", "--verbose"])
            assert result.exit_code == 0
            mock_doctor.assert_called_once()

    def test_doctor_alias(self, runner):
        """Test doctor alias 'd' works."""
        with patch("code_assistant_manager.cli.doctor.run_doctor_checks") as mock_doctor:
            mock_doctor.return_value = 0

            result = runner.invoke(app, ["d"])
            assert result.exit_code == 0
            mock_doctor.assert_called_once()

    def test_upgrade_command_basic(self, runner):
        """Test upgrade command with basic options."""
        with patch("code_assistant_manager.cli.upgrade.handle_upgrade_command") as mock_upgrade:
            mock_upgrade.return_value = 0

            result = runner.invoke(app, ["upgrade"])
            assert result.exit_code == 0
            mock_upgrade.assert_called_once()

    def test_upgrade_command_with_target(self, runner):
        """Test upgrade command with target parameter."""
        with patch("code_assistant_manager.cli.upgrade.handle_upgrade_command") as mock_upgrade:
            mock_upgrade.return_value = 0

            result = runner.invoke(app, ["upgrade", "claude"])
            assert result.exit_code == 0
            # Check that handle_upgrade_command was called with "claude"
            args, kwargs = mock_upgrade.call_args
            assert args[0] == "claude"

    def test_upgrade_command_verbose(self, runner):
        """Test upgrade command with verbose option."""
        with patch("code_assistant_manager.cli.upgrade.handle_upgrade_command") as mock_upgrade:
            mock_upgrade.return_value = 0

            result = runner.invoke(app, ["upgrade", "--verbose"])
            assert result.exit_code == 0
            args, kwargs = mock_upgrade.call_args
            assert kwargs.get("verbose") is True

    def test_upgrade_command_with_config(self, runner, temp_config_file):
        """Test upgrade command with config file option."""
        with patch("code_assistant_manager.cli.upgrade.handle_upgrade_command") as mock_upgrade:
            mock_upgrade.return_value = 0

            result = runner.invoke(app, ["upgrade", "--config", temp_config_file])
            assert result.exit_code == 0
            mock_upgrade.assert_called_once()

    def test_upgrade_aliases(self, runner):
        """Test upgrade aliases work."""
        with patch("code_assistant_manager.cli.upgrade.handle_upgrade_command") as mock_upgrade:
            mock_upgrade.return_value = 0

            # Test 'u' alias
            result = runner.invoke(app, ["u"])
            assert result.exit_code == 0

            # Test 'install' command
            result = runner.invoke(app, ["install"])
            assert result.exit_code == 0

            # Test 'i' alias
            result = runner.invoke(app, ["i"])
            assert result.exit_code == 0

    def test_uninstall_command_basic(self, runner):
        """Test uninstall command exists and accepts basic options."""
        # Test that the command exists and accepts the --help flag
        result = runner.invoke(app, ["uninstall", "--help"])
        assert result.exit_code == 0
        assert "Uninstall CLI tools" in result.output

    def test_uninstall_command_with_target(self, runner):
        """Test uninstall command accepts target parameter."""
        result = runner.invoke(app, ["uninstall", "claude", "--help"])
        assert result.exit_code == 0

    def test_uninstall_command_force(self, runner):
        """Test uninstall command accepts force option."""
        result = runner.invoke(app, ["uninstall", "--force", "--help"])
        assert result.exit_code == 0

    def test_uninstall_command_keep_config(self, runner):
        """Test uninstall command accepts keep-config option."""
        result = runner.invoke(app, ["uninstall", "--keep-config", "--help"])
        assert result.exit_code == 0

    def test_uninstall_aliases(self, runner):
        """Test uninstall aliases work."""
        # Test 'un' alias exists
        result = runner.invoke(app, ["un", "--help"])
        assert result.exit_code == 0

    def test_launch_command_no_args(self, runner):
        """Test launch command without arguments shows help."""
        result = runner.invoke(app, ["launch"])
        # Should show help since no_args_is_help=False but no subcommand provided
        assert result.exit_code == 0 or result.exit_code == 2  # Help or error

    def test_launch_alias_no_args(self, runner):
        """Test launch alias 'l' without arguments."""
        result = runner.invoke(app, ["l"])
        assert result.exit_code == 0 or result.exit_code == 2


class TestConfigCommands:
    """Test config subcommands and their parameters/options."""

    def test_config_validate_success(self, runner, temp_config_file):
        """Test config validate command with valid config."""
        mock_cm = MagicMock()
        mock_cm.validate_config.return_value = (True, [])

        with patch("code_assistant_manager.config.ConfigManager", return_value=mock_cm):
            result = runner.invoke(config_app, ["validate", "--config", temp_config_file])
            assert result.exit_code == 0
            assert "passed" in result.output.lower()

    def test_config_validate_failure(self, runner, temp_config_file):
        """Test config validate command with invalid config."""
        mock_cm = MagicMock()
        mock_cm.validate_config.return_value = (False, ["Missing required field"])

        with patch("code_assistant_manager.config.ConfigManager", return_value=mock_cm):
            result = runner.invoke(config_app, ["validate", "--config", temp_config_file])
            assert result.exit_code == 1
            assert "failed" in result.output.lower()

    def test_config_validate_verbose(self, runner, temp_config_file):
        """Test config validate command with verbose option."""
        mock_cm = MagicMock()
        mock_cm.validate_config.return_value = (True, [])

        with patch("code_assistant_manager.config.ConfigManager", return_value=mock_cm):
            result = runner.invoke(config_app, ["validate", "--verbose", "--config", temp_config_file])
            assert result.exit_code == 0

    def test_config_list(self, runner):
        """Test config list command."""
        result = runner.invoke(config_app, ["list"])
        assert result.exit_code == 0
        assert "Configuration Files:" in result.output

    def test_config_set_basic(self, runner):
        """Test config set command with basic key=value."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.set_value.return_value = "/path/to/config"

            result = runner.invoke(config_app, ["set", "claude.model=gpt-4"])
            assert result.exit_code == 0
            assert "Set claude.model = gpt-4" in result.output

    def test_config_set_with_scope(self, runner):
        """Test config set command with scope option."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.set_value.return_value = "/path/to/config"

            result = runner.invoke(config_app, ["set", "--scope", "project", "claude.model=gpt-4"])
            assert result.exit_code == 0
            mock_config.set_value.assert_called_once()
            args, kwargs = mock_config.set_value.call_args
            assert args[2] == "project"  # scope parameter

    def test_config_unset_basic(self, runner):
        """Test config unset command."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.unset_value.return_value = True

            result = runner.invoke(config_app, ["unset", "claude.model"])
            assert result.exit_code == 0
            assert "Unset claude.model" in result.output

    def test_config_unset_with_scope(self, runner):
        """Test config unset command with scope option."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.unset_value.return_value = True

            result = runner.invoke(config_app, ["unset", "--scope", "project", "claude.model"])
            assert result.exit_code == 0
            mock_config.unset_value.assert_called_once()
            args, kwargs = mock_config.unset_value.call_args
            assert args[1] == "project"  # scope parameter

    def test_config_show_basic(self, runner):
        """Test config show command."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.load_config.return_value = {"user": {"data": {"model": "gpt-4"}, "path": "/path/to/config"}}

            result = runner.invoke(config_app, ["show"])
            assert result.exit_code == 0

    def test_config_show_with_app(self, runner):
        """Test config show command with app option."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.load_config.return_value = {"user": {"data": {"model": "gpt-4"}, "path": "/path/to/config"}}

            result = runner.invoke(config_app, ["show", "--app", "claude"])
            assert result.exit_code == 0

    def test_config_show_with_scope(self, runner):
        """Test config show command with scope option."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.load_config.return_value = {"user": {"data": {"model": "gpt-4"}, "path": "/path/to/config"}}

            result = runner.invoke(config_app, ["show", "--scope", "user"])
            assert result.exit_code == 0

    def test_config_show_specific_key(self, runner):
        """Test config show command with specific key."""
        with patch("code_assistant_manager.configs.get_tool_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            mock_config.load_config.return_value = {"user": {"data": {"model": "gpt-4"}, "path": "/path/to/config"}}

            result = runner.invoke(config_app, ["show", "claude.model"])
            assert result.exit_code == 0


class TestSubcommandGroups:
    """Test subcommand groups and their basic functionality."""

    def test_skill_group_exists(self, runner):
        """Test that skill subcommand group exists."""
        result = runner.invoke(app, ["skill", "--help"])
        assert result.exit_code == 0

    def test_skill_fetch_command(self, runner):
        """Test skill fetch subcommand."""
        with patch("code_assistant_manager.skills.manager.SkillManager.fetch_skills_from_repos") as mock_fetch:
            mock_fetch.return_value = []

            result = runner.invoke(app, ["skill", "fetch"])
            assert result.exit_code == 0
            mock_fetch.assert_called_once()

    def test_skill_list_command(self, runner):
        """Test skill list subcommand."""
        with patch("code_assistant_manager.skills.manager.SkillManager.get_all") as mock_get_all:
            mock_get_all.return_value = {}

            result = runner.invoke(app, ["skill", "list"])
            assert result.exit_code == 0

    def test_agent_group_exists(self, runner):
        """Test that agent subcommand group exists."""
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0

    def test_agent_fetch_command(self, runner):
        """Test agent fetch subcommand."""
        with patch("code_assistant_manager.agents.manager.AgentManager.fetch_agents_from_repos") as mock_fetch:
            mock_fetch.return_value = []

            result = runner.invoke(app, ["agent", "fetch"])
            assert result.exit_code == 0
            mock_fetch.assert_called_once()

    def test_plugin_marketplace_add_basic(self, runner):
        """Test plugin marketplace add command exists and accepts help."""
        result = runner.invoke(app, ["plugin", "marketplace", "add", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_add_with_save(self, runner):
        """Test plugin marketplace add with save option accepts help."""
        result = runner.invoke(app, ["plugin", "marketplace", "add", "--save", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_list_basic(self, runner):
        """Test plugin marketplace list command exists."""
        result = runner.invoke(app, ["plugin", "marketplace", "list", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_list_with_installed(self, runner):
        """Test plugin marketplace list with installed option accepts help."""
        result = runner.invoke(app, ["plugin", "marketplace", "list", "--installed", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_remove(self, runner):
        """Test plugin marketplace remove command exists."""
        result = runner.invoke(app, ["plugin", "marketplace", "remove", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_update(self, runner):
        """Test plugin marketplace update command exists."""
        result = runner.invoke(app, ["plugin", "marketplace", "update", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_install(self, runner):
        """Test plugin marketplace install command exists."""
        result = runner.invoke(app, ["plugin", "marketplace", "install", "--help"])
        assert result.exit_code == 0

    def test_plugin_marketplace_uninstall(self, runner):
        """Test plugin marketplace uninstall command exists."""
        result = runner.invoke(app, ["plugin", "marketplace", "uninstall", "--help"])
        assert result.exit_code == 0

    def test_plugin_list_command(self, runner):
        """Test plugin list subcommand."""
        with patch("code_assistant_manager.cli.plugins.plugin_management_commands.list_plugins") as mock_list, \
             patch("typer.echo"):
            mock_list.return_value = None

            result = runner.invoke(app, ["plugin", "list"])
            assert result.exit_code == 0

    def test_plugin_repos_command(self, runner):
        """Test plugin repos subcommand."""
        with patch("code_assistant_manager.cli.plugins.plugin_management_commands.list_repos") as mock_repos, \
             patch("typer.echo"):
            mock_repos.return_value = None

            result = runner.invoke(app, ["plugin", "repos"])
            assert result.exit_code == 0

    def test_plugin_add_repo_command(self, runner):
        """Test plugin add-repo subcommand."""
        result = runner.invoke(app, ["plugin", "add-repo", "--help"])
        assert result.exit_code == 0

    def test_plugin_remove_repo_command(self, runner):
        """Test plugin remove-repo subcommand."""
        result = runner.invoke(app, ["plugin", "remove-repo", "--help"])
        assert result.exit_code == 0

    def test_plugin_install_command(self, runner):
        """Test plugin install subcommand."""
        result = runner.invoke(app, ["plugin", "install", "--help"])
        assert result.exit_code == 0

    def test_plugin_uninstall_command(self, runner):
        """Test plugin uninstall subcommand."""
        result = runner.invoke(app, ["plugin", "uninstall", "--help"])
        assert result.exit_code == 0

    def test_plugin_enable_command(self, runner):
        """Test plugin enable subcommand."""
        result = runner.invoke(app, ["plugin", "enable", "--help"])
        assert result.exit_code == 0

    def test_plugin_disable_command(self, runner):
        """Test plugin disable subcommand."""
        result = runner.invoke(app, ["plugin", "disable", "--help"])
        assert result.exit_code == 0

    def test_plugin_validate_command(self, runner):
        """Test plugin validate subcommand."""
        result = runner.invoke(app, ["plugin", "validate", "--help"])
        assert result.exit_code == 0

    def test_plugin_view_command(self, runner):
        """Test plugin view subcommand."""
        result = runner.invoke(app, ["plugin", "view", "--help"])
        assert result.exit_code == 0

    def test_plugin_status_command(self, runner):
        """Test plugin status subcommand."""
        result = runner.invoke(app, ["plugin", "status", "--help"])
        assert result.exit_code == 0

    def test_mcp_endpoints_command(self, runner):
        """Test mcp endpoints subcommand."""
        result = runner.invoke(app, ["mcp", "endpoints", "--help"])
        assert result.exit_code == 0

    def test_mcp_list_command(self, runner):
        """Test mcp list subcommand."""
        result = runner.invoke(app, ["mcp", "list", "--help"])
        assert result.exit_code == 0

    def test_mcp_search_command(self, runner):
        """Test mcp search subcommand."""
        result = runner.invoke(app, ["mcp", "search", "--help"])
        assert result.exit_code == 0

    def test_mcp_show_command(self, runner):
        """Test mcp show subcommand."""
        result = runner.invoke(app, ["mcp", "show", "--help"])
        assert result.exit_code == 0

    def test_mcp_add_command(self, runner):
        """Test mcp add subcommand."""
        result = runner.invoke(app, ["mcp", "add", "--help"])
        assert result.exit_code == 0

    def test_mcp_remove_command(self, runner):
        """Test mcp remove subcommand."""
        result = runner.invoke(app, ["mcp", "remove", "--help"])
        assert result.exit_code == 0

    def test_mcp_update_command(self, runner):
        """Test mcp update subcommand."""
        result = runner.invoke(app, ["mcp", "update", "--help"])
        assert result.exit_code == 0

    def test_extensions_browse_command(self, runner):
        """Test extensions browse subcommand."""
        result = runner.invoke(app, ["extensions", "browse", "--help"])
        assert result.exit_code == 0

    def test_extensions_install_command(self, runner):
        """Test extensions install subcommand."""
        result = runner.invoke(app, ["extensions", "install", "--help"])
        assert result.exit_code == 0

    def test_extensions_uninstall_command(self, runner):
        """Test extensions uninstall subcommand."""
        result = runner.invoke(app, ["extensions", "uninstall", "--help"])
        assert result.exit_code == 0

    def test_extensions_list_command(self, runner):
        """Test extensions list subcommand."""
        result = runner.invoke(app, ["extensions", "list", "--help"])
        assert result.exit_code == 0

    def test_extensions_update_command(self, runner):
        """Test extensions update subcommand."""
        result = runner.invoke(app, ["extensions", "update", "--help"])
        assert result.exit_code == 0

    def test_extensions_disable_command(self, runner):
        """Test extensions disable subcommand."""
        result = runner.invoke(app, ["extensions", "disable", "--help"])
        assert result.exit_code == 0

    def test_extensions_enable_command(self, runner):
        """Test extensions enable subcommand."""
        result = runner.invoke(app, ["extensions", "enable", "--help"])
        assert result.exit_code == 0

    def test_extensions_link_command(self, runner):
        """Test extensions link subcommand."""
        result = runner.invoke(app, ["extensions", "link", "--help"])
        assert result.exit_code == 0

    def test_extensions_new_command(self, runner):
        """Test extensions new subcommand."""
        result = runner.invoke(app, ["extensions", "new", "--help"])
        assert result.exit_code == 0

    def test_extensions_validate_command(self, runner):
        """Test extensions validate subcommand."""
        result = runner.invoke(app, ["extensions", "validate", "--help"])
        assert result.exit_code == 0

    def test_extensions_settings_command(self, runner):
        """Test extensions settings subcommand."""
        result = runner.invoke(app, ["extensions", "settings", "--help"])
        assert result.exit_code == 0

    def test_prompt_list_command(self, runner):
        """Test prompt list subcommand."""
        result = runner.invoke(app, ["prompt", "list", "--help"])
        assert result.exit_code == 0

    def test_prompt_show_command(self, runner):
        """Test prompt show subcommand."""
        result = runner.invoke(app, ["prompt", "show", "--help"])
        assert result.exit_code == 0

    def test_prompt_add_command(self, runner):
        """Test prompt add subcommand."""
        result = runner.invoke(app, ["prompt", "add", "--help"])
        assert result.exit_code == 0

    def test_prompt_update_command(self, runner):
        """Test prompt update subcommand."""
        result = runner.invoke(app, ["prompt", "update", "--help"])
        assert result.exit_code == 0

    def test_prompt_remove_command(self, runner):
        """Test prompt remove subcommand."""
        result = runner.invoke(app, ["prompt", "remove", "--help"])
        assert result.exit_code == 0

    def test_prompt_import_command(self, runner):
        """Test prompt import subcommand."""
        result = runner.invoke(app, ["prompt", "import", "--help"])
        assert result.exit_code == 0

    def test_prompt_install_command(self, runner):
        """Test prompt install subcommand."""
        result = runner.invoke(app, ["prompt", "install", "--help"])
        assert result.exit_code == 0

    def test_prompt_uninstall_command(self, runner):
        """Test prompt uninstall subcommand."""
        result = runner.invoke(app, ["prompt", "uninstall", "--help"])
        assert result.exit_code == 0

    def test_prompt_status_command(self, runner):
        """Test prompt status subcommand."""
        result = runner.invoke(app, ["prompt", "status", "--help"])
        assert result.exit_code == 0

    def test_prompt_rename_command(self, runner):
        """Test prompt rename subcommand."""
        result = runner.invoke(app, ["prompt", "rename", "--help"])
        assert result.exit_code == 0

    def test_extension_group_exists(self, runner):
        """Test that extension subcommand group exists."""
        result = runner.invoke(app, ["extensions", "--help"])
        assert result.exit_code == 0

    def test_mcp_group_exists(self, runner):
        """Test that mcp subcommand group exists."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0

    def test_prompt_group_exists(self, runner):
        """Test that prompt subcommand group exists."""
        result = runner.invoke(app, ["prompt", "--help"])
        assert result.exit_code == 0


class TestGlobalOptions:
    """Test global CLI options."""

    def test_debug_option(self, runner):
        """Test global debug option."""
        with patch("logging.basicConfig") as mock_logging:
            result = runner.invoke(app, ["--debug", "version"])
            assert result.exit_code == 0
            mock_logging.assert_called_once()


class TestErrorHandling:
    """Test error handling in CLI commands."""

    def test_invalid_command(self, runner):
        """Test response to invalid command."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    def test_missing_required_args(self, runner):
        """Test response to missing required arguments."""
        result = runner.invoke(config_app, ["set"])
        assert result.exit_code != 0

    def test_config_file_not_found(self, runner):
        """Test handling of non-existent config file."""
        result = runner.invoke(config_app, ["validate", "--config", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()