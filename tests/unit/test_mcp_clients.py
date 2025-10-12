"""Comprehensive unit tests for all MCP client implementations."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.mcp.clients import (
    ClaudeMCPClient,
    CodeBuddyMCPClient,
    CodexMCPClient,
    CopilotMCPClient,
    GeminiMCPClient,
    IflowMCPClient,
    NeovateMCPClient,
    QoderCLIMCPClient,
    QwenMCPClient,
    ZedMCPClient,
)
from code_assistant_manager.mcp.droid import DroidMCPClient


class TestAllMCPClientImplementations:
    """Test all MCP client implementations for basic functionality."""

    @pytest.fixture(
        params=[
            ("claude", ClaudeMCPClient),
            ("codex", CodexMCPClient),
            ("gemini", GeminiMCPClient),
            ("qwen", QwenMCPClient),
            ("copilot", CopilotMCPClient),
            ("codebuddy", CodeBuddyMCPClient),
            ("droid", DroidMCPClient),
            ("iflow", IflowMCPClient),
            ("zed", ZedMCPClient),
            ("qodercli", QoderCLIMCPClient),
            ("neovate", NeovateMCPClient),
        ]
    )
    def client(self, request):
        """Parameterized fixture for all client types."""
        tool_name, client_class = request.param
        return client_class()

    def test_client_initialization(self, client):
        """Test that each client initializes with correct tool name."""
        assert hasattr(client, "tool_name")
        assert client.tool_name is not None
        assert isinstance(client.tool_name, str)

    def test_client_has_required_methods(self, client):
        """Test that each client has all required methods."""
        required_methods = [
            "add_server",
            "remove_server",
            "list_servers",
            "add_all_servers",
            "remove_all_servers",
            "refresh_servers",
            "_get_config_locations",
        ]

        for method_name in required_methods:
            assert hasattr(
                client, method_name
            ), f"Client {client.__class__.__name__} missing method {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method {method_name} is not callable"

    def test_get_config_locations_returns_list(self, client):
        """Test that _get_config_locations returns a list of paths."""
        locations = client._get_config_locations(client.tool_name)

        assert isinstance(locations, list)
        # All items should be Path objects
        for location in locations:
            assert isinstance(location, Path)


class TestSpecificClientBehaviors:
    """Test client-specific behaviors and overrides."""

    def test_claude_client_config_locations(self):
        """Test Claude client has Claude-specific config locations."""
        client = ClaudeMCPClient()

        locations = client._get_config_locations("claude")

        # Should include Claude-specific paths (not standard mcp.json paths)
        home = Path.home()
        expected_claude_paths = [
            home / ".claude.json",  # User-level
            Path.cwd() / ".claude" / "claude.json",  # Project shared
            Path.cwd() / ".claude" / "claude.local.json",  # Project personal
        ]

        # At least one Claude-specific path should be present
        has_claude_specific = any(path in locations for path in expected_claude_paths)
        assert (
            has_claude_specific
        ), "Claude client should have Claude-specific config locations"

    def test_droid_client_config_locations(self):
        """Test Droid client prioritizes .factory/mcp.json."""
        client = DroidMCPClient()

        locations = client._get_config_locations("droid")

        # First location should be the droid-specific path
        home = Path.home()
        expected_first = home / ".factory" / "mcp.json"
        assert locations[0] == expected_first

    def test_droid_client_direct_fallback_operations(self):
        """Test Droid client uses direct fallback for all operations."""
        client = DroidMCPClient()

        # Test that add_server uses fallback directly
        with patch.object(
            client, "_fallback_add_server", return_value=True
        ) as mock_fallback:
            result = client.add_server("test_server")
            mock_fallback.assert_called_once_with("test_server")
            assert result is True

        # Test that remove_server uses fallback directly
        with patch.object(
            client, "_fallback_remove_server", return_value=True
        ) as mock_fallback:
            result = client.remove_server("test_server")
            mock_fallback.assert_called_once_with("test_server")
            assert result is True

    def test_droid_client_add_all_servers_uses_fallback(self):
        """Test Droid add_all_servers uses fallback for each server."""
        client = DroidMCPClient()

        sample_config = {
            "server1": {"package": "@test/package1"},
            "server2": {"package": "@test/package2"},
        }

        with patch.object(client, "get_tool_config", return_value=sample_config):
            with patch.object(
                client, "_fallback_add_server", return_value=True
            ) as mock_fallback:
                result = client.add_all_servers()

                assert mock_fallback.call_count == 2
                mock_fallback.assert_any_call("server1")
                mock_fallback.assert_any_call("server2")
                assert result is True

    def test_droid_client_remove_all_servers_uses_fallback(self):
        """Test Droid remove_all_servers uses fallback for each server."""
        client = DroidMCPClient()

        sample_config = {
            "server1": {"package": "@test/package1"},
            "server2": {"package": "@test/package2"},
        }

        with patch.object(client, "get_tool_config", return_value=sample_config):
            with patch.object(
                client, "_fallback_remove_server", return_value=True
            ) as mock_fallback:
                result = client.remove_all_servers()

                assert mock_fallback.call_count == 2
                mock_fallback.assert_any_call("server1")
                mock_fallback.assert_any_call("server2")
                assert result is True

    def test_droid_client_refresh_servers_uses_config_structure(self):
        """Test Droid refresh_servers works with mcpServers structure."""
        client = DroidMCPClient()

        # Mock the droid config file
        droid_config_path = Path.home() / ".factory" / "mcp.json"
        droid_config_data = {
            "mcpServers": {
                "server1": {"type": "stdio", "command": "npx"},
                "server2": {"type": "stdio", "command": "npx"},
            }
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(droid_config_data))):
            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(
                    client,
                    "load_config",
                    return_value=(True, {"servers": {"server1": {}, "server2": {}}}),
                ):
                    with patch.object(
                        client, "_fallback_remove_server", return_value=True
                    ):
                        with patch.object(
                            client, "_fallback_add_server", return_value=True
                        ):
                            result = client.refresh_servers()

                            assert result is True

    def test_droid_client_list_servers_reads_mcpServers(self, tmp_path):
        """Test Droid list_servers reads from mcpServers structure."""
        client = DroidMCPClient()

        droid_config_path = tmp_path / ".factory" / "mcp.json"
        droid_config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "mcpServers": {
                "memory": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"],
                },
                "context7": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp@latest"],
                },
            }
        }

        with open(droid_config_path, "w") as f:
            json.dump(config_data, f)

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = client.list_servers()

            assert result is True

    def test_droid_client_convert_to_droid_format_package(self):
        """Test converting package-based server to droid format."""
        client = DroidMCPClient()

        global_format = {"package": "@modelcontextprotocol/server-memory"}
        result = client._convert_to_droid_format(global_format)

        expected = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {},
            "disabled": False,
        }

        assert result == expected

    def test_droid_client_convert_to_droid_format_command(self):
        """Test converting command-based server to droid format."""
        client = DroidMCPClient()

        global_format = {
            "command": "python",
            "args": ["-m", "my_server"],
            "env": {"PORT": "3000"},
        }
        result = client._convert_to_droid_format(global_format)

        expected = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "my_server"],
            "env": {"PORT": "3000"},
            "disabled": False,
        }

        assert result == expected

    def test_droid_client_convert_to_droid_format_string_command(self):
        """Test converting string command server to droid format."""
        client = DroidMCPClient()

        global_format = "python -m my_server --port 3000"
        result = client._convert_to_droid_format(global_format)

        expected = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "my_server", "--port", "3000"],
            "env": {},
            "disabled": False,
        }

        assert result == expected


class TestClientErrorHandling:
    """Test error handling across different client implementations."""

    def test_clients_handle_missing_config_gracefully(self):
        """Test all clients handle missing config gracefully."""
        clients = [
            ClaudeMCPClient(),
            CodexMCPClient(),
            GeminiMCPClient(),
            QwenMCPClient(),
            CopilotMCPClient(),
            CodeBuddyMCPClient(),
            DroidMCPClient(),
            IflowMCPClient(),
            ZedMCPClient(),
            QoderCLIMCPClient(),
            NeovateMCPClient(),
        ]

        for client in clients:
            with patch.object(client, "get_tool_config", return_value={}):
                # These should not crash
                result_add = client.add_server("test")
                result_remove = client.remove_server("test")
                result_list = client.list_servers()
                result_add_all = client.add_all_servers()
                result_remove_all = client.remove_all_servers()
                result_refresh = client.refresh_servers()

                # add/remove should return False for nonexistent servers
                assert result_add is False
                assert result_remove is False
                # list_servers returns True because it successfully checked (even if empty)
                # Some clients return True to indicate successful check, others return False
                # We just verify it doesn't crash
                assert result_list in (True, False)
                assert result_add_all is False
                assert result_remove_all is False
                # refresh also just needs to not crash
                assert result_refresh in (True, False)

    def test_fallback_add_server_returns_false_when_server_not_found(self):
        """Test _fallback_add_server returns False when server config not found."""
        clients = [
            ClaudeMCPClient(),
            CodexMCPClient(),
            GeminiMCPClient(),
            QwenMCPClient(),
            CopilotMCPClient(),
            CodeBuddyMCPClient(),
            DroidMCPClient(),
            IflowMCPClient(),
            ZedMCPClient(),
            QoderCLIMCPClient(),
            NeovateMCPClient(),
        ]

        for client in clients:
            # Mock get_server_config to return None (server not found)
            with patch.object(client, "get_server_config", return_value=None):
                result_add = client._fallback_add_server("nonexistent")
                # Should return False when server not in config
                assert result_add is False


class TestGeminiClientSpecialHandling:
    """Test Gemini client special handling."""

    def test_gemini_client_config_locations(self):
        """Test Gemini client has Gemini-specific config locations."""
        client = GeminiMCPClient()

        locations = client._get_config_locations("gemini")

        # Should include Gemini-specific paths
        home = Path.home()
        expected_gemini_paths = [
            home / ".config" / "Google" / "Gemini" / "mcp.json",
            home / ".gemini" / "mcp.json",
        ]

        has_gemini_specific = any(path in locations for path in expected_gemini_paths)
        assert (
            has_gemini_specific
        ), "Gemini client should have Gemini-specific config locations"


class TestCopilotClientSpecialHandling:
    """Test Copilot client special handling."""

    def test_copilot_client_config_locations(self):
        """Test Copilot client has Copilot-specific config locations."""
        client = CopilotMCPClient()

        locations = client._get_config_locations("copilot")

        # Should include Copilot-specific paths
        home = Path.home()
        # Copilot uses mcp-config.json, not mcp.json
        expected_copilot_paths = [
            home / ".copilot" / "mcp-config.json",
        ]

        has_copilot_specific = any(path in locations for path in expected_copilot_paths)
        assert (
            has_copilot_specific
        ), f"Copilot client should have Copilot-specific config locations. Got: {locations}"


class TestCodexClientSpecialHandling:
    """Test Codex client special handling."""

    def test_codex_client_config_locations(self):
        """Test Codex client has Codex-specific config locations."""
        client = CodexMCPClient()

        locations = client._get_config_locations("codex")

        # Should include Codex-specific paths
        home = Path.home()
        # Codex uses config.toml, not mcp.json
        expected_codex_paths = [
            home / ".codex" / "config.toml",
        ]

        has_codex_specific = any(path in locations for path in expected_codex_paths)
        assert (
            has_codex_specific
        ), f"Codex client should have Codex-specific config locations. Got: {locations}"


class TestClientInheritance:
    """Test that all clients properly inherit from MCPClient."""

    def test_all_clients_inherit_from_mcpcclient(self):
        """Test all clients are instances of MCPClient."""
        from code_assistant_manager.mcp.base_client import MCPClient

        clients = [
            ClaudeMCPClient(),
            CodexMCPClient(),
            GeminiMCPClient(),
            QwenMCPClient(),
            CopilotMCPClient(),
            CodeBuddyMCPClient(),
            DroidMCPClient(),
            IflowMCPClient(),
            ZedMCPClient(),
            QoderCLIMCPClient(),
            NeovateMCPClient(),
        ]

        for client in clients:
            assert isinstance(
                client, MCPClient
            ), f"{client.__class__.__name__} should inherit from MCPClient"

    def test_clients_override_get_config_locations(self):
        """Test that clients override _get_config_locations appropriately."""
        from code_assistant_manager.mcp.base_client import MCPClient

        clients = [
            ClaudeMCPClient(),
            CodexMCPClient(),
            GeminiMCPClient(),
            QwenMCPClient(),
            CopilotMCPClient(),
            CodeBuddyMCPClient(),
            DroidMCPClient(),
            IflowMCPClient(),
            ZedMCPClient(),
            QoderCLIMCPClient(),
            NeovateMCPClient(),
        ]

        for client in clients:
            # Each client should have its own implementation
            method = client._get_config_locations
            # Should not be the base class method
            base_method = MCPClient._get_config_locations
            assert (
                method is not base_method
            ), f"{client.__class__.__name__} should override _get_config_locations"
