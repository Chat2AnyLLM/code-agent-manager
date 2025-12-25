"""Tests for code_assistant_manager.tools module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools import (
    ClaudeTool,
    CLITool,
    CodeBuddyTool,
    CodexTool,
    CopilotTool,
    DroidTool,
    GeminiTool,
    GooseTool,
    QwenTool,
)


# Parametrized fixture for all tools that need similar testing
@pytest.fixture(
    params=[
        (
            "claude",
            ClaudeTool,
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_MODEL",
        ),
        ("codex", CodexTool, "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"),
        ("qwen", QwenTool, "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"),
        (
            "codebuddy",
            CodeBuddyTool,
            "OPENAI_BASE_URL",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
        ),
    ]
)
def tool_class_and_env(request):
    """Parametrized fixture for tool classes and their environment variables."""
    tool_name, tool_class, base_url_env, api_key_env, model_env = request.param
    return tool_name, tool_class, base_url_env, api_key_env, model_env


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
                    "supported_client": "claude,codex,qwen,codebuddy,droid",
                }
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


@pytest.fixture
def config_manager(temp_config):
    """Create a ConfigManager instance."""
    return ConfigManager(temp_config)


class TestCLIToolBase:
    """Test CLITool base class."""

    def test_cli_tool_initialization(self, config_manager):
        """Test CLITool initialization."""
        # CLITool is abstract, so we use a concrete subclass
        tool = ClaudeTool(config_manager)
        assert tool.config is not None
        assert tool.endpoint_manager is not None

    @patch("subprocess.run")
    def test_check_command_available(self, mock_run, config_manager):
        """Test checking if command is available."""
        tool = ClaudeTool(config_manager)
        mock_run.return_value = MagicMock(returncode=0)
        assert tool._check_command_available("claude") is True

    @patch("subprocess.run")
    def test_check_command_not_available(self, mock_run, config_manager):
        """Test checking if command is not available."""
        from subprocess import CalledProcessError

        tool = ClaudeTool(config_manager)
        mock_run.side_effect = CalledProcessError(1, "cmd")
        assert tool._check_command_available("nonexistent") is False

    def test_set_node_tls_env(self, config_manager):
        """Test setting Node.js TLS environment variables."""
        tool = ClaudeTool(config_manager)
        env = {}
        tool._set_node_tls_env(env)
        assert env["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"


class TestAllTools:
    """Parametrized tests for all tools."""

    def test_tool_initialization(self, tool_class_and_env, config_manager):
        """Test that all tools initialize correctly."""
        tool_name, tool_class, base_url_env, api_key_env, model_env = tool_class_and_env
        tool = tool_class(config_manager)
        assert tool.config is not None
        assert tool.endpoint_manager is not None
        assert tool.command_name == tool_name

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch("code_assistant_manager.tools.EndpointManager")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_tool_successful_run(
        self, mock_em_class, mock_run, tool_class_and_env, config_manager
    ):
        """Test successful execution for all tools."""
        from unittest.mock import MagicMock
        from subprocess import CompletedProcess

        tool_name, tool_class, base_url_env, api_key_env, model_env = tool_class_and_env

        # Set up subprocess.run mock to return successful completion
        mock_process = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        mock_run.return_value = mock_process

        mock_em = MagicMock()
        mock_em_class.return_value = mock_em

        mock_em.select_endpoint.return_value = (True, "endpoint1")
        mock_em.get_endpoint_config.return_value = (
            True,
            {"endpoint": "https://api.example.com", "actual_api_key": "key123"},
        )

        if tool_name == "claude":
            mock_em.fetch_models.return_value = (True, ["claude-3", "claude-2"])
            from code_assistant_manager.tools import select_two_models

            with patch(
                "code_assistant_manager.tools.select_two_models",
                return_value=(True, ("claude-3", "claude-2")),
            ):
                tool = tool_class(config_manager)
                with patch.object(tool, "_ensure_tool_installed", return_value=True):
                    result = tool.run([])
                    assert result == 0
        else:
            mock_em.fetch_models.return_value = (True, ["model1", "model2"])
            from code_assistant_manager.tools import select_model

            with patch(
                "code_assistant_manager.tools.select_model",
                return_value=(True, "model1"),
            ):
                tool = tool_class(config_manager)
                with patch.object(tool, "_ensure_tool_installed", return_value=True):
                    result = tool.run([])
                    assert result == 0

    def test_tool_package_not_available(self, tool_class_and_env, config_manager):
        """Test all tools when package is not available."""
        tool_name, tool_class, base_url_env, api_key_env, model_env = tool_class_and_env
        tool = tool_class(config_manager)

        with patch.object(tool, "_ensure_tool_installed", return_value=False):
            result = tool.run([])
            assert result == 1


class TestDroidTool:
    """Test DroidTool."""

    def test_droid_build_models_json(self, config_manager):
        """Test building models JSON for Droid."""
        tool = DroidTool(config_manager)
        entries = [
            "model1 [ep1]|https://api.com|key|provider|16384",
            "model2 [ep2]|https://api2.com|key2|provider|65536",
        ]
        models = tool._build_models_json(entries)
        assert len(models) == 2
        assert models[0]["model"] == "model1"
        assert models[0]["base_url"] == "https://api.com"
        assert models[1]["max_tokens"] == 65536

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch("code_assistant_manager.tools.select_model")
    @patch.object(DroidTool, "_ensure_tool_installed", return_value=True)
    @patch.object(DroidTool, "_check_command_available", return_value=True)
    @patch("code_assistant_manager.tools.EndpointManager")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_droid_tool_run_success(
        self,
        mock_em_class,
        mock_check,
        mock_install,
        mock_select,
        mock_run,
        config_manager,
    ):
        """Test successful Droid tool execution."""
        # Setup mock endpoint manager instance

        mock_em = MagicMock()

        mock_em_class.return_value = mock_em

        # Mock config.get_sections to return endpoints
        with patch.object(config_manager, 'get_sections', return_value=["endpoint1"]):
            mock_em.select_endpoint = MagicMock()
            mock_em.get_endpoint_config.return_value = (
                True,
                {"endpoint": "https://api.example.com", "actual_api_key": "key123"},
            )
            mock_em.fetch_models.return_value = (True, ["model1"])
            mock_select.return_value = (True, "model1")
            mock_em._is_client_supported.return_value = True

            # Mock subprocess.run to return success
            mock_run.return_value.returncode = 0

            tool = DroidTool(config_manager)

            result = tool.run([])
            assert result == 0


class TestCopilotTool:
    """Test CopilotTool."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(CopilotTool, "_ensure_tool_installed", return_value=True)
    def test_copilot_tool_run_success(self, mock_install, mock_run, config_manager):
        """Test successful Copilot tool execution."""
        mock_run.return_value.returncode = 0
        tool = CopilotTool(config_manager)
        result = tool.run([])
        assert result == 0

    @patch.dict("os.environ", {}, clear=True)
    @patch.object(CopilotTool, "_ensure_tool_installed", return_value=True)
    def test_copilot_tool_missing_token(self, mock_install, config_manager):
        """Test Copilot tool without GITHUB_TOKEN."""
        tool = CopilotTool(config_manager)
        result = tool.run([])
        assert result == 1


