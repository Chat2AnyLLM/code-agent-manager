"""Unit tests for CLI app commands and interfaces."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from code_assistant_manager.cli.app import app


class TestCLIAppCommands:
    """Test main CLI application commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_app_help_command(self, runner):
        """Test that app help command works."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_app_version_command(self, runner):
        """Test that version command works."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_app_invalid_command(self, runner):
        """Test handling of invalid commands."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output or "unrecognized" in result.output.lower()

    def test_app_subcommands_available(self, runner):
        """Test that main subcommands are available."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Check for main subcommands
        expected_commands = ["launch", "config", "plugin", "agent", "mcp", "prompt", "skill"]
        for cmd in expected_commands:
            assert cmd in result.output

    @patch("code_assistant_manager.cli.app.get_available_tools")
    def test_launch_command_help(self, runner, mock_get_tools):
        """Test launch command help."""
        mock_get_tools.return_value = {}
        result = runner.invoke(app, ["launch", "--help"])
        assert result.exit_code == 0
        assert "launch" in result.output.lower()

    @patch("code_assistant_manager.config.validate_config")
    def test_config_command_help(self, runner, mock_validate):
        """Test config command help."""
        mock_validate.return_value = (True, "Valid")
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()

    @patch("code_assistant_manager.cli.plugins.plugin_discovery_commands.browse_marketplace")
    def test_plugin_command_help(self, runner, mock_browse):
        """Test plugin command help."""
        mock_browse.return_value = []
        result = runner.invoke(app, ["plugin", "--help"])
        assert result.exit_code == 0
        assert "plugin" in result.output.lower()

    @patch("code_assistant_manager.cli.agents_commands.list_agents")
    def test_agent_command_help(self, runner, mock_list):
        """Test agent command help."""
        mock_list.return_value = []
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.output.lower()

    @patch("code_assistant_manager.cli.mcp.server_commands.list_servers")
    def test_mcp_command_help(self, runner, mock_list):
        """Test MCP command help."""
        mock_list.return_value = []
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "mcp" in result.output.lower()

    @patch("code_assistant_manager.cli.prompts_commands.list_templates")
    def test_prompt_command_help(self, runner, mock_list):
        """Test prompt command help."""
        mock_list.return_value = {}
        result = runner.invoke(app, ["prompt", "--help"])
        assert result.exit_code == 0
        assert "prompt" in result.output.lower()

    @patch("code_assistant_manager.cli.skills_commands.list_available_skills")
    def test_skill_command_help(self, runner, mock_list):
        """Test skill command help."""
        mock_list.return_value = {}
        result = runner.invoke(app, ["skill", "--help"])
        assert result.exit_code == 0
        assert "skill" in result.output.lower()


class TestCLIGlobalOptions:
    """Test global CLI options."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("code_assistant_manager.cli.app.logger")
    def test_debug_option(self, runner, mock_logger):
        """Test debug option sets logging level."""
        with patch("code_assistant_manager.config.validate_config") as mock_validate:
            mock_validate.return_value = (True, "Valid")

            result = runner.invoke(app, ["--debug", "config", "validate"])
            assert result.exit_code == 0
            # Debug option should be processed (exact behavior may vary)

    @patch("code_assistant_manager.cli.app.get_config_path")
    def test_config_option(self, runner, mock_config):
        """Test custom config path option."""
        mock_config.return_value = "/tmp/test-config.json"

        with patch("code_assistant_manager.config.validate_config") as mock_validate:
            mock_validate.return_value = (True, "Valid")

            result = runner.invoke(app, ["--config", "/tmp/test-config.json", "config", "validate"])
            assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_command_without_required_args(self, runner):
        """Test commands that require arguments."""
        result = runner.invoke(app, ["launch"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "requires" in result.output.lower()

    def test_invalid_app_type(self, runner):
        """Test invalid app type handling."""
        result = runner.invoke(app, ["--app", "invalid-app", "config", "validate"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "not supported" in result.output.lower()

    @patch("code_assistant_manager.cli.app.resolve_single_app")
    def test_app_resolution_failure(self, runner, mock_resolve):
        """Test app resolution failure."""
        mock_resolve.side_effect = ValueError("Unknown app type")

        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code != 0


class TestCLISubcommandIntegration:
    """Test integration between CLI subcommands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("code_assistant_manager.config.validate_config")
    @patch("code_assistant_manager.config.get_config")
    def test_config_workflow(self, runner, mock_get, mock_validate):
        """Test config command workflow."""
        mock_validate.return_value = (True, "Valid")
        mock_get.return_value = {"api_key": "test-key"}

        # Test validate
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0

        # Test show
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0

        # Test list locations
        result = runner.invoke(app, ["config", "list-locations"])
        assert result.exit_code == 0

    @patch("code_assistant_manager.cli.plugins.plugin_discovery_commands.browse_marketplace")
    @patch("code_assistant_manager.cli.plugins.plugin_install_commands.install_plugin")
    def test_plugin_workflow(self, runner, mock_install, mock_browse):
        """Test plugin command workflow."""
        mock_browse.return_value = [{"name": "test-plugin", "description": "Test"}]
        mock_install.return_value = None

        # Test browse
        result = runner.invoke(app, ["plugin", "browse"])
        assert result.exit_code == 0

        # Test list
        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0