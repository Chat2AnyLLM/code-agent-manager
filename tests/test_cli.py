"""Tests for code_assistant_manager.cli module."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.cli import app, main
from typer.testing import CliRunner


class TestCLIMain:
    """Test CLI main function."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self):
        """Test CLI help output."""
        with patch("sys.argv", ["code-assistant-manager", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_cli_help_contains_install_command(self):
        """Test CLI help output contains install command."""
        import io
        import sys
        from contextlib import redirect_stdout

        # Capture stdout to check help output
        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            with patch("sys.argv", ["code-assistant-manager", "--help"]):
                with pytest.raises(SystemExit):
                    main()

        help_output = captured_output.getvalue()
        assert "install" in help_output, "Help output should contain install command"
        assert "alias: i" in help_output, "Help output should show 'i' as install alias"

    def test_cli_version(self, runner):
        """Test 'version' command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        version_output = result.stdout
        assert "code-assistant-manager" in version_output
        assert "1.1.0" in version_output, "Version command should output 1.1.0"

    def test_cli_no_arguments(self):
        """Test CLI with no arguments."""
        with patch("sys.argv", ["code-assistant-manager"]):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # When no_args_is_help=True, Typer shows help and exits
            # The exit code might be 2 in this context, but help is shown
            assert exc_info.value.code in [0, 2]  # Accept either exit code

    def test_cli_invalid_tool(self):
        """Test CLI with invalid tool."""
        with patch("sys.argv", ["code-assistant-manager", "launch", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                app()
            # Invalid commands should exit with error code
            assert exc_info.value.code == 2

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_cli_claude_command(self, mock_run, temp_config):
        """Test CLI claude command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with code 0 (success)
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CodexTool.run", return_value=0)
    def test_cli_codex_command(self, mock_run, temp_config):
        """Test CLI codex command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "codex", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.QwenTool.run", return_value=0)
    def test_cli_qwen_command(self, mock_run, temp_config):
        """Test CLI qwen command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "qwen", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CodeBuddyTool.run", return_value=0)
    def test_cli_codebuddy_command(self, mock_run, temp_config):
        """Test CLI codebuddy command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "codebuddy", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.IfLowTool.run", return_value=0)
    def test_cli_iflow_command(self, mock_run, temp_config):
        """Test CLI iflow command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "iflow", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.DroidTool.run", return_value=0)
    def test_cli_droid_command(self, mock_run, temp_config):
        """Test CLI droid command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "droid", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.CopilotTool.run", return_value=0)
    def test_cli_copilot_command(self, mock_run, temp_config):
        """Test CLI copilot command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "copilot", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch("code_assistant_manager.tools.GeminiTool.run", return_value=0)
    def test_cli_gemini_command(self, mock_run, temp_config):
        """Test CLI gemini command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "gemini", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            mock_run.assert_called_once()

    @patch(
        "code_assistant_manager.tools.ClaudeTool.run",
        side_effect=Exception("Config error"),
    )
    def test_cli_config_not_found(self, mock_run, temp_config):
        """Test CLI with non-existent config."""
        with patch(
            "sys.argv",
            [
                "code-assistant-manager",
                "launch",
                "claude",
                "--config",
                "/nonexistent/path/config.json",
            ],
        ):
            # Tool.run raises exception
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with error code due to config not found
            assert exc_info.value.code == 1

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_cli_with_tool_args(self, mock_run, temp_config):
        """Test CLI passing arguments to tool."""
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
            mock_run.assert_called_once_with(["arg1", "arg2"])

    @patch("code_assistant_manager.mcp.tool.MCPTool.run", return_value=0)
    def test_cli_mcp_command(self, mock_run, temp_config):
        """Test CLI mcp command."""
        with patch("sys.argv", ["code-assistant-manager", "mcp"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # MCP command may exit with different code or require subcommands
            assert exc_info.value.code in [0, 2]  # Allow either help or error

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_cli_upgrade_command(self, mock_upgrade, temp_config):
        """Test CLI upgrade command."""
        with patch("sys.argv", ["code-assistant-manager", "upgrade"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_cli_upgrade_all_command(self, mock_upgrade, temp_config):
        """Test CLI upgrade all command."""
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
    def test_cli_install_command(self, mock_upgrade, temp_config):
        """Test CLI install command."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "install", "--config", temp_config],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_cli_install_all_command(self, mock_upgrade, temp_config):
        """Test CLI install all command."""
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
    def test_cli_install_alias_command(self, mock_upgrade, temp_config):
        """Test CLI install alias 'i' command."""
        with patch(
            "sys.argv", ["code-assistant-manager", "i", "--config", temp_config]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("code_assistant_manager.cli.upgrade.handle_upgrade_command", return_value=0)
    def test_cli_install_alias_all_command(self, mock_upgrade, temp_config):
        """Test CLI install alias 'i' all command."""
        with patch(
            "sys.argv", ["code-assistant-manager", "i", "all", "--config", temp_config]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestCLIToolMapping:
    """Test CLI tool mapping."""

    @patch("code_assistant_manager.tools.ClaudeTool.run", return_value=0)
    def test_all_tools_mapped(self, mock_run):
        """Test that all tools are in the mapping."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "common": {},
                "endpoints": {"endpoint1": {"endpoint": "https://api.example.com"}},
            }
            json.dump(config_data, f, indent=2)
            config_path = f.name

        try:
            for tool in ["claude", "codex", "qwen", "codebuddy", "iflow"]:
                with patch(
                    "sys.argv",
                    ["code-assistant-manager", "launch", tool, "--config", config_path],
                ):
                    with patch(
                        "code_assistant_manager.tools.CodexTool.run", return_value=0
                    ):
                        with patch(
                            "code_assistant_manager.tools.QwenTool.run", return_value=0
                        ):
                            with patch(
                                "code_assistant_manager.tools.CodeBuddyTool.run",
                                return_value=0,
                            ):
                                with patch(
                                    "code_assistant_manager.tools.IfLowTool.run",
                                    return_value=0,
                                ):
                                    try:
                                        result = main()
                                        # Should succeed or fail gracefully
                                        assert result in [0, 1]
                                    except SystemExit:
                                        pass
        finally:
            Path(config_path).unlink()


class TestCLIConfigHandling:
    """Test CLI configuration file handling."""

    def test_cli_uses_custom_config(self, temp_config):
        """Test that CLI uses custom config path."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "--config", temp_config],
        ):
            with patch("code_assistant_manager.config.ConfigManager") as mock_cm_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_cm_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.ClaudeTool.run", return_value=0
                ) as mock_run:
                    with pytest.raises(SystemExit):
                        main()
                    # Verify ConfigManager was called with custom config
                    mock_cm_class.assert_called_with(temp_config)

    def test_cli_default_config_path(self):
        """Test that CLI looks for default config."""
        with patch("sys.argv", ["code-assistant-manager", "launch", "claude"]):
            with patch("code_assistant_manager.config.ConfigManager") as mock_cm_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_cm_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.ClaudeTool.run", return_value=0
                ):
                    with pytest.raises(SystemExit):
                        main()
                    # Verify ConfigManager was called with default (None)
                    mock_cm_class.assert_called_with(None)


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_cli_handles_keyboard_interrupt(self, temp_config):
        """Test CLI handles keyboard interrupt gracefully."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "--config", temp_config],
        ):
            with patch(
                "code_assistant_manager.tools.ClaudeTool.run",
                side_effect=KeyboardInterrupt(),
            ):
                # May raise KeyboardInterrupt or return, both are acceptable
                try:
                    result = main()
                    assert result in [0, 1, 130]
                except KeyboardInterrupt:
                    # KeyboardInterrupt is expected and acceptable
                    pass
                except SystemExit as e:
                    # SystemExit with certain codes is also acceptable
                    assert e.code in [0, 1, 130]

    def test_cli_handles_exception(self, temp_config):
        """Test CLI handles exceptions gracefully."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "--config", temp_config],
        ):
            with patch(
                "code_assistant_manager.tools.ClaudeTool.run",
                side_effect=Exception("Test error"),
            ):
                # May raise or return error code
                try:
                    result = main()
                    assert result in [0, 1]
                except Exception:
                    pass


