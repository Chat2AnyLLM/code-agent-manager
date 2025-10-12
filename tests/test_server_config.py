"""Tests for server_config module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from code_assistant_manager.mcp.server_config import (
    _add_server_to_config,
    _remove_server_from_config,
)


class TestAddServerToConfig:
    """Test adding servers to config files."""

    def test_add_server_to_json_config(self):
        """Test adding a server to a JSON config file."""
        initial_config = {"mcpServers": {"existing-server": {"command": "echo"}}}
        new_server_config = {"command": "cat", "args": ["-n"]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_config, f)
            temp_path = Path(f.name)

        try:
            success = _add_server_to_config(temp_path, "new-server", new_server_config)
            assert success is True

            # Verify the server was added
            with open(temp_path, "r") as f:
                updated_config = json.load(f)

            assert "new-server" in updated_config["mcpServers"]
            assert updated_config["mcpServers"]["new-server"] == new_server_config
            assert "existing-server" in updated_config["mcpServers"]
        finally:
            temp_path.unlink()

    def test_add_server_already_exists(self):
        """Test adding a server that already exists."""
        initial_config = {"mcpServers": {"existing-server": {"command": "echo"}}}
        duplicate_config = {"command": "cat"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_config, f)
            temp_path = Path(f.name)

        try:
            success = _add_server_to_config(
                temp_path, "existing-server", duplicate_config
            )
            assert success is False

            # Verify config wasn't changed
            with open(temp_path, "r") as f:
                config = json.load(f)
            assert config == initial_config
        finally:
            temp_path.unlink()

    def test_add_server_create_container(self):
        """Test adding a server when the container doesn't exist."""
        initial_config = {}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_config, f)
            temp_path = Path(f.name)

        try:
            server_config = {"command": "echo"}
            success = _add_server_to_config(temp_path, "new-server", server_config)
            assert success is True

            with open(temp_path, "r") as f:
                updated_config = json.load(f)

            assert "mcpServers" in updated_config
            assert "new-server" in updated_config["mcpServers"]
        finally:
            temp_path.unlink()

    def test_add_server_invalid_config_file(self):
        """Test adding server to a corrupted config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = Path(f.name)

        try:
            success = _add_server_to_config(temp_path, "server", {"command": "echo"})
            assert success is False
        finally:
            temp_path.unlink()


class TestRemoveServerFromConfig:
    """Test removing servers from config files."""

    def test_remove_server_from_json_config(self):
        """Test removing a server from a JSON config file."""
        initial_config = {
            "mcpServers": {
                "server1": {"command": "echo"},
                "server2": {"command": "cat"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_config, f)
            temp_path = Path(f.name)

        try:
            success = _remove_server_from_config(temp_path, "server1")
            assert success is True

            # Verify the server was removed
            with open(temp_path, "r") as f:
                updated_config = json.load(f)

            assert "server1" not in updated_config["mcpServers"]
            assert "server2" in updated_config["mcpServers"]
        finally:
            temp_path.unlink()

    def test_remove_server_not_found(self):
        """Test removing a server that doesn't exist."""
        initial_config = {"mcpServers": {"server1": {"command": "echo"}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_config, f)
            temp_path = Path(f.name)

        try:
            success = _remove_server_from_config(temp_path, "nonexistent-server")
            assert success is False

            # Verify config wasn't changed
            with open(temp_path, "r") as f:
                config = json.load(f)
            assert config == initial_config
        finally:
            temp_path.unlink()

    def test_remove_server_nonexistent_file(self):
        """Test removing server from a file that doesn't exist."""
        success = _remove_server_from_config(Path("/nonexistent/file.json"), "server")
        assert success is False

    def test_remove_server_invalid_config_file(self):
        """Test removing server from a corrupted config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = Path(f.name)

        try:
            success = _remove_server_from_config(temp_path, "server")
            assert success is False
        finally:
            temp_path.unlink()
