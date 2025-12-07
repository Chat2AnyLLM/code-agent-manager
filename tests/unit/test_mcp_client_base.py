"""Comprehensive unit tests for MCPClient base class functionality."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.mcp.base_client import MCPClient


@pytest.fixture
def sample_config():
    """Sample MCP configuration for testing."""
    return {
        "global": {
            "tools_with_scope": ["claude", "codex"],
            "tools_with_tls_flag": ["claude"],
            "tools_with_cli_separator": ["codex"],
            "all_tools": ["claude", "codex"],
        },
        "servers": {
            "memory": {
                "package": "@modelcontextprotocol/server-memory",
                "add_cmd": "claude mcp add memory --scope user",
                "remove_cmd": "claude mcp remove memory",
                "list_cmd": "claude mcp list",
            },
            "context7": {
                "package": "@upstash/context7-mcp@latest",
                "add_cmd": "claude mcp add context7 --scope user",
                "remove_cmd": "claude mcp remove context7",
                "list_cmd": "claude mcp list",
            },
        },
    }


@pytest.fixture
def client():
    """Create a test MCPClient instance."""
    return MCPClient("test_tool")


class TestMCPClientInitialization:
    """Test MCPClient initialization."""

    def test_client_initializes_with_tool_name(self):
        """Test client initializes with correct tool name."""
        client = MCPClient("claude")
        assert client.tool_name == "claude"


class TestMCPClientServerOperations:
    """Test individual server operations in MCPClient."""

    def test_add_server_success(self, client, sample_config):
        """Test successful server addition."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "_check_and_install_server", return_value=True
            ) as mock_check:
                result = client.add_server("memory")

                mock_check.assert_called_with(
                    "memory", "claude mcp add memory --scope user"
                )
                assert result is True

    def test_add_server_server_not_found(self, client):
        """Test add_server when server not found in config."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.add_server("nonexistent")

            assert result is False

    def test_add_server_no_add_cmd(self, client):
        """Test add_server when server config has no add_cmd."""
        server_config = {"memory": {"package": "@modelcontextprotocol/server-memory"}}
        with patch.object(client, "get_tool_config", return_value=server_config):
            result = client.add_server("memory")

            assert result is False

    def test_remove_server_success(self, client, sample_config):
        """Test successful server removal."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "_execute_remove_command", return_value=True
            ) as mock_execute:
                result = client.remove_server("memory")

                mock_execute.assert_called_with("memory", "claude mcp remove memory")
                assert result is True

    def test_remove_server_server_not_found(self, client):
        """Test remove_server when server not found in config."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.remove_server("nonexistent")

            assert result is False

    def test_remove_server_no_remove_cmd(self, client):
        """Test remove_server when server config has no remove_cmd."""
        server_config = {"memory": {"package": "@modelcontextprotocol/server-memory"}}
        with patch.object(client, "get_tool_config", return_value=server_config):
            result = client.remove_server("memory")

            assert result is False


class TestMCPClientListOperations:
    """Test list operations in MCPClient."""

    def test_list_servers_success(self, client, sample_config):
        """Test successful server listing."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(client, "_get_config_paths_for_scope", return_value=[]):
                with patch.object(
                    client,
                    "_read_servers_from_configs",
                    return_value={
                        "server1": {"type": "stdio"},
                        "server2": {"type": "http"},
                    },
                ):
                    result = client.list_servers()

                    assert result is True

    def test_list_servers_no_servers_configured(self, client):
        """Test list_servers when no servers configured."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.list_servers()

            assert result is False

    def test_list_servers_command_failure(self, client, sample_config):
        """Test list_servers when command execution fails."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(client, "_get_config_paths_for_scope", return_value=[]):
                with patch.object(
                    client, "_read_servers_from_configs", return_value={}
                ):
                    with patch.object(
                        client, "execute_command", return_value=(False, "error message")
                    ):
                        result = client.list_servers()

                        assert result is False


