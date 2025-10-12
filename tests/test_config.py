"""Tests for code_assistant_manager.config module."""

import json
import tempfile
from pathlib import Path

import pytest

from code_assistant_manager.config import (
    ConfigManager,
    validate_api_key,
    validate_model_id,
    validate_url,
)


class TestValidateFunctions:
    """Test validation functions."""

    def test_validate_url_valid_https(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://api.example.com") is True

    def test_validate_url_valid_http(self):
        """Test valid HTTP URL."""
        assert validate_url("http://localhost:8000") is True

    def test_validate_url_localhost(self):
        """Test localhost URL."""
        assert validate_url("http://localhost:5000") is True

    def test_validate_url_loopback(self):
        """Test loopback IP."""
        assert validate_url("http://127.0.0.1:8000") is True

    def test_validate_url_ip_address(self):
        """Test IP address."""
        assert validate_url("https://192.168.1.1:4142") is True

    def test_validate_url_with_path(self):
        """Test URL with path."""
        assert validate_url("https://api.example.com/v1/models") is True

    def test_validate_url_empty(self):
        """Test empty URL."""
        assert validate_url("") is False

    def test_validate_url_too_long(self):
        """Test URL that's too long."""
        long_url = "https://" + "a" * 2050
        assert validate_url(long_url) is False

    def test_validate_url_invalid_format(self):
        """Test invalid URL format."""
        assert validate_url("not-a-url") is False

    def test_validate_url_missing_protocol(self):
        """Test URL missing protocol."""
        assert validate_url("example.com") is False

    def test_validate_api_key_valid(self):
        """Test valid API key."""
        assert validate_api_key("sk-1234567890abcdef") is True

    def test_validate_api_key_with_dots(self):
        """Test API key with dots."""
        assert validate_api_key("sk-1234.5678.abcd") is True

    def test_validate_api_key_with_hyphens(self):
        """Test API key with hyphens."""
        assert validate_api_key("sk-1234-5678-abcd") is True

    def test_validate_api_key_with_underscores(self):
        """Test API key with underscores."""
        assert validate_api_key("sk_1234_5678_abcd") is True

    def test_validate_api_key_with_equals(self):
        """Test API key with equals (base64)."""
        assert validate_api_key("YWJjZGVmZ2hpams=") is True

    def test_validate_api_key_too_short(self):
        """Test API key that's too short."""
        assert validate_api_key("short") is False

    def test_validate_api_key_empty(self):
        """Test empty API key."""
        assert validate_api_key("") is False

    def test_validate_api_key_invalid_chars(self):
        """Test API key with invalid characters."""
        assert validate_api_key("sk-1234@5678!abcd") is False

    def test_validate_model_id_valid(self):
        """Test valid model ID."""
        assert validate_model_id("gpt-4-turbo") is True

    def test_validate_model_id_with_slash(self):
        """Test model ID with slash."""
        assert validate_model_id("openai/gpt-4") is True

    def test_validate_model_id_with_colon(self):
        """Test model ID with colon."""
        assert validate_model_id("claude-3:sonnet") is True

    def test_validate_model_id_with_dots(self):
        """Test model ID with dots."""
        assert validate_model_id("v1.2.3-model") is True

    def test_validate_model_id_invalid_chars(self):
        """Test model ID with invalid characters."""
        assert validate_model_id("gpt@4") is False

    def test_validate_model_id_with_spaces(self):
        """Test model ID with spaces."""
        assert validate_model_id("gpt 4") is False


class TestConfigManager:
    """Test ConfigManager class."""

    @pytest.fixture
    def temp_config(self):
        """Create a temporary config file for testing."""
        import json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "common": {
                    "http_proxy": "http://proxy.example.com:3128/",
                    "https_proxy": "http://proxy.example.com:3128/",
                    "cache_ttl_seconds": 3600,
                },
                "endpoints": {
                    "endpoint1": {
                        "endpoint": "https://api.example.com",
                        "api_key": "test-key-12345",
                        "description": "Test Endpoint 1",
                        "supported_client": "claude,codex",
                    },
                    "endpoint2": {
                        "endpoint": "https://api2.example.com",
                        "api_key_env": "API_KEY_2",
                        "description": "Test Endpoint 2",
                        "list_models_cmd": "echo model1 model2",
                        "use_proxy": True,
                    },
                },
            }
            json.dump(config_data, f, indent=2)
            config_path = f.name
        yield config_path
        Path(config_path).unlink()

    def test_config_manager_initialization(self, temp_config):
        """Test ConfigManager initialization."""
        config = ConfigManager(temp_config)
        assert config.config_path == Path(temp_config)

    def test_get_sections(self, temp_config):
        """Test getting sections from config."""
        config = ConfigManager(temp_config)
        sections = config.get_sections()
        assert "endpoint1" in sections
        assert "endpoint2" in sections
        assert "common" not in sections

    def test_get_sections_include_common(self, temp_config):
        """Test getting sections including common."""
        config = ConfigManager(temp_config)
        # In JSON format, get_sections always returns only endpoint names
        # The exclude_common parameter is kept for API compatibility but doesn't affect behavior
        sections = config.get_sections(exclude_common=False)
        assert "common" not in sections  # Common is separate in JSON format

    def test_get_value(self, temp_config):
        """Test getting a value from config."""
        config = ConfigManager(temp_config)
        value = config.get_value("endpoint1", "endpoint")
        assert value == "https://api.example.com"

    def test_get_value_default(self, temp_config):
        """Test getting a value with default."""
        config = ConfigManager(temp_config)
        value = config.get_value("endpoint1", "nonexistent", "default")
        assert value == "default"

    def test_get_endpoint_config(self, temp_config):
        """Test getting full endpoint config."""
        config = ConfigManager(temp_config)
        ep_config = config.get_endpoint_config("endpoint1")
        assert ep_config["endpoint"] == "https://api.example.com"
        assert ep_config["api_key"] == "test-key-12345"
        assert ep_config["description"] == "Test Endpoint 1"
        assert ep_config["supported_client"] == "claude,codex"

    def test_get_endpoint_config_with_boolean(self, temp_config):
        """Test getting endpoint config with boolean values."""
        config = ConfigManager(temp_config)
        ep_config = config.get_endpoint_config("endpoint2")
        # Boolean values should be converted to strings
        assert ep_config["use_proxy"] == "true"

    def test_get_endpoint_config_missing(self, temp_config):
        """Test getting missing endpoint config."""
        config = ConfigManager(temp_config)
        ep_config = config.get_endpoint_config("nonexistent")
        assert ep_config == {}

    def test_get_common_config(self, temp_config):
        """Test getting common config."""
        config = ConfigManager(temp_config)
        common = config.get_common_config()
        assert common["http_proxy"] == "http://proxy.example.com:3128/"
        assert common["cache_ttl_seconds"] == "3600"

    def test_reload(self, temp_config):
        """Test reloading config."""
        config = ConfigManager(temp_config)
        sections_before = config.get_sections()
        config.reload()
        sections_after = config.get_sections()
        assert sections_before == sections_after

    def test_file_not_found(self):
        """Test ConfigManager with non-existent file."""
        with pytest.raises(FileNotFoundError):
            ConfigManager("/nonexistent/path/config.json")

    def test_load_env_file(self, temp_config):
        """Test loading .env file."""
        import os

        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=test_value\n")
            f.write("API_KEY=secret123\n")
            env_path = f.name

        try:
            config = ConfigManager(temp_config)
            config.load_env_file(env_path)
            assert os.environ.get("TEST_VAR") == "test_value"
            assert os.environ.get("API_KEY") == "secret123"
        finally:
            Path(env_path).unlink()
            os.environ.pop("TEST_VAR", None)
            os.environ.pop("API_KEY", None)


