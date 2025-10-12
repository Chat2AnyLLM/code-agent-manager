"""Integration tests for code_assistant_manager."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager
from code_assistant_manager.tools import ClaudeTool, CodexTool, QwenTool


@pytest.fixture
def integration_config():
    """Create a comprehensive config file for integration testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {
                "http_proxy": "http://proxy.example.com:3128/",
                "https_proxy": "http://proxy.example.com:3128/",
                "cache_ttl_seconds": 3600,
            },
            "endpoints": {
                "test-endpoint": {
                    "endpoint": "https://api.test.com/v1",
                    "api_key": "test-key-12345",
                    "description": "Test Endpoint for Integration",
                    "list_models_cmd": "echo gpt-4 gpt-3.5-turbo claude-3",
                    "supported_client": "claude,codex,qwen",
                    "keep_proxy_config": False,
                    "use_proxy": False,
                }
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


class TestModelSelectionFlow:
    """Integration tests for the complete model selection flow."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_full_endpoint_and_model_selection(
        self, mock_menu, mock_subprocess, integration_config
    ):
        """Test complete flow of endpoint and model selection."""
        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        # Mock subprocess to return models
        mock_subprocess.return_value = MagicMock(
            stdout="gpt-4\ngpt-3.5-turbo\nclaude-3", returncode=0
        )

        # Mock menu selections: endpoint selection
        mock_menu.return_value = (True, 0)

        # Select endpoint
        success, endpoint_name = endpoint_manager.select_endpoint("claude")
        assert success is True
        assert endpoint_name == "test-endpoint"

        # Get endpoint config
        success, endpoint_config = endpoint_manager.get_endpoint_config(endpoint_name)
        assert success is True
        assert endpoint_config["endpoint"] == "https://api.test.com/v1"

        # Fetch models
        success, models = endpoint_manager.fetch_models(endpoint_name, endpoint_config)
        assert success is True
        assert len(models) >= 3
        assert "gpt-4" in models

    @patch("subprocess.run")
    @patch("code_assistant_manager.ui.display_centered_menu")
    @patch("code_assistant_manager.tools.select_two_models")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_claude_tool_complete_workflow(
        self, mock_select_models, mock_menu, mock_run, integration_config
    ):
        """Test complete Claude tool workflow."""
        config = ConfigManager(integration_config)
        tool = ClaudeTool(config)

        # Mock tool is installed
        with patch.object(tool, "_check_command_available", return_value=True):
            # User chooses to use current version
            mock_menu.return_value = (True, 1)

            # Mock endpoint selection
            with patch.object(
                tool.endpoint_manager,
                "select_endpoint",
                return_value=(True, "test-endpoint"),
            ):
                # Mock endpoint config
                endpoint_config = {
                    "endpoint": "https://api.test.com/v1",
                    "actual_api_key": "fake-test-key-do-not-use",
                    "list_models_cmd": "echo model1 model2",
                }
                with patch.object(
                    tool.endpoint_manager,
                    "get_endpoint_config",
                    return_value=(True, endpoint_config),
                ):
                    # Mock models fetch
                    with patch.object(
                        tool.endpoint_manager,
                        "fetch_models",
                        return_value=(True, ["claude-3", "claude-2"]),
                    ):
                        # Mock model selection
                        mock_select_models.return_value = (
                            True,
                            ("claude-3", "claude-2"),
                        )
                        mock_run.return_value = MagicMock(returncode=0)

                        result = tool.run([])
                        assert result == 0

    @patch("subprocess.run")
    @patch("code_assistant_manager.ui.display_centered_menu")
    @patch("code_assistant_manager.tools.select_model")
    @patch.dict(os.environ, {"CODE_ASSISTANT_MANAGER_NONINTERACTIVE": "1"})
    def test_qwen_tool_complete_workflow(
        self, mock_select_model, mock_menu, mock_run, integration_config
    ):
        """Test complete Qwen tool workflow."""
        config = ConfigManager(integration_config)
        tool = QwenTool(config)

        with patch.object(tool, "_check_command_available", return_value=True):
            mock_menu.return_value = (True, 1)

            with patch.object(
                tool.endpoint_manager,
                "select_endpoint",
                return_value=(True, "test-endpoint"),
            ):
                endpoint_config = {
                    "endpoint": "https://api.test.com/v1",
                    "actual_api_key": "fake-test-key-do-not-use",
                    "list_models_cmd": "echo model1",
                }
                with patch.object(
                    tool.endpoint_manager,
                    "get_endpoint_config",
                    return_value=(True, endpoint_config),
                ):
                    with patch.object(
                        tool.endpoint_manager,
                        "fetch_models",
                        return_value=(True, ["qwen-model"]),
                    ):
                        mock_select_model.return_value = (True, "qwen-model")
                        mock_run.return_value = MagicMock(returncode=0)

                        result = tool.run([])
                        assert result == 0


class TestEndpointManagerIntegration:
    """Integration tests for EndpointManager."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_cache_persistence(self, mock_subprocess, integration_config):
        """Test that model cache persists correctly."""
        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        # First fetch - create cache
        mock_subprocess.return_value = MagicMock(
            stdout="model1\nmodel2\nmodel3", returncode=0
        )

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "fake-test-key-do-not-use",
            "list_models_cmd": "echo model1 model2 model3",
            "keep_proxy_config": "false",
        }

        success, models = endpoint_manager.fetch_models(
            "test-endpoint", endpoint_config
        )
        assert success is True
        assert len(models) >= 3

        # Check cache file exists
        cache_file = (
            endpoint_manager.cache_dir
            / "code_assistant_manager_models_cache_test-endpoint.txt"
        )
        assert cache_file.exists()

        # Read cache content
        with open(cache_file, "r") as f:
            lines = f.readlines()

        # First line should be timestamp
        assert lines[0].strip().isdigit()

        # Rest should be models
        cached_models = [line.strip() for line in lines[1:] if line.strip()]
        assert len(cached_models) >= 3

        # Cleanup
        cache_file.unlink(missing_ok=True)

    def test_proxy_configuration_handling(self, integration_config):
        """Test proxy configuration is handled correctly."""
        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        success, endpoint_config = endpoint_manager.get_endpoint_config("test-endpoint")
        assert success is True

        # Check proxy settings
        proxy_settings = json.loads(endpoint_config.get("proxy_settings", "{}"))
        # use_proxy is false, so proxy_settings should be empty
        assert proxy_settings == {}

    def test_api_key_resolution_priority(self, integration_config):
        """Test API key resolution follows correct priority."""
        import os

        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        # Test 1: Config file key
        endpoint_config_data = config.get_endpoint_config("test-endpoint")
        api_key = endpoint_manager._resolve_api_key(
            "test-endpoint", endpoint_config_data
        )
        assert api_key == "test-key-12345"

        # Test 2: Environment variable override
        os.environ["API_KEY_TEST_ENDPOINT"] = "env-key"
        try:
            api_key = endpoint_manager._resolve_api_key(
                "test-endpoint", endpoint_config_data
            )
            assert api_key == "env-key"
        finally:
            os.environ.pop("API_KEY_TEST_ENDPOINT", None)


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""

    def test_config_reload_updates_data(self, integration_config):
        """Test that reloading config updates the data."""
        config = ConfigManager(integration_config)

        # Get initial sections
        sections_before = config.get_sections()
        assert "test-endpoint" in sections_before

        # Modify config file
        with open(integration_config, "r") as f:
            data = json.load(f)

        data["endpoints"]["new-endpoint"] = {
            "endpoint": "https://new.example.com",
            "api_key": "new-key",
        }

        with open(integration_config, "w") as f:
            json.dump(data, f, indent=2)

        # Reload
        config.reload()

        # Check new sections
        sections_after = config.get_sections()
        assert "new-endpoint" in sections_after
        assert "test-endpoint" in sections_after

    def test_env_file_loading(self, integration_config):
        """Test environment file loading integration."""
        import os

        config = ConfigManager(integration_config)

        # Create temp .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR_1=value1\n")
            f.write('TEST_VAR_2="value2"\n')
            f.write("# Comment line\n")
            f.write("\n")
            f.write("TEST_VAR_3='value3'\n")
            env_path = f.name

        try:
            config.load_env_file(env_path)

            assert os.environ.get("TEST_VAR_1") == "value1"
            assert os.environ.get("TEST_VAR_2") == "value2"
            assert os.environ.get("TEST_VAR_3") == "value3"
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR_1", None)
            os.environ.pop("TEST_VAR_2", None)
            os.environ.pop("TEST_VAR_3", None)


