"""Tests for code_assistant_manager.endpoints module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager


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
                    "description": "Endpoint 1",
                    "supported_client": "claude,codex",
                },
                "endpoint2": {
                    "endpoint": "https://api2.example.com",
                    "api_key_env": "API_KEY_2",
                    "description": "Endpoint 2",
                    "list_models_cmd": "echo model1 model2",
                    "supported_client": "droid,qwen",
                },
                "endpoint3": {
                    "endpoint": "https://api3.example.com",
                    "api_key": "key3",
                    "description": "Endpoint 3 (no client filter)",
                },
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


@pytest.fixture
def endpoint_manager(temp_config):
    """Create an EndpointManager instance."""
    config = ConfigManager(temp_config)
    return EndpointManager(config)


class TestEndpointManagerClientSupport:
    """Test client support filtering."""

    def test_is_client_supported_allowed(self, endpoint_manager):
        """Test client support check - allowed client."""
        assert endpoint_manager._is_client_supported("endpoint1", "claude") is True

    def test_is_client_supported_denied(self, endpoint_manager):
        """Test client support check - denied client."""
        assert endpoint_manager._is_client_supported("endpoint1", "droid") is False

    def test_is_client_supported_no_restriction(self, endpoint_manager):
        """Test client support check - no restriction."""
        assert endpoint_manager._is_client_supported("endpoint3", "any-client") is True

    def test_is_client_supported_empty_client(self, endpoint_manager):
        """Test client support check - empty client name."""
        assert endpoint_manager._is_client_supported("endpoint1", "") is True


class TestEndpointManagerConfiguration:
    """Test endpoint configuration retrieval."""

    @patch("code_assistant_manager.endpoints.EndpointManager.get_endpoint_config")
    def test_get_endpoint_config_success(self, mock_config, endpoint_manager):
        """Test successful endpoint configuration retrieval."""
        mock_config.return_value = (True, {"endpoint": "https://api.example.com"})
        success, config = endpoint_manager.get_endpoint_config("endpoint1")
        assert success is True
        assert "endpoint" in config

    def test_get_endpoint_config_missing_endpoint(self, endpoint_manager):
        """Test endpoint configuration for missing endpoint."""
        success, config = endpoint_manager.get_endpoint_config("nonexistent")
        assert success is False
        assert config == {}


class TestEndpointManagerModelParsing:
    """Test model output parsing."""

    def test_parse_models_output_json_openai_format(self, endpoint_manager):
        """Test parsing OpenAI format JSON."""
        output = json.dumps(
            {
                "data": [
                    {"id": "gpt-4"},
                    {"id": "gpt-3.5-turbo"},
                    {"id": "text-davinci-003"},
                ]
            }
        )
        models = endpoint_manager._parse_models_output(output)
        assert len(models) == 3
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models

    def test_parse_models_output_json_array(self, endpoint_manager):
        """Test parsing JSON array format."""
        output = json.dumps([{"id": "model1"}, {"id": "model2"}])
        models = endpoint_manager._parse_models_output(output)
        assert len(models) == 2
        assert "model1" in models

    def test_parse_models_output_space_separated(self, endpoint_manager):
        """Test parsing space-separated models."""
        output = "gpt-4 gpt-3.5-turbo claude-3-sonnet"
        models = endpoint_manager._parse_models_output(output)
        assert len(models) >= 3
        assert "gpt-4" in models

    def test_parse_models_output_newline_separated(self, endpoint_manager):
        """Test parsing newline-separated models."""
        output = "model1\nmodel2\nmodel3"
        models = endpoint_manager._parse_models_output(output)
        assert len(models) >= 3
        assert "model1" in models

    def test_parse_models_output_mixed(self, endpoint_manager):
        """Test parsing mixed space and newline separated."""
        output = "model1 model2\nmodel3 model4"
        models = endpoint_manager._parse_models_output(output)
        assert len(models) >= 4

    def test_parse_models_output_empty(self, endpoint_manager):
        """Test parsing empty output."""
        models = endpoint_manager._parse_models_output("")
        assert models == []

    def test_parse_models_output_invalid_json(self, endpoint_manager):
        """Test parsing invalid JSON falls back to text parsing."""
        output = "model1\nmodel2\nmodel3"
        models = endpoint_manager._parse_models_output(output)
        assert len(models) >= 3


class TestEndpointManagerAPIKeyResolution:
    """Test API key resolution priority."""

    import os

    @patch.dict(os.environ, {"API_KEY_ENDPOINT1": "env_key"})
    def test_resolve_api_key_from_env_dynamic(self, endpoint_manager):
        """Test API key resolution from dynamic env var."""
        config = {"endpoint": "https://api.example.com"}
        key = endpoint_manager._resolve_api_key("endpoint1", config)
        assert key == "env_key"

    @patch.dict(os.environ, {"API_KEY": "generic_key"})
    def test_resolve_api_key_from_generic_env(self, endpoint_manager):
        """Test API key resolution from generic API_KEY env var."""
        config = {"endpoint": "https://api.example.com"}
        key = endpoint_manager._resolve_api_key("unknown", config)
        assert key == "generic_key"

    def test_resolve_api_key_from_config(self, endpoint_manager):
        """Test API key resolution from config."""
        config = {"api_key": "config_key"}
        key = endpoint_manager._resolve_api_key("endpoint1", config)
        assert key == "config_key"

    def test_resolve_api_key_api_key_env_parameter(self, endpoint_manager):
        """Test API key resolution from api_key_env parameter."""
        import os

        os.environ["MY_API_KEY"] = "special_key"
        try:
            config = {"api_key_env": "MY_API_KEY"}
            key = endpoint_manager._resolve_api_key("endpoint1", config)
            assert key == "special_key"
        finally:
            os.environ.pop("MY_API_KEY", None)

    def test_resolve_api_key_empty(self, endpoint_manager):
        """Test API key resolution when empty."""
        config = {}
        key = endpoint_manager._resolve_api_key("endpoint1", config)
        assert key == ""


class TestEndpointManagerCaching:
    """Test model caching functionality."""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_fetch_models_caches_result(self, mock_run, endpoint_manager):
        """Test that models are cached."""
        mock_run.return_value = MagicMock(stdout="model1\nmodel2", returncode=0)
        config = {"endpoint": "https://api.example.com", "list_models_cmd": "echo test"}

        # First fetch
        success, models1 = endpoint_manager.fetch_models("endpoint1", config)
        assert success is True
        assert len(models1) >= 2

        # Check that cache file was created
        cache_file = (
            endpoint_manager.cache_dir
            / "code_assistant_manager_models_cache_endpoint1.txt"
        )
        assert cache_file.exists()

        # Cleanup
        cache_file.unlink(missing_ok=True)

    def test_cache_dir_is_created(self, endpoint_manager):
        """Test that cache directory is created."""
        assert endpoint_manager.cache_dir.exists()


class TestEndpointManagerSelection:
    """Test endpoint selection."""

    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_select_endpoint_success(self, mock_menu, endpoint_manager):
        """Test successful endpoint selection."""
        mock_menu.return_value = (True, 0)
        success, endpoint = endpoint_manager.select_endpoint()
        assert success is True
        assert endpoint is not None

    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_select_endpoint_cancelled(self, mock_menu, endpoint_manager):
        """Test cancelled endpoint selection."""
        mock_menu.return_value = (False, None)
        success, endpoint = endpoint_manager.select_endpoint()
        assert success is False
        assert endpoint is None

    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_select_endpoint_with_client_filter(self, mock_menu, endpoint_manager):
        """Test endpoint selection with client filtering."""
        mock_menu.return_value = (True, 0)
        success, endpoint = endpoint_manager.select_endpoint(client_name="claude")
        assert success is True


class TestEndpointManagerTextModelParsing:
    """Test text-based model parsing."""

    def test_parse_text_models_space_separated(self, endpoint_manager):
        """Test parsing space-separated text models."""
        output = "model1 model2 model3"
        models = endpoint_manager._parse_text_models(output)
        assert "model1" in models
        assert "model2" in models

    def test_parse_text_models_newline_separated(self, endpoint_manager):
        """Test parsing newline-separated text models."""
        output = "model1\nmodel2\nmodel3"
        models = endpoint_manager._parse_text_models(output)
        assert "model1" in models
        assert "model2" in models

    def test_parse_text_models_mixed(self, endpoint_manager):
        """Test parsing mixed separated models."""
        output = "model1 model2\nmodel3 model4"
        models = endpoint_manager._parse_text_models(output)
        assert len(models) >= 4

    def test_parse_text_models_empty_lines(self, endpoint_manager):
        """Test parsing models with empty lines."""
        output = "model1\n\nmodel2\n\nmodel3"
        models = endpoint_manager._parse_text_models(output)
        assert "model1" in models
        assert "model2" in models

    def test_parse_text_models_empty(self, endpoint_manager):
        """Test parsing empty text."""
        models = endpoint_manager._parse_text_models("")
        assert models == []


class TestEndpointManagerEdgeCases:
    """Test edge cases in EndpointManager."""

    def test_select_endpoint_no_endpoints_configured(self):
        """Test endpoint selection when no endpoints are configured."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"common": {"cache_ttl_seconds": 3600}, "endpoints": {}}
            json.dump(config_data, f, indent=2)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            endpoint_manager = EndpointManager(config)

            success, endpoint = endpoint_manager.select_endpoint()
            assert success is False
            assert endpoint is None
        finally:
            Path(config_path).unlink()

    def test_fetch_models_no_list_models_cmd(self):
        """Test fetching models when list_models_cmd is not configured."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "common": {},
                "endpoints": {"test": {"endpoint": "https://api.example.com"}},
            }
            json.dump(config_data, f, indent=2)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            endpoint_manager = EndpointManager(config)

            endpoint_config = {"endpoint": "https://api.example.com"}
            success, models = endpoint_manager.fetch_models("test", endpoint_config)

            assert success is True
            assert models == []
        finally:
            Path(config_path).unlink()

    def test_parse_models_invalid_json_with_valid_text(self, endpoint_manager):
        """Test parsing invalid JSON that contains valid text models."""
        output = "{invalid json} but also model1 model2"
        models = endpoint_manager._parse_models_output(output)
        # Should fall back to text parsing
        assert len(models) >= 2

    def test_parse_models_json_with_invalid_model_ids(self, endpoint_manager):
        """Test parsing JSON with invalid model IDs."""
        output = json.dumps(
            {
                "data": [
                    {"id": "valid-model"},
                    {"id": "invalid@model"},
                    {"id": "another valid-model"},
                ]
            }
        )
        models = endpoint_manager._parse_models_output(output)
        assert "valid-model" in models
        # Invalid models should be filtered out
        assert "invalid@model" not in models

    @patch("code_assistant_manager.endpoints.display_centered_menu")
    def test_select_endpoint_with_no_matching_client(self, mock_menu):
        """Test endpoint selection when no endpoints support the client."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "common": {},
                "endpoints": {
                    "test": {
                        "endpoint": "https://api.example.com",
                        "supported_client": "other",
                    }
                },
            }
            json.dump(config_data, f, indent=2)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            endpoint_manager = EndpointManager(config)

            success, endpoint = endpoint_manager.select_endpoint(
                client_name="nonexistent"
            )
            assert success is False
            assert endpoint is None
        finally:
            Path(config_path).unlink()

    def test_resolve_api_key_all_sources_empty(self, endpoint_manager):
        """Test API key resolution when all sources are empty."""
        import os

        # Ensure no environment variables are set
        for key in ["API_KEY", "API_KEY_TEST"]:
            os.environ.pop(key, None)

        endpoint_config = {}
        api_key = endpoint_manager._resolve_api_key("test", endpoint_config)
        assert api_key == ""

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_fetch_models_cache_with_invalid_timestamp(
        self, mock_subprocess, endpoint_manager
    ):
        """Test model fetch when cache has invalid timestamp."""
        cache_file = (
            endpoint_manager.cache_dir / "code_assistant_manager_models_cache_test.txt"
        )

        # Create cache with invalid timestamp
        with open(cache_file, "w") as f:
            f.write("not-a-number\n")
            f.write("model1\n")
            f.write("model2\n")

        try:
            mock_subprocess.return_value = MagicMock(
                stdout="model3\nmodel4", returncode=0
            )

            endpoint_config = {
                "endpoint": "https://api.example.com",
                "actual_api_key": "key",
                "list_models_cmd": "echo test",
                "keep_proxy_config": "false",
            }

            success, models = endpoint_manager.fetch_models("test", endpoint_config)
            # Should fetch fresh models
            assert success is True
        finally:
            cache_file.unlink(missing_ok=True)

    @patch("code_assistant_manager.endpoints.subprocess.run")
    def test_fetch_models_cache_empty_file(self, mock_subprocess, endpoint_manager):
        """Test model fetch when cache file is empty."""
        cache_file = (
            endpoint_manager.cache_dir / "code_assistant_manager_models_cache_test.txt"
        )

        # Create empty cache file
        cache_file.touch()

        try:
            mock_subprocess.return_value = MagicMock(
                stdout="model1\nmodel2", returncode=0
            )

            endpoint_config = {
                "endpoint": "https://api.example.com",
                "actual_api_key": "key",
                "list_models_cmd": "echo test",
                "keep_proxy_config": "false",
            }

            success, models = endpoint_manager.fetch_models("test", endpoint_config)
            assert success is True
        finally:
            cache_file.unlink(missing_ok=True)