class TestConfigManagerEdgeCases:
    """Test edge cases in ConfigManager."""

    def test_get_value_with_boolean_conversion(self):
        """Test getting boolean values converted to strings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "endpoints": {
                        "test": {"use_proxy": True, "keep_proxy_config": False}
                    }
                },
                f,
            )
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            assert config.get_value("test", "use_proxy") == "true"
            assert config.get_value("test", "keep_proxy_config") == "false"
        finally:
            Path(config_path).unlink()

    def test_get_value_with_numeric_conversion(self):
        """Test getting numeric values converted to strings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"common": {"cache_ttl_seconds": 3600, "max_retries": 5}}, f)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            assert config.get_value("common", "cache_ttl_seconds") == "3600"
            assert config.get_value("common", "max_retries") == "5"
        finally:
            Path(config_path).unlink()

    def test_get_value_with_whitespace_stripping(self):
        """Test that values with whitespace are stripped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "endpoints": {
                        "test": {
                            "endpoint": "  https://api.example.com  ",
                            "api_key": "\tkey123\n",
                        }
                    }
                },
                f,
            )
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            assert config.get_value("test", "endpoint") == "https://api.example.com"
            assert config.get_value("test", "api_key") == "key123"
        finally:
            Path(config_path).unlink()

    def test_get_endpoint_config_empty_endpoint(self):
        """Test getting config for endpoint with no values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"endpoints": {"empty": {}}}, f)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            ep_config = config.get_endpoint_config("empty")
            assert ep_config == {}
        finally:
            Path(config_path).unlink()

    def test_get_common_config_missing(self):
        """Test getting common config when it doesn't exist."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"endpoints": {}}, f)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            common = config.get_common_config()
            assert common == {}
        finally:
            Path(config_path).unlink()

    def test_load_env_file_nonexistent(self):
        """Test loading non-existent .env file."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"endpoints": {}}, f)
            config_path = f.name

        try:
            config = ConfigManager(config_path)
            # Should not raise error
            config.load_env_file("/nonexistent/.env")
        finally:
            Path(config_path).unlink()

    def test_load_env_file_with_comments_and_empty_lines(self):
        """Test loading .env file with comments and empty lines."""
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"endpoints": {}}, f)
            config_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("VAR1=value1\n")
            f.write("  # Another comment\n")
            f.write("VAR2=value2\n")
            f.write("\n")
            env_path = f.name

        try:
            config = ConfigManager(config_path)
            config.load_env_file(env_path)
            assert os.environ.get("VAR1") == "value1"
            assert os.environ.get("VAR2") == "value2"
        finally:
            Path(config_path).unlink()
            Path(env_path).unlink()
            os.environ.pop("VAR1", None)
            os.environ.pop("VAR2", None)

    def test_load_env_file_with_quoted_values(self):
        """Test loading .env file with quoted values."""
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"endpoints": {}}, f)
            config_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('VAR1="quoted value"\n')
            f.write("VAR2='single quoted'\n")
            f.write("VAR3=unquoted\n")
            env_path = f.name

        try:
            config = ConfigManager(config_path)
            config.load_env_file(env_path)
            assert os.environ.get("VAR1") == "quoted value"
            assert os.environ.get("VAR2") == "single quoted"
            assert os.environ.get("VAR3") == "unquoted"
        finally:
            Path(config_path).unlink()
            Path(env_path).unlink()
            os.environ.pop("VAR1", None)
            os.environ.pop("VAR2", None)
            os.environ.pop("VAR3", None)
