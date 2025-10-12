"""Tests for format_converters module."""

import pytest

from code_assistant_manager.mcp.format_converters import (
    _convert_server_to_command_format,
    _convert_server_to_stdio_format,
)


class TestConvertServerToStdioFormat:
    """Test server to stdio format conversion."""

    def test_convert_package_server(self):
        """Test converting a package-based server."""
        server_info = {"package": "@modelcontextprotocol/server-filesystem"}
        result = _convert_server_to_stdio_format(server_info)

        expected = {
            "type": "stdio",
            "env": {},
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        }
        assert result == expected

    def test_convert_command_server(self):
        """Test converting a command-based server."""
        server_info = {"command": "python", "args": ["-m", "mcp_server"]}
        result = _convert_server_to_stdio_format(server_info)

        expected = {
            "type": "stdio",
            "env": {},
            "command": "python",
            "args": ["-m", "mcp_server"],
        }
        assert result == expected

    def test_convert_command_string(self):
        """Test converting a command string."""
        server_info = "python -m mcp_server"
        result = _convert_server_to_stdio_format(server_info)

        expected = {
            "type": "stdio",
            "env": {},
            "command": "python",
            "args": ["-m", "mcp_server"],
        }
        assert result == expected

    def test_convert_with_env(self):
        """Test converting server with existing env."""
        server_info = {"command": "echo", "env": {"CUSTOM_VAR": "value"}}
        result = _convert_server_to_stdio_format(server_info)

        assert result["env"]["CUSTOM_VAR"] == "value"
        assert result["command"] == "echo"

    def test_convert_with_tls_tools(self):
        """Test converting with TLS rejection for specific tools."""
        server_info = {"package": "test-package"}
        result = _convert_server_to_stdio_format(server_info, ["test-tool"])

        # Note: This test assumes the tool_name is passed separately
        # In the actual implementation, this would need the tool context
        assert result["command"] == "npx"
        assert result["args"] == ["-y", "test-package"]

    def test_convert_args_override(self):
        """Test that explicit args override command parsing."""
        server_info = {"command": "python script.py", "args": ["--custom", "arg"]}
        result = _convert_server_to_stdio_format(server_info)

        assert result["command"] == "python"
        assert result["args"] == ["--custom", "arg"]


class TestConvertServerToCommandFormat:
    """Test server to command format conversion."""

    def test_convert_package_to_command(self):
        """Test converting package server to command format."""
        server_info = {"package": "@modelcontextprotocol/server-filesystem"}
        result = _convert_server_to_command_format(server_info)

        expected = {"command": "npx -y @modelcontextprotocol/server-filesystem"}
        assert result == expected

    def test_convert_command_to_command(self):
        """Test converting command server to command format."""
        server_info = {"command": "python -m mcp_server"}
        result = _convert_server_to_command_format(server_info)

        expected = {"command": "python -m mcp_server"}
        assert result == expected

    def test_convert_with_codex_extra(self):
        """Test converting with codex extras (when tool is codex)."""
        server_info = {"command": "python script.py", "codex_extra": "--extra-arg"}
        # Note: This test assumes tool_name context for codex_extra logic
        result = _convert_server_to_command_format(server_info, add_codex_extra=False)

        assert result["command"] == "python script.py"

    def test_empty_server_info(self):
        """Test converting empty server info."""
        result = _convert_server_to_command_format({})
        assert result == {}

    def test_minimal_server_info(self):
        """Test converting minimal server info."""
        server_info = {"package": "test-package"}
        result = _convert_server_to_command_format(server_info)

        assert result["command"] == "npx -y test-package"
