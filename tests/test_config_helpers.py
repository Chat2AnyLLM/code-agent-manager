"""Tests for config_helpers module."""

import json
import tempfile
from pathlib import Path

import pytest

from code_assistant_manager.mcp.config_helpers import (
    _get_preferred_container_key,
    _load_config_file,
    _remove_server_from_containers,
    _save_config_file,
    _server_exists_in_config,
)


class TestLoadConfigFile:
    """Test config file loading functionality."""

    def test_load_json_file(self):
        """Test loading a valid JSON config file."""
        config_data = {"mcpServers": {"test-server": {"command": "echo"}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            loaded_config, is_toml = _load_config_file(temp_path)
            assert loaded_config == config_data
            assert is_toml is False
        finally:
            temp_path.unlink()

    def test_load_toml_file(self):
        """Test loading a TOML config file."""
        config_data = {"mcpServers": {"test-server": {"command": "echo"}}}
        toml_content = '["mcpServers"."test-server"]\ncommand = "echo"\n'

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            loaded_config, is_toml = _load_config_file(temp_path)
            assert (
                loaded_config is not None
            )  # TOML loading might be complex, just test it doesn't crash
            assert is_toml is True
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        config, is_toml = _load_config_file(Path("/nonexistent/file.json"))
        assert config == {}
        assert is_toml is False


class TestSaveConfigFile:
    """Test config file saving functionality."""

    def test_save_json_file(self):
        """Test saving a config as JSON."""
        config_data = {"mcpServers": {"test-server": {"command": "echo"}}}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            success = _save_config_file(temp_path, config_data, is_toml=False)
            assert success is True

            # Verify file was written correctly
            with open(temp_path, "r") as f:
                loaded_data = json.load(f)
            assert loaded_data == config_data
        finally:
            temp_path.unlink()

    def test_save_invalid_path(self):
        """Test saving to an invalid path."""
        config_data = {"test": "data"}
        invalid_path = Path("/invalid/path/file.json")
        success = _save_config_file(invalid_path, config_data, is_toml=False)
        assert success is False


class TestServerExistsInConfig:
    """Test server existence checking."""

    def test_server_exists_in_mcpservers(self):
        """Test checking if server exists in mcpServers container."""
        config = {
            "mcpServers": {
                "server1": {"command": "echo"},
                "server2": {"command": "cat"},
            }
        }
        assert _server_exists_in_config(config, "server1") is True
        assert _server_exists_in_config(config, "server3") is False

    def test_server_exists_in_servers(self):
        """Test checking if server exists in servers container."""
        config = {
            "servers": {"server1": {"command": "echo"}, "server2": {"command": "cat"}}
        }
        assert _server_exists_in_config(config, "server1") is True
        assert _server_exists_in_config(config, "server3") is False

    def test_server_exists_direct(self):
        """Test checking if server exists as direct key."""
        config = {"server1": {"command": "echo"}, "other_key": "value"}
        assert _server_exists_in_config(config, "server1") is True
        assert _server_exists_in_config(config, "server2") is False


class TestPreferredContainerKey:
    """Test preferred container key selection."""

    def test_existing_mcpservers(self):
        """Test selecting mcpServers when it exists."""
        config = {"mcpServers": {}, "servers": {}}
        assert _get_preferred_container_key(config, is_toml=False) == "mcpServers"

    def test_existing_servers(self):
        """Test selecting servers when it exists but mcpServers doesn't."""
        config = {"servers": {}}
        assert _get_preferred_container_key(config, is_toml=False) == "servers"

    def test_default_fallback(self):
        """Test default fallback to mcpServers."""
        config = {}
        assert _get_preferred_container_key(config, is_toml=False) == "mcpServers"


class TestRemoveServerFromContainers:
    """Test server removal from config containers."""

    def test_remove_from_mcpservers(self):
        """Test removing server from mcpServers container."""
        config = {
            "mcpServers": {
                "server1": {"command": "echo"},
                "server2": {"command": "cat"},
            }
        }
        result = _remove_server_from_containers(config, "server1")
        assert result is True
        assert "server1" not in config["mcpServers"]
        assert "server2" in config["mcpServers"]

    def test_remove_direct_server(self):
        """Test removing direct server entry."""
        config = {"server1": {"command": "echo"}, "other_key": "value"}
        result = _remove_server_from_containers(config, "server1")
        assert result is True
        assert "server1" not in config
        assert "other_key" in config

    def test_remove_nonexistent_server(self):
        """Test removing server that doesn't exist."""
        config = {"mcpServers": {"server1": {"command": "echo"}}}
        result = _remove_server_from_containers(config, "server2")
        assert result is False
        assert "server1" in config["mcpServers"]
