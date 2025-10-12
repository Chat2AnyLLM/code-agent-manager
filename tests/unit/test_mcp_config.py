"""Tests for MCP configuration loading and parsing."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from code_assistant_manager.mcp.base import MCPBase
from code_assistant_manager.mcp.manager import MCPManager


@pytest.fixture
def sample_config():
    """Sample MCP configuration for testing."""
    return {
        "global": {
            "tools_with_scope": ["claude", "gemini"],
            "tools_with_tls_flag": ["claude", "codex"],
            "tools_with_cli_separator": ["codex", "qwen"],
            "all_tools": ["claude", "codex", "gemini", "qwen", "copilot"],
        },
        "servers": {
            "memory": {"package": "@modelcontextprotocol/server-memory"},
            "context7": {
                "package": "@upstash/context7-mcp@latest",
                "quote_package_for": ["codex"],
            },
            "filesystem": {
                "package": "@modelcontextprotocol/server-filesystem",
                "env": {"ALLOWED_DIRS": "/tmp,/home/user"},
            },
            "command": {
                "command": "python",
                "args": ["-m", "my_mcp_server"],
                "env": {"PORT": "3000"},
            },
        },
    }


@pytest.fixture
def temp_config_file(tmp_path, sample_config):
    """Create a temporary config file."""
    config_path = tmp_path / "mcp.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=4)
    return config_path


class TestMCPBaseConfigLoading:
    """Test MCPBase configuration loading functionality."""

    def test_load_config_success(self, temp_config_file, sample_config):
        """Test successful config loading."""
        base = MCPManager()  # Use manager which inherits from MCPBase

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            success, config = base.load_config()

            assert success is True
            assert config == sample_config

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        base = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=Path("/nonexistent/path"),
        ):
            success, config = base.load_config()

            assert success is False
            assert config == {}

    def test_load_config_malformed_json(self, tmp_path):
        """Test config loading with malformed JSON."""
        base = MCPManager()
        config_path = tmp_path / "bad.json"
        with open(config_path, "w") as f:
            f.write("{ invalid json }")

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            success, config = base.load_config()

            assert success is False
            assert config == {}

    def test_load_config_empty_file(self, tmp_path):
        """Test config loading with empty file."""
        base = MCPManager()
        config_path = tmp_path / "empty.json"
        with open(config_path, "w") as f:
            f.write("")

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            success, config = base.load_config()

            assert success is False
            assert config == {}


class TestMCPManagerToolConfigGeneration:
    """Test MCPManager tool configuration generation."""

    def test_get_tool_config_claude_with_scope_and_tls(
        self, temp_config_file, sample_config
    ):
        """Test Claude tool config includes scope and TLS flags."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            config = manager.get_tool_config("claude")

            assert "memory" in config
            assert "context7" in config
            assert "filesystem" in config

            # Check memory server command
            memory_cmd = config["memory"]["add_cmd"]
            assert "claude mcp add memory --scope user" in memory_cmd
            assert "--env NODE_TLS_REJECT_UNAUTHORIZED" in memory_cmd

            # Check context7 server command
            context7_cmd = config["context7"]["add_cmd"]
            assert "claude mcp add context7 --scope user" in context7_cmd
            assert "--env NODE_TLS_REJECT_UNAUTHORIZED" in context7_cmd

    def test_get_tool_config_codex_with_cli_separator_and_quoting(
        self, temp_config_file, sample_config
    ):
        """Test Codex tool config includes CLI separator and package quoting."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            config = manager.get_tool_config("codex")

            assert "memory" in config
            assert "context7" in config

            # Check memory server command
            memory_cmd = config["memory"]["add_cmd"]
            assert "codex mcp add memory" in memory_cmd  # Command format
            assert "-- npx" in memory_cmd  # CLI separator before npx command
            assert "NODE_TLS_REJECT_UNAUTHORIZED" in memory_cmd  # TLS flag

            # Check context7 server command (should be quoted due to quote_package_for)
            context7_cmd = config["context7"]["add_cmd"]
            assert "codex mcp add context7" in context7_cmd
            assert "-- npx" in context7_cmd  # CLI separator before npx command
            assert '"@upstash/context7-mcp@latest"' in context7_cmd  # Quoted package

    def test_get_tool_config_gemini_with_scope_no_tls(
        self, temp_config_file, sample_config
    ):
        """Test Gemini tool config has scope flag but no TLS flag."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            config = manager.get_tool_config("gemini")

            assert "memory" in config

            # Check memory server command
            memory_cmd = config["memory"]["add_cmd"]
            assert "gemini mcp add memory" in memory_cmd
            assert (
                "--scope user" in memory_cmd
            )  # Has scope flag (gemini is in tools_with_scope)
            assert "NODE_TLS_REJECT_UNAUTHORIZED" not in memory_cmd  # No TLS flag

    def test_get_tool_config_unknown_tool(self, temp_config_file):
        """Test getting config for unknown tool - should still generate commands."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            config = manager.get_tool_config("unknown_tool")

            # Unknown tools still get config generated (commands use the tool name)
            # This allows flexibility for new tools without explicit configuration
            assert isinstance(config, dict)
            assert "memory" in config  # Should have memory server config
            assert "unknown_tool mcp add memory" in config["memory"]["add_cmd"]

    def test_get_available_tools_from_config(self, temp_config_file, sample_config):
        """Test extracting available tools from config."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            tools = manager.get_available_tools()

            expected_tools = ["claude", "codex", "gemini", "qwen", "copilot"]
            assert set(tools) == set(expected_tools)
            assert tools == sorted(expected_tools)  # Should be sorted

    def test_get_available_tools_empty_config(self):
        """Test getting available tools from empty config."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=Path("/nonexistent"),
        ):
            tools = manager.get_available_tools()

            assert tools == []


class TestMCPConfigServerTypes:
    """Test different server configuration types."""

    def test_package_based_servers(self, temp_config_file, sample_config):
        """Test package-based server configuration."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            claude_config = manager.get_tool_config("claude")

            memory_config = claude_config["memory"]
            assert "add_cmd" in memory_config
            assert "remove_cmd" in memory_config
            assert "list_cmd" in memory_config

            add_cmd = memory_config["add_cmd"]
            assert "@modelcontextprotocol/server-memory" in add_cmd

    def test_command_based_servers(self, temp_config_file, sample_config):
        """Test command-based server configuration."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            claude_config = manager.get_tool_config("claude")

            command_config = claude_config["command"]
            assert "add_cmd" in command_config
            assert "remove_cmd" in command_config
            assert "list_cmd" in command_config

            add_cmd = command_config["add_cmd"]
            # Command-based servers include the command (python) but not args
            # The implementation uses only server_info["command"], not "args"
            assert "python" in add_cmd
            assert "claude mcp add command" in add_cmd

    def test_servers_with_env_variables(self, temp_config_file, sample_config):
        """Test servers with environment variables config section."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            claude_config = manager.get_tool_config("claude")

            fs_config = claude_config["filesystem"]
            add_cmd = fs_config["add_cmd"]

            # Server-specific env vars are NOT included in generated commands
            # (env vars are stored in config but handled separately by the MCP clients)
            # Only global TLS flag is included for claude (as per tools_with_tls_flag)
            assert "NODE_TLS_REJECT_UNAUTHORIZED" in add_cmd
            assert "claude mcp add filesystem" in add_cmd


class TestMCPConfigEdgeCases:
    """Test edge cases in MCP configuration."""

    def test_config_with_missing_global_section(self, tmp_path):
        """Test config missing global section."""
        config_path = tmp_path / "mcp.json"
        config_data = {
            "servers": {"memory": {"package": "@modelcontextprotocol/server-memory"}}
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            tools = manager.get_available_tools()
            assert tools == []

    def test_config_with_empty_servers_section(self, tmp_path):
        """Test config with empty servers section."""
        config_path = tmp_path / "mcp.json"
        config_data = {"global": {"all_tools": ["claude"]}, "servers": {}}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            claude_config = manager.get_tool_config("claude")
            assert claude_config == {}

    def test_config_with_malformed_server_entries(self, tmp_path):
        """Test config with malformed server entries."""
        config_path = tmp_path / "mcp.json"
        config_data = {
            "global": {"all_tools": ["claude"]},
            "servers": {
                "good_server": {"package": "@good/package"},
                "bad_server": "not_an_object",
                "empty_server": {},
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            claude_config = manager.get_tool_config("claude")

            # Should handle good server
            assert "good_server" in claude_config
            # Should skip bad servers gracefully
            assert (
                "bad_server" not in claude_config
                or "add_cmd" not in claude_config["bad_server"]
            )

    def test_config_with_unknown_tool_flags(self, tmp_path):
        """Test config with unknown tool flags."""
        config_path = tmp_path / "mcp.json"
        config_data = {
            "global": {"tools_with_unknown_flag": ["claude"], "all_tools": ["claude"]},
            "servers": {"memory": {"package": "@modelcontextprotocol/server-memory"}},
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config", return_value=config_path
        ):
            claude_config = manager.get_tool_config("claude")

            # Should still generate basic commands despite unknown flags
            assert "memory" in claude_config
            assert "add_cmd" in claude_config["memory"]


class TestMCPConfigToolSpecificFlags:
    """Test tool-specific flag handling."""

    def test_tools_with_scope_flag(self, temp_config_file, sample_config):
        """Test tools_with_scope flag application."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            # Claude should have scope (in tools_with_scope)
            claude_config = manager.get_tool_config("claude")
            assert "--scope user" in claude_config["memory"]["add_cmd"]

            # Gemini should also have scope (in tools_with_scope per fixture)
            gemini_config = manager.get_tool_config("gemini")
            assert "--scope user" in gemini_config["memory"]["add_cmd"]

            # Copilot should NOT have scope (not in tools_with_scope)
            copilot_config = manager.get_tool_config("copilot")
            assert "--scope user" not in copilot_config["memory"]["add_cmd"]

    def test_tools_with_tls_flag(self, temp_config_file, sample_config):
        """Test tools_with_tls_flag application."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            # Claude should have TLS flag
            claude_config = manager.get_tool_config("claude")
            assert "NODE_TLS_REJECT_UNAUTHORIZED" in claude_config["memory"]["add_cmd"]

            # Gemini should not have TLS flag
            gemini_config = manager.get_tool_config("gemini")
            assert (
                "NODE_TLS_REJECT_UNAUTHORIZED" not in gemini_config["memory"]["add_cmd"]
            )

    def test_tools_with_cli_separator(self, temp_config_file, sample_config):
        """Test tools_with_cli_separator flag application."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            # Codex should have CLI separator before the npx command
            codex_config = manager.get_tool_config("codex")
            assert "codex mcp add memory" in codex_config["memory"]["add_cmd"]
            assert (
                "-- npx" in codex_config["memory"]["add_cmd"]
            )  # CLI separator before npx

            # Claude should not have CLI separator
            claude_config = manager.get_tool_config("claude")
            assert "claude mcp add memory" in claude_config["memory"]["add_cmd"]
            assert " -- " not in claude_config["memory"]["add_cmd"]

    def test_quote_package_for_servers(self, temp_config_file, sample_config):
        """Test quote_package_for flag quotes packages correctly."""
        manager = MCPManager()

        with patch(
            "code_assistant_manager.mcp.base.find_mcp_config",
            return_value=temp_config_file,
        ):
            codex_config = manager.get_tool_config("codex")

            # context7 should be quoted for Codex
            context7_cmd = codex_config["context7"]["add_cmd"]
            assert '"@upstash/context7-mcp@latest"' in context7_cmd
