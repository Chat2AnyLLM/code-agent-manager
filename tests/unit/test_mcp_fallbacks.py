"""Tests for MCP fallback mechanisms and error handling."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.mcp.base_client import MCPClient
from code_assistant_manager.mcp.droid import DroidMCPClient


@pytest.fixture
def sample_config():
    """Sample MCP configuration."""
    return {
        "global": {"tools_with_scope": ["claude"], "all_tools": ["claude"]},
        "servers": {"memory": {"package": "@modelcontextprotocol/server-memory"}},
    }


@pytest.fixture
def client():
    """Create a test MCPClient."""
    return MCPClient("test_tool")


class TestFallbackOperations:
    """Test fallback operation mechanisms."""

    def test_fallback_add_server_success(self, client, tmp_path):
        """Test successful fallback server addition."""
        config_path = tmp_path / "mcp.json"
        global_config_path = tmp_path / "global_mcp.json"

        # _fallback_add_server calls get_server_config and find_mcp_config (from .base)
        with patch.object(
            client,
            "get_server_config",
            return_value={"package": "@test/package"},
        ):
            with patch.object(
                client, "_get_config_locations", return_value=[config_path]
            ):
                # find_mcp_config is imported from .base inside the method
                with patch(
                    "code_assistant_manager.mcp.base.find_mcp_config",
                    return_value=global_config_path,
                ):
                    result = client._fallback_add_server("test_server")

                    assert result is True
                    assert config_path.exists()

    def test_fallback_add_server_no_config(self, client):
        """Test fallback addition when no server config available."""
        # get_server_config returns None when server not found
        with patch.object(client, "get_server_config", return_value=None):
            result = client._fallback_add_server("test_server")

            assert result is False

    def test_fallback_add_server_server_not_found(self, client, tmp_path):
        """Test fallback addition when server not in global config."""
        config_path = tmp_path / "mcp.json"

        # get_server_config returns None for nonexistent servers
        with patch.object(
            client,
            "get_server_config",
            return_value=None,
        ):
            with patch.object(
                client, "_get_config_locations", return_value=[config_path]
            ):
                result = client._fallback_add_server("nonexistent_server")

                assert result is False

    def test_fallback_remove_server_success(self, client, tmp_path):
        """Test successful fallback server removal."""
        config_path = tmp_path / "mcp.json"
        global_config_path = tmp_path / "global_mcp.json"

        # Pre-create config with server
        config_data = {"mcpServers": {"test_server": {"type": "stdio"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch.object(client, "_get_config_locations", return_value=[config_path]):
            with patch(
                "code_assistant_manager.mcp.base.find_mcp_config",
                return_value=global_config_path,
            ):
                result = client._fallback_remove_server("test_server")

                assert result is True

                # Verify server was removed
                with open(config_path, "r") as f:
                    updated_config = json.load(f)
                assert "test_server" not in updated_config["mcpServers"]

    def test_fallback_remove_server_config_not_found(self, client, tmp_path):
        """Test fallback removal when config file doesn't exist."""
        global_config_path = tmp_path / "global_mcp.json"

        with patch.object(
            client, "_get_config_locations", return_value=[Path("/nonexistent/path")]
        ):
            with patch(
                "code_assistant_manager.mcp.base.find_mcp_config",
                return_value=global_config_path,
            ):
                result = client._fallback_remove_server("test_server")

                assert result is False

    def test_fallback_remove_server_server_not_present(self, client, tmp_path):
        """Test fallback removal when server not in config."""
        config_path = tmp_path / "mcp.json"
        global_config_path = tmp_path / "global_mcp.json"

        # Pre-create config without the server
        config_data = {"mcpServers": {"other_server": {"type": "stdio"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch.object(client, "_get_config_locations", return_value=[config_path]):
            with patch(
                "code_assistant_manager.mcp.base.find_mcp_config",
                return_value=global_config_path,
            ):
                result = client._fallback_remove_server("nonexistent_server")

                assert result is False


class TestConfigFileOperations:
    """Test config file read/write operations."""

    def test_add_server_to_config_mcpServers(self, client, tmp_path):
        """Test adding server to config with mcpServers structure."""
        config_path = tmp_path / "mcp.json"
        server_info = {"type": "stdio", "command": "npx"}

        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test_server" in config["mcpServers"]
        assert config["mcpServers"]["test_server"]["command"] == "npx"

    def test_add_server_to_config_servers_structure(self, client, tmp_path):
        """Test adding server to config with servers structure."""
        config_path = tmp_path / "mcp.json"

        # Pre-create with servers structure
        with open(config_path, "w") as f:
            json.dump({"servers": {}}, f)

        server_info = {"package": "@test/package"}
        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "test_server" in config["servers"]

    def test_add_server_to_config_direct_structure(self, client, tmp_path):
        """Test adding server to config with direct structure."""
        config_path = tmp_path / "mcp.json"

        # Pre-create empty config
        with open(config_path, "w") as f:
            json.dump({}, f)

        server_info = {"command": "test"}
        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test_server" in config["mcpServers"]

    def test_add_server_to_config_existing_server_no_overwrite(self, client, tmp_path):
        """Test adding server doesn't overwrite existing server."""
        config_path = tmp_path / "mcp.json"

        # Pre-create with existing server
        config_data = {"mcpServers": {"test_server": {"existing": "config"}}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        server_info = {"new": "config"}
        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is False  # Should fail because server already exists

        # Verify existing config unchanged
        with open(config_path, "r") as f:
            config = json.load(f)
        assert config["mcpServers"]["test_server"] == {"existing": "config"}

    def test_remove_server_from_config_mcpServers(self, client, tmp_path):
        """Test removing server from mcpServers structure."""
        config_path = tmp_path / "mcp.json"

        config_data = {
            "mcpServers": {
                "test_server": {"type": "stdio"},
                "other_server": {"type": "stdio"},
            }
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = client._remove_server_from_config(config_path, "test_server")

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "test_server" not in config["mcpServers"]
        assert "other_server" in config["mcpServers"]  # Other server should remain

    def test_remove_server_from_config_servers_structure(self, client, tmp_path):
        """Test removing server from servers structure."""
        config_path = tmp_path / "mcp.json"

        config_data = {
            "servers": {
                "test_server": {"package": "@test"},
                "other_server": {"package": "@other"},
            }
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = client._remove_server_from_config(config_path, "test_server")

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "test_server" not in config["servers"]
        assert "other_server" in config["servers"]

    def test_remove_server_from_config_direct_structure(self, client, tmp_path):
        """Test removing server from direct structure."""
        config_path = tmp_path / "mcp.json"

        config_data = {
            "test_server": {"command": "test"},
            "other_server": {"command": "other"},
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = client._remove_server_from_config(config_path, "test_server")

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "test_server" not in config
        assert "other_server" in config


class TestFallbackErrorHandling:
    """Test error handling in fallback operations."""

    def test_fallback_operations_handle_json_errors(self, client, tmp_path):
        """Test fallback operations handle JSON parsing errors."""
        config_path = tmp_path / "bad_config.json"

        # Create file with invalid JSON
        with open(config_path, "w") as f:
            f.write("{ invalid json }")

        result_add = client._add_server_to_config(config_path, "test", {})
        result_remove = client._remove_server_from_config(config_path, "test")

        assert result_add is False
        assert result_remove is False

    def test_fallback_operations_handle_file_permission_errors(self, client, tmp_path):
        """Test fallback operations handle file permission errors."""
        config_path = tmp_path / "readonly_config.json"

        # Create file and make it read-only
        with open(config_path, "w") as f:
            json.dump({"mcpServers": {}}, f)

        config_path.chmod(0o444)  # Read-only

        server_info = {"type": "stdio"}
        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is False

    def test_fallback_operations_handle_path_creation_errors(self, client):
        """Test fallback operations handle path creation errors."""
        # Try to create in a directory that doesn't allow creation
        invalid_path = Path("/proc/1/root/nonexistent/deep/path/config.json")

        server_info = {"type": "stdio"}
        result = client._add_server_to_config(invalid_path, "test_server", server_info)

        assert result is False


class TestDroidFallbackSpecialization:
    """Test Droid-specific fallback behavior."""

    def test_droid_fallback_add_uses_mcpServers(self, tmp_path):
        """Test Droid fallback add uses mcpServers structure specifically."""
        client = DroidMCPClient()

        droid_config_path = tmp_path / ".factory" / "mcp.json"
        droid_config_path.parent.mkdir(parents=True)

        with patch.object(
            client,
            "load_config",
            return_value=(
                True,
                {"servers": {"test_server": {"package": "@test/package"}}},
            ),
        ):
            with patch("pathlib.Path.home", return_value=tmp_path):
                result = client._fallback_add_server("test_server")

                assert result is True
                assert droid_config_path.exists()

                with open(droid_config_path, "r") as f:
                    config = json.load(f)

                assert "mcpServers" in config
                assert "test_server" in config["mcpServers"]

    def test_droid_fallback_remove_uses_mcpServers(self, tmp_path):
        """Test Droid fallback remove uses mcpServers structure specifically."""
        client = DroidMCPClient()

        droid_config_path = tmp_path / ".factory" / "mcp.json"
        droid_config_path.parent.mkdir(parents=True)

        # Pre-create config
        config_data = {"mcpServers": {"test_server": {"type": "stdio"}}}
        with open(droid_config_path, "w") as f:
            json.dump(config_data, f)

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = client._fallback_remove_server("test_server")

            assert result is True

            with open(droid_config_path, "r") as f:
                config = json.load(f)

            assert "test_server" not in config["mcpServers"]

    def test_droid_fallback_handles_nonexistent_config(self, tmp_path):
        """Test Droid fallback handles nonexistent config files."""
        client = DroidMCPClient()

        # Don't create the config file
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = client._fallback_remove_server("test_server")

            assert result is False


class TestCommandExecutionFallback:
    """Test command execution and fallback logic."""

    def test_check_and_install_server_prefers_tool_command(self, client, sample_config):
        """Test that _check_and_install_server prefers tool commands over fallback."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "is_server_installed", side_effect=[False, True]
            ):  # Not installed initially, installed after command
                with patch.object(
                    client, "execute_command", return_value=(True, "")
                ) as mock_execute:
                    with patch.object(
                        client, "_fallback_add_server", return_value=False
                    ) as mock_fallback:

                        result = client._check_and_install_server(
                            "memory", "test command"
                        )

                        # Should try tool command first
                        mock_execute.assert_called_once_with("test command")
                        mock_fallback.assert_not_called()  # Fallback not needed
                        assert result is True

    def test_check_and_install_server_falls_back_on_tool_failure(
        self, client, sample_config
    ):
        """Test fallback when tool command fails."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "is_server_installed", side_effect=[False, True]
            ):  # Not installed, then installed after fallback
                with patch.object(
                    client, "execute_command", return_value=(False, "command failed")
                ):
                    with patch.object(
                        client, "_fallback_add_server", return_value=True
                    ) as mock_fallback:

                        result = client._check_and_install_server(
                            "memory", "failing command"
                        )

                        mock_fallback.assert_called_once_with("memory")
                        assert result is True

    def test_check_and_install_server_fails_when_both_methods_fail(
        self, client, sample_config
    ):
        """Test failure when both tool command and fallback fail."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(client, "is_server_installed", return_value=False):
                with patch.object(
                    client, "execute_command", return_value=(False, "command failed")
                ):
                    with patch.object(
                        client, "_fallback_add_server", return_value=False
                    ):

                        result = client._check_and_install_server(
                            "memory", "failing command"
                        )

                        assert result is False

    def test_check_and_install_server_verifies_installation(
        self, client, sample_config
    ):
        """Test that installation is verified after successful command."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(
                client, "is_server_installed", side_effect=[False, False]
            ):  # Not installed before and after
                with patch.object(
                    client, "execute_command", return_value=(True, "command succeeded")
                ):
                    with patch.object(
                        client, "_fallback_add_server", return_value=False
                    ):

                        result = client._check_and_install_server("memory", "command")

                        assert (
                            result is False
                        )  # Fails because verification shows not installed

    def test_check_and_install_server_skips_already_installed(
        self, client, sample_config
    ):
        """Test that already installed servers are skipped."""
        with patch.object(
            client, "get_tool_config", return_value=sample_config["servers"]
        ):
            with patch.object(client, "is_server_installed", return_value=True):
                with patch.object(client, "execute_command") as mock_execute:
                    with patch.object(client, "_fallback_add_server") as mock_fallback:

                        result = client._check_and_install_server("memory", "command")

                        mock_execute.assert_not_called()
                        mock_fallback.assert_not_called()
                        assert result is True


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    def test_operations_continue_after_individual_failures(self, client, sample_config):
        """Test that batch operations continue after individual server failures."""
        # Mock get_tool_config to return a small sample config instead of real config
        tool_config = {
            "memory": {"add_cmd": "test cmd 1"},
            "context7": {"add_cmd": "test cmd 2"},
        }
        with patch.object(client, "get_tool_config", return_value=tool_config):
            with patch.object(
                client, "_check_and_install_server", side_effect=[True, False]
            ):
                # One server fails in the middle, but operations continue
                result = client.add_all_servers()

                # Implementation returns False when any server fails
                # This test verifies that operations complete without crashing
                assert result is False

    def test_refresh_servers_handles_partial_failures(self, client, sample_config):
        """Test refresh_servers handles partial failures gracefully."""
        # Mock get_tool_config to return a small sample config
        tool_config = {
            "memory": {"add_cmd": "test cmd 1"},
            "context7": {"add_cmd": "test cmd 2"},
        }
        with patch.object(client, "get_tool_config", return_value=tool_config):
            with patch.object(client, "_execute_remove_command", return_value=True):
                with patch.object(
                    client, "_check_and_install_server", side_effect=[True, False]
                ):

                    result = client.refresh_servers()

                    # Implementation returns False when any server fails
                    # This test verifies that refresh operations complete without crashing
                    assert result is False

    def test_config_operations_handle_corrupted_files(self, client, tmp_path):
        """Test config operations handle corrupted config files."""
        config_path = tmp_path / "corrupted.json"

        # Create corrupted config
        with open(config_path, "w") as f:
            f.write('{"mcpServers": {"incomplete": }')

        result_add = client._add_server_to_config(config_path, "test", {})
        result_remove = client._remove_server_from_config(config_path, "test")

        assert result_add is False
        assert result_remove is False

    def test_get_config_locations_handles_path_errors(self, client):
        """Test _get_config_locations handles path construction errors."""
        # Should not crash even with unusual paths
        locations = client._get_config_locations("test_tool")

        assert isinstance(locations, list)
        # All locations should be Path objects
        for location in locations:
            assert isinstance(location, Path)
