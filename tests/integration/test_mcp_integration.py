"""Integration tests for MCP system components."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.mcp.manager import MCPManager
from code_assistant_manager.mcp.tool import MCPTool


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary MCP config file."""
    config_path = tmp_path / "mcp.json"
    config_data = {
        "global": {
            "tools_with_scope": ["claude", "codex"],
            "tools_with_tls_flag": ["claude"],
            "tools_with_cli_separator": ["codex"],
            "all_tools": ["claude", "codex", "gemini"],
        },
        "servers": {
            "memory": {"package": "@modelcontextprotocol/server-memory"},
            "context7": {
                "package": "@upstash/context7-mcp@latest",
                "quote_package_for": ["codex"],
            },
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    return config_path


@pytest.fixture
def mock_config_manager(temp_config_file):
    """Create a mock ConfigManager."""
    config = MagicMock(spec=ConfigManager)
    return config


class TestMCPToolIntegration:
    """Integration tests for MCPTool."""

    def test_mcp_tool_initialization(self, mock_config_manager):
        """Test MCPTool initializes with config manager."""
        tool = MCPTool(mock_config_manager)

        assert tool.config == mock_config_manager
        assert tool.command_name == "mcp"
        assert hasattr(tool, "manager")
        assert isinstance(tool.manager, MCPManager)

    def test_mcp_tool_run_with_no_args_shows_help(self, mock_config_manager, capsys):
        """Test MCPTool shows help when run with no arguments."""
        tool = MCPTool(mock_config_manager)

        result = tool.run([])

        assert result == 0
        captured = capsys.readouterr()
        assert "Manage Model Context Protocol servers" in captured.out
        assert "Usage:" in captured.out

    def test_mcp_tool_run_invalid_command(self, mock_config_manager, capsys):
        """Test MCPTool handles invalid commands."""
        tool = MCPTool(mock_config_manager)

        result = tool.run(["invalid_command"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown command 'invalid_command'" in captured.out

    def test_mcp_tool_run_invalid_tool(self, mock_config_manager, capsys):
        """Test MCPTool handles invalid tools."""
        tool = MCPTool(mock_config_manager)

        result = tool.run(["invalid_tool", "add", "memory"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown command 'invalid_tool'" in captured.out


class TestMCPManagerConfigIntegration:
    """Integration tests for MCPManager with config loading."""

    def test_manager_loads_config_correctly(self, temp_config_file):
        """Test manager loads and parses config correctly."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            success, config = manager.load_config()

            assert success is True
            assert "global" in config
            assert "servers" in config
            assert config["global"]["all_tools"] == ["claude", "codex", "gemini"]

    def test_manager_get_available_tools(self, temp_config_file):
        """Test manager extracts available tools from config."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            tools = manager.get_available_tools()

            assert set(tools) == {"claude", "codex", "gemini"}

    def test_manager_get_tool_config_claude(self, temp_config_file):
        """Test manager generates correct tool config for Claude."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            claude_config = manager.get_tool_config("claude")

            # Should have both servers
            assert "memory" in claude_config
            assert "context7" in claude_config

            # Should include scope and TLS flags for Claude
            memory_cmd = claude_config["memory"]["add_cmd"]
            assert "--scope user" in memory_cmd
            assert "--env NODE_TLS_REJECT_UNAUTHORIZED" in memory_cmd

    def test_manager_get_tool_config_codex(self, temp_config_file):
        """Test manager generates correct tool config for Codex."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            codex_config = manager.get_tool_config("codex")

            # Should have both servers
            assert "memory" in codex_config
            assert "context7" in codex_config

            # Should include CLI separator for Codex
            memory_cmd = codex_config["memory"]["add_cmd"]
            assert "--" in memory_cmd  # CLI separator

            # Should quote packages for Codex
            context7_cmd = codex_config["context7"]["add_cmd"]
            assert '"@upstash/context7-mcp@latest"' in context7_cmd


class TestMCPSystemEndToEnd:
    """End-to-end integration tests for MCP system."""

    def test_manager_handles_config_not_found(self):
        """Test manager handles missing config file."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=Path("/nonexistent/path"),
        ):
            success, config = manager.load_config()

            assert success is False
            assert config == {}

    def test_manager_handles_malformed_config(self, tmp_path):
        """Test manager handles malformed config file."""
        config_path = tmp_path / "bad_config.json"
        with open(config_path, "w") as f:
            f.write("{ invalid json content }")

        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            success, config = manager.load_config()

            assert success is False
            assert config == {}

    def test_parallel_operations_complete_successfully(self, temp_config_file):
        """Test that parallel operations complete without deadlocks."""
        manager = MCPManager()

        with patch.object(
            manager, "get_available_tools", return_value=["claude", "codex"]
        ):
            # Mock successful operations
            with patch.object(manager, "add_all_servers_for_tool", return_value=True):
                result = manager.add_all_servers()
                assert result is True

            with patch.object(
                manager, "remove_all_servers_for_tool", return_value=True
            ):
                result = manager.remove_all_servers()
                assert result is True

    def test_tool_config_handles_unknown_flags(self, temp_config_file):
        """Test tool config generation handles unknown flags gracefully."""
        manager = MCPManager()

        # Config with unknown tool
        config_data = {
            "global": {"tools_with_unknown_flag": ["claude"], "all_tools": ["claude"]},
            "servers": {"memory": {"package": "@test/package"}},
        }

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
                claude_config = manager.get_tool_config("claude")

                # Should still generate basic commands even with unknown flags
                assert "memory" in claude_config
                assert "add_cmd" in claude_config["memory"]


class TestMCPClientBaseIntegration:
    """Integration tests for base client functionality."""

    def test_client_command_execution_integration(self):
        """Test client command execution integrates with MCPBase."""
        from code_assistant_manager.mcp.base_client import MCPClient

        client = MCPClient("test_tool")

        # Mock subprocess.run behavior
        with patch("subprocess.run") as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "Success output"
            mock_process.stderr = ""
            mock_subprocess.return_value = mock_process

            success, output = client.execute_command("echo test")

            assert success is True
            assert output == "Success output"
            mock_subprocess.assert_called_once()

    def test_client_config_operations_integration(self, tmp_path):
        """Test client config file operations integration."""
        from code_assistant_manager.mcp.base_client import MCPClient

        client = MCPClient("test_tool")
        config_path = tmp_path / "test.json"

        # Test adding to config
        server_info = {"type": "stdio", "command": "npx"}
        result = client._add_server_to_config(config_path, "test_server", server_info)

        assert result is True
        assert config_path.exists()

        # Verify content
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test_server" in config["mcpServers"]

        # Test removing from config
        result = client._remove_server_from_config(config_path, "test_server")

        assert result is True
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "test_server" not in config["mcpServers"]
