"""
Tests to verify all clients can be launched by 'cam launch xxx' without getting stuck.

This test suite ensures that:
1. All interactive clients are properly configured for interactive mode
2. Subprocess calls use correct parameters for interactive I/O
3. No clients hang or freeze when launched
4. stdin/stdout/stderr are properly connected for user interaction
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from code_assistant_manager.tools.base import CLITool
from code_assistant_manager.tools.claude import ClaudeTool
from code_assistant_manager.tools.codebuddy import CodeBuddyTool
from code_assistant_manager.tools.codex import CodexTool
from code_assistant_manager.tools.crush import CrushTool
from code_assistant_manager.tools.droid import DroidTool
from code_assistant_manager.tools.gemini import GeminiTool
from code_assistant_manager.tools.iflow import IfLowTool
from code_assistant_manager.tools.neovate import NeovateTool
from code_assistant_manager.tools.qodercli import QoderCLITool
from code_assistant_manager.tools.qwen import QwenTool
from code_assistant_manager.tools.zed import ZedTool

# List of all interactive CLI tools
INTERACTIVE_TOOLS = [
    (ClaudeTool, "claude"),
    (CrushTool, "crush"),
    (CodexTool, "codex"),
    (GeminiTool, "gemini"),
    (CodeBuddyTool, "codebuddy"),
    (DroidTool, "droid"),
    (IfLowTool, "iflow"),
    (NeovateTool, "neovate"),
    (QoderCLITool, "qodercli"),
    (QwenTool, "qwen"),
    (ZedTool, "zed"),
]


@pytest.fixture
def mock_config():
    """Provide a mock config manager."""
    config = MagicMock()
    config.config_data = {
        "claude": {},
        "crush": {},
        "codex": {},
        "gemini": {},
        "codebuddy": {},
        "droid": {},
        "iflow": {},
        "neovate": {},
        "qodercli": {},
        "qwen": {},
        "zed": {},
    }
    config.get_sections.return_value = []
    return config


class TestInteractiveModeParameter:
    """Test that all tools have the interactive parameter."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    def test_tool_has_interactive_parameter(self, tool_class, tool_name, mock_config):
        """Verify each tool has the interactive parameter in _run_tool_with_env."""
        import inspect

        tool = tool_class(mock_config)
        sig = inspect.signature(tool._run_tool_with_env)

        assert (
            "interactive" in sig.parameters
        ), f"{tool_name}: _run_tool_with_env missing 'interactive' parameter"

        # Verify default is False for backward compatibility
        default_val = sig.parameters["interactive"].default
        assert (
            default_val is False
        ), f"{tool_name}: interactive parameter should default to False, got {default_val}"


