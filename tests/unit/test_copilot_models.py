"""Tests for code_assistant_manager.copilot_models module."""

import pytest
from unittest.mock import patch, MagicMock


class TestCopilotModels:
    """Test Copilot models functionality."""

    def test_copilot_base_url_individual(self):
        """Test copilot_base_url with individual account type."""
        from code_assistant_manager.copilot_models import copilot_base_url

        result = copilot_base_url("individual")
        assert result == "https://api.githubcopilot.com"

    def test_copilot_base_url_enterprise(self):
        """Test copilot_base_url with enterprise account type."""
        from code_assistant_manager.copilot_models import copilot_base_url

        result = copilot_base_url("mycompany")
        assert result == "https://api.mycompany.githubcopilot.com"

    def test_copilot_headers_basic(self):
        """Test copilot_headers with basic parameters."""
        from code_assistant_manager.copilot_models import copilot_headers

        result = copilot_headers("test_token")

        expected_keys = ["Authorization", "content-type", "user-agent", "x-request-id"]
        for key in expected_keys:
            assert key in result

        assert result["Authorization"] == "Bearer test_token"
        assert result["content-type"] == "application/json"

    def test_copilot_headers_with_vision(self):
        """Test copilot_headers with vision enabled."""
        from code_assistant_manager.copilot_models import copilot_headers

        result = copilot_headers("test_token", vision=True)

        assert "copilot-integration-id" in result
        assert result["copilot-integration-id"] == "vscode-chat"

    @patch('code_assistant_manager.copilot_models.requests.get')
    def test_get_copilot_token_success(self, mock_get):
        """Test successful copilot token retrieval."""
        from code_assistant_manager.copilot_models import get_copilot_token

        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"token": "test_copilot_token"}
        mock_get.return_value = mock_response

        result = get_copilot_token("github_token")

        assert result == {"token": "test_copilot_token"}
        mock_get.assert_called_once()

        # Check the call arguments
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.github.com/copilot_internal/v2/token"
        assert kwargs["headers"]["authorization"] == "token github_token"
        assert kwargs["timeout"] == 30

    @patch('code_assistant_manager.copilot_models.requests.get')
    def test_get_copilot_token_failure(self, mock_get):
        """Test copilot token retrieval with HTTP error."""
        from code_assistant_manager.copilot_models import get_copilot_token

        # Mock failed response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 401")
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="HTTP 401"):
            get_copilot_token("invalid_token")