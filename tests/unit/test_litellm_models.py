"""Tests for code_assistant_manager.litellm_models module."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
import json


class TestLitellmModels:
    """Test Litellm models functionality."""

    @patch('code_assistant_manager.litellm_models.requests.get')
    def test_fetch_litellm_models_success(self, mock_get):
        """Test successful model fetching."""
        from code_assistant_manager.litellm_models import fetch_litellm_models

        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"id": "model1"}, {"id": "model2"}]}
        mock_get.return_value = mock_response

        result = fetch_litellm_models("test_key", "https://example.com")

        assert result == {"data": [{"id": "model1"}, {"id": "model2"}]}
        mock_get.assert_called_once()

        # Check call arguments
        args, kwargs = mock_get.call_args
        assert args[0] == "https://example.com/v1/models"
        assert kwargs["headers"]["x-litellm-api-key"] == "test_key"
        assert kwargs["timeout"] == 30

    @patch('code_assistant_manager.litellm_models.requests.get')
    def test_fetch_litellm_models_ssl_verification_private_ip(self, mock_get):
        """Test SSL verification is disabled for private IPs."""
        from code_assistant_manager.litellm_models import fetch_litellm_models

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # Test with private IP
        fetch_litellm_models("test_key", "https://192.168.1.100:4142")

        # Check that verify=False was passed
        args, kwargs = mock_get.call_args
        assert kwargs["verify"] is False

    @patch('code_assistant_manager.litellm_models.requests.get')
    def test_fetch_litellm_models_ssl_verification_public_ip(self, mock_get):
        """Test SSL verification is enabled for public IPs."""
        from code_assistant_manager.litellm_models import fetch_litellm_models

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # Test with public hostname
        fetch_litellm_models("test_key", "https://api.example.com")

        # Check that verify=True was passed (default)
        args, kwargs = mock_get.call_args
        assert kwargs["verify"] is True

    @patch('code_assistant_manager.litellm_models.os.environ.get')
    @patch('code_assistant_manager.litellm_models.load_env')
    @patch('code_assistant_manager.litellm_models.fetch_litellm_models')
    @patch('builtins.print')
    def test_list_models_success(self, mock_print, mock_fetch, mock_load_env, mock_environ_get):
        """Test successful model listing."""
        from code_assistant_manager.litellm_models import list_models

        # Mock environment variables
        mock_environ_get.side_effect = lambda key: {
            "API_KEY_LITELLM": "test_key",
            "endpoint": "https://test.com"
        }.get(key)

        # Mock fetch response
        mock_fetch.return_value = {"data": [{"id": "model1"}, {"id": "model2"}]}

        list_models()

        # Verify load_env was called
        mock_load_env.assert_called_once()

        # Verify fetch was called with correct parameters
        mock_fetch.assert_called_once_with("test_key", "https://test.com")

        # Verify prints
        from unittest.mock import call
        mock_print.assert_has_calls([
            call("model1"),
            call("model2")
        ])

    @patch('code_assistant_manager.litellm_models.os.environ.get')
    @patch('code_assistant_manager.litellm_models.load_env')
    def test_list_models_missing_api_key(self, mock_load_env, mock_environ_get):
        """Test list_models with missing API key."""
        from code_assistant_manager.litellm_models import list_models

        # Mock missing API key
        mock_environ_get.return_value = None

        with pytest.raises(SystemExit, match="API_KEY_LITELLM environment variable is required"):
            list_models()

    @patch('code_assistant_manager.litellm_models.os.environ.get')
    @patch('code_assistant_manager.litellm_models.load_env')
    @patch('code_assistant_manager.litellm_models.ConfigManager')
    @patch('code_assistant_manager.litellm_models.fetch_litellm_models')
    def test_list_models_fallback_to_config(self, mock_fetch, mock_config_manager, mock_load_env, mock_environ_get):
        """Test list_models falls back to config when endpoint env var is missing."""
        from code_assistant_manager.litellm_models import list_models

        # Mock environment - API key present, endpoint missing
        mock_environ_get.side_effect = lambda key: {
            "API_KEY_LITELLM": "test_key",
            "endpoint": None
        }.get(key)

        # Mock config manager
        mock_config = MagicMock()
        mock_config.get_endpoint_config.return_value = {"endpoint": "https://config-endpoint.com"}
        mock_config_manager.return_value = mock_config

        # Mock fetch response
        mock_fetch.return_value = {"data": [{"id": "model1"}]}

        list_models()

        # Verify config was used
        mock_config.get_endpoint_config.assert_called_once_with("litellm")
        mock_fetch.assert_called_once_with("test_key", "https://config-endpoint.com")