"""Tests for upgrade loop fix in code_assistant_manager."""

from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.tools import TOOL_REGISTRY, CLITool


class TestUpgradeLoopFix:
    """Test that upgrade loop is fixed."""

    @patch("code_assistant_manager.tools.base.CLITool._perform_upgrade")
    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_simple_menu")
    def test_upgrade_prompt_only_once_per_session(
        self, mock_menu, mock_check_available, mock_perform_upgrade
    ):
        """Test that upgrade prompt is only shown once per session for the same tool."""
        # Setup
        mock_check_available.return_value = True
        mock_menu.return_value = (
            True,
            0,
        )  # User selects "Yes, upgrade to latest version"
        mock_perform_upgrade.return_value = True  # Upgrade succeeds

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

            # First call - should prompt for upgrade
            result1 = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Second call - should NOT prompt for upgrade (use cached decision)
            result2 = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Verify that the menu was only called once
            assert mock_menu.call_count == 1
            # Verify that _perform_upgrade was called only once
            assert mock_perform_upgrade.call_count == 1
            # Both calls should return True
            assert result1 is True
            assert result2 is True

    @patch("code_assistant_manager.tools.base.CLITool._perform_upgrade")
    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_simple_menu")
    def test_no_upgrade_prompt_when_user_skips(
        self, mock_menu, mock_check_available, mock_perform_upgrade
    ):
        """Test that no upgrade prompt is shown when user previously skipped."""
        # Setup
        mock_check_available.return_value = True
        mock_menu.return_value = (True, 1)  # User selects "No, use current version"
        mock_perform_upgrade.return_value = (
            True  # This won't be called, but need to mock it
        )

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

            # First call - user skips upgrade
            result1 = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Second call - should NOT prompt for upgrade (use cached decision)
            result2 = tool._ensure_tool_installed("testcmd", "test-tool", "Test Tool")

            # Verify that the menu was only called once
            assert mock_menu.call_count == 1
            # _perform_upgrade should not have been called
            assert mock_perform_upgrade.call_count == 0
            # Both calls should return True
            assert result1 is True
            assert result2 is True

    @patch("code_assistant_manager.tools.base.CLITool._perform_upgrade")
    @patch("code_assistant_manager.tools.CLITool._check_command_available")
    @patch("code_assistant_manager.menu.menus.display_simple_menu")
    def test_different_tools_still_prompt(
        self, mock_menu, mock_check_available, mock_perform_upgrade
    ):
        """Test that different tools still get their own prompts."""
        # Setup
        mock_check_available.return_value = True
        mock_menu.return_value = (
            True,
            0,
        )  # User selects "Yes, upgrade to latest version"
        mock_perform_upgrade.return_value = True

        # Create test tool instances
        class TestTool1(CLITool):
            command_name = "testcmd1"
            tool_key = "test-tool-1"
            install_description = "Test Tool 1"

        class TestTool2(CLITool):
            command_name = "testcmd2"
            tool_key = "test-tool-2"
            install_description = "Test Tool 2"

        # Mock the tool registry to return install commands
        with patch.object(
            TOOL_REGISTRY,
            "get_install_command",
            side_effect=lambda key: f"npm install -g {key}@latest",
        ):
            tool1 = TestTool1(MagicMock())
            tool2 = TestTool2(MagicMock())

            # Call tool1 - should prompt for upgrade
            result1 = tool1._ensure_tool_installed(
                "testcmd1", "test-tool-1", "Test Tool 1"
            )

            # Call tool2 - should also prompt for upgrade (different tool)
            result2 = tool2._ensure_tool_installed(
                "testcmd2", "test-tool-2", "Test Tool 2"
            )

            # Verify that the menu was called twice (once for each tool)
            assert mock_menu.call_count == 2
            # Both calls should return True
            assert result1 is True
            assert result2 is True
