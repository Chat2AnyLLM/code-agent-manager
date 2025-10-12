"""Pytest configuration and fixtures."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_terminal_size():
    """Mock terminal size for consistent testing."""
    from unittest.mock import patch

    with patch("shutil.get_terminal_size", return_value=(80, 24)):
        yield


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing with comprehensive test data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {
                "cache_ttl_seconds": 3600,
                "http_proxy": "http://proxy.example.com:3128/",
                "https_proxy": "http://proxy.example.com:3128/",
            },
            "endpoints": {
                "endpoint1": {
                    "endpoint": "https://api1.example.com",
                    "api_key": "key1",
                    "description": "Test Endpoint",
                    "list_models_cmd": "echo model1 model2",
                    "supported_client": "claude,codex,qwen,codebuddy,droid",
                },
                "endpoint2": {
                    "endpoint": "https://api2.example.com",
                    "api_key_env": "API_KEY_2",
                    "description": "Test Endpoint 2",
                    "use_proxy": True,
                    "keep_proxy_config": False,
                },
            },
        }
        json.dump(config_data, f, indent=2)
        config_path = f.name
    yield config_path
    Path(config_path).unlink()


@pytest.fixture
def temp_config_simple():
    """Create a simple temporary config file for basic testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "endpoint1": {
                    "endpoint": "https://api.example.com",
                    "api_key": "key1",
                    "description": "Test Endpoint",
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
    from code_assistant_manager.config import ConfigManager

    return ConfigManager(temp_config)
