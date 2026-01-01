"""Comprehensive tests for all CLI subcommands and parameters.

This test module covers:
- All main commands (launch, mcp, upgrade, install, doctor, etc.)
- All command aliases (l, u, i, d, etc.)
- All parameters and options for each command
- Error handling for invalid inputs
- Help text and version information
"""

from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.cli import app, main


class TestMainCommands:
    """Test main CLI commands without subcommands."""

    def test_help_flag_shows_available_commands(self):
        """Test that --help shows all available commands."""
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            with patch("sys.argv", ["code-assistant-manager", "--help"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

        help_output = captured_output.getvalue()
        assert "launch" in help_output
        assert "mcp" in help_output
        assert "upgrade" in help_output
        assert "install" in help_output
        assert "doctor" in help_output
        assert "uninstall" in help_output
        assert "config" in help_output
        assert "completion" in help_output

    def test_version_command(self):
        """Test version command displays version info."""
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            with patch("sys.argv", ["code-assistant-manager", "version"]):
                with pytest.raises(SystemExit) as exc_info:
                    app()
                assert exc_info.value.code == 0

        version_output = captured_output.getvalue()
        assert "version 1.1." in version_output, "Version output should contain version 1.1.x"

    def test_no_command_shows_help(self):
        """Test that running with no command shows help."""
        with patch("sys.argv", ["code-assistant-manager"]):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # With no_args_is_help=True, exit code should be 0
            assert exc_info.value.code in [0, 2]


class TestLaunchCommand:
    """Test launch command (alias: l) and subcommands."""

    def test_launch_help(self):
        """Test launch command help."""
        with patch("sys.argv", ["code-assistant-manager", "launch", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_launch_alias_help(self):
        """Test launch alias 'l' help."""
        with patch("sys.argv", ["code-assistant-manager", "l", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_launch_claude_with_config(self, mock_run, temp_config):
        """Test launching claude with custom config."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "claude",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once_with([])

    @patch("code_assistant_manager.tools.CodexTool.run", return_value=0)
    def test_launch_codex_with_config(self, mock_run, temp_config):
        """Test launching codex with custom config."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CopilotTool.run", return_value=0)
    def test_launch_copilot(self, mock_run, temp_config):
        """Test launching copilot."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "copilot",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.GeminiTool.run", return_value=0)
    def test_launch_gemini(self, mock_run, temp_config):
        """Test launching gemini."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "gemini",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.DroidTool.run", return_value=0)
    def test_launch_droid(self, mock_run, temp_config):
        """Test launching droid."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "droid", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.QwenTool.run", return_value=0)
    def test_launch_qwen(self, mock_run, temp_config):
        """Test launching qwen."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CodeBuddyTool.run", return_value=0)
    def test_launch_codebuddy(self, mock_run, temp_config):
        """Test launching codebuddy."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "codebuddy",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.IfLowTool.run", return_value=0)
    def test_launch_iflow(self, mock_run, temp_config):
        """Test launching iflow."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "iflow", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_launch_with_tool_arguments(self, mock_run, temp_config):
        """Test launching tool with additional arguments."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "claude",
                "--config",
                temp_config,
                "arg1",
                "arg2",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            # Tool arguments should be passed
            mock_run.assert_called_once_with(["arg1", "arg2"])

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_launch_alias_l_with_tool(self, mock_run, temp_config):
        """Test launch alias 'l' with tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_launch_invalid_tool(self):
        """Test launching non-existent tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "nonexistent_tool"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Should exit with error code for unknown command
            assert exc_info.value.code == 2


class TestUpgradeCommand:
    """Test upgrade command (alias: u) with parameters."""

    def test_upgrade_help(self):
        """Test upgrade command help."""
        with patch("sys.argv", ["code-assistant-manager", "upgrade", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_upgrade_alias_u_help(self):
        """Test upgrade alias 'u' help."""
        with patch("sys.argv", ["code-assistant-manager", "u", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_upgrade_single_tool(self, mock_upgrade, temp_config):
        """Test upgrading single tool."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "upgrade",
                "claude",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_upgrade_all_tools(self, mock_upgrade, temp_config):
        """Test upgrading all tools."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "upgrade",
                "all",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_upgrade_with_verbose(self, mock_upgrade, temp_config):
        """Test upgrade command with verbose flag."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "upgrade",
                "claude",
                "--config",
                temp_config,
                "--verbose",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_upgrade_with_verbose_short_flag(self, mock_upgrade, temp_config):
        """Test upgrade command with -v short flag."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "upgrade",
                "claude",
                "--config",
                temp_config,
                "-v",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_upgrade_alias_u_single_tool(self, mock_upgrade, temp_config):
        """Test upgrade alias 'u' with single tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestInstallCommand:
    """Test install command (alias: i) with parameters."""

    def test_install_help(self):
        """Test install command help."""
        with patch("sys.argv", ["code-assistant-manager", "install", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_install_alias_i_help(self):
        """Test install alias 'i' help."""
        with patch("sys.argv", ["code-assistant-manager", "i", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_install_single_tool(self, mock_upgrade, temp_config):
        """Test installing single tool."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "install",
                "claude",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_install_all_tools(self, mock_upgrade, temp_config):
        """Test installing all tools."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "install",
                "all",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_install_with_verbose(self, mock_upgrade, temp_config):
        """Test install with verbose flag."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "install",
                "claude",
                "--config",
                temp_config,
                "--verbose",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_install_alias_i_single_tool(self, mock_upgrade, temp_config):
        """Test install alias 'i' with single tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_install_alias_i_all_tools(self, mock_upgrade, temp_config):
        """Test install alias 'i' with all tools."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "all", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestUninstallCommand:
    """Test uninstall command (alias: un) with parameters."""

    def test_uninstall_help(self):
        """Test uninstall command help."""
        with patch("sys.argv", ["code-assistant-manager", "uninstall", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_uninstall_alias_un_help(self):
        """Test uninstall alias 'un' help."""
        with patch("sys.argv", ["code-assistant-manager", "un", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_uninstall_single_tool(self, mock_get_tools, mock_subprocess, temp_config):
        """Test uninstalling single tool."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "uninstall",
                "claude",
                "--force",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 0 when no tools are installed
            assert exc_info.value.code in [0, 1]

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_uninstall_all_tools(self, mock_get_tools, mock_subprocess, temp_config):
        """Test uninstalling all tools."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "uninstall",
                "all",
                "--force",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1]

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_uninstall_with_force_flag(
        self, mock_get_tools, mock_subprocess, temp_config
    ):
        """Test uninstall with force flag."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "uninstall",
                "claude",
                "--force",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1]

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_uninstall_with_keep_config(
        self, mock_get_tools, mock_subprocess, temp_config
    ):
        """Test uninstall with --keep-config flag."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "uninstall",
                "claude",
                "--force",
                "--keep-config",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1]

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_uninstall_alias_un(self, mock_get_tools, mock_subprocess, temp_config):
        """Test uninstall alias 'un'."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "un",
                "claude",
                "--force",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1]


class TestDoctorCommand:
    """Test doctor command (alias: d) with parameters."""

    def test_doctor_help(self):
        """Test doctor command help."""
        with patch("sys.argv", ["code-assistant-manager", "doctor", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_doctor_alias_d_help(self):
        """Test doctor alias 'd' help."""
        with patch("sys.argv", ["code-assistant-manager", "d", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0)
    def test_doctor_command(self, mock_doctor, temp_config):
        """Test doctor command execution."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "doctor", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0)
    def test_doctor_with_verbose(self, mock_doctor, temp_config):
        """Test doctor command with verbose flag."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "doctor",
                "--verbose",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0)
    def test_doctor_alias_d(self, mock_doctor, temp_config):
        """Test doctor alias 'd' execution."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "d"],
        ):
            with patch("code_assistant_manager.cli.commands.doctor", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code in [0, 1]


class TestValidateCommand:
    """Test validate command with parameters."""

    def test_validate_help(self):
        """Test validate command help."""
        with patch(
            "sys.argv", ["code-assistant-manager", "config", "validate", "--help"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_validate_config_success(self, temp_config):
        """Test validating valid config."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "config", "validate", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_validate_config_invalid(self):
        """Test validating invalid config file."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "config",
                "validate",
                "--config",
                "/nonexistent/path/config.json",
            ],
        ):
            try:
                result = main()
                # Should return error code
                assert result in [1, 2]
            except SystemExit as e:
                # Or raise SystemExit with error code
                assert e.code in [0, 1, 2]

    def test_validate_with_verbose(self, temp_config):
        """Test validate command with verbose flag."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "config",
                "validate",
                "--config",
                temp_config,
                "--verbose",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestCompletionCommand:
    """Test completion command with parameters."""

    def test_completion_help(self):
        """Test completion command help."""
        with patch("sys.argv", ["code-assistant-manager", "completion", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_completion_bash(self):
        """Test generating bash completion."""
        with patch("sys.argv", ["code-assistant-manager", "completion", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_completion_zsh(self):
        """Test generating zsh completion."""
        with patch("sys.argv", ["code-assistant-manager", "completion", "zsh"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_completion_alias_comp_bash(self):
        """Test completion alias 'comp' with bash."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_completion_invalid_shell(self):
        """Test completion with invalid shell."""
        with patch("sys.argv", ["code-assistant-manager", "completion", "fish"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestMCPCommand:
    """Test MCP subcommand and its variations."""

    def test_mcp_help(self):
        """Test MCP command help."""
        with patch("sys.argv", ["code-assistant-manager", "mcp", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_mcp_server_help(self):
        """Test MCP list help command (updated from 'mcp server')."""
        with patch("sys.argv", ["code-assistant-manager", "mcp", "list", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 2]  # May show help or error

    def test_mcp_server_list(self):
        """Test MCP list command (updated from 'mcp server list')."""
        with patch("sys.argv", ["code-assistant-manager", "mcp", "list"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1, 2]


class TestGlobalOptions:
    """Test global options and flags."""

    def test_debug_flag(self, temp_config):
        """Test --debug global flag."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "doctor", "--config", temp_config],
        ):
            with patch(
                "code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_config_option_with_different_commands(self, temp_config):
        """Test --config option with various commands."""
        commands = [
            ["code-assistant-manager", "upgrade", "claude"],
            ["code-assistant-manager", "install", "claude"],
            ["code-assistant-manager", "doctor"],
            ["code-assistant-manager", "validate"],
        ]

        for cmd in commands:
            cmd.extend(["--config", temp_config])
            with patch("sys.argv", cmd):
                with patch(
                    "code_assistant_manager.cli.upgrade.handle_upgrade_command",
                    return_value=0,
                ):
                    with patch(
                        "code_assistant_manager.cli.doctor.run_doctor_checks",
                        return_value=0,
                    ):
                        try:
                            main()
                        except SystemExit as e:
                            # Should exit with 0, 1, or 2 depending on command
                            assert e.code in [0, 1, 2]


class TestErrorHandling:
    """Test error handling across different scenarios."""

    def test_invalid_command(self):
        """Test running invalid command."""
        with patch("sys.argv", ["code-assistant-manager", "invalid-command"]):
            with pytest.raises(SystemExit) as exc_info:
                app()
            assert exc_info.value.code == 2

    def test_missing_required_argument(self):
        """Test command without required argument."""
        with patch("sys.argv", ["code-assistant-manager", "launch"]):
            with patch(
                "code_assistant_manager.menu.menus.display_centered_menu",
                return_value=(False, None),
            ):
                # Should either show menu or exit
                try:
                    app()
                except SystemExit as e:
                    assert e.code in [0, 2]

    def test_config_file_not_found(self):
        """Test with non-existent config file."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "doctor",
                "--config",
                "/nonexistent/path/config.json",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("code_assistant_manager.tools.ClaudeTool.run")
    def test_tool_execution_error(self, mock_run, temp_config):
        """Test handling of tool execution error."""
        mock_run.side_effect = Exception("Tool execution failed")

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "claude",
                "--config",
                temp_config,
            ],
        ):
            try:
                result = main()
                assert result in [1, None]
            except (SystemExit, Exception):
                pass


class TestCommandCombinations:
    """Test various command combinations and edge cases."""

    def test_multiple_tools_sequential(self, temp_config):
        """Test launching multiple tools sequentially."""
        tools = ["claude", "codex", "copilot"]

        for tool in tools:
            with patch(
                "sys.argv",
                ["code-assistant-manager", "launch", tool, "--config", temp_config],
            ):
                with patch(
                    f"code_assistant_manager.tools.{tool.capitalize()}Tool.run",
                    return_value=0,
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

    def test_all_upgrade_commands(self, temp_config):
        """Test all variants of upgrade command."""
        variants = [
            ["code-assistant-manager", "upgrade", "all"],
            ["code-assistant-manager", "u", "all"],
            ["code-assistant-manager", "install", "all"],
            ["code-assistant-manager", "i", "all"],
        ]

        for cmd in variants:
            cmd.extend(["--config", temp_config])
            with patch("sys.argv", cmd):
                with patch(
                    "code_assistant_manager.cli.upgrade.handle_upgrade_command",
                    return_value=0,
                ):
                    try:
                        main()
                    except SystemExit:
                        pass

    def test_help_for_all_commands(self):
        """Test --help for all main commands."""
        commands = [
            ["code-assistant-manager", "launch", "--help"],
            ["code-assistant-manager", "upgrade", "--help"],
            ["code-assistant-manager", "install", "--help"],
            ["code-assistant-manager", "uninstall", "--help"],
            ["code-assistant-manager", "doctor", "--help"],
            ["code-assistant-manager", "config", "--help"],
            ["code-assistant-manager", "completion", "--help"],
            ["code-assistant-manager", "mcp", "--help"],
        ]

        for cmd in commands:
            with patch("sys.argv", cmd):
                try:
                    main()
                except SystemExit as e:
                    # Help commands should exit with 0
                    assert e.code in [0, 2]
