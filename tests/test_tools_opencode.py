"""Tests for OpenCode tool functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools.opencode import OpenCodeTool


@pytest.fixture
def opencode_config():
    """Create a config file for OpenCode testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {
                "http_proxy": "http://proxy.example.com:3128/",
                "https_proxy": "http://proxy.example.com:3128/",
                "cache_ttl_seconds": 3600,
            },
            "endpoints": {
                "test-provider": {
                    "endpoint": "https://api.test.com/v1",
                    "api_key": "test-key-12345",
                    "description": "Test Provider for OpenCode",
                    "list_models_cmd": "echo gpt-4 gpt-3.5-turbo claude-3",
                    "supported_client": "opencode",
                },
                "unsupported-provider": {
                    "endpoint": "https://api.unsupported.com/v1",
                    "api_key": "test-key-67890",
                    "description": "Unsupported Provider",
                    "supported_client": "claude,codex",
                }
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


class TestOpenCodeTool:
    """Test cases for OpenCodeTool class."""

    def test_tool_initialization(self, opencode_config):
        """Test OpenCodeTool initialization."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        assert tool.command_name == "opencode"
        assert tool.tool_key == "opencode"
        assert tool.install_description == "OpenCode.ai CLI"

    @patch("subprocess.run")
    def test_get_filtered_endpoints(self, mock_subprocess, opencode_config):
        """Test filtering endpoints that support opencode client."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        # Mock subprocess for supported client check
        mock_subprocess.return_value = MagicMock(returncode=0)

        filtered = tool._get_filtered_endpoints()
        assert "test-provider" in filtered
        assert "unsupported-provider" not in filtered

    @patch("code_assistant_manager.tools.select_model")
    def test_process_endpoint_success(self, mock_select_model, opencode_config):
        """Test successful endpoint processing."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        # Mock model selection
        mock_select_model.return_value = (True, "gpt-4")

        with patch.object(tool.endpoint_manager, "get_endpoint_config") as mock_get_config:
            mock_get_config.return_value = (True, {
                "endpoint": "https://api.test.com/v1",
                "list_models_cmd": "echo gpt-4 gpt-3.5-turbo"
            })

            result = tool._process_endpoint("test-provider")
            assert result == ["gpt-4"]

    def test_process_endpoint_no_models(self, opencode_config):
        """Test endpoint processing when no models found."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        with patch.object(tool.endpoint_manager, "get_endpoint_config") as mock_get_config:
            mock_get_config.return_value = (True, {
                "endpoint": "https://api.test.com/v1",
                "list_models_cmd": "echo"  # Empty output
            })

            result = tool._process_endpoint("test-provider")
            assert result is None

    def test_write_opencode_config(self, opencode_config, tmp_path):
        """Test OpenCode configuration file generation."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        selected_models = {
            "test-provider": ["gpt-4", "claude-3"]
        }

        # Mock endpoint config
        with patch.object(tool.endpoint_manager, "get_endpoint_config") as mock_get_config:
            mock_get_config.return_value = (True, {
                "endpoint": "https://api.test.com/v1",
                "description": "Test Provider",
                "api_key": "test-key"
            })

            config_file = tool._write_opencode_config(selected_models)

            # Verify file was created
            assert config_file.exists()

            # Verify content
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            assert "$schema" in config_data
            assert "provider" in config_data
            assert "test-provider" in config_data["provider"]
            assert "model" in config_data

            # Verify provider structure
            provider = config_data["provider"]["test-provider"]
            assert provider["npm"] == "@ai-sdk/openai-compatible"
            assert provider["name"] == "Test Provider"
            assert "options" in provider
            assert "models" in provider

    @patch("subprocess.run")
    def test_run_opencode_installed(self, mock_subprocess, opencode_config):
        """Test run method when OpenCode is already installed."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        # Mock OpenCode as installed
        with patch("pathlib.Path.exists", return_value=True):
            mock_subprocess.return_value = MagicMock(returncode=0)

            with patch.object(tool, "_get_filtered_endpoints", return_value=[]):
                result = tool.run([])
                assert result == 0

    @patch("pathlib.Path.exists")
    def test_run_opencode_not_installed(self, mock_exists, opencode_config):
        """Test run method when OpenCode is not installed."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        # Mock OpenCode as not installed
        mock_exists.return_value = False

        with patch.object(tool, "_ensure_tool_installed", return_value=False):
            result = tool.run([])
            assert result == 1

    @patch("pathlib.Path.exists")
    @patch("code_assistant_manager.tools.select_model")
    @patch("subprocess.run")
    def test_run_with_model_selection(self, mock_subprocess, mock_select_model, mock_exists, opencode_config):
        """Test complete run workflow with model selection."""
        config = ConfigManager(opencode_config)
        tool = OpenCodeTool(config)

        # Mock OpenCode as installed
        mock_exists.return_value = True

        # Mock model selection
        mock_select_model.return_value = (True, "gpt-4")

        # Mock subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="gpt-4\ngpt-3.5-turbo")

        with patch.object(tool, "_get_filtered_endpoints", return_value=["test-provider"]):
            with patch.object(tool.endpoint_manager, "get_endpoint_config") as mock_get_config:
                mock_get_config.return_value = (True, {
                    "endpoint": "https://api.test.com/v1",
                    "list_models_cmd": "echo gpt-4 gpt-3.5-turbo"
                })

                result = tool.run([])
                assert result == 0