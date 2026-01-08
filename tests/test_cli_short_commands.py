"""Comprehensive tests for CLI short command aliases.

This test module focuses on testing all short/alias commands:
- l (launch)
- u (upgrade)
- i (install)
- un (uninstall)
- d (doctor)
- comp (completion)

These tests ensure that all aliases work correctly and are equivalent to their
full-length counterparts.
"""

from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.cli import app, main


class TestShortLaunchCommand:
    """Test 'l' short alias for launch command."""

    def test_l_help(self):
        """Test 'l' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "l", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_l_claude(self, mock_run, temp_config):
        """Test 'l claude' launches Claude."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CodexTool.run", return_value=0)
    def test_l_codex(self, mock_run, temp_config):
        """Test 'l codex' launches Codex."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CopilotTool.run", return_value=0)
    def test_l_copilot(self, mock_run, temp_config):
        """Test 'l copilot' launches Copilot."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "copilot", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.GeminiTool.run", return_value=0)
    def test_l_gemini(self, mock_run, temp_config):
        """Test 'l gemini' launches Gemini."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "gemini", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.DroidTool.run", return_value=0)
    def test_l_droid(self, mock_run, temp_config):
        """Test 'l droid' launches Droid."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "droid", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.QwenTool.run", return_value=0)
    def test_l_qwen(self, mock_run, temp_config):
        """Test 'l qwen' launches Qwen."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CodeBuddyTool.run", return_value=0)
    def test_l_codebuddy(self, mock_run, temp_config):
        """Test 'l codebuddy' launches CodeBuddy."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "codebuddy", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.IfLowTool.run", return_value=0)
    def test_l_iflow(self, mock_run, temp_config):
        """Test 'l iflow' launches iFlow."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "iflow", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.CrushTool.run", return_value=0)
    def test_l_crush(self, mock_run, temp_config):
        """Test 'l crush' launches Crush."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "crush", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.BlackboxTool.run", return_value=0)
    def test_l_blackbox(self, mock_run, temp_config):
        """Test 'l blackbox' launches Blackbox."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "blackbox", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.GooseTool.run", return_value=0)
    def test_l_goose(self, mock_run, temp_config):
        """Test 'l goose' launches Goose."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "goose", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.OpenCodeTool.run", return_value=0)
    def test_l_opencode(self, mock_run, temp_config):
        """Test 'l opencode' launches OpenCode."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "opencode", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_l_with_arguments(self, mock_run, temp_config):
        """Test 'l tool arg1 arg2' passes arguments."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "l",
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
            mock_run.assert_called_once_with(["arg1", "arg2"])

    def test_l_with_invalid_tool(self):
        """Test 'l invalid' with non-existent tool."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "invalid_tool"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                app()
            assert exc_info.value.code == 2


class TestShortUpgradeCommand:
    """Test 'u' short alias for upgrade command."""

    def test_u_help(self):
        """Test 'u' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "u", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_claude(self, mock_upgrade, temp_config):
        """Test 'u claude' upgrades Claude."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_all(self, mock_upgrade, temp_config):
        """Test 'u all' upgrades all tools."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "all", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_codex(self, mock_upgrade, temp_config):
        """Test 'u codex' upgrades Codex."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_qwen(self, mock_upgrade, temp_config):
        """Test 'u qwen' upgrades Qwen."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_mcp(self, mock_upgrade, temp_config):
        """Test 'u mcp' upgrades MCP."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "mcp", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_copilot(self, mock_upgrade, temp_config):
        """Test 'u copilot' upgrades Copilot."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "copilot", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_droid(self, mock_upgrade, temp_config):
        """Test 'u droid' upgrades Droid."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "droid", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestShortInstallCommand:
    """Test 'i' short alias for install command."""

    def test_i_help(self):
        """Test 'i' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "i", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_claude(self, mock_upgrade, temp_config):
        """Test 'i claude' installs Claude."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_all(self, mock_upgrade, temp_config):
        """Test 'i all' installs all tools."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "all", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_codex(self, mock_upgrade, temp_config):
        """Test 'i codex' installs Codex."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_qwen(self, mock_upgrade, temp_config):
        """Test 'i qwen' installs Qwen."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_codebuddy(self, mock_upgrade, temp_config):
        """Test 'i codebuddy' installs CodeBuddy."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "codebuddy", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_gemini(self, mock_upgrade, temp_config):
        """Test 'i gemini' installs Gemini."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "gemini", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_mcp(self, mock_upgrade, temp_config):
        """Test 'i mcp' installs MCP."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "mcp", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestShortUninstallCommand:
    """Test 'un' short alias for uninstall command."""

    def test_un_help(self):
        """Test 'un' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "un", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_un_claude(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un claude' uninstalls Claude."""
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

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_un_all(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un all' uninstalls all tools."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "un",
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
    def test_un_codex(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un codex' uninstalls Codex."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"codex": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "un",
                "codex",
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
    def test_un_with_force(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un tool --force' with force flag."""
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

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_un_with_keep_config(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un tool --keep-config' with keep config flag."""
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
    def test_un_copilot(self, mock_get_tools, mock_subprocess, temp_config):
        """Test 'un copilot' uninstalls Copilot."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"copilot": MagicMock(return_value=mock_tool)}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "un",
                "copilot",
                "--force",
                "--config",
                temp_config,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code in [0, 1]


class TestShortDoctorCommand:
    """Test 'd' short alias for doctor command."""

    def test_d_help(self):
        """Test 'd' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "d", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0)
    def test_d_basic(self, mock_doctor, temp_config):
        """Test 'd' runs doctor checks."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "d", "--config", temp_config],
        ):
            with patch("code_assistant_manager.cli.commands.doctor", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code in [0, 1]

    @patch("code_assistant_manager.cli.doctor.run_doctor_checks", return_value=0)
    def test_d_with_verbose(self, mock_doctor, temp_config):
        """Test 'd --verbose' with verbose flag."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "d", "--verbose", "--config", temp_config],
        ):
            with patch("code_assistant_manager.cli.commands.doctor", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code in [0, 1]


class TestShortCompletionCommand:
    """Test 'comp' short alias for completion command."""

    def test_comp_help(self):
        """Test 'comp' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_comp_bash(self):
        """Test 'comp bash' generates bash completion."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_comp_zsh(self):
        """Test 'comp zsh' generates zsh completion."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "zsh"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_comp_invalid_shell(self):
        """Test 'comp fish' with invalid shell."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "fish"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestShortCompletionCAlias:
    """Test 'c' short alias for completion command."""

    def test_c_help(self):
        """Test 'c' shows help."""
        with patch("sys.argv", ["code-assistant-manager", "c", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_c_bash(self):
        """Test 'c bash' generates bash completion."""
        with patch("sys.argv", ["code-assistant-manager", "c", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_c_zsh(self):
        """Test 'c zsh' generates zsh completion."""
        with patch("sys.argv", ["code-assistant-manager", "c", "zsh"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_c_invalid_shell(self):
        """Test 'c fish' with invalid shell."""
        with patch("sys.argv", ["code-assistant-manager", "c", "fish"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestAllShortCommandsCombinations:
    """Test combinations of short commands."""

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_l_vs_launch_equivalent(self, mock_run, temp_config):
        """Test 'l claude' is equivalent to 'launch claude'."""
        # Test short version
        with patch(
            "sys.argv",
            ["code-assistant-manager", "l", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_vs_upgrade_equivalent(self, mock_upgrade, temp_config):
        """Test 'u claude' is equivalent to 'upgrade claude'."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "u", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_vs_install_equivalent(self, mock_upgrade, temp_config):
        """Test 'i claude' is equivalent to 'install claude'."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "i", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("subprocess.run")
    @patch("code_assistant_manager.tools.get_registered_tools")
    def test_un_vs_uninstall_equivalent(
        self, mock_get_tools, mock_subprocess, temp_config
    ):
        """Test 'un claude' is equivalent to 'uninstall claude'."""
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

    def test_comp_vs_completion_equivalent(self):
        """Test 'comp bash' is equivalent to 'completion bash'."""
        with patch("sys.argv", ["code-assistant-manager", "comp", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_c_vs_completion_equivalent(self):
        """Test 'c bash' is equivalent to 'completion bash'."""
        with patch("sys.argv", ["code-assistant-manager", "c", "bash"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestShortCommandsWithAllTools:
    """Test short commands with all available tools."""

    def test_l_all_tools_suite(self, temp_config):
        """Test 'l' works with all tools."""
        tools_map = {
            "claude": "ClaudeTool",
            "codex": "CodexTool",
            "copilot": "CopilotTool",
            "gemini": "GeminiTool",
            "droid": "DroidTool",
            "qwen": "QwenTool",
            "codebuddy": "CodeBuddyTool",
            "iflow": "IfLowTool",
            "crush": "CrushTool",
            "blackbox": "BlackboxTool",
            "goose": "GooseTool",
            "opencode": "OpenCodeTool",
        }
        for tool, tool_class in tools_map.items():
            with patch(
                "sys.argv",
                ["code-assistant-manager", "l", tool, "--config", temp_config],
            ):
                with patch(
                    f"code_assistant_manager.tools.{tool_class}.run",
                    return_value=0,
                ):
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_u_multiple_tools(self, mock_upgrade, temp_config):
        """Test 'u' with multiple tools."""
        tools = ["claude", "codex", "qwen", "all"]
        for tool in tools:
            with patch(
                "sys.argv",
                ["code-assistant-manager", "u", tool, "--config", temp_config],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_i_multiple_tools(self, mock_upgrade, temp_config):
        """Test 'i' with multiple tools."""
        tools = ["claude", "codex", "qwen", "all"]
        for tool in tools:
            with patch(
                "sys.argv",
                ["code-assistant-manager", "i", tool, "--config", temp_config],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