class TestErrorRecovery:
    """Integration tests for error recovery."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_model_fetch_timeout_handling(self, mock_subprocess, integration_config):
        """Test handling of model fetch timeout."""
        from subprocess import TimeoutExpired

        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        # Simulate timeout
        mock_subprocess.side_effect = TimeoutExpired("cmd", 30)

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "fake-test-key-do-not-use",
            "list_models_cmd": "sleep 100",
            "keep_proxy_config": "false",
        }

        success, models = endpoint_manager.fetch_models(
            "test-endpoint", endpoint_config
        )
        assert success is False
        assert models == []

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_model_fetch_error_handling(self, mock_subprocess, integration_config):
        """Test handling of model fetch errors."""
        config = ConfigManager(integration_config)
        endpoint_manager = EndpointManager(config)

        # Simulate command error
        mock_subprocess.return_value = MagicMock(
            stdout="", stderr="Error: Connection refused", returncode=1
        )

        endpoint_config = {
            "endpoint": "https://api.test.com/v1",
            "actual_api_key": "test-key",
            "list_models_cmd": "curl https://nonexistent",
            "keep_proxy_config": "false",
        }

        success, models = endpoint_manager.fetch_models(
            "test-endpoint", endpoint_config
        )
        # Should succeed but return empty list
        assert success is True
        assert models == []

    def test_invalid_endpoint_url_validation(self, integration_config):
        """Test validation of invalid endpoint URLs."""
        from code_assistant_manager.config import validate_url

        # Test various invalid URLs
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://invalid.com") is False
        assert validate_url("http://") is False

        # Test valid URLs
        assert validate_url("https://api.example.com") is True
        assert validate_url("http://localhost:8000") is True
        assert validate_url("http://127.0.0.1:5000") is True
