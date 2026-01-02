"""Tests for launching all enabled tools via 'cam launch + tool-name' command.

This test module verifies that the launch command can successfully launch all
enabled tools defined in tools.yaml. Each test mocks the tool's run method
to ensure the command execution path works correctly without actually
launching external tools.
"""

import pytest
from unittest.mock import patch

from code_assistant_manager.cli import app, main
from typer.testing import CliRunner


class TestLaunchAllTools:
    """Test launching all enabled tools via 'cam launch + tool-name'."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config file for testing."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "config"}')
        return str(config_file)

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_launch_claude_tool(self, mock_run, temp_config):
        """Test launching Claude tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CodexTool.run", return_value=0)
    def test_launch_codex_tool(self, mock_run, temp_config):
        """Test launching Codex tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.GeminiTool.run", return_value=0)
    def test_launch_gemini_tool(self, mock_run, temp_config):
        """Test launching Gemini tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "gemini", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.QwenTool.run", return_value=0)
    def test_launch_qwen_tool(self, mock_run, temp_config):
        """Test launching Qwen tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CopilotTool.run", return_value=0)
    def test_launch_copilot_tool(self, mock_run, temp_config):
        """Test launching GitHub Copilot tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "copilot", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CodeBuddyTool.run", return_value=0)
    def test_launch_codebuddy_tool(self, mock_run, temp_config):
        """Test launching CodeBuddy tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "codebuddy", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.DroidTool.run", return_value=0)
    def test_launch_droid_tool(self, mock_run, temp_config):
        """Test launching Factory.ai Droid tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "droid", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.IfLowTool.run", return_value=0)
    def test_launch_iflow_tool(self, mock_run, temp_config):
        """Test launching iFlow tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "iflow", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CrushTool.run", return_value=0)
    def test_launch_crush_tool(self, mock_run, temp_config):
        """Test launching Charmland Crush tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "crush", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CursorTool.run", return_value=0)
    def test_launch_cursor_agent_tool(self, mock_run, temp_config):
        """Test launching Cursor Agent tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "cursor-agent", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.OpenCodeTool.run", return_value=0)
    def test_launch_opencode_tool(self, mock_run, temp_config):
        """Test launching OpenCode.ai tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "opencode", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    # @patch("code_assistant_manager.tools.ContinueTool.run", return_value=0)
    # def test_launch_continue_tool(self, mock_run, temp_config):
    #     """Test launching Continue.dev tool."""
    #     with patch(
    #         "sys.argv",
    #         ["code-assistant-manager", "launch", "cn", "--config", temp_config],
    #     ):
    #         with pytest.raises(SystemExit) as exc_info:
    #             main()
    #         assert exc_info.value.code == 0
    #         mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.GooseTool.run", return_value=0)
    def test_launch_goose_tool(self, mock_run, temp_config):
        """Test launching Block Goose tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "goose", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.BlackboxTool.run", return_value=0)
    def test_launch_blackbox_tool(self, mock_run, temp_config):
        """Test launching Blackbox AI tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "blackbox", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    def test_launch_invalid_tool(self):
        """Test launching non-existent tool fails."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "nonexistent_tool"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Should exit with error code for unknown command
            assert exc_info.value.code == 2

    def test_launch_disabled_tool_zed(self):
        """Test that disabled tool 'zed' cannot be launched."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "zed"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Should exit with error code for unknown/disabled command
            assert exc_info.value.code == 1

    def test_launch_disabled_tool_qodercli(self):
        """Test that disabled tool 'qodercli' cannot be launched."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "qodercli"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Should exit with error code for unknown/disabled command
            assert exc_info.value.code == 1

    def test_launch_disabled_tool_neovate(self):
        """Test that disabled tool 'neovate' cannot be launched."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "neovate"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Should exit with error code for unknown/disabled command
            assert exc_info.value.code == 1

    def test_launch_with_arguments(self, temp_config):
        """Test launching tool with additional arguments."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "claude",
                "--config",
                temp_config,
                "--help",
            ],
        ):
            with patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_launch_alias_l_works(self, temp_config):
        """Test that launch alias 'l' works the same as 'launch'."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "claude", "--config", temp_config],
        ):
            with patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0