class TestGooseTool:
    """Test GooseTool."""

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GooseTool, "_ensure_tool_installed", return_value=True)
    def test_goose_tool_run_success(self, mock_install, mock_run, config_manager):
        """Test successful Goose tool execution."""
        mock_run.return_value.returncode = 0
        tool = GooseTool(config_manager)
        result = tool.run([])
        assert result == 0

    @patch.object(GooseTool, "_ensure_tool_installed", return_value=False)
    def test_goose_tool_not_installed(self, mock_install, config_manager):
        """Test Goose tool when not installed."""
        tool = GooseTool(config_manager)
        result = tool.run([])
        assert result == 1


class TestGeminiTool:
    """Test GeminiTool."""

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=True)
    @patch.object(GeminiTool, "_check_command_available", return_value=True)
    @patch("code_assistant_manager.tools.EndpointManager")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_gemini_tool_run_success(
        self, mock_em_class, mock_check, mock_install, mock_run, config_manager
    ):
        """Test successful Gemini tool execution."""
        # Setup mock endpoint manager instance
        mock_em = MagicMock()
        mock_em_class.return_value = mock_em

        mock_em.select_endpoint.return_value = (True, "endpoint1")
        mock_em.get_endpoint_config.return_value = (
            True,
            {"endpoint": "https://api.example.com", "actual_api_key": "key123"},
        )
        mock_em.fetch_models.return_value = (True, ["gemini-1.5"])

        # Mock the model selector
        with patch("code_assistant_manager.menu.model_selector.ModelSelector.select_model_with_endpoint_info",
                   return_value=(True, "gemini-1.5")):
            # Mock subprocess.run to return success
            mock_run.return_value.returncode = 0

            tool = GeminiTool(config_manager)
            result = tool.run([])
            assert result == 0

    @patch.object(GeminiTool, "_ensure_tool_installed", return_value=False)
    def test_gemini_tool_package_not_available(self, mock_install, config_manager):
        """Test Gemini tool when package is not available."""
        tool = GeminiTool(config_manager)
        result = tool.run([])
        assert result == 1


