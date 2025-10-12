"""Comprehensive unit tests for MCP manager functionality."""

import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.mcp.manager import MCPManager


@pytest.fixture
def sample_config():
    """Sample MCP configuration for testing."""
    return {
        "global": {
            "tools_with_scope": ["claude", "codex"],
            "tools_with_tls_flag": ["claude"],
            "tools_with_cli_separator": ["codex"],
            "all_tools": ["claude", "codex", "gemini"],
        },
        "servers": {
            "memory": {"package": "@modelcontextprotocol/server-memory"},
            "context7": {"package": "@upstash/context7-mcp@latest"},
        },
    }


class TestMCPManagerInitialization:
    """Test MCPManager initialization and client setup."""

    @patch("code_assistant_manager.mcp.clients.ClaudeMCPClient")
    @patch("code_assistant_manager.mcp.clients.CodexMCPClient")
    @patch("code_assistant_manager.mcp.clients.GeminiMCPClient")
    @patch("code_assistant_manager.mcp.clients.QwenMCPClient")
    @patch("code_assistant_manager.mcp.clients.CopilotMCPClient")
    @patch("code_assistant_manager.mcp.clients.CodeBuddyMCPClient")
    @patch("code_assistant_manager.mcp.clients.DroidMCPClient")
    @patch("code_assistant_manager.mcp.clients.IflowMCPClient")
    @patch("code_assistant_manager.mcp.clients.ZedMCPClient")
    @patch("code_assistant_manager.mcp.clients.QoderCLIMCPClient")
    @patch("code_assistant_manager.mcp.clients.NeovateMCPClient")
    @patch("code_assistant_manager.mcp.clients.CrushMCPClient")
    @patch("code_assistant_manager.mcp.clients.CursorAgentMCPClient")
    def test_manager_initializes_all_clients(self, *mock_clients):
        """Test that manager initializes all expected clients."""
        manager = MCPManager()

        expected_clients = [
            "claude",
            "codex",
            "gemini",
            "qwen",
            "copilot",
            "codebuddy",
            "droid",
            "iflow",
            "zed",
            "qodercli",
            "neovate",
            "crush",
            "cursor-agent",
        ]

        assert len(manager.clients) == len(expected_clients)
        for client_name in expected_clients:
            assert client_name in manager.clients

    def test_get_client_returns_correct_client(self):
        """Test get_client returns the correct client instance."""
        manager = MCPManager()

        client = manager.get_client("claude")
        assert client is not None
        assert client.tool_name == "claude"

    def test_get_client_returns_none_for_invalid_tool(self):
        """Test get_client returns None for invalid tool name."""
        manager = MCPManager()

        client = manager.get_client("invalid_tool")
        assert client is None


