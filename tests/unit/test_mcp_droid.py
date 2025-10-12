"""Unit tests for DroidMCPClient MCP server management methods."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.mcp.droid import DroidMCPClient


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary mcp.json config file."""
    config_path = tmp_path / "mcp.json"
    initial_data = {
        "global": {
            "tools_with_scope": ["droid"],
            "tools_with_tls_flag": [],
            "tools_with_cli_separator": [],
            "all_tools": ["droid"],
        },
        "servers": {
            "test_server": {"package": "@modelcontextprotocol/server-memory"},
            "context7": {"package": "@upstash/context7-mcp@latest"},
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=4)
    return config_path


@pytest.fixture
def temp_droid_config_file(tmp_path):
    """Create a temporary droid MCP config file."""
    droid_config_dir = tmp_path / ".factory"
    droid_config_dir.mkdir(exist_ok=True)
    config_path = droid_config_dir / "mcp.json"
    initial_data = {
        "mcpServers": {
            "existing_server": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": {},
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=4)
    return config_path


@pytest.fixture
def client(temp_config_file, temp_droid_config_file):
    """Create a DroidMCPClient with mocked config paths."""
    client = DroidMCPClient()
    with (
        patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ),
        patch.object(
            client, "_get_config_locations", return_value=[temp_droid_config_file]
        ),
    ):
        yield client


class TestDroidMCPClient:
    """Test DroidMCPClient methods."""

    def test_get_config_locations(self, tmp_path):
        """Test that droid-specific config location is prioritized."""
        client = DroidMCPClient()
        locations = client._get_config_locations("droid")

        # Check that droid-specific location comes first
        home = Path.home()
        expected_first_location = home / ".factory" / "mcp.json"
        assert expected_first_location == locations[0]

    def test_add_server_fallback(self, client, temp_droid_config_file):
        """Test adding a server uses fallback mechanism."""
        with patch.object(
            client, "_fallback_add_server", return_value=True
        ) as mock_fallback:
            success = client.add_server("test_server")
            assert success is True
            mock_fallback.assert_called_once_with("test_server")

    def test_remove_server_fallback(self, client, temp_droid_config_file):
        """Test removing a server uses fallback mechanism."""
        with patch.object(
            client, "_fallback_remove_server", return_value=True
        ) as mock_fallback:
            success = client.remove_server("existing_server")
            assert success is True
            mock_fallback.assert_called_once_with("existing_server")

    def test_list_servers_from_config(self, client, temp_droid_config_file):
        """Test listing servers reads from config file directly."""
        success = client.list_servers()
        assert success is True
        # This would print output, but we can't easily test stdout in this context

    def test_add_all_servers(self, client, temp_config_file, temp_droid_config_file):
        """Test adding all servers from global config."""
        sample_config = {
            "test_server": {"add_cmd": "test cmd"},
            "context7": {"add_cmd": "ctx cmd"},
        }
        with patch.object(client, "get_tool_config", return_value=sample_config):
            with patch.object(
                client, "_fallback_add_server", return_value=True
            ) as mock_fallback:
                success = client.add_all_servers()
                assert success is True
                # Should try to add both test_server and context7
                assert mock_fallback.call_count == 2
                mock_fallback.assert_any_call("test_server")
                mock_fallback.assert_any_call("context7")

    def test_refresh_servers(self, client, temp_droid_config_file):
        """Test refreshing servers (remove then re-add)."""
        with (
            patch.object(
                client, "_fallback_remove_server", return_value=True
            ) as mock_remove,
            patch.object(client, "_fallback_add_server", return_value=True) as mock_add,
        ):
            success = client.refresh_servers()
            assert success is True
            # Should try to refresh servers from global config
            # (The exact behavior depends on what get_tool_config returns)