class TestMCPClientBatchOperations:
    """Test batch operations in MCPClient."""

    def test_add_all_servers_success(self, client, sample_config):
        """Test successful addition of all servers."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "_check_and_install_server", return_value=True
            ) as mock_check:
                result = client.add_all_servers()

                assert mock_check.call_count == 2  # Called for both servers
                assert result is True

    def test_add_all_servers_partial_failure(self, client, sample_config):
        """Test add_all_servers with partial failures."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "_check_and_install_server", side_effect=[True, False]
            ) as mock_check:
                result = client.add_all_servers()

                assert mock_check.call_count == 2
                assert result is False  # Should fail due to partial failure

    def test_add_all_servers_no_servers_configured(self, client):
        """Test add_all_servers when no servers configured."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.add_all_servers()

            assert result is False

    def test_remove_all_servers_success(self, client, sample_config):
        """Test successful removal of all servers."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "get_tool_config", return_value=sample_config["servers"]
            ):
                with patch.object(
                    client, "_fallback_remove_server", return_value=True
                ) as mock_execute:
                    result = client.remove_all_servers()

                    assert mock_execute.call_count == 2  # Called for both servers
                    assert result is True

    def test_remove_all_servers_partial_failure(self, client, sample_config):
        """Test remove_all_servers with partial failures."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "get_tool_config", return_value=sample_config["servers"]
            ):
                with patch.object(
                    client, "_fallback_remove_server", side_effect=[True, False]
                ) as mock_execute:
                    result = client.remove_all_servers()

                    assert mock_execute.call_count == 2
                    assert result is False  # Should fail due to partial failure


class TestMCPClientRefreshOperations:
    """Test refresh operations in MCPClient."""

    def test_refresh_servers_success(self, client, sample_config):
        """Test successful server refresh."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "get_tool_config", return_value=sample_config["servers"]
            ):
                with patch.object(
                    client, "execute_command", return_value=(True, "")
                ) as mock_execute:
                    with patch.object(
                        client, "is_server_installed", return_value=False
                    ) as mock_is_installed:
                        with patch.object(
                            client, "_check_and_install_server", return_value=True
                        ) as mock_add:
                            result = client.refresh_servers()

                            # Should call execute_command for remove commands (2 servers)
                            assert mock_execute.call_count == 2
                            # Should call is_server_installed for both servers after removal attempts
                            assert mock_is_installed.call_count == 2
                            # Should call _check_and_install_server for both servers
                            assert mock_add.call_count == 2
                            assert result is True

    def test_refresh_servers_remove_failure(self, client, sample_config):
        """Test refresh_servers when remove operation fails."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "get_tool_config", return_value=sample_config["servers"]
            ):
                # First server remove fails (tool command fails and fallback fails), second succeeds
                with patch.object(
                    client,
                    "execute_command",
                    side_effect=[(False, "remove failed"), (True, "")],
                ) as mock_execute:
                    with patch.object(
                        client, "_fallback_remove_server", return_value=False
                    ) as mock_fallback:
                        with patch.object(
                            client, "is_server_installed", return_value=True
                        ):  # Servers still installed after failed removal
                            result = client.refresh_servers()

                            assert result is False  # Should fail due to remove failure

    def test_refresh_servers_add_failure_after_remove(self, client, sample_config):
        """Test refresh_servers when add operation fails after successful remove."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "get_tool_config", return_value=sample_config["servers"]
            ):
                # Remove commands succeed and servers are not installed afterward
                with patch.object(
                    client, "execute_command", return_value=(True, "")
                ) as mock_execute:
                    with patch.object(
                        client, "is_server_installed", return_value=False
                    ) as mock_is_installed:
                        # First server add succeeds, second fails
                        with patch.object(
                            client,
                            "_check_and_install_server",
                            side_effect=[True, False],
                        ) as mock_add:
                            result = client.refresh_servers()

                            assert result is False  # Should fail due to add failure


