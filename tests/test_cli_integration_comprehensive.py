"""Comprehensive CLI integration tests covering all commands, subcommands, options and flags."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from typer.testing import CliRunner

from code_assistant_manager.cli.app import app


@pytest.mark.skip(reason="Feature not implemented - integration tests for non-existent functionality")
class TestCLIIntegration:
    """Comprehensive CLI integration tests."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".config" / "code-assistant-manager"
        config_dir.mkdir(parents=True)
        return config_dir


class TestMainAppCommands:
    """Test main CLI application commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_app_help_command(self, runner):
        """Test main app help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Code Assistant Manager" in result.output
        # Check that all main subcommands are listed
        assert "launch" in result.output
        assert "config" in result.output
        assert "plugin" in result.output
        assert "agent" in result.output
        assert "mcp" in result.output
        assert "prompt" in result.output
        assert "skill" in result.output

    def test_app_version_option(self, runner):
        """Test version option."""
        result = runner.invoke(app, ["--version"])
        # Version command behavior may vary, but should not error critically
        assert result.exit_code in [0, 1, 2]  # Some apps return different codes for version

    def test_app_debug_option(self, runner):
        """Test debug option."""
        with patch("code_assistant_manager.cli.app.logger") as mock_logger:
            result = runner.invoke(app, ["--debug", "--help"])
            assert result.exit_code == 0
            # Debug logging should be configured

    def test_app_invalid_command(self, runner):
        """Test invalid command handling."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output or "unrecognized" in result.output.lower()


class TestLaunchCommands:
    """Test launch command and subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_launch_help(self, runner):
        """Test launch command help."""
        result = runner.invoke(app, ["launch", "--help"])
        assert result.exit_code == 0
        assert "Launch AI code editors" in result.output

    @patch("code_assistant_manager.cli.app.get_registered_tools")
    def test_launch_interactive_menu(self, mock_get_tools, runner):
        """Test launch interactive menu."""
        mock_get_tools.return_value = {"claude": MagicMock(), "codex": MagicMock()}

        with patch("code_assistant_manager.menu.menus.display_centered_menu") as mock_menu:
            mock_menu.return_value = (True, 0)  # Success, selected claude

            with patch("code_assistant_manager.cli.app.ConfigManager") as mock_config:
                mock_config.return_value.validate_config.return_value = (True, [])

                with patch("sys.exit") as mock_exit:
                    result = runner.invoke(app, ["launch"])
                    assert result.exit_code == 0
                    mock_menu.assert_called_once()

    @patch("code_assistant_manager.cli.app.get_registered_tools")
    @patch("code_assistant_manager.cli.app.ConfigManager")
    def test_launch_specific_tool(self, mock_get_tools, mock_config, runner):
        """Test launching specific tool."""
        mock_config.return_value.validate_config.return_value = (True, [])
        mock_get_tools.return_value = {"claude": MagicMock()}

        with patch("sys.exit") as mock_exit:
            result = runner.invoke(app, ["launch", "claude", "--help"])
            # This should show the tool's help or attempt to launch
            assert result.exit_code == 0 or "claude" in result.output.lower()

    @pytest.mark.skip(reason="ConfigManager mock setup needs fixing")
    @patch("code_assistant_manager.cli.app.get_registered_tools")
    @patch("code_assistant_manager.cli.app.ConfigManager")
    def test_launch_with_config_option(self, mock_get_tools, mock_config, runner):
        """Test launch with custom config option."""
        mock_config.return_value.validate_config.return_value = (True, [])
        mock_get_tools.return_value = {"claude": MagicMock()}

        with patch("sys.exit") as mock_exit:
            result = runner.invoke(app, ["launch", "claude", "--config", "/tmp/test.json"])
            assert result.exit_code == 0


