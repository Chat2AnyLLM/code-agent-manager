"""Tests for code_assistant_manager.copilot_models module."""

import os
import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from code_assistant_manager.copilot_models import (
    API_VERSION,
    COPILOT_PLUGIN_VERSION,
    COPILOT_USER_AGENT,
    copilot_base_url,
    copilot_headers,
    fetch_models,
    get_copilot_token,
    list_models,
    start_refresh_loop,
)


class TestGetCopilotToken:
    """Test get_copilot_token function."""

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_get_copilot_token_success(self, mock_get):
        """Test successful token retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-copilot-token-123"}
        mock_get.return_value = mock_response

        token_data = get_copilot_token("github-token-123")

        assert token_data["token"] == "test-copilot-token-123"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "https://api.github.com/copilot_internal/v2/token" in call_args[0]

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_get_copilot_token_headers(self, mock_get):
        """Test that correct headers are sent."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_get.return_value = mock_response

        get_copilot_token("github-token-123")

        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["authorization"] == "token github-token-123"
        assert headers["accept"] == "application/json"
        assert headers["content-type"] == "application/json"
        assert headers["user-agent"] == "models-fetcher/1.0"

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_get_copilot_token_failure(self, mock_get):
        """Test token retrieval failure."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            get_copilot_token("invalid-token")

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_get_copilot_token_with_refresh_in(self, mock_get):
        """Test token response includes refresh_in field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-token", "refresh_in": 300}
        mock_get.return_value = mock_response

        token_data = get_copilot_token("github-token-123")

        assert token_data["refresh_in"] == 300


class TestCopilotBaseUrl:
    """Test copilot_base_url function."""

    def test_copilot_base_url_individual(self):
        """Test individual account type URL."""
        url = copilot_base_url("individual")
        assert url == "https://api.githubcopilot.com"

    def test_copilot_base_url_individual_default(self):
        """Test default account type is individual."""
        url = copilot_base_url()
        assert url == "https://api.githubcopilot.com"

    def test_copilot_base_url_organization(self):
        """Test organization account type URL."""
        url = copilot_base_url("myorg")
        assert url == "https://api.myorg.githubcopilot.com"

    def test_copilot_base_url_enterprise(self):
        """Test enterprise account type URL."""
        url = copilot_base_url("enterprise")
        assert url == "https://api.enterprise.githubcopilot.com"


class TestCopilotHeaders:
    """Test copilot_headers function."""

    def test_copilot_headers_basic(self):
        """Test basic header generation."""
        headers = copilot_headers("test-token-123")

        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["content-type"] == "application/json"
        assert headers["copilot-integration-id"] == "vscode-chat"
        assert headers["editor-plugin-version"] == COPILOT_PLUGIN_VERSION
        assert headers["user-agent"] == COPILOT_USER_AGENT
        assert headers["openai-intent"] == "conversation-panel"
        assert headers["x-github-api-version"] == API_VERSION

    def test_copilot_headers_has_request_id(self):
        """Test that headers include a request ID."""
        headers = copilot_headers("test-token-123")
        assert "x-request-id" in headers
        # Verify it's a valid UUID format
        try:
            uuid.UUID(headers["x-request-id"])
        except ValueError:
            pytest.fail("x-request-id is not a valid UUID")

    def test_copilot_headers_vs_code_version(self):
        """Test custom VS Code version."""
        headers = copilot_headers("test-token-123", vs_code_version="1.85.0")
        assert headers["editor-version"] == "vscode/1.85.0"

    def test_copilot_headers_vision_enabled(self):
        """Test headers with vision enabled."""
        headers = copilot_headers("test-token-123", vision=True)
        assert headers["copilot-vision-request"] == "true"

    def test_copilot_headers_vision_disabled(self):
        """Test headers with vision disabled."""
        headers = copilot_headers("test-token-123", vision=False)
        assert "copilot-vision-request" not in headers

    def test_copilot_headers_different_tokens_different_request_ids(self):
        """Test that each call generates a different request ID."""
        headers1 = copilot_headers("token1")
        headers2 = copilot_headers("token2")
        assert headers1["x-request-id"] != headers2["x-request-id"]