class TestToolEnvironmentVariables:
    """Test environment variable setup in tools."""

    @patch("code_assistant_manager.tools.subprocess.run")
    @patch("code_assistant_manager.tools.select_two_models")
    @patch.object(ClaudeTool, "_ensure_tool_installed", return_value=True)
    @patch("code_assistant_manager.tools.EndpointManager")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_claude_environment_variables(
        self, mock_em_class, mock_install, mock_select, mock_run, config_manager
    ):
        """Test that Claude sets correct environment variables."""
        # Setup mock endpoint manager instance

        mock_em = MagicMock()

        mock_em_class.return_value = mock_em

        mock_em.select_endpoint.return_value = (True, "endpoint1")
        mock_em.get_endpoint_config.return_value = (
            True,
            {"endpoint": "https://api.example.com", "actual_api_key": "key123"},
        )
        mock_em.fetch_models.return_value = (True, ["claude-3"])
        mock_select.return_value = (True, ("claude-3", "claude-2"))

        tool = ClaudeTool(config_manager)

        tool.run([])

        # Get the environment passed to subprocess.run
        env_used = mock_run.call_args[1]["env"]
        assert env_used["ANTHROPIC_BASE_URL"] == "https://api.example.com"
        assert env_used["ANTHROPIC_AUTH_TOKEN"] == "key123"
        assert env_used["ANTHROPIC_MODEL"] == "claude-3"
        assert env_used["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"


class TestToolErrorHandling:
    """Test error handling in tools."""

    @patch.object(ClaudeTool, "_ensure_tool_installed", return_value=True)
    @patch("code_assistant_manager.tools.EndpointManager")
    def test_claude_endpoint_selection_failure(
        self, mock_em_class, mock_install, config_manager
    ):
        """Test Claude tool when endpoint selection fails."""
        # Setup mock endpoint manager instance

        mock_em = MagicMock()

        mock_em_class.return_value = mock_em

        mock_em.select_endpoint.return_value = (False, None)

        tool = ClaudeTool(config_manager)

        result = tool.run([])
        assert result == 1

    @patch(
        "code_assistant_manager.tools.subprocess.run", side_effect=KeyboardInterrupt()
    )
    @patch("code_assistant_manager.tools.select_two_models")
    @patch.object(ClaudeTool, "_ensure_tool_installed", return_value=True)
    @patch("code_assistant_manager.tools.EndpointManager")
    def test_claude_keyboard_interrupt(
        self, mock_em_class, mock_install, mock_select, mock_run, config_manager
    ):
        """Test Claude tool handling keyboard interrupt."""
        # Setup mock endpoint manager instance

        mock_em = MagicMock()

        mock_em_class.return_value = mock_em

        mock_em.select_endpoint.return_value = (True, "endpoint1")
        mock_em.get_endpoint_config.return_value = (
            True,
            {"endpoint": "https://api.example.com", "actual_api_key": "key123"},
        )
        mock_em.fetch_models.return_value = (True, ["model1"])
        mock_select.return_value = (True, ("model1", "model2"))

        tool = ClaudeTool(config_manager)

        result = tool.run([])
        assert result == 130  # Keyboard interrupt exit code
