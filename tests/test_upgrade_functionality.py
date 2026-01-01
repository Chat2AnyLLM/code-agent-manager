"""Tests for upgrade functionality in code_assistant_manager."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.tools import TOOL_REGISTRY, CLITool


class TestUpgradeFunctionality:
    """Test upgrade functionality in CLITool."""

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_simple_menu")
    def test_upgrade_functionality(self, mock_menu, mock_check_available, mock_run):
        """Test that upgrade functionality runs install command from tools.yaml and returns structured result."""
        # Setup
        mock_check_available.return_value = True
        mock_menu.return_value = (
            True,
            0,
        )  # User selects "Yes, upgrade to latest version"
        # Mock subprocess.run to return success for both clear commands and the install command
        mock_run.side_effect = [
            MagicMock(returncode=0),  # clear command
            MagicMock(returncode=0),  # clear command
            MagicMock(returncode=0),  # install command
        ]

        # Create a test tool instance
        class TestTool(CLITool):
            command_name = "testcmd"
            tool_key = "test-tool"
            install_description = "Test Tool"

        # Mock the tool registry to return an install command
        with patch.object(
            TOOL_REGISTRY,
            "get_install_command",
            return_value="npm install -g test-tool@latest",
        ):
            tool = TestTool(MagicMock())

            # Execute the tool installation check which should trigger upgrade
            result = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Verify that subprocess.run was called with the install command
            # The CLI may invoke subprocess.run with capture_output/text kwargs; accept either signature
            found = False
            for call in mock_run.call_args_list:
                args, kwargs = call
                if (
                    args
                    and isinstance(args[0], list)
                    and " ".join(args[0]) == "npm install -g test-tool@latest"
                ):
                    found = True
                    break
            assert (
                found
            ), f"Expected subprocess.run to be called with install command, calls: {mock_run.call_args_list}"
            # Since _ensure_tool_installed returns True on success, ensure True is returned
            assert result is True

    @patch("code_assistant_manager.tools.CLITool._perform_upgrade")
    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_simple_menu")
    def test_upgrade_failure_handling(self, mock_menu, mock_check_available, mock_perform_upgrade):
        """Test that upgrade failures are handled correctly."""
        # Setup
        mock_check_available.return_value = True  # Command is initially available
        mock_menu.return_value = (
            True,
            0,
        )  # User selects "Yes, upgrade to latest version"
        # Mock _perform_upgrade to return failure
        mock_perform_upgrade.return_value = {"success": False, "error": "install_failed"}

        # Create a test tool instance
        class TestTool(CLITool):
            command_name = "testcmd"
            tool_key = "test-tool"
            install_description = "Test Tool"

        # Mock the tool registry to return an install command
        with patch.object(
            TOOL_REGISTRY,
            "get_install_command",
            return_value="npm install -g test-tool@latest",
        ):
            tool = TestTool(MagicMock())

            # Execute the tool installation check which should trigger upgrade
            result = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Verify that _perform_upgrade was called
            mock_perform_upgrade.assert_called_once()
            # Upgrade failure should return False
            assert result is False

    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_centered_menu")
    def test_no_upgrade_when_no_install_cmd(self, mock_menu, mock_check_available):
        """Test that no upgrade prompt is shown when no install command is defined."""
        # Setup
        mock_check_available.return_value = True

        # Create a test tool instance
        class TestTool(CLITool):
            command_name = "testcmd"
            tool_key = "test-tool"
            install_description = "Test Tool"

        # Mock the tool registry to return no install command
        with patch.object(TOOL_REGISTRY, "get_install_command", return_value=None):
            tool = TestTool(MagicMock())

            # Execute the tool installation check
            result = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Verify that no menu was displayed (no upgrade prompt)
            mock_menu.assert_not_called()
            # Should return True since tool is available and no upgrade is needed
            assert result is True
