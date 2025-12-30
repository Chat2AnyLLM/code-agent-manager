"""Tests for the Gemini tool fixes."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools import GeminiTool


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "endpoint1": {
                    "endpoint": "https://api1.example.com",
                    "api_key": "key1",
                    "description": "Test Endpoint",
                    "list_models_cmd": "echo model1 model2",
                    "supported_client": "gemini",
                }
            },
        }
        import json

        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


@pytest.fixture
def config_manager(temp_config):
    """Create a ConfigManager instance."""
    return ConfigManager(temp_config)


class TestGeminiToolFixes:
    """Test the fixes made to the GeminiTool."""

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    def test_gemini_tool_calls_ensure_tool_installed(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that Gemini tool calls _ensure_tool_installed to show upgrade menu."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            tool = GeminiTool(config_manager)
            result = tool.run([])

            # Verify that _ensure_tool_installed was called
            mock_install.assert_called_once_with(
                tool.command_name, tool.tool_key, tool.install_description
            )
            assert result == 0

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    def test_gemini_tool_calls_load_environment(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that Gemini tool calls _load_environment to load .env files."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            with patch.object(GeminiTool, "_load_environment") as mock_load_env:
                tool = GeminiTool(config_manager)
                result = tool.run([])

                # Verify that _load_environment was called
                mock_load_env.assert_called_once()
                assert result == 0

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    def test_gemini_tool_loads_env_vars_from_file(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that Gemini tool calls _load_environment to load .env files."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            with patch.object(GeminiTool, "_load_environment") as mock_load_env:
                tool = GeminiTool(config_manager)
                result = tool.run([])

                # Verify that _load_environment was called
                mock_load_env.assert_called_once()
                assert result == 0

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    def test_gemini_extension_commands_skip_upgrade_check(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that extension commands skip the upgrade check."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            tool = GeminiTool(config_manager)
            result = tool.run(["extensions", "list"])

            # Verify that _ensure_tool_installed was NOT called for extension commands
            mock_install.assert_not_called()
            # But _check_command_available should still be called to verify tool exists
            mock_check.assert_called_once_with("gemini")
            assert result == 0

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=False)
    def test_gemini_extension_commands_fail_when_tool_not_available(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that extension commands fail when gemini tool is not available."""
        tool = GeminiTool(config_manager)
        result = tool.run(["extensions", "list"])

        # Verify that _ensure_tool_installed was NOT called for extension commands
        mock_install.assert_not_called()
        # _check_command_available should be called and return False
        mock_check.assert_called_once_with("gemini")
        # Should return 1 when tool is not available
        assert result == 1

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    def test_gemini_non_extension_commands_still_check_upgrade(
        self, mock_check, mock_install, mock_run, config_manager
    ):
        """Test that non-extension commands still perform upgrade checks."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            tool = GeminiTool(config_manager)
            result = tool.run([])  # No args, not an extension command

            # Verify that _ensure_tool_installed was called for non-extension commands
            mock_install.assert_called_once_with(
                tool.command_name, tool.tool_key, tool.install_description
            )
            assert result == 0