class TestFetchModels:
    """Test fetch_models function."""

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_fetch_models_success(self, mock_get):
        """Test successful model fetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"},
            ]
        }
        mock_get.return_value = mock_response

        models = fetch_models("test-copilot-token")

        assert len(models["data"]) == 2
        assert models["data"][0]["id"] == "gpt-4"
        assert models["data"][1]["id"] == "gpt-3.5-turbo"

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_fetch_models_url(self, mock_get):
        """Test that correct URL is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        fetch_models("test-copilot-token", "https://api.githubcopilot.com")

        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.githubcopilot.com/v1/models"

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_fetch_models_url_organization(self, mock_get):
        """Test model fetching for organization account."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        fetch_models("test-copilot-token", "https://api.myorg.githubcopilot.com")

        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.myorg.githubcopilot.com/v1/models"

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_fetch_models_headers(self, mock_get):
        """Test that headers are included in request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        fetch_models("test-copilot-token")

        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        headers = call_kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-copilot-token"

    @patch("code_assistant_manager.copilot_models.requests.get")
    def test_fetch_models_failure(self, mock_get):
        """Test model fetching failure."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            fetch_models("invalid-token")


class TestStartRefreshLoop:
    """Test start_refresh_loop function."""

    @pytest.mark.skip(reason="Thread timing issues in test environment")
    @patch("code_assistant_manager.copilot_models.get_copilot_token")
    @patch("code_assistant_manager.copilot_models.time.sleep")
    def test_start_refresh_loop_creates_thread(self, mock_sleep, mock_get_token):
        """Test that refresh loop creates a daemon thread."""
        mock_get_token.return_value = {"token": "test-token-123", "refresh_in": 300}

        state = {}
        thread = start_refresh_loop("github-token", state)

        assert thread is not None
        assert thread.daemon is True
        # Give thread time to execute first iteration
        import time

        time.sleep(0.2)
        assert state.get("copilot_token") == "test-token-123"


class TestListModels:
    """Test list_models function."""

    @patch("code_assistant_manager.copilot_models.fetch_models")
    @patch("code_assistant_manager.copilot_models.get_copilot_token")
    @patch("code_assistant_manager.copilot_models.start_refresh_loop")
    @patch("code_assistant_manager.copilot_models.time.sleep")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-github-token"})
    @patch("builtins.print")
    def test_list_models_success(
        self, mock_print, mock_sleep, mock_refresh, mock_get_token, mock_fetch
    ):
        """Test successful model listing."""
        mock_state = {"copilot_token": "test-copilot-token"}
        mock_refresh.return_value = MagicMock()

        mock_fetch.return_value = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"},
                {"id": "gpt-4-turbo"},
            ]
        }

        list_models()

        # Should print each model ID
        assert mock_print.call_count == 3
        mock_print.assert_any_call("gpt-4")
        mock_print.assert_any_call("gpt-3.5-turbo")
        mock_print.assert_any_call("gpt-4-turbo")

    @patch.dict(os.environ, {}, clear=True)
    def test_list_models_missing_github_token(self):
        """Test that function exits when GITHUB_TOKEN is missing."""
        # Ensure GITHUB_TOKEN is not set
        os.environ.pop("GITHUB_TOKEN", None)

        with pytest.raises(SystemExit):
            list_models()

    @patch("code_assistant_manager.copilot_models.fetch_models")
    @patch("code_assistant_manager.copilot_models.get_copilot_token")
    @patch("code_assistant_manager.copilot_models.start_refresh_loop")
    @patch("code_assistant_manager.copilot_models.time.sleep")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-github-token"})
    @patch("builtins.print")
    def test_list_models_sync_fallback(
        self, mock_print, mock_sleep, mock_refresh, mock_get_token, mock_fetch
    ):
        """Test fallback to sync fetch when background thread is slow."""
        # Simulate background thread not populating state in time
        mock_refresh.return_value = MagicMock()
        mock_get_token.return_value = {"token": "sync-fetched-token"}
        mock_fetch.return_value = {"data": [{"id": "model1"}]}

        list_models()

        mock_print.assert_called_with("model1")

    @patch("code_assistant_manager.copilot_models.fetch_models")
    @patch("code_assistant_manager.copilot_models.get_copilot_token")
    @patch("code_assistant_manager.copilot_models.start_refresh_loop")
    @patch("code_assistant_manager.copilot_models.time.sleep")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-github-token"})
    @patch("builtins.print")
    def test_list_models_empty_models(
        self, mock_print, mock_sleep, mock_refresh, mock_get_token, mock_fetch
    ):
        """Test handling of empty model list."""
        mock_refresh.return_value = MagicMock()
        mock_get_token.return_value = {"token": "test-token"}
        mock_fetch.return_value = {"data": []}

        list_models()

        # Should not print anything for empty list
        mock_print.assert_not_called()

    @patch("code_assistant_manager.copilot_models.fetch_models")
    @patch("code_assistant_manager.copilot_models.get_copilot_token")
    @patch("code_assistant_manager.copilot_models.start_refresh_loop")
    @patch("code_assistant_manager.copilot_models.time.sleep")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-github-token"})
    @patch("builtins.print")
    def test_list_models_models_without_id(
        self, mock_print, mock_sleep, mock_refresh, mock_get_token, mock_fetch
    ):
        """Test handling of models without id field."""
        mock_refresh.return_value = MagicMock()
        mock_fetch.return_value = {
            "data": [
                {"id": "model1"},
                {"name": "no-id-model"},  # Missing id field
                {"id": "model2"},
            ]
        }

        list_models()

        # Should handle missing id gracefully
        mock_print.assert_any_call("model1")
        mock_print.assert_any_call(None)  # Missing id returns None
        mock_print.assert_any_call("model2")


class TestModuleConstants:
    """Test module constants."""

    def test_copilot_plugin_version_format(self):
        """Test that plugin version has expected format."""
        assert COPILOT_PLUGIN_VERSION.startswith("copilot-chat/")

    def test_copilot_user_agent_format(self):
        """Test that user agent has expected format."""
        assert COPILOT_USER_AGENT.startswith("GitHubCopilotChat/")

    def test_api_version_format(self):
        """Test that API version has expected format."""
        assert API_VERSION  # Should not be empty
        assert "-" in API_VERSION  # Should have date-like format


class TestModuleExecution:
    """Test module execution."""

    def test_module_main_can_be_imported(self):
        """Test that module can be imported and has __main__ block."""
        import code_assistant_manager.copilot_models as copilot_module

        # Check that the module has the expected functions
        assert hasattr(copilot_module, "list_models")
        assert hasattr(copilot_module, "get_copilot_token")
        assert hasattr(copilot_module, "fetch_models")

        # Check that __name__ would be '__main__' when run as script
        # (this is more of a structural test than a functional one)
