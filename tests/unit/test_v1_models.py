"""Tests for v1_models module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from code_assistant_manager.v1_models import (
    fetch_v1_models,
    get_copilot_token,
    list_models,
)


class TestV1Models:
    @patch("requests.get")
    def test_fetch_v1_models_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "model1"}, {"id": "model2"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_v1_models("https://example.com/v1/models", {"Authorization": "Bearer test"})

        assert result["data"][0]["id"] == "model1"
        assert result["data"][1]["id"] == "model2"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_fetch_v1_models_ssl_verification_private_ip(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # Private IP should skip SSL verification
        fetch_v1_models("https://192.168.1.1/v1/models", {})
        mock_get.assert_called_with(
            "https://192.168.1.1/v1/models",
            params={
                "return_wildcard_routes": "false",
                "include_model_access_groups": "false",
                "only_model_access_groups": "false",
                "include_metadata": "false",
            },
            headers={},
            timeout=30,
            verify=False
        )

    @patch("requests.get")
    def test_fetch_v1_models_ssl_verification_public_ip(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # Public IP should use SSL verification
        fetch_v1_models("https://8.8.8.8/v1/models", {})
        mock_get.assert_called_with(
            "https://8.8.8.8/v1/models",
            params={
                "return_wildcard_routes": "false",
                "include_model_access_groups": "false",
                "only_model_access_groups": "false",
                "include_metadata": "false",
            },
            headers={},
            timeout=30,
            verify=True
        )

    @patch("code_assistant_manager.v1_models.load_env")
    @patch("code_assistant_manager.v1_models.fetch_v1_models")
    @patch("builtins.print")
    def test_list_models_litellm_style(self, mock_print, mock_fetch, mock_load_env):
        os.environ["endpoint"] = "https://example.com"
        os.environ["api_key"] = "test-api-key"

        mock_fetch.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}

        list_models()

        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[0] == "https://example.com/v1/models"
        assert args[1]["Authorization"] == "Bearer test-api-key"

        mock_print.assert_any_call("model-a")
        mock_print.assert_any_call("model-b")

    @patch("code_assistant_manager.v1_models.load_env")
    @patch("code_assistant_manager.v1_models.fetch_v1_models")
    @patch("builtins.print")
    def test_list_models_v1_endpoint(self, mock_print, mock_fetch, mock_load_env):
        os.environ["endpoint"] = "https://example.com/v1"
        os.environ["api_key"] = "test-api-key"

        mock_fetch.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}

        list_models()

        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[0] == "https://example.com/v1/models"
        assert args[1]["Authorization"] == "Bearer test-api-key"

        mock_print.assert_any_call("model-a")
        mock_print.assert_any_call("model-b")

    @patch("code_assistant_manager.v1_models.load_env")
    @patch("code_assistant_manager.v1_models.fetch_v1_models")
    @patch("builtins.print")
    def test_list_models_v1_models_endpoint(self, mock_print, mock_fetch, mock_load_env):
        os.environ["endpoint"] = "https://example.com/v1/models"
        os.environ["api_key"] = "test-api-key"

        mock_fetch.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}

        list_models()

        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[0] == "https://example.com/v1/models"
        assert args[1]["Authorization"] == "Bearer test-api-key"

        mock_print.assert_any_call("model-a")
        mock_print.assert_any_call("model-b")

    @patch("code_assistant_manager.v1_models.load_env")
    @patch("code_assistant_manager.v1_models.get_copilot_token")
    @patch("code_assistant_manager.v1_models.fetch_v1_models")
    @patch("builtins.print")
    def test_list_models_copilot_style(self, mock_print, mock_fetch, mock_get_token, mock_load_env):
        if "api_key" in os.environ:
            del os.environ["api_key"]
        os.environ["endpoint"] = "https://example.com"
        os.environ["GITHUB_TOKEN"] = "test-github-token"

        mock_get_token.return_value = {"token": "test-copilot-token", "refresh_in": 3600}
        mock_fetch.return_value = {"data": [{"id": "copilot-model"}]}

        list_models()

        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[1]["Authorization"] == "Bearer test-copilot-token"
        mock_print.assert_any_call("copilot-model")
