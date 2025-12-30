"""Unit tests for extension CLI commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from code_assistant_manager.cli.app import app


class TestExtensionCommands:
    """Test extension CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_extensions_browse_command_help(self, runner):
        """Test extensions browse command help."""
        result = runner.invoke(app, ["extensions", "browse", "--help"])
        assert result.exit_code == 0
        assert "browse" in result.output.lower()

    def test_extensions_install_command_help(self, runner):
        """Test extensions install command help."""
        result = runner.invoke(app, ["extensions", "install", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output.lower()

    def test_extensions_uninstall_command_help(self, runner):
        """Test extensions uninstall command help."""
        result = runner.invoke(app, ["extensions", "uninstall", "--help"])
        assert result.exit_code == 0
        assert "uninstall" in result.output.lower()

    def test_extensions_list_command_help(self, runner):
        """Test extensions list command help."""
        result = runner.invoke(app, ["extensions", "list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower()

    def test_extensions_update_command_help(self, runner):
        """Test extensions update command help."""
        result = runner.invoke(app, ["extensions", "update", "--help"])
        assert result.exit_code == 0
        assert "update" in result.output.lower()

    def test_extensions_disable_command_help(self, runner):
        """Test extensions disable command help."""
        result = runner.invoke(app, ["extensions", "disable", "--help"])
        assert result.exit_code == 0
        assert "disable" in result.output.lower()

    def test_extensions_enable_command_help(self, runner):
        """Test extensions enable command help."""
        result = runner.invoke(app, ["extensions", "enable", "--help"])
        assert result.exit_code == 0
        assert "enable" in result.output.lower()

    def test_extensions_link_command_help(self, runner):
        """Test extensions link command help."""
        result = runner.invoke(app, ["extensions", "link", "--help"])
        assert result.exit_code == 0
        assert "link" in result.output.lower()

    def test_extensions_new_command_help(self, runner):
        """Test extensions new command help."""
        result = runner.invoke(app, ["extensions", "new", "--help"])
        assert result.exit_code == 0
        assert "new" in result.output.lower()

    def test_extensions_validate_command_help(self, runner):
        """Test extensions validate command help."""
        result = runner.invoke(app, ["extensions", "validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output.lower()

    def test_extensions_settings_command_help(self, runner):
        """Test extensions settings command help."""
        result = runner.invoke(app, ["extensions", "settings", "--help"])
        assert result.exit_code == 0
        assert "settings" in result.output.lower()

    @patch('code_assistant_manager.tools.gemini.GeminiTool')
    def test_extensions_list_command_calls_gemini_tool(self, mock_gemini_tool_class, runner):
        """Test that extensions list command calls GeminiTool with correct args."""
        mock_tool_instance = MagicMock()
        mock_gemini_tool_class.return_value = mock_tool_instance
        mock_tool_instance.run.return_value = 0

        result = runner.invoke(app, ["extensions", "list"])

        assert result.exit_code == 0
        mock_gemini_tool_class.assert_called_once()
        mock_tool_instance.run.assert_called_once_with(["extensions", "list"])

    @patch('code_assistant_manager.tools.gemini.GeminiTool')
    def test_extensions_install_command_calls_gemini_tool(self, mock_gemini_tool_class, runner):
        """Test that extensions install command calls GeminiTool with correct args."""
        mock_tool_instance = MagicMock()
        mock_gemini_tool_class.return_value = mock_tool_instance
        mock_tool_instance.run.return_value = 0

        result = runner.invoke(app, ["extensions", "install", "test-extension"])

        assert result.exit_code == 0
        mock_gemini_tool_class.assert_called_once()
        mock_tool_instance.run.assert_called_once_with(["extensions", "install", "test-extension"])

    @patch('code_assistant_manager.tools.gemini.GeminiTool')
    def test_extensions_uninstall_command_calls_gemini_tool(self, mock_gemini_tool_class, runner):
        """Test that extensions uninstall command calls GeminiTool with correct args."""
        mock_tool_instance = MagicMock()
        mock_gemini_tool_class.return_value = mock_tool_instance
        mock_tool_instance.run.return_value = 0

        result = runner.invoke(app, ["extensions", "uninstall", "test-extension"])

        assert result.exit_code == 0
        mock_gemini_tool_class.assert_called_once()
        mock_tool_instance.run.assert_called_once_with(["extensions", "uninstall", "test-extension"])