class TestMCPClientFallbackOperations:
    """Test fallback operations in MCPClient."""

    def test_fallback_add_server_success(self, client, tmp_path):
        """Test successful fallback server addition."""
        config_path = tmp_path / "test_config.json"
        server_info = {"package": "@test/package"}

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(client, "get_server_config", return_value=server_info):
                with patch.object(
                    client, "_get_config_locations", return_value=[config_path]
                ):
                    result = client._fallback_add_server("test_server")

                    assert result is True
                    # Check that config file was created/modified
                    assert config_path.exists()

    def test_fallback_add_server_no_config(self, client):
        """Test fallback addition when no server config available."""
        with patch.object(client, "load_config", return_value=(False, {})):
            result = client._fallback_add_server("test_server")

            assert result is False

    def test_fallback_remove_server_success(self, client, tmp_path):
        """Test successful fallback server removal."""
        config_path = tmp_path / "test_config.json"
        # Pre-create config with server
        config_data = {"mcpServers": {"test_server": {"type": "stdio"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client, "_get_config_locations", return_value=[config_path]
            ):
                result = client._fallback_remove_server("test_server")

                assert result is True

    def test_fallback_remove_server_config_not_found(self, client):
        """Test fallback removal when config file doesn't exist."""
        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value="/fake/config.json",
        ):
            with patch.object(
                client,
                "_get_config_locations",
                return_value=[Path("/nonexistent/path")],
            ):
                result = client._fallback_remove_server("test_server")

                assert result is False


class TestMCPClientConfigOperations:
    """Test config file operations in MCPClient."""

    def test_add_server_to_config_mcpServers_structure(self, client, tmp_path):
        """Test adding server to config with mcpServers structure."""
        config_path = tmp_path / "test_config.json"
        server_info = {"type": "stdio", "command": "npx"}

        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)
        assert "mcpServers" in config
        assert "test_server" in config["mcpServers"]

    def test_add_server_to_config_servers_structure(self, client, tmp_path):
        """Test adding server to config with servers structure."""
        config_path = tmp_path / "test_config.json"
        # Pre-create config with servers structure
        with open(config_path, "w") as f:
            json.dump({"servers": {}}, f)

        server_info = {"package": "@test/package"}

        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)
        assert "test_server" in config["servers"]

    def test_remove_server_from_config_success(self, client, tmp_path):
        """Test successful server removal from config."""
        config_path = tmp_path / "test_config.json"
        # Pre-create config with server
        config_data = {"mcpServers": {"test_server": {"type": "stdio"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = client._remove_server_from_config(config_path, "test_server")

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)
        assert "test_server" not in config["mcpServers"]

    def test_remove_server_from_config_nonexistent_file(self, client):
        """Test server removal when config file doesn't exist."""
        result = client._remove_server_from_config(
            Path("/nonexistent/path"), "test_server"
        )

        assert result is False


class TestMCPClientConfigLocations:
    """Test config location detection in MCPClient."""

    def test_get_config_locations_includes_common_patterns(self, client):
        """Test that _get_config_locations includes expected common patterns."""
        locations = client._get_config_locations("claude")

        # Should include home directory patterns
        home = Path.home()
        expected_patterns = [
            home / ".config" / "claude" / "mcp.json",
            home / ".local" / "share" / "claude" / "mcp.json",
            home / ".claude" / "mcp.json",
        ]

        for pattern in expected_patterns:
            assert pattern in locations

    def test_get_config_locations_tool_specific_patterns(self, client):
        """Test tool-specific config location patterns."""
        # Test Claude-specific locations
        claude_client = MCPClient("claude")
        claude_locations = claude_client._get_config_locations("claude")

        # Should include Claude-specific macOS path
        home = Path.home()
        macos_path = home / "Library" / "Application Support" / "Claude" / "mcp.json"
        assert macos_path in claude_locations


class TestMCPClientParallelProcessing:
    """Test parallel processing in MCPClient operations."""

    def test_add_all_servers_uses_thread_pool(self, client, sample_config):
        """Test add_all_servers uses ThreadPoolExecutor."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch(
                "code_assistant_manager.mcp.base_client.ThreadPoolExecutor"
            ) as mock_executor:
                # Create mock futures
                mock_future1 = MagicMock()
                mock_future1.result.return_value = True
                mock_future2 = MagicMock()
                mock_future2.result.return_value = True

                # Make submit return different futures
                mock_executor.return_value.__enter__.return_value.submit.side_effect = [
                    mock_future1,
                    mock_future2,
                ]

                # Patch as_completed at module level (where it's imported)
                with patch(
                    "code_assistant_manager.mcp.base_client.as_completed",
                    return_value=[mock_future1, mock_future2],
                ):
                    result = client.add_all_servers()

                assert mock_executor.called
                assert result is True

    def test_remove_all_servers_uses_thread_pool(self, client, sample_config):
        """Test remove_all_servers uses ThreadPoolExecutor."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch(
                "code_assistant_manager.mcp.base_client.ThreadPoolExecutor"
            ) as mock_executor:
                # Create mock futures
                mock_future1 = MagicMock()
                mock_future1.result.return_value = True
                mock_future2 = MagicMock()
                mock_future2.result.return_value = True

                # Make submit return different futures
                mock_executor.return_value.__enter__.return_value.submit.side_effect = [
                    mock_future1,
                    mock_future2,
                ]

                # Patch as_completed at module level (where it's imported)
                with patch(
                    "code_assistant_manager.mcp.base_client.as_completed",
                    return_value=[mock_future1, mock_future2],
                ):
                    result = client.remove_all_servers()

                assert mock_executor.called
                assert result is True


class TestMCPClientErrorHandling:
    """Test error handling in MCPClient."""

    def test_operations_return_false_for_missing_servers(self, client, sample_config):
        """Test that operations return False for nonexistent servers."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            # Server not in config should return False
            result_add = client.add_server("nonexistent")
            result_remove = client.remove_server("nonexistent")

            assert result_add is False
            assert result_remove is False

    def test_add_all_servers_returns_false_when_no_servers(self, client):
        """Test add_all_servers returns False when no servers configured."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.add_all_servers()
            assert result is False

    def test_remove_all_servers_returns_false_when_no_servers(self, client):
        """Test remove_all_servers returns False when no servers configured."""
        with patch.object(client, "get_tool_config", return_value={}):
            result = client.remove_all_servers()
            assert result is False

    def test_fallback_operations_handle_json_errors(self, client, tmp_path):
        """Test fallback operations handle JSON parsing errors."""
        config_path = tmp_path / "bad_config.json"
        # Create file with invalid JSON
        with open(config_path, "w") as f:
            f.write("{ invalid json }")

        result_add = client._add_server_to_config(config_path, "test", {})
        result_remove = client._remove_server_from_config(config_path, "test")

        # Should handle errors gracefully
        assert result_add is False
        assert result_remove is False


class TestConfigFileHelpers:
    """Test module-level config file helper functions."""

    def test_load_config_file_json(self, tmp_path):
        """Test loading a JSON config file."""
        from code_assistant_manager.mcp.base_client import _load_config_file

        config_path = tmp_path / "test.json"
        config_data = {"mcpServers": {"test": {"type": "stdio"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config, is_toml = _load_config_file(config_path)

        assert config == config_data
        assert is_toml is False

    def test_load_config_file_nonexistent(self, tmp_path):
        """Test loading a nonexistent config file returns empty dict."""
        from code_assistant_manager.mcp.base_client import _load_config_file

        config_path = tmp_path / "nonexistent.json"

        config, is_toml = _load_config_file(config_path)

        assert config == {}
        assert is_toml is False

    def test_load_config_file_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        from code_assistant_manager.mcp.base_client import _load_config_file

        config_path = tmp_path / "invalid.json"
        with open(config_path, "w") as f:
            f.write("{ invalid json }")

        config, is_toml = _load_config_file(config_path)

        assert config is None
        assert is_toml is False

    def test_save_config_file_json(self, tmp_path):
        """Test saving a JSON config file."""
        from code_assistant_manager.mcp.base_client import _save_config_file

        config_path = tmp_path / "test.json"
        config_data = {"mcpServers": {"test": {"type": "stdio"}}}

        result = _save_config_file(config_path, config_data, is_toml=False)

        assert result is True
        assert config_path.exists()
        with open(config_path, "r") as f:
            saved_config = json.load(f)
        assert saved_config == config_data

    def test_save_config_file_creates_parent_dirs(self, tmp_path):
        """Test that save creates parent directories if needed."""
        from code_assistant_manager.mcp.base_client import _save_config_file

        config_path = tmp_path / "subdir" / "nested" / "test.json"
        config_data = {"key": "value"}

        result = _save_config_file(config_path, config_data, is_toml=False)

        assert result is True
        assert config_path.exists()

    def test_server_exists_in_config_mcpServers(self):
        """Test checking server existence in mcpServers structure."""
        from code_assistant_manager.mcp.base_client import _server_exists_in_config

        config = {"mcpServers": {"test_server": {"type": "stdio"}}}

        assert _server_exists_in_config(config, "test_server") is True
        assert _server_exists_in_config(config, "nonexistent") is False

    def test_server_exists_in_config_servers(self):
        """Test checking server existence in servers structure."""
        from code_assistant_manager.mcp.base_client import _server_exists_in_config

        config = {"servers": {"test_server": {"type": "http"}}}

        assert _server_exists_in_config(config, "test_server") is True
        assert _server_exists_in_config(config, "nonexistent") is False

    def test_server_exists_in_config_direct(self):
        """Test checking server existence in direct structure."""
        from code_assistant_manager.mcp.base_client import _server_exists_in_config

        config = {"test_server": {"type": "stdio"}}

        assert _server_exists_in_config(config, "test_server") is True
        assert _server_exists_in_config(config, "nonexistent") is False

    def test_get_preferred_container_key_existing(self):
        """Test getting preferred container key when one exists."""
        from code_assistant_manager.mcp.base_client import _get_preferred_container_key

        config = {"servers": {}}

        result = _get_preferred_container_key(config, is_toml=False)

        assert result == "servers"

    def test_get_preferred_container_key_default_json(self):
        """Test default container key for JSON files."""
        from code_assistant_manager.mcp.base_client import _get_preferred_container_key

        config = {}

        result = _get_preferred_container_key(config, is_toml=False)

        assert result == "mcpServers"

    def test_get_preferred_container_key_default_toml(self):
        """Test default container key for TOML files."""
        from code_assistant_manager.mcp.base_client import _get_preferred_container_key

        config = {}

        result = _get_preferred_container_key(config, is_toml=True)

        # Default is mcpServers for both JSON and TOML when no existing containers
        assert result == "mcpServers"

    def test_remove_server_from_containers_mcpServers(self):
        """Test removing server from mcpServers container."""
        from code_assistant_manager.mcp.base_client import (
            _remove_server_from_containers,
        )

        config = {"mcpServers": {"server1": {}, "server2": {}}}

        result = _remove_server_from_containers(config, "server1")

        assert result is True
        assert "server1" not in config["mcpServers"]
        assert "server2" in config["mcpServers"]

    def test_remove_server_from_containers_multiple(self):
        """Test removing server that exists in multiple containers."""
        from code_assistant_manager.mcp.base_client import (
            _remove_server_from_containers,
        )

        config = {
            "mcpServers": {"server1": {}},
            "servers": {"server1": {}},
        }

        result = _remove_server_from_containers(config, "server1")

        assert result is True
        assert "server1" not in config["mcpServers"]
        assert "server1" not in config["servers"]

    def test_remove_server_from_containers_not_found(self):
        """Test removing server that doesn't exist."""
        from code_assistant_manager.mcp.base_client import (
            _remove_server_from_containers,
        )

        config = {"mcpServers": {"other": {}}}

        result = _remove_server_from_containers(config, "nonexistent")

        assert result is False