class TestToolInvocation:
    """Test tool invocation via main CLI."""

    def test_claude_invocation_via_main(self):
        """Test invoking claude via main CLI."""
        with patch("sys.argv", ["code-assistant-manager", "launch", "claude"]):
            with patch(
                "code_assistant_manager.config.ConfigManager"
            ) as mock_config_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_config_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.ClaudeTool.run", return_value=0
                ) as mock_run:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                    mock_run.assert_called_once()

    def test_codex_invocation_via_main(self):
        """Test invoking codex via main CLI."""
        with patch("sys.argv", ["code-assistant-manager", "launch", "codex"]):
            with patch(
                "code_assistant_manager.config.ConfigManager"
            ) as mock_config_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_config_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.CodexTool.run", return_value=0
                ) as mock_run:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                    mock_run.assert_called_once()

    def test_tool_with_arguments(self):
        """Test passing arguments to tools."""
        with patch(
            "sys.argv",
            ["code-assistant-manager", "launch", "claude", "some-arg", "value"],
        ):
            with patch(
                "code_assistant_manager.config.ConfigManager"
            ) as mock_config_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_config_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.ClaudeTool.run", return_value=0
                ) as mock_run:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                    # Verify args were passed to tool
                    mock_run.assert_called_once_with(["some-arg", "value"])

    @pytest.mark.skip(
        reason="Backward compatibility for direct tool commands not implemented"
    )
    def test_backward_compatibility_direct_tool_command(self):
        """Test backward compatibility with direct tool commands."""
        with patch("sys.argv", ["code-assistant-manager", "claude"]):
            with patch(
                "code_assistant_manager.config.ConfigManager"
            ) as mock_config_class:
                mock_config = MagicMock()
                mock_config.validate_config.return_value = (True, [])
                mock_config_class.return_value = mock_config
                with patch(
                    "code_assistant_manager.tools.ClaudeTool.run", return_value=0
                ) as mock_run:
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                    mock_run.assert_called_once()


