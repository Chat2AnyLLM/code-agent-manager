#!/usr/bin/env python3
"""
Integration tests for tools with mocked interactive components.

These tests verify that tools work correctly when menus are bypassed
using the non-interactive mode or key_provider mechanisms.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools.claude import ClaudeTool
from code_assistant_manager.tools.codex import CodexTool


class TestToolIntegration:
    """Test suite for tool integration with mocked menus."""

    def setup_method(self):
        """Set up test environment."""
        # Create a temporary config file for testing
        self.temp_config = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "test_endpoint": {
                    "endpoint": "https://api.test.com",
                    "api_key": "test_key",
                    "description": "Test Endpoint",
                    "list_models_cmd": "echo model1 model2 model3",
                    "supported_client": "codex,claude",
                }
            },
        }
        json.dump(config_data, self.temp_config, indent=2)
        self.temp_config.close()

        # Create config manager
        self.config = ConfigManager(self.temp_config.name)

    def teardown_method(self):
        """Clean up test environment."""
        # Remove temporary config file
        if hasattr(self, "temp_config") and self.temp_config:
            os.unlink(self.temp_config.name)

    @patch("code_assistant_manager.tools.base.subprocess.run")
    @patch("code_assistant_manager.tools.base.CLITool._check_command_available")
    @patch("code_assistant_manager.tools.registry.TOOL_REGISTRY.get_install_command")
    def test_codex_tool_non_interactive(
        self, mock_get_install_cmd, mock_check_command, mock_subprocess
    ):
        """Test Codex tool in non-interactive mode."""
        # Set non-interactive mode
        os.environ["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"] = "1"

        try:
            # Mock the tool registry to return no install command
            mock_get_install_cmd.return_value = None

            # Mock the command availability check
            mock_check_command.return_value = True
            # Mock subprocess.run to avoid actually running codex
            mock_subprocess.return_value = MagicMock(returncode=0)

            # Mock the endpoint manager methods
            with patch(
                "code_assistant_manager.tools.EndpointManager"
            ) as mock_endpoint_manager:
                mock_em_instance = MagicMock()
                mock_endpoint_manager.return_value = mock_em_instance

                # Mock endpoint selection
                mock_em_instance.select_endpoint.return_value = (True, "test_endpoint")

                # Mock endpoint config retrieval
                mock_em_instance.get_endpoint_config.return_value = (
                    True,
                    {"endpoint": "https://api.test.com", "actual_api_key": "test_key"},
                )

                # Mock model fetching
                mock_em_instance.fetch_models.return_value = (
                    True,
                    ["model1", "model2", "model3"],
                )

                # Create and run the tool
                tool = CodexTool(self.config)
                result = tool.run([])

                # Verify the tool ran successfully
                assert result == 0

                # Verify that subprocess.run was called with the expected arguments
                mock_subprocess.assert_called_once()
        finally:
            # Clean up environment variable
            if "CODE_ASSISTANT_MANAGER_NONINTERACTIVE" in os.environ:
                del os.environ["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"]

    @patch("code_assistant_manager.tools.base.subprocess.run")
    @patch("code_assistant_manager.tools.base.CLITool._check_command_available")
    @patch("code_assistant_manager.tools.registry.TOOL_REGISTRY.get_install_command")
    def test_claude_tool_non_interactive(
        self, mock_get_install_cmd, mock_check_command, mock_subprocess
    ):
        """Test Claude tool in non-interactive mode."""
        # Set non-interactive mode
        os.environ["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"] = "1"

        try:
            # Mock the tool registry to return no install command
            mock_get_install_cmd.return_value = None

            # Mock the command availability check
            mock_check_command.return_value = True
            # Mock subprocess.run to avoid actually running claude
            mock_subprocess.return_value = MagicMock(returncode=0)

            # Mock the endpoint manager methods
            with patch(
                "code_assistant_manager.tools.EndpointManager"
            ) as mock_endpoint_manager:
                mock_em_instance = MagicMock()
                mock_endpoint_manager.return_value = mock_em_instance

                # Mock endpoint selection
                mock_em_instance.select_endpoint.return_value = (True, "test_endpoint")

                # Mock endpoint config retrieval
                mock_em_instance.get_endpoint_config.return_value = (
                    True,
                    {"endpoint": "https://api.test.com", "actual_api_key": "test_key"},
                )

                # Mock model fetching
                mock_em_instance.fetch_models.return_value = (
                    True,
                    ["claude-1", "claude-2"],
                )

                # Create and run the tool
                tool = ClaudeTool(self.config)
                result = tool.run([])

                # Verify the tool ran successfully
                assert result == 0

                # Verify that subprocess.run was called with the expected arguments
                mock_subprocess.assert_called_once()
        finally:
            # Clean up environment variable
            if "CODE_ASSISTANT_MANAGER_NONINTERACTIVE" in os.environ:
                del os.environ["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"]

    def test_menu_key_provider_integration(self):
        """Test integration of key_provider with actual menu system."""
        from code_assistant_manager.menu.base import SimpleMenu

        # Create a sequence of inputs to simulate user interaction
        inputs = ["1"]  # Select first option
        input_iter = iter(inputs)

        def key_provider():
            try:
                return next(input_iter)
            except StopIteration:
                return None

        # Test the menu with our key provider
        menu = SimpleMenu(
            "Integration Test Menu",
            ["First Option", "Second Option", "Third Option"],
            "Cancel",
            key_provider=key_provider,
        )
        success, idx = menu.display()

        # Should have successfully selected the first option
        assert success is True
        assert idx == 0

    @patch("code_assistant_manager.tools.base.subprocess.run")
    @patch("code_assistant_manager.tools.base.CLITool._check_command_available")
    def test_tool_with_key_provider_menus(self, mock_check_command, mock_subprocess):
        """Test tool with key_provider controlled menus."""
        # Mock the command availability check
        mock_check_command.return_value = True

        # Mock subprocess.run to avoid actually running the tool
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Mock the endpoint manager methods
        with patch(
            "code_assistant_manager.tools.EndpointManager"
        ) as mock_endpoint_manager:
            mock_em_instance = MagicMock()
            mock_endpoint_manager.return_value = mock_em_instance

            # Mock endpoint selection with key_provider
            mock_em_instance.select_endpoint.return_value = (True, "test_endpoint")

            # Mock endpoint config retrieval
            mock_em_instance.get_endpoint_config.return_value = (
                True,
                {"endpoint": "https://api.test.com", "actual_api_key": "test_key"},
            )

            # Mock model fetching
            mock_em_instance.fetch_models.return_value = (
                True,
                ["model1", "model2", "model3"],
            )

            # Mock the model selection functions to use key_provider
            with patch(
                "code_assistant_manager.tools.base.ModelSelector"
            ) as mock_model_selector:
                # Mock single model selection
                mock_model_selector.select_model_with_endpoint_info.return_value = (
                    True,
                    "model1",
                )

                # Mock dual model selection
                mock_model_selector.select_two_models_with_endpoint_info.return_value = (
                    True,
                    ("claude-1", "claude-2"),
                )

                # Test Codex tool (single model)
                codex_tool = CodexTool(self.config)
                result = codex_tool.run([])
                assert result == 0

                # Test Claude tool (dual model)
                claude_tool = ClaudeTool(self.config)
                result = claude_tool.run([])
                assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