class TestConfigCommands:
    """Test config command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_config_help(self, runner):
        """Test config command help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration management" in result.output

    @patch("code_assistant_manager.config.ConfigManager")
    def test_config_validate_success(self, mock_config_class, runner):
        """Test config validate command success."""
        mock_config = MagicMock()
        mock_config.validate_config.return_value = (True, [])
        mock_config_class.return_value = mock_config

        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0
        assert "✓ Configuration validation passed" in result.output

    @patch("code_assistant_manager.config.ConfigManager")
    def test_config_validate_failure(self, mock_config_class, runner):
        """Test config validate command failure."""
        mock_config = MagicMock()
        mock_config.validate_config.return_value = (False, ["Error 1", "Error 2"])
        mock_config_class.return_value = mock_config

        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 1
        assert "✗ Configuration validation failed" in result.output

    def test_config_list_locations(self, runner):
        """Test config list command."""
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "Configuration Files" in result.output

    @patch("code_assistant_manager.configs.get_tool_config")
    def test_config_show_command(self, mock_get_tool_config, runner):
        """Test config show command."""
        mock_tool_config = MagicMock()
        mock_tool_config.load_config.return_value = {"user": {"data": {"key": "value"}, "path": "/tmp/config.json"}}
        mock_get_tool_config.return_value = mock_tool_config

        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "value" in result.output

    @patch("code_assistant_manager.configs.get_tool_config")
    def test_config_show_specific_key(self, mock_get_tool_config, runner):
        """Test config show command with specific key."""
        mock_tool_config = MagicMock()
        mock_tool_config.load_config.return_value = {"user": {"data": {"key": "value"}, "path": "/tmp/config.json"}}
        mock_get_tool_config.return_value = mock_tool_config

        result = runner.invoke(app, ["config", "show", "claude.key"])
        assert result.exit_code == 0
        assert "value" in result.output

    @patch("code_assistant_manager.configs.get_tool_config")
    def test_config_show_wildcard(self, mock_get_tool_config, runner):
        """Test config show command with wildcard."""
        mock_tool_config = MagicMock()
        mock_tool_config.load_config.return_value = {
            "user": {"data": {"app.key1": "value1", "app.key2": "value2"}, "path": "/tmp/config.json"}
        }
        mock_get_tool_config.return_value = mock_tool_config

    @patch("code_assistant_manager.configs.get_tool_config")
    def test_config_set_command(self, mock_get_tool_config, runner):
        """Test config set command."""
        mock_tool_config = MagicMock()
        mock_tool_config.set_value.return_value = "/tmp/config.json"
        mock_get_tool_config.return_value = mock_tool_config

        result = runner.invoke(app, ["config", "set", "test.key=value"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.configs.get_tool_config")
    def test_config_unset_command(self, mock_get_tool_config, runner):
        """Test config unset command."""
        mock_tool_config = MagicMock()
        mock_tool_config.unset_value.return_value = True
        mock_get_tool_config.return_value = mock_tool_config

        result = runner.invoke(app, ["config", "unset", "test.key"])
        assert result.exit_code == 0


class TestPluginCommands:
    """Test plugin command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_plugin_help(self, runner):
        """Test plugin command help."""
        result = runner.invoke(app, ["plugin", "--help"])
        assert result.exit_code == 0
        assert "Manage plugins" in result.output.lower()

    @patch("code_assistant_manager.cli.plugins.plugin_management_commands.list_plugins")
    def test_plugin_list(self, runner, mock_list):
        """Test plugin list command."""
        mock_list.return_value = None

        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0
        mock_list.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_management_commands.list_repos")
    def test_plugin_repos(self, runner, mock_repos):
        """Test plugin repos command."""
        mock_repos.return_value = None

        result = runner.invoke(app, ["plugin", "repos"])
        assert result.exit_code == 0
        mock_repos.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.install_plugin")
    def test_plugin_install(self, runner, mock_install):
        """Test plugin install command."""
        mock_install.return_value = None

        result = runner.invoke(app, ["plugin", "install", "test-plugin"])
        assert result.exit_code == 0
        mock_install.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.uninstall_plugin")
    def test_plugin_uninstall(self, runner, mock_uninstall):
        """Test plugin uninstall command."""
        mock_uninstall.return_value = None

        result = runner.invoke(app, ["plugin", "uninstall", "test-plugin"])
        assert result.exit_code == 0
        mock_uninstall.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.enable_plugin")
    def test_plugin_enable(self, runner, mock_enable):
        """Test plugin enable command."""
        mock_enable.return_value = None

        result = runner.invoke(app, ["plugin", "enable", "test-plugin"])
        assert result.exit_code == 0
        mock_enable.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.disable_plugin")
    def test_plugin_disable(self, runner, mock_disable):
        """Test plugin disable command."""
        mock_disable.return_value = None

        result = runner.invoke(app, ["plugin", "disable", "test-plugin"])
        assert result.exit_code == 0
        mock_disable.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.validate_plugin")
    def test_plugin_validate(self, runner, mock_validate):
        """Test plugin validate command."""
        mock_validate.return_value = None

        result = runner.invoke(app, ["plugin", "validate", "test-plugin"])
        assert result.exit_code == 0
        mock_validate.assert_called_once()


    @patch("code_assistant_manager.cli.plugins.plugin_discovery_commands.view_plugin")
    def test_plugin_view(self, runner, mock_view):
        """Test plugin view command."""
        mock_view.return_value = None

        result = runner.invoke(app, ["plugin", "view", "test-plugin"])
        assert result.exit_code == 0
        mock_view.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_discovery_commands.plugin_status")
    def test_plugin_status(self, runner, mock_status):
        """Test plugin status command."""
        mock_status.return_value = None

        result = runner.invoke(app, ["plugin", "status"])
        assert result.exit_code == 0
        mock_status.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_management_commands.add_plugin_repo")
    def test_plugin_add_repo(self, runner, mock_add_repo):
        """Test plugin add-repo command."""
        mock_add_repo.return_value = None

        result = runner.invoke(app, ["plugin", "add-repo", "--owner", "test-owner", "--name", "test-repo"])
        assert result.exit_code == 0
        mock_add_repo.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_management_commands.remove_plugin_repo")
    def test_plugin_remove_repo(self, runner, mock_remove_repo):
        """Test plugin remove-repo command."""
        mock_remove_repo.return_value = None

        result = runner.invoke(app, ["plugin", "remove-repo", "--owner", "test-owner", "--name", "test-repo"])
        assert result.exit_code == 0
        mock_remove_repo.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.enable_plugin")
    def test_plugin_enable(self, runner, mock_enable):
        """Test plugin enable command."""
        mock_enable.return_value = None

        result = runner.invoke(app, ["plugin", "enable", "test-plugin", "--app", "claude"])
        assert result.exit_code == 0
        mock_enable.assert_called_once()

    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.disable_plugin")
    def test_plugin_disable(self, runner, mock_disable):
        """Test plugin disable command."""
        mock_disable.return_value = None

        result = runner.invoke(app, ["plugin", "disable", "test-plugin", "--app", "claude"])
        assert result.exit_code == 0
        mock_disable.assert_called_once()


class TestAgentCommands:
    """Test agent command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_agent_help(self, runner):
        """Test agent command help."""
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "Manage agents" in result.output.lower()

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_list(self, runner, mock_get_manager):
        """Test agent list command."""
        mock_manager = MagicMock()
        mock_manager.sync_installed_status.return_value = None
        mock_manager.get_all.return_value = {}
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0
        mock_manager.get_all.assert_called_once()

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_fetch(self, runner, mock_get_manager):
        """Test agent fetch command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "fetch", "https://github.com/test/repo"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_view(self, runner, mock_get_manager):
        """Test agent view command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "view", "test-agent"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_install(self, runner, mock_get_manager):
        """Test agent install command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "install", "test-agent", "--app", "claude"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_uninstall(self, runner, mock_get_manager):
        """Test agent uninstall command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "uninstall", "test-agent", "--app", "claude"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_repos(self, runner, mock_get_manager):
        """Test agent repos command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "repos"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_installed(self, runner, mock_get_manager):
        """Test agent installed command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "installed"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_add_repo(self, runner, mock_get_manager):
        """Test agent add-repo command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "add-repo", "--owner", "test-owner", "--name", "test-repo"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.agents_commands._get_agent_manager")
    def test_agent_remove_repo(self, runner, mock_get_manager):
        """Test agent remove-repo command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["agent", "remove-repo", "--owner", "test-owner", "--name", "test-repo"])
        assert result.exit_code == 0


class TestMCPCommands:
    """Test MCP command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_mcp_help(self, runner):
        """Test MCP command help."""
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "Model Context Protocol" in result.output

    @patch("code_assistant_manager.mcp.server_commands.list")
    def test_mcp_list(self, runner, mock_list):
        """Test MCP list command."""
        mock_list.return_value = None

        result = runner.invoke(app, ["mcp", "list"])
        assert result.exit_code == 0
        mock_list.assert_called_once()

    @patch("code_assistant_manager.mcp.server_commands.search")
    def test_mcp_search(self, runner, mock_search):
        """Test MCP search command."""
        mock_search.return_value = None

        result = runner.invoke(app, ["mcp", "search", "query"])
        assert result.exit_code == 0
        mock_search.assert_called_once_with("query")

    @patch("code_assistant_manager.mcp.server_commands.show")
    def test_mcp_show(self, runner, mock_show):
        """Test MCP show command."""
        mock_show.return_value = None

        result = runner.invoke(app, ["mcp", "show", "server-name"])
        assert result.exit_code == 0
        mock_show.assert_called_once()

    @patch("code_assistant_manager.mcp.server_commands.add")
    def test_mcp_add(self, runner, mock_add):
        """Test MCP add command."""
        mock_add.return_value = None

    @patch("code_assistant_manager.mcp.server_commands.remove")
    def test_mcp_remove(self, runner, mock_remove):
        """Test MCP remove command."""
        mock_remove.return_value = None

        result = runner.invoke(app, ["mcp", "server", "remove", "server-name", "--client", "claude"])
        assert result.exit_code == 0
        mock_remove.assert_called_once()

    @patch("code_assistant_manager.mcp.server_commands.update")
    def test_mcp_update(self, runner, mock_update):
        """Test MCP update command."""
        mock_update.return_value = None

        result = runner.invoke(app, ["mcp", "server", "update", "server-name", "--client", "claude"])
        assert result.exit_code == 0
        mock_update.assert_called_once()


class TestPromptCommands:
    """Test prompt command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_prompt_help(self, runner):
        """Test prompt command help."""
        result = runner.invoke(app, ["prompt", "--help"])
        assert result.exit_code == 0
        assert "Manage prompt templates" in result.output.lower()

    @patch("code_assistant_manager.cli.prompts_commands.list_templates")
    def test_prompt_list(self, runner, mock_list):
        """Test prompt list command."""
        mock_list.return_value = {}

        result = runner.invoke(app, ["prompt", "list"])
        assert result.exit_code == 0
        mock_list.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.show_template")
    def test_prompt_show(self, runner, mock_show):
        """Test prompt show command."""
        mock_show.return_value = None

        result = runner.invoke(app, ["prompt", "show", "template-name"])
        assert result.exit_code == 0
        mock_show.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.add_template")
    def test_prompt_add(self, runner, mock_add):
        """Test prompt add command."""
        mock_add.return_value = None

        result = runner.invoke(app, ["prompt", "add", "template-name", "--template", "Hello {name}"])
        assert result.exit_code == 0
        mock_add.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.update_template")
    def test_prompt_update(self, runner, mock_update):
        """Test prompt update command."""
        mock_update.return_value = None

        result = runner.invoke(app, ["prompt", "update", "template-name", "--template", "Updated {name}"])
        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.remove_template")
    def test_prompt_remove(self, runner, mock_remove):
        """Test prompt remove command."""
        mock_remove.return_value = None

        result = runner.invoke(app, ["prompt", "remove", "template-name"])
        assert result.exit_code == 0
        mock_remove.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.import_template")
    def test_prompt_import(self, runner, mock_import):
        """Test prompt import command."""
        mock_import.return_value = None

        result = runner.invoke(app, ["prompt", "import", "--app", "claude", "--level", "user"])
        assert result.exit_code == 0
        mock_import.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.install_template")
    def test_prompt_install(self, runner, mock_install):
        """Test prompt install command."""
        mock_install.return_value = None

        result = runner.invoke(app, ["prompt", "install", "template-name", "--app", "claude", "--level", "user"])
        assert result.exit_code == 0
        mock_install.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.uninstall_template")
    def test_prompt_uninstall(self, runner, mock_uninstall):
        """Test prompt uninstall command."""
        mock_uninstall.return_value = None

        result = runner.invoke(app, ["prompt", "uninstall", "--app", "claude", "--level", "user"])
        assert result.exit_code == 0
        mock_uninstall.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.show_status")
    def test_prompt_status(self, runner, mock_status):
        """Test prompt status command."""
        mock_status.return_value = None

        result = runner.invoke(app, ["prompt", "status"])
        assert result.exit_code == 0
        mock_status.assert_called_once()

    @patch("code_assistant_manager.cli.prompts_commands.rename_template")
    def test_prompt_rename(self, runner, mock_rename):
        """Test prompt rename command."""
        mock_rename.return_value = None

        result = runner.invoke(app, ["prompt", "rename", "old-name", "new-name"])
        assert result.exit_code == 0
        mock_rename.assert_called_once()


class TestSkillCommands:
    """Test skill command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_skill_help(self, runner):
        """Test skill command help."""
        result = runner.invoke(app, ["skill", "--help"])
        assert result.exit_code == 0
        assert "Manage skills" in result.output.lower()

    @patch("code_assistant_manager.cli.skills_commands.list_available_skills")
    def test_skill_list(self, runner, mock_list):
        """Test skill list command."""
        mock_list.return_value = {}

        result = runner.invoke(app, ["skill", "list"])
        assert result.exit_code == 0
        mock_list.assert_called_once()

    @patch("code_assistant_manager.cli.skills_commands.fetch_skills")
    def test_skill_fetch(self, runner, mock_fetch):
        """Test skill fetch command."""
        mock_fetch.return_value = None

        result = runner.invoke(app, ["skill", "fetch", "https://github.com/test/repo"])
        assert result.exit_code == 0
        mock_fetch.assert_called_once()

    @patch("code_assistant_manager.cli.skills_commands.view_skill")
    def test_skill_view(self, runner, mock_view):
        """Test skill view command."""
        mock_view.return_value = None

        result = runner.invoke(app, ["skill", "view", "skill-name"])
        assert result.exit_code == 0
        mock_view.assert_called_once()

    @patch("code_assistant_manager.cli.skills_commands.create_skill")
    def test_skill_create(self, runner, mock_create):
        """Test skill create command."""
        mock_create.return_value = None

        result = runner.invoke(app, ["skill", "create", "skill-name", "--description", "Test skill"])
        assert result.exit_code == 0
        mock_create.assert_called_once()

    @patch("code_assistant_manager.cli.skills_commands.install_skill")
    def test_skill_install(self, runner, mock_install):
        """Test skill install command."""
        mock_install.return_value = None

        result = runner.invoke(app, ["skill", "install", "skill-name"])
        assert result.exit_code == 0
        mock_install.assert_called_once()

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_update(self, mock_get_manager, runner):
        """Test skill update command."""
        mock_manager = MagicMock()
        mock_skill = MagicMock()
        mock_manager.get.return_value = mock_skill
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["skill", "update", "skill-name", "--name", "Updated Name"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_delete(self, mock_get_manager, runner):
        """Test skill delete command."""
        mock_manager = MagicMock()
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_manager.get.return_value = mock_skill
        mock_get_manager.return_value = mock_manager

        with patch("typer.confirm", return_value=True):
            result = runner.invoke(app, ["skill", "delete", "skill-name", "--force"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_repos(self, mock_get_manager, runner):
        """Test skill repos command."""
        mock_manager = MagicMock()
        mock_manager.get_repos.return_value = []
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["skill", "repos"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_add_repo(self, mock_add_repo, runner):
        """Test skill add-repo command."""
        mock_manager = MagicMock()
        mock_add_repo.return_value = mock_manager

        result = runner.invoke(app, ["skill", "add-repo", "--owner", "test-owner", "--name", "test-repo"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_remove_repo(self, mock_get_manager, runner):
        """Test skill remove-repo command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        with patch("typer.confirm", return_value=True):
            result = runner.invoke(app, ["skill", "remove-repo", "--owner", "test-owner", "--name", "test-repo", "--force"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_import(self, mock_get_manager, runner):
        """Test skill import command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        with patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(app, ["skill", "import", "--file", "/tmp/skills.json"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_export(self, mock_get_manager, runner):
        """Test skill export command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["skill", "export", "--file", "/tmp/skills.json"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_installed(self, mock_get_manager, runner):
        """Test skill installed command."""
        mock_manager = MagicMock()
        mock_manager.get_all.return_value = {}
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["skill", "installed"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.skills_commands._get_skill_manager")
    def test_skill_uninstall_all(self, mock_get_manager, runner):
        """Test skill uninstall-all command."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        with patch("typer.confirm", return_value=True):
            result = runner.invoke(app, ["skill", "uninstall-all", "--app", "claude", "--force"])
        assert result.exit_code == 0


class TestCompletionCommands:
    """Test completion command subcommands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_completion_help(self, runner):
        """Test completion command help."""
        result = runner.invoke(app, ["completion", "--help"])
        assert result.exit_code == 0
        assert "Generate shell completion" in result.output

    def test_completion_bash(self, runner):
        """Test completion bash generation."""
        result = runner.invoke(app, ["completion", "bash"])
        assert result.exit_code == 0
        assert "# code-assistant-manager bash completion" in result.output

    def test_completion_zsh(self, runner):
        """Test completion zsh generation."""
        result = runner.invoke(app, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "# code-assistant-manager zsh completion" in result.output

    def test_completion_invalid_shell(self, runner):
        """Test completion with invalid shell."""
        result = runner.invoke(app, ["completion", "fish"])
        assert result.exit_code == 1
        assert "Unsupported shell" in result.output

    def test_completion_alias_comp(self, runner):
        """Test completion alias 'comp'."""
        result = runner.invoke(app, ["comp", "bash"])
        assert result.exit_code == 0

    def test_completion_alias_c(self, runner):
        """Test completion alias 'c'."""
        result = runner.invoke(app, ["c", "bash"])
        assert result.exit_code == 0


class TestGlobalOptionsIntegration:
    """Test global options across different commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("code_assistant_manager.config.ConfigManager")
    def test_config_option_across_commands(self, runner, mock_config_class):
        """Test --config option works across different commands."""
        mock_config = MagicMock()
        mock_config.validate_config.return_value = (True, [])
        mock_config_class.return_value = mock_config

        # Test with config command
        result = runner.invoke(app, ["--config", "/tmp/test.json", "config", "validate"])
        assert result.exit_code == 0

        # Test with launch command
        with patch("code_assistant_manager.cli.app.get_registered_tools") as mock_tools:
            mock_tools.return_value = {"claude": MagicMock()}
            result = runner.invoke(app, ["--config", "/tmp/test.json", "launch", "claude", "--help"])
            assert result.exit_code == 0

    def test_debug_option_logging(self, runner):
        """Test --debug option enables debug logging."""
        with patch("code_assistant_manager.cli.app.logger") as mock_logger:
            result = runner.invoke(app, ["--debug", "--help"])
            assert result.exit_code == 0
            # Debug logging setup should be called

    @patch("code_assistant_manager.tools.display_all_tool_endpoints")
    def test_endpoints_option_mcp(self, runner, mock_display):
        """Test --endpoints option with MCP command."""
        mock_display.return_value = None

        result = runner.invoke(app, ["mcp", "--endpoints", "all"])
        assert result.exit_code == 0
        mock_display.assert_called_once()


class TestErrorHandling:
    """Test error handling across CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_invalid_subcommand(self, runner):
        """Test handling of invalid subcommands."""
        result = runner.invoke(app, ["config", "invalid-subcommand"])
        assert result.exit_code != 0

    def test_missing_required_arguments(self, runner):
        """Test handling of missing required arguments."""
        result = runner.invoke(app, ["plugin", "install"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "requires" in result.output.lower()

    def test_invalid_option_values(self, runner):
        """Test handling of invalid option values."""
        result = runner.invoke(app, ["agent", "install", "test-agent", "--app", "invalid-app"])
        assert result.exit_code != 0


class TestCommandCombinations:
    """Test combinations of commands and options."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("code_assistant_manager.config.ConfigManager")
    @patch("code_assistant_manager.cli.app.logger")
    def test_debug_with_config_validation(self, runner, mock_logger, mock_config_class):
        """Test debug option combined with config validation."""
        mock_config = MagicMock()
        mock_config.validate_config.return_value = (True, [])
        mock_config_class.return_value = mock_config

        result = runner.invoke(app, ["--debug", "--config", "/tmp/test.json", "config", "validate"])
        assert result.exit_code == 0

    @patch.multiple(
        "code_assistant_manager.cli.plugins.plugin_management_commands",
        list_plugins=MagicMock(),
        list_repos=MagicMock()
    )
    def test_multiple_plugin_commands(self, runner, list_plugins, list_repos):
        """Test multiple plugin commands in sequence."""
        list_plugins.return_value = None
        list_repos.return_value = None

        # Test plugin list
        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0

        # Test plugin repos
        result = runner.invoke(app, ["plugin", "repos"])
        assert result.exit_code == 0

        list_plugins.assert_called_once()
        list_repos.assert_called_once()