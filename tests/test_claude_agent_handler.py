"""Unit tests for Claude agent handler."""

import pytest
from unittest.mock import patch, MagicMock

from code_assistant_manager.agents.claude import ClaudeAgentHandler


class TestClaudeAgentHandler:
    """Test Claude agent handler functionality."""

    @pytest.fixture
    def handler(self):
        """Create Claude agent handler instance."""
        return ClaudeAgentHandler()

    def test_app_name_property(self, handler):
        """Test app name property."""
        assert handler.app_name == "claude"

    def test_default_home_dir(self, handler):
        """Test default home directory."""
        home_dir = handler._default_home_dir
        assert str(home_dir).endswith(".claude")

    def test_default_settings_file(self, handler):
        """Test default settings file."""
        settings_file = handler._default_settings_file
        assert str(settings_file).endswith("settings.json")

    @patch("code_assistant_manager.agents.claude.subprocess.run")
    def test_run_claude_command_success(self, mock_run, handler):
        """Test running Claude command successfully."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success output"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code, stdout, stderr = handler._run_claude_command("test", "command")

        assert code == 0
        assert stdout == "Success output"
        assert stderr == ""
        mock_run.assert_called_once()

    @patch("code_assistant_manager.agents.claude.subprocess.run")
    def test_run_claude_command_failure(self, mock_run, handler):
        """Test running Claude command with failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Error message"
        mock_run.return_value = mock_process

        code, stdout, stderr = handler._run_claude_command("failing", "command")

        assert code == 1
        assert stdout == ""
        assert stderr == "Error message"

    @patch("code_assistant_manager.agents.claude.subprocess.run")
    def test_run_claude_command_timeout(self, mock_run, handler):
        """Test running Claude command with timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("claude", 30)

        code, stdout, stderr = handler._run_claude_command("timeout", "command")

        assert code == -1
        assert stdout == ""
        assert stderr == "Command timed out"

    @patch("code_assistant_manager.agents.claude.subprocess.run")
    def test_run_claude_command_not_found(self, mock_run, handler):
        """Test running Claude command when not found."""
        from subprocess import FileNotFoundError
        mock_run.side_effect = FileNotFoundError("claude command not found")

        code, stdout, stderr = handler._run_claude_command("missing", "command")

        assert code == -1
        assert stdout == ""
        assert "not found" in stderr

    @patch("code_assistant_manager.agents.claude.logger")
    def test_get_enabled_agents_empty_settings(self, mock_logger, handler):
        """Test getting enabled agents when settings file doesn't exist."""
        with patch.object(handler, 'settings_file', None):
            result = handler.get_enabled_agents()
            assert result == {}

    @patch("code_assistant_manager.agents.claude.Path")
    @patch("code_assistant_manager.agents.claude.json")
    def test_get_enabled_agents_with_settings(self, mock_json, mock_path, handler):
        """Test getting enabled agents from settings file."""
        mock_settings_file = MagicMock()
        mock_settings_file.exists.return_value = True

        with patch.object(handler, 'settings_file', mock_settings_file):
            mock_json.load.return_value = {
                "enabledAgents": {
                    "agent1": True,
                    "agent2": False
                }
            }

            result = handler.get_enabled_agents()
            assert result == {"agent1": True, "agent2": False}

    @patch("code_assistant_manager.agents.claude.Path")
    def test_get_enabled_agents_corrupted_settings(self, mock_path, handler):
        """Test getting enabled agents with corrupted settings file."""
        mock_settings_file = MagicMock()
        mock_settings_file.exists.return_value = True

        with patch.object(handler, 'settings_file', mock_settings_file):
            with patch("code_assistant_manager.agents.claude.json.load", side_effect=Exception("Corrupted JSON")):
                result = handler.get_enabled_agents()
                assert result == {}


class TestClaudeAgentOperations:
    """Test Claude agent operations."""

    @pytest.fixture
    def handler(self):
        """Create Claude agent handler instance."""
        return ClaudeAgentHandler()

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_install_agent_success(self, mock_run, handler):
        """Test successful agent installation."""
        mock_run.return_value = (0, "Agent installed successfully", "")

        result = handler.install_agent("test-agent")

        assert result == (True, "Agent installed successfully")
        mock_run.assert_called_once_with("agent", "install", "test-agent")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_install_agent_failure(self, mock_run, handler):
        """Test failed agent installation."""
        mock_run.return_value = (1, "", "Installation failed")

        result = handler.install_agent("failing-agent")

        assert result == (False, "Installation failed")
        mock_run.assert_called_once_with("agent", "install", "failing-agent")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_uninstall_agent_success(self, mock_run, handler):
        """Test successful agent uninstallation."""
        mock_run.return_value = (0, "Agent uninstalled", "")

        result = handler.uninstall_agent("test-agent")

        assert result == (True, "Agent uninstalled")
        mock_run.assert_called_once_with("agent", "uninstall", "test-agent")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_list_agents_success(self, mock_run, handler):
        """Test successful agent listing."""
        mock_run.return_value = (0, "agent1\nagent2", "")

        result = handler.list_agents()

        assert result == (True, "agent1\nagent2")
        mock_run.assert_called_once_with("agent", "list")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_get_agent_info_success(self, mock_run, handler):
        """Test getting agent information."""
        mock_run.return_value = (0, "Agent info", "")

        result = handler.get_agent_info("test-agent")

        assert result == (True, "Agent info")
        mock_run.assert_called_once_with("agent", "info", "test-agent")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_enable_agent_success(self, mock_run, handler):
        """Test enabling agent."""
        mock_run.return_value = (0, "Agent enabled", "")

        result = handler.enable_agent("test-agent")

        assert result == (True, "Agent enabled")
        mock_run.assert_called_once_with("agent", "enable", "test-agent")

    @patch("code_assistant_manager.agents.claude.ClaudeAgentHandler._run_claude_command")
    def test_disable_agent_success(self, mock_run, handler):
        """Test disabling agent."""
        mock_run.return_value = (0, "Agent disabled", "")

        result = handler.disable_agent("test-agent")

        assert result == (True, "Agent disabled")
        mock_run.assert_called_once_with("agent", "disable", "test-agent")