class TestMCPManagerOperations:
    """Test MCPManager operation methods."""

    def test_add_server_calls_client_method(self, sample_config):
        """Test add_server delegates to appropriate client."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.add_server.return_value = True

            result = manager.add_server("claude", "memory")

            mock_get_client.assert_called_with("claude")
            mock_client.add_server.assert_called_with("memory", "user")
            assert result is True

    def test_add_server_handles_invalid_client(self):
        """Test add_server handles invalid client gracefully."""
        manager = MCPManager()

        with patch.object(manager, "get_client", return_value=None):
            result = manager.add_server("invalid_tool", "memory")

            assert result is False

    def test_remove_server_calls_client_method(self):
        """Test remove_server delegates to appropriate client."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.remove_server.return_value = True

            result = manager.remove_server("claude", "memory")

            mock_get_client.assert_called_with("claude")
            mock_client.remove_server.assert_called_with("memory")
            assert result is True

    def test_list_servers_calls_client_method(self):
        """Test list_servers delegates to appropriate client."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.list_servers.return_value = True

            result = manager.list_servers("claude")

            mock_get_client.assert_called_with("claude")
            mock_client.list_servers.assert_called()
            assert result is True

    def test_add_all_servers_for_tool_calls_client_method(self):
        """Test add_all_servers_for_tool delegates correctly."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.add_all_servers.return_value = True

            result = manager.add_all_servers_for_tool("claude")

            mock_get_client.assert_called_with("claude")
            mock_client.add_all_servers.assert_called_with("user")
            assert result is True

    def test_remove_all_servers_for_tool_calls_client_method(self):
        """Test remove_all_servers_for_tool delegates correctly."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.remove_all_servers.return_value = True

            result = manager.remove_all_servers_for_tool("claude")

            mock_get_client.assert_called_with("claude")
            mock_client.remove_all_servers.assert_called()
            assert result is True

    def test_refresh_servers_for_tool_calls_client_method(self):
        """Test refresh_servers_for_tool delegates correctly."""
        manager = MCPManager()

        with patch.object(manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.refresh_servers.return_value = True

            result = manager.refresh_servers_for_tool("claude")

            mock_get_client.assert_called_with("claude")
            mock_client.refresh_servers.assert_called()
            assert result is True


class TestMCPManagerParallelOperations:
    """Test parallel operations in MCPManager."""

    def test_add_all_servers_processes_tools_in_parallel(self, sample_config):
        """Test add_all_servers uses ThreadPoolExecutor for parallel processing."""
        manager = MCPManager()

        with patch.object(
            manager, "get_available_tools", return_value=["claude", "codex"]
        ):
            with patch.object(manager, "add_all_servers_for_tool") as mock_add_tool:
                mock_add_tool.return_value = True

                mock_future = MagicMock()
                mock_future.result.return_value = True

                with patch(
                    "code_assistant_manager.mcp.manager.ThreadPoolExecutor"
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value.submit.return_value = (
                        mock_future
                    )
                    # as_completed is imported directly, need to patch it separately
                    with patch(
                        "code_assistant_manager.mcp.manager.as_completed",
                        return_value=[mock_future, mock_future],
                    ):
                        result = manager.add_all_servers()

                        assert mock_executor.called
                        assert result is True

    def test_add_all_servers_handles_partial_failures(self, sample_config):
        """Test add_all_servers handles partial failures correctly."""
        manager = MCPManager()

        with patch.object(
            manager, "get_available_tools", return_value=["claude", "codex"]
        ):
            with patch.object(manager, "add_all_servers_for_tool") as mock_add_tool:
                # First call succeeds, second fails
                mock_add_tool.side_effect = [True, False]

                mock_future1 = MagicMock()
                mock_future1.result.return_value = True
                mock_future2 = MagicMock()
                mock_future2.result.return_value = False

                with patch(
                    "code_assistant_manager.mcp.manager.ThreadPoolExecutor"
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value.submit.side_effect = [
                        mock_future1,
                        mock_future2,
                    ]
                    # as_completed is imported directly, need to patch it separately
                    with patch(
                        "code_assistant_manager.mcp.manager.as_completed",
                        return_value=[mock_future1, mock_future2],
                    ):
                        result = manager.add_all_servers()

                        assert result is False  # Should fail due to partial failure

    def test_remove_all_servers_processes_tools_in_parallel(self):
        """Test remove_all_servers uses parallel processing."""
        manager = MCPManager()

        with patch.object(
            manager, "get_available_tools", return_value=["claude", "codex"]
        ):
            with patch.object(
                manager, "remove_all_servers_for_tool"
            ) as mock_remove_tool:
                mock_remove_tool.return_value = True

                mock_future = MagicMock()
                mock_future.result.return_value = True

                with patch(
                    "code_assistant_manager.mcp.manager.ThreadPoolExecutor"
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value.submit.return_value = (
                        mock_future
                    )
                    # as_completed is imported directly, need to patch it separately
                    with patch(
                        "code_assistant_manager.mcp.manager.as_completed",
                        return_value=[mock_future, mock_future],
                    ):
                        result = manager.remove_all_servers()

                        assert mock_executor.called
                        assert result is True

    def test_refresh_all_servers_processes_sequentially(self):
        """Test refresh_all_servers processes tools sequentially."""
        manager = MCPManager()

        with patch.object(
            manager, "get_available_tools", return_value=["claude", "codex"]
        ):
            with patch.object(manager, "refresh_servers_for_tool") as mock_refresh_tool:
                mock_refresh_tool.return_value = True

                result = manager.refresh_all_servers()

                # Should be called once for each tool
                assert mock_refresh_tool.call_count == 2
                assert result is True

    def test_list_all_servers_uses_parallel_processing(self):
        """Test list_all_servers uses parallel processing."""
        manager = MCPManager()

        with patch.object(manager, "get_available_tools", return_value=["claude"]):
            with patch.object(
                manager.clients["claude"], "list_servers", return_value=True
            ) as mock_list:
                mock_future = MagicMock()
                mock_future.result.return_value = True

                with patch(
                    "code_assistant_manager.mcp.manager.ThreadPoolExecutor"
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value.submit.return_value = (
                        mock_future
                    )
                    # as_completed is imported directly, need to patch it separately
                    with patch(
                        "code_assistant_manager.mcp.manager.as_completed",
                        return_value=[mock_future],
                    ):
                        result = manager.list_all_servers()

                        assert mock_executor.called
                        assert result is True


class TestMCPManagerErrorHandling:
    """Test error handling in MCPManager."""

    def test_add_all_servers_handles_exceptions(self):
        """Test add_all_servers handles exceptions in parallel execution."""
        manager = MCPManager()

        with patch.object(manager, "get_available_tools", return_value=["claude"]):
            with patch.object(manager, "add_all_servers_for_tool") as mock_add_tool:
                mock_add_tool.side_effect = Exception("Test error")

                mock_future = MagicMock()
                mock_future.result.side_effect = Exception("Test error")

                with patch(
                    "code_assistant_manager.mcp.manager.ThreadPoolExecutor"
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value.submit.return_value = (
                        mock_future
                    )
                    # as_completed is imported directly, need to patch it separately
                    with patch(
                        "code_assistant_manager.mcp.manager.as_completed",
                        return_value=[mock_future],
                    ):
                        result = manager.add_all_servers()

                        assert result is False

    def test_manager_handles_empty_tool_list(self):
        """Test manager operations handle empty tool lists gracefully."""
        manager = MCPManager()

        with patch.object(manager, "get_available_tools", return_value=[]):
            # These operations should handle empty lists without crashing
            result_add = manager.add_all_servers()
            result_remove = manager.remove_all_servers()
            result_refresh = manager.refresh_all_servers()
            result_list = manager.list_all_servers()

            # All should return True (success) with no work to do
            assert result_add is True
            assert result_remove is True
            assert result_refresh is True
            assert result_list is True