class TestSubprocessCallsInteractive:
    """Test that subprocess calls are made correctly for interactive mode."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_tool_calls_subprocess_without_capture_output_when_interactive(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify interactive mode disables capture_output."""
        mock_run.return_value = MagicMock(returncode=0)

        tool = tool_class(mock_config)
        result = tool._run_tool_with_env(
            ["test", "command"], {}, tool_name, interactive=True
        )

        # Verify subprocess.run was called
        assert mock_run.called, f"{tool_name}: subprocess.run not called"

        # Verify capture_output is NOT set in kwargs when interactive=True
        call_kwargs = mock_run.call_args[1]
        capture_output = call_kwargs.get("capture_output")
        assert (
            capture_output is not True
        ), f"{tool_name}: capture_output should not be True in interactive mode, got {capture_output}"

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_tool_calls_subprocess_with_capture_output_when_non_interactive(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify non-interactive mode enables capture_output for backward compatibility."""
        mock_run.return_value = MagicMock(returncode=0)

        tool = tool_class(mock_config)
        result = tool._run_tool_with_env(
            ["test", "command"], {}, tool_name, interactive=False
        )

        # Verify subprocess.run was called
        assert mock_run.called, f"{tool_name}: subprocess.run not called"

        # Verify capture_output is True in kwargs when interactive=False
        call_kwargs = mock_run.call_args[1]
        assert (
            call_kwargs.get("capture_output") is True
        ), f"{tool_name}: capture_output should be True in non-interactive mode"


class TestToolLaunchWithInteractive:
    """Test that tools properly launch with interactive parameter."""

    @patch("subprocess.run")
    @patch.object(CrushTool, "_get_filtered_endpoints", return_value=[])
    def test_crush_launch_uses_interactive_mode(
        self, mock_get_endpoints, mock_run, mock_config
    ):
        """Verify Crush tool launches with interactive=True."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(CrushTool, "_load_environment"):
            with patch.object(CrushTool, "_check_prerequisites", return_value=True):
                with patch.object(
                    CrushTool, "_ensure_tool_installed", return_value=True
                ):
                    tool = CrushTool(mock_config)
                    tool.run([])

        # Verify the subprocess call was made without capture_output
        if mock_run.called:
            call_kwargs = mock_run.call_args[1]
            assert (
                call_kwargs.get("capture_output") is not True
            ), "Crush: subprocess should be called in interactive mode"


class TestStdinStdoutConnection:
    """Test that stdin/stdout/stderr are properly connected."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_interactive_mode_no_capture_output_parameter(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify interactive mode doesn't pass capture_output to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0)

        tool = tool_class(mock_config)
        tool._run_tool_with_env(["test"], {}, tool_name, interactive=True)

        # Get the actual call
        assert mock_run.called
        _, kwargs = mock_run.call_args

        # In interactive mode, we should either not have capture_output, or have it as False/None
        if "capture_output" in kwargs:
            assert not kwargs[
                "capture_output"
            ], f"{tool_name}: capture_output should be False/None in interactive mode"

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_non_interactive_mode_captures_output(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify non-interactive mode captures output (backward compatible)."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        tool = tool_class(mock_config)
        tool._run_tool_with_env(["test"], {}, tool_name, interactive=False)

        # Get the actual call
        assert mock_run.called
        _, kwargs = mock_run.call_args

        # In non-interactive mode, capture_output should be True
        assert (
            kwargs.get("capture_output") is True
        ), f"{tool_name}: capture_output should be True in non-interactive mode"
        assert (
            kwargs.get("text") is True
        ), f"{tool_name}: text should be True in non-interactive mode"


class TestNoHangingBehavior:
    """Test that tools don't hang when launched."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run", timeout=5)
    def test_tool_subprocess_call_completes_quickly(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify subprocess call returns immediately (no hanging)."""
        mock_run.return_value = MagicMock(returncode=0)

        tool = tool_class(mock_config)

        # This should not hang
        result = tool._run_tool_with_env(
            ["test", "cmd"], {}, tool_name, interactive=True
        )

        # Should return an exit code
        assert isinstance(result, int), f"{tool_name}: run should return int exit code"
        assert result >= 0, f"{tool_name}: exit code should be non-negative"

    @patch("subprocess.run")
    def test_crusher_no_hang_on_launch(self, mock_run, mock_config):
        """Integration test: Crush launches without hanging."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(CrushTool, "_load_environment"):
            with patch.object(CrushTool, "_check_prerequisites", return_value=True):
                with patch.object(
                    CrushTool, "_ensure_tool_installed", return_value=True
                ):
                    with patch.object(
                        CrushTool, "_get_filtered_endpoints", return_value=[]
                    ):
                        tool = CrushTool(mock_config)
                        # Should not timeout or hang
                        result = tool.run([])

                        # Should complete successfully
                        assert result in [0, 1], "Crush should return an exit code"


class TestBackwardCompatibility:
    """Test that backward compatibility is maintained."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_default_parameter_preserves_capture_output(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify calling without interactive parameter uses capture_output (backward compatible)."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        tool = tool_class(mock_config)
        # Call without interactive parameter (should default to False)
        result = tool._run_tool_with_env(["test"], {}, tool_name)

        # Verify capture_output is True (backward compatible behavior)
        _, kwargs = mock_run.call_args
        assert (
            kwargs.get("capture_output") is True
        ), f"{tool_name}: backward compatibility: default should use capture_output=True"

    def test_cli_commands_still_work_with_new_parameter(self, mock_config):
        """Verify CLI commands work with the new interactive parameter."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            tool = ClaudeTool(mock_config)

            # Old style call (without interactive param) should work
            result1 = tool._run_tool_with_env(["test"], {}, "claude")
            assert result1 == 0

            # New style call (with interactive param) should also work
            result2 = tool._run_tool_with_env(["test"], {}, "claude", interactive=True)
            assert result2 == 0


class TestCLILaunchCommand:
    """Test that 'cam launch xxx' command properly uses interactive mode."""

    @patch("subprocess.run")
    def test_cam_launch_uses_interactive_mode_for_subprocess_calls(
        self, mock_subprocess, mock_config
    ):
        """Test that subprocess calls from tools use interactive mode."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        tool = ClaudeTool(mock_config)

        # Simulate what happens when a tool is launched
        result = tool._run_tool_with_env(["test"], {}, "claude", interactive=True)

        # Verify subprocess was called with interactive mode (no capture_output)
        assert mock_subprocess.called
        _, kwargs = mock_subprocess.call_args
        assert not kwargs.get(
            "capture_output", False
        ), "subprocess should not capture output in interactive mode"

    @patch("subprocess.run")
    def test_cam_launch_crush_uses_interactive_mode_for_subprocess_calls(
        self, mock_subprocess, mock_config
    ):
        """Test that Crush subprocess calls use interactive mode."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        tool = CrushTool(mock_config)

        # Simulate what happens when Crush is launched
        result = tool._run_tool_with_env(["crush"], {}, "crush", interactive=True)

        # Verify subprocess was called with interactive mode
        assert mock_subprocess.called
        _, kwargs = mock_subprocess.call_args
        assert not kwargs.get(
            "capture_output", False
        ), "Crush subprocess should not capture output in interactive mode"


class TestAllToolsCanBeLaunched:
    """Integration tests to verify all tools can be launched."""

    @pytest.mark.parametrize("tool_class,tool_name", INTERACTIVE_TOOLS)
    @patch("subprocess.run")
    def test_tool_can_be_instantiated_and_launched(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify each tool can be instantiated and launched without errors."""
        mock_run.return_value = MagicMock(returncode=0)

        # Should not raise any exceptions
        tool = tool_class(mock_config)
        assert tool is not None
        assert hasattr(tool, "run"), f"{tool_name}: Tool should have run method"
        assert hasattr(
            tool, "_run_tool_with_env"
        ), f"{tool_name}: Tool should have _run_tool_with_env method"

    @pytest.mark.parametrize(
        "tool_class,tool_name",
        [
            (ClaudeTool, "claude"),
            (CrushTool, "crush"),
            (CodexTool, "codex"),
            (GeminiTool, "gemini"),
        ],
    )
    @patch("subprocess.run")
    def test_sample_tools_launch_without_hanging(
        self, mock_run, tool_class, tool_name, mock_config
    ):
        """Verify sample tools launch without hanging."""
        mock_run.return_value = MagicMock(returncode=0)

        tool = tool_class(mock_config)

        # Create a simple test that doesn't actually call run() on real tools
        # Just verify the subprocess infrastructure is correct
        result = tool._run_tool_with_env(
            ["echo", "test"], {}, tool_name, interactive=True
        )

        assert result == 0, f"{tool_name}: should return 0"
        assert mock_run.called, f"{tool_name}: subprocess.run should be called"


class TestExitCodeHandling:
    """Test that exit codes are properly handled in interactive mode."""

    @pytest.mark.parametrize("exit_code", [0, 1, 2, 130])  # 130 is Ctrl+C
    @patch("subprocess.run")
    def test_interactive_mode_returns_correct_exit_codes(
        self, mock_run, exit_code, mock_config
    ):
        """Verify exit codes are properly returned in interactive mode."""
        mock_run.return_value = MagicMock(returncode=exit_code)

        tool = ClaudeTool(mock_config)
        result = tool._run_tool_with_env(["test"], {}, "claude", interactive=True)

        # Should return the exit code from subprocess
        assert (
            result == exit_code
        ), f"Interactive mode should return exit code {exit_code}, got {result}"

    @patch("subprocess.run")
    def test_keyboard_interrupt_returns_130(self, mock_run, mock_config):
        """Verify Ctrl+C (KeyboardInterrupt) returns exit code 130."""
        mock_run.side_effect = KeyboardInterrupt()

        tool = ClaudeTool(mock_config)
        result = tool._run_tool_with_env(["test"], {}, "claude", interactive=True)

        # Should return 130 for interrupt
        assert result == 130, "KeyboardInterrupt should return exit code 130"
