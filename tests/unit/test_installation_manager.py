"""Tests for MCP Installation Manager.

This module tests the InstallationManager class which handles installation
of MCP servers to specific tools/clients using schema-defined methods.

Key test areas:
- Server installation to different clients
- Installation method selection (preferred, fallback)
- Server configuration with environment variables
- Client manager retrieval
- Error handling for unsupported clients/servers
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from code_assistant_manager.mcp.installation_manager import (
    BaseClientManager,
    InstallationManager,
)
from code_assistant_manager.mcp.schema import (
    InstallationMethod,
    RemoteServerConfig,
    ServerSchema,
    STDIOServerConfig,
)


@pytest.fixture
def mock_server_schema():
    """Create a mock server schema for testing."""
    return ServerSchema(
        name="test-server",
        display_name="Test Server",
        description="A test MCP server",
        repository="https://github.com/test/test-server",
        license="MIT",
        installations={
            "npx": InstallationMethod(
                type="stdio",
                command="npx",
                args=["-y", "test-server"],
                description="Install via npx",
                recommended=True,
            ),
            "docker": InstallationMethod(
                type="stdio",
                command="docker",
                args=["run", "test-server"],
                description="Install via Docker",
                recommended=False,
            ),
        },
        arguments={
            "API_KEY": {
                "required": True,
                "description": "API key for authentication",
                "example": "sk-xxx",
            },
            "OPTIONAL_ARG": {
                "required": False,
                "description": "Optional argument",
            },
        },
        categories=["testing"],
        tags=["test", "mock"],
    )


@pytest.fixture
def mock_http_server_schema():
    """Create a mock HTTP server schema for testing."""
    return ServerSchema(
        name="http-server",
        display_name="HTTP Test Server",
        description="A test HTTP MCP server",
        installations={
            "http": InstallationMethod(
                type="http",
                url="https://api.example.com/mcp",
                headers={"Authorization": "Bearer ${API_KEY}"},
                description="HTTP endpoint",
                recommended=True,
            ),
        },
        arguments={},
        categories=["testing"],
        tags=["http"],
    )


@pytest.fixture
def mock_registry_manager(mock_server_schema):
    """Create a mock registry manager."""
    mock = MagicMock()
    mock.get_server_schema.return_value = mock_server_schema
    return mock


@pytest.fixture
def installation_manager(mock_registry_manager, monkeypatch):
    """Create an InstallationManager with mocked dependencies."""
    manager = InstallationManager()
    monkeypatch.setattr(manager, "registry_manager", mock_registry_manager)
    return manager


class TestInstallationMethodSelection:
    """Tests for installation method selection logic."""

    def test_select_explicit_method(self, installation_manager, mock_server_schema):
        """Test selecting an explicitly specified method."""
        method = installation_manager._select_installation_method(
            mock_server_schema, "docker"
        )
        assert method is not None
        assert method.command == "docker"

    def test_select_default_method(self, installation_manager, mock_server_schema):
        """Test selecting the default (first) method when none specified."""
        method = installation_manager._select_installation_method(
            mock_server_schema, None, interactive=False
        )
        assert method is not None
        # Should return first method (npx in this case)
        assert method.command == "npx"

    def test_select_nonexistent_method(self, installation_manager, mock_server_schema):
        """Test selecting a non-existent method returns None."""
        method = installation_manager._select_installation_method(
            mock_server_schema, "nonexistent", interactive=False
        )
        assert method is None

    def test_select_method_empty_installations(self, installation_manager):
        """Test method selection with empty installations."""
        schema = ServerSchema(
            name="empty-server",
            description="No installations",
            installations={},
            arguments={},
        )
        method = installation_manager._select_installation_method(
            schema, None, interactive=False
        )
        assert method is None


class TestServerConfiguration:
    """Tests for server configuration logic."""

    def test_configure_stdio_server(
        self, installation_manager, mock_server_schema, monkeypatch
    ):
        """Test configuring a STDIO server."""
        # Set environment variable for required argument
        monkeypatch.setenv("API_KEY", "test-key-123")

        method = mock_server_schema.installations["npx"]
        config = installation_manager._configure_server(mock_server_schema, method)

        assert config is not None
        assert isinstance(config, STDIOServerConfig)
        assert config.command == "npx"
        assert config.env.get("API_KEY") == "test-key-123"

    def test_configure_http_server(self, installation_manager, mock_http_server_schema):
        """Test configuring an HTTP server."""
        method = mock_http_server_schema.installations["http"]
        config = installation_manager._configure_server(mock_http_server_schema, method)

        assert config is not None
        assert isinstance(config, RemoteServerConfig)
        assert config.url == "https://api.example.com/mcp"

    def test_configure_server_missing_required_arg(
        self, installation_manager, mock_server_schema, monkeypatch
    ):
        """Test that missing required arguments are handled."""
        # Remove environment variable
        monkeypatch.delenv("API_KEY", raising=False)

        method = mock_server_schema.installations["npx"]

        # Mock input to return empty string (user doesn't provide value)
        with patch("builtins.input", return_value=""):
            config = installation_manager._configure_server(mock_server_schema, method)

        # Should return None due to missing required argument
        assert config is None

    def test_configure_server_user_provides_arg(
        self, installation_manager, mock_server_schema, monkeypatch
    ):
        """Test that user-provided arguments work."""
        monkeypatch.delenv("API_KEY", raising=False)

        method = mock_server_schema.installations["npx"]

        # Mock input to return a value
        with patch("builtins.input", return_value="user-provided-key"):
            config = installation_manager._configure_server(mock_server_schema, method)

        assert config is not None
        assert config.env.get("API_KEY") == "user-provided-key"


class TestClientManagerRetrieval:
    """Tests for client manager retrieval."""

    def test_get_claude_client(self, installation_manager):
        """Test retrieving Claude client manager."""
        with patch("code_assistant_manager.mcp.claude.ClaudeMCPClient") as MockClient:
            MockClient.return_value = MagicMock()
            client = installation_manager._get_client_manager("claude")
            assert client is not None
            MockClient.assert_called_once()

    def test_get_codex_client(self, installation_manager):
        """Test retrieving Codex client manager."""
        with patch("code_assistant_manager.mcp.codex.CodexMCPClient") as MockClient:
            MockClient.return_value = MagicMock()
            client = installation_manager._get_client_manager("codex")
            assert client is not None

    def test_get_unsupported_client(self, installation_manager):
        """Test retrieving unsupported client returns None."""
        client = installation_manager._get_client_manager("unsupported-client")
        assert client is None

    def test_get_client_import_error(self, installation_manager):
        """Test handling ImportError during client retrieval."""
        with patch(
            "code_assistant_manager.mcp.claude.ClaudeMCPClient",
            side_effect=ImportError("Module not found"),
        ):
            client = installation_manager._get_client_manager("claude")
            assert client is None


class TestServerInstallation:
    """Tests for full server installation flow."""

    def test_install_server_success(self, installation_manager, monkeypatch):
        """Test successful server installation."""
        monkeypatch.setenv("API_KEY", "test-key")

        # Mock the MCP manager and client
        mock_client = MagicMock()
        mock_client.is_server_installed.return_value = False
        mock_client.add_server_with_config.return_value = True

        mock_manager = MagicMock()
        mock_manager.get_client.return_value = mock_client

        with patch(
            "code_assistant_manager.mcp.manager.MCPManager",
            return_value=mock_manager,
        ):
            success = installation_manager.install_server(
                server_name="test-server",
                client_name="claude",
                scope="user",
                interactive=False,
            )

        assert success is True
        mock_client.add_server_with_config.assert_called_once()

    def test_install_server_not_found(
        self, installation_manager, mock_registry_manager
    ):
        """Test installation of non-existent server."""
        mock_registry_manager.get_server_schema.return_value = None

        success = installation_manager.install_server(
            server_name="nonexistent",
            client_name="claude",
        )

        assert success is False

    def test_install_server_unsupported_client(self, installation_manager):
        """Test installation to unsupported client."""
        mock_manager = MagicMock()
        mock_manager.get_client.return_value = None

        with patch(
            "code_assistant_manager.mcp.manager.MCPManager",
            return_value=mock_manager,
        ):
            success = installation_manager.install_server(
                server_name="test-server",
                client_name="unsupported",
            )

        assert success is False

    def test_install_server_already_installed(self, installation_manager, monkeypatch):
        """Test that already installed servers are handled gracefully."""
        monkeypatch.setenv("API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.is_server_installed.return_value = True  # Already installed

        mock_manager = MagicMock()
        mock_manager.get_client.return_value = mock_client

        with patch(
            "code_assistant_manager.mcp.manager.MCPManager",
            return_value=mock_manager,
        ):
            success = installation_manager.install_server(
                server_name="test-server",
                client_name="claude",
                interactive=False,
            )

        # Should return True but not call add_server_with_config
        assert success is True
        mock_client.add_server_with_config.assert_not_called()

    def test_install_server_with_specific_method(
        self, installation_manager, monkeypatch
    ):
        """Test installation with specific method."""
        monkeypatch.setenv("API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.is_server_installed.return_value = False
        mock_client.add_server_with_config.return_value = True

        mock_manager = MagicMock()
        mock_manager.get_client.return_value = mock_client

        with patch(
            "code_assistant_manager.mcp.manager.MCPManager",
            return_value=mock_manager,
        ):
            success = installation_manager.install_server(
                server_name="test-server",
                client_name="claude",
                installation_method="docker",
            )

        assert success is True


class TestBaseClientManager:
    """Tests for BaseClientManager abstract class."""

    def test_server_exists_not_implemented(self):
        """Test that server_exists raises NotImplementedError."""
        manager = BaseClientManager()
        with pytest.raises(NotImplementedError):
            manager.server_exists("test-server")