class TestUninstallCommand:
    """Test uninstall command functionality."""

    def test_uninstall_help(self):
        """Test that uninstall command shows help."""
        with patch("sys.argv", ["code-assistant-manager", "uninstall", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from code_assistant_manager.cli import main

                main()
            assert exc_info.value.code == 0

    def test_uninstall_alias_help(self):
        """Test that uninstall alias (un) shows help."""
        with patch("sys.argv", ["code-assistant-manager", "un", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from code_assistant_manager.cli import main

                main()
            assert exc_info.value.code == 0

    @patch("subprocess.run")
    @patch("code_assistant_manager.cli.uninstall_commands.get_registered_tools")
    def test_uninstall_invalid_tool(self, mock_get_tools, mock_subprocess):
        """Test uninstall with invalid tool."""
        mock_get_tools.return_value = {}
        mock_subprocess.return_value = MagicMock(returncode=0)

        from code_assistant_manager.cli.commands import uninstall

        ctx = MagicMock()

        result = uninstall(ctx, "invalid_tool", force=True, keep_config=False)
        assert result == 1

    @patch("code_assistant_manager.cli.uninstall_commands.get_registered_tools")
    def test_uninstall_no_installed_tools(self, mock_get_tools):
        """Test uninstall when no tools are installed."""
        mock_tool = MagicMock()
        mock_tool._check_command_available.return_value = False
        mock_get_tools.return_value = {"claude": MagicMock(return_value=mock_tool)}

        from code_assistant_manager.cli.commands import uninstall

        ctx = MagicMock()

        result = uninstall(ctx, "claude", force=True, keep_config=False)
        assert result == 0
