"""Tests for Litellm SSL handling functionality."""

import os
from unittest.mock import patch, MagicMock

import pytest
import requests

from code_assistant_manager.litellm_models import fetch_litellm_models


class TestLitellmSSLHandling:
    """Test cases for SSL verification handling in litellm models."""

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_private_ip_ssl_bypass_10_range(self, mock_get):
        """Test SSL verification bypass for private IP in 10.0.0.0/8 range."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test private IP in 10.x.x.x range
        fetch_litellm_models("test-key", "http://10.0.0.1:4142")

        # Verify SSL verification was disabled
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is False

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_private_ip_ssl_bypass_172_range(self, mock_get):
        """Test SSL verification bypass for private IP in 172.16.0.0/12 range."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test private IP in 172.16.x.x range
        fetch_litellm_models("test-key", "https://172.16.0.1:4142")

        # Verify SSL verification was disabled
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is False

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_private_ip_ssl_bypass_192_range(self, mock_get):
        """Test SSL verification bypass for private IP in 192.168.0.0/16 range."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test private IP in 192.168.x.x range
        fetch_litellm_models("test-key", "https://192.168.1.100:4142")

        # Verify SSL verification was disabled
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is False

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_private_ip_ssl_bypass_loopback(self, mock_get):
        """Test SSL verification bypass for loopback IP 127.0.0.1."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test loopback IP
        fetch_litellm_models("test-key", "http://127.0.0.1:4142")

        # Verify SSL verification was disabled
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is False

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_public_ip_ssl_verification_enabled(self, mock_get):
        """Test SSL verification is enabled for public IPs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test public IP
        fetch_litellm_models("test-key", "https://8.8.8.8:4142")

        # Verify SSL verification was enabled (default)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is True

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_hostname_ssl_verification_enabled(self, mock_get):
        """Test SSL verification is enabled for hostnames (not IPs)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test hostname
        fetch_litellm_models("test-key", "https://api.example.com:4142")

        # Verify SSL verification was enabled (default)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is True

    @patch("code_assistant_manager.litellm_models.requests.get")
    def test_ssl_parsing_error_falls_back_to_verification(self, mock_get):
        """Test that parsing errors fall back to SSL verification enabled."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        # Test invalid URL that causes parsing error
        fetch_litellm_models("test-key", "not-a-url")

        # Verify SSL verification was enabled (fallback)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["verify"] is True

    @patch("code_assistant_manager.litellm_models.requests.get")
    @patch.dict(os.environ, {"API_KEY_LITELLM": "test-key"})
    def test_endpoint_url_from_config(self, mock_get):
        """Test that endpoint URL is read from config when not in environment."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        from code_assistant_manager.litellm_models import list_models

        # Mock ConfigManager
        with patch("code_assistant_manager.litellm_models.ConfigManager") as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            mock_config.get_endpoint_config.return_value = {
                "endpoint": "https://config-endpoint.com:4142"
            }

            # Mock stdout to capture output
            with patch("builtins.print"):
                list_models()

            # Verify the URL used was from config
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0]
            assert "https://config-endpoint.com:4142/v1/models" in call_args[0]

    @patch("code_assistant_manager.litellm_models.requests.get")
    @patch.dict(os.environ, {"API_KEY_LITELLM": "test-key", "endpoint": "https://env-endpoint.com:4142"})
    def test_endpoint_url_from_environment(self, mock_get):
        """Test that endpoint URL prioritizes environment variable over config."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        from code_assistant_manager.litellm_models import list_models

        # Mock ConfigManager - this should not be used for endpoint URL
        with patch("code_assistant_manager.litellm_models.ConfigManager") as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            # Mock stdout to capture output
            with patch("builtins.print"):
                list_models()

            # Verify the URL used was from environment
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0]
            assert "https://env-endpoint.com:4142/v1/models" in call_args[0]