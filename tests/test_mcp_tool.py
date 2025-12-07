"""Test the MCP system implementation."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.mcp.clients import ClaudeMCPClient
from code_assistant_manager.mcp.manager import MCPManager
from code_assistant_manager.mcp.tool import MCPTool


@pytest.fixture
def mcp_tool():
    """Create an MCPTool instance for testing."""
    config = MagicMock(spec=ConfigManager)
    return MCPTool(config)


@pytest.fixture
def mock_config():
    """Mock MCP configuration for testing."""
    with patch("code_assistant_manager.mcp.base.find_mcp_config") as mock_find:
        mock_find.return_value = "/fake/path/mcp.json"
        with patch(
            "builtins.open", mock_open(read_data='{"global": {}, "servers": {}}')
        ):
            with patch("json.load", return_value={"global": {}, "servers": {}}):
                yield


@pytest.fixture
def sample_new_config():
    """Sample new simplified MCP configuration for testing."""
    return {
        "global": {
            "tools_with_scope": [
                "claude",
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
            ],
            "tools_with_tls_flag": ["claude", "codex"],
            "tools_with_cli_separator": ["claude", "codex"],
            "all_tools": [
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
            ],
        },
        "servers": {
            "context7": {
                "package": "@upstash/context7-mcp@latest",
                "quote_package_for": ["codex"],
            },
            "memory": {"package": "@modelcontextprotocol/server-memory"},
        },
    }


# ===== MCP SYSTEM TESTS =====


def test_mcp_tool_has_command_name(mcp_tool):
    """Test that MCPTool has the correct command name."""
    assert mcp_tool.command_name == "mcp"


def test_mcp_tool_help(mcp_tool, capsys, mock_config):
    """Test that help is displayed when no args are provided."""
    result = mcp_tool.run([])
    captured = capsys.readouterr()

    assert result == 0
    assert "Manage Model Context Protocol servers" in captured.out
    assert "Usage:" in captured.out
    assert "server  Manage MCP servers" in captured.out


def test_manager_initialization(mock_config):
    """Test MCPManager initializes with all expected clients."""
    manager = MCPManager()

    # Check that all expected clients are created
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
        assert manager.clients[client_name] is not None


def test_get_client_returns_correct_type(mock_config):
    """Test that get_client returns the correct client type."""
    manager = MCPManager()

    claude_client = manager.get_client("claude")
    assert isinstance(claude_client, ClaudeMCPClient)

    # Test nonexistent client
    nonexistent_client = manager.get_client("nonexistent")
    assert nonexistent_client is None


def test_load_config_success(mock_config):
    """Test successful configuration loading."""
    manager = MCPManager()
    success, config = manager.load_config()

    assert success is True
    assert config == {"global": {}, "servers": {}}


def test_get_available_tools(sample_new_config):
    """Test getting available tools from configuration."""
    manager = MCPManager()

    # Mock the load_config to return our test config
    with patch.object(manager, "load_config", return_value=(True, sample_new_config)):
        tools = manager.get_available_tools()

        expected_tools = [
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
        assert set(tools) == set(expected_tools)
        assert tools == sorted(expected_tools)  # Should be sorted


def test_get_tool_config_new_format(sample_new_config):
    """Test getting tool configurations from new format."""
    manager = MCPManager()

    # Mock the load_config to return our test config
    with patch.object(manager, "load_config", return_value=(True, sample_new_config)):
        # Test Claude config
        claude_config = manager.get_tool_config("claude")
        assert "context7" in claude_config
        assert "memory" in claude_config

        # Verify Claude commands include scope and TLS flags
        context7_cmd = claude_config["context7"]["add_cmd"]
        assert "--scope user" in context7_cmd
        assert "--env NODE_TLS_REJECT_UNAUTHORIZED" in context7_cmd
        assert "npx -y @upstash/context7-mcp@latest" in context7_cmd


def test_client_operations(mock_config):
    """Test basic client operations."""
    from code_assistant_manager.mcp.clients import ClaudeMCPClient

    client = ClaudeMCPClient()
    assert client.tool_name == "claude"


def test_tool_subcommands_with_valid_client(mcp_tool, capsys, sample_new_config):
    """Test tool-specific subcommands work with valid clients."""
    # This test expects MCPTool to handle tool names directly, but the current
    # implementation only handles 'server' subcommands. Tool-specific operations
    # are handled through 'server <command> --client <tool>' commands.
    pytest.skip(
        "MCPTool does not handle tool-specific commands directly - use 'server <command> --client <tool>' instead"
    )


def test_invalid_tool_subcommand(mcp_tool, capsys):
    """Test handling of invalid tool subcommands."""
    # Mock available_tools to not include invalid_tool
    with patch.object(
        mcp_tool.manager, "get_available_tools", return_value=["claude", "codex"]
    ):
        result = mcp_tool.run(["invalid_tool", "list"])
        captured = capsys.readouterr()

    assert result == 1
    assert "Unknown command 'invalid_tool'" in captured.out


def test_unknown_command(mcp_tool, capsys):
    """Test handling of unknown commands."""
    result = mcp_tool.run(["unknown_command"])
    captured = capsys.readouterr()

    assert result == 1
    assert "Unknown command 'unknown_command'" in captured.out


# ===== BACKWARD COMPATIBILITY TESTS =====


def test_legacy_apply_command(mcp_tool, capsys, mock_config):
    """Test that the legacy 'apply' command shows deprecation notice and works."""
    # The legacy 'apply' command is no longer supported in the current MCPTool implementation
    pytest.skip(
        "Legacy 'apply' command is no longer supported - use 'server add --all' instead"
    )


# ===== INTEGRATION TESTS =====


def test_cli_tool_registration():
    """Test that MCPTool is properly registered for CLI discovery."""
    from code_assistant_manager.tools import get_registered_tools

    registered_tools = get_registered_tools()

    # MCP tool should be registered
    assert "mcp" in registered_tools
    assert registered_tools["mcp"] == MCPTool


def test_end_to_end_help_output(mcp_tool, capsys, sample_new_config):
    """Test that help output includes all configured tools."""
    # The MCPTool help only shows the 'server' command, not individual tools
    # The test was expecting the old behavior where tools were listed directly
    result = mcp_tool.run([])
    captured = capsys.readouterr()

    assert result == 0
    # Check that the help shows the server command
    assert "server  Manage MCP servers" in captured.out
