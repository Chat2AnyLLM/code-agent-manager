"""Integration tests for error handling system."""

import subprocess
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager
from code_assistant_manager.exceptions import (
    CodeAssistantManagerError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
    ToolExecutionError,
    ValidationError,
    create_error_handler,
)
from code_assistant_manager.tools.base import CLITool


class TestToolErrorHandling:
    """Test error handling in tool execution."""

    def test_tool_execution_with_structured_errors(self):
        """Test that tool execution uses structured error handling."""

        # Create a mock tool class
        class TestTool(CLITool):
            command_name = "test_tool"

            def run(self, args=None):
                # Simulate an error
                raise FileNotFoundError("Command not found")

        # Mock config manager
        mock_config = MagicMock(spec=ConfigManager)
        tool = TestTool(mock_config)

        # Mock the error handler
        with patch(
            "code_assistant_manager.tools.base.create_error_handler"
        ) as mock_handler:
            mock_error_handler = MagicMock()
            mock_error_handler.return_value = ToolExecutionError(
                "Tool execution failed", tool_name="test_tool", command="test command"
            )
            mock_handler.return_value = mock_error_handler

            # Test error handling
            result = tool._handle_error(
                "Test error", FileNotFoundError("Command not found")
            )

            # Verify error handler was called
            mock_handler.assert_called_once_with("test_tool")
            mock_error_handler.assert_called_once()
            assert result == 1

    def test_tool_run_with_env_error_handling(self):
        """Test error handling in _run_tool_with_env method."""

        class TestTool(CLITool):
            command_name = "test_tool"

            def run(self, args=None):
                return 0

        # Mock config manager
        mock_config = MagicMock(spec=ConfigManager)
        tool = TestTool(mock_config)

        # Mock subprocess.run to return error
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Command failed"
            mock_run.return_value = mock_result

            with patch(
                "code_assistant_manager.tools.base.create_error_handler"
            ) as mock_handler:
                mock_error_handler = MagicMock()
                mock_error_handler.return_value = ToolExecutionError(
                    "Tool execution failed",
                    tool_name="test_tool",
                    command="test command",
                )
                mock_handler.return_value = mock_error_handler

                # Test error handling
                result = tool._run_tool_with_env(["test", "command"], {}, "test_tool")

                # Verify error handler was called
                mock_handler.assert_called_once_with("test_tool")
                assert result == 1


class TestEndpointErrorHandling:
    """Test error handling in endpoint management."""

    def test_endpoint_url_validation_error(self):
        """Test structured error handling for invalid endpoint URLs."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get_endpoint_config.return_value = {
            "endpoint": "invalid-url",
            "api_key_env": "API_KEY",
        }

        endpoint_manager = EndpointManager(config_manager)

        # Mock the validation function to return False
        with patch("code_assistant_manager.endpoints.validate_url", return_value=False):
            success, config = endpoint_manager.get_endpoint_config("test_endpoint")

            assert success is False
            assert config == {}

    def test_api_key_validation_error(self):
        """Test structured error handling for invalid API keys."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get_endpoint_config.return_value = {
            "endpoint": "https://api.test.com",
            "api_key_env": "API_KEY",
        }

        endpoint_manager = EndpointManager(config_manager)

        # Mock the validation function to return False
        with patch("code_assistant_manager.endpoints.validate_url", return_value=True):
            with patch(
                "code_assistant_manager.endpoints.validate_api_key", return_value=False
            ):
                with patch.object(
                    endpoint_manager, "_resolve_api_key", return_value="invalid-key"
                ):
                    success, config = endpoint_manager.get_endpoint_config(
                        "test_endpoint"
                    )

                    assert success is False
                    assert config == {}

    def test_model_fetch_timeout_error(self):
        """Test structured error handling for model fetch timeouts."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get_common_config.return_value = {"cache_ttl_seconds": 3600}

        endpoint_manager = EndpointManager(config_manager)

        # Mock subprocess.run to raise TimeoutExpired
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("test", 60)

            success, models = endpoint_manager.fetch_models(
                "test_endpoint",
                {"list_models_cmd": "test command"},
                use_cache_if_available=False,
            )

            assert success is False
            assert models == []

    def test_model_fetch_generic_error(self):
        """Test structured error handling for generic model fetch errors."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get_common_config.return_value = {"cache_ttl_seconds": 3600}

        endpoint_manager = EndpointManager(config_manager)

        # Mock subprocess.run to raise generic exception
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Generic error")

            with patch(
                "code_assistant_manager.endpoints.create_error_handler"
            ) as mock_handler:
                mock_error_handler = MagicMock()
                mock_error_handler.return_value = NetworkError(
                    "Network error", endpoint="test_endpoint"
                )
                mock_handler.return_value = mock_error_handler

                success, models = endpoint_manager.fetch_models(
                    "test_endpoint",
                    {"list_models_cmd": "test command"},
                    use_cache_if_available=False,
                )

                # Verify error handler was called
                mock_handler.assert_called_once_with("model_fetch")
                assert success is False
                assert models == []


class TestCLIErrorHandling:
    """Test error handling in CLI."""

    def test_cli_tool_execution_error(self):
        """Test CLI error handling for tool execution."""
        from code_assistant_manager.cli import main

        # Test the error handling logic directly
        error_handler = create_error_handler("cli")
        structured_error = error_handler(
            RuntimeError("Test error"), "Tool execution failed"
        )

        # Verify the error was properly structured
        assert isinstance(structured_error, CodeAssistantManagerError)
        assert structured_error.context.tool_name == "cli"


class TestErrorHandlerIntegration:
    """Test error handler integration across components."""

    def test_error_handler_consistency(self):
        """Test that error handlers are consistent across components."""
        # Test that all components can create error handlers
        tool_handler = create_error_handler("test_tool")
        cli_handler = create_error_handler("cli")
        endpoint_handler = create_error_handler("endpoint_manager")

        # All should be callable
        assert callable(tool_handler)
        assert callable(cli_handler)
        assert callable(endpoint_handler)

        # All should handle the same error types consistently
        test_error = FileNotFoundError("File not found")

        tool_result = tool_handler(test_error, "Tool error")
        cli_result = cli_handler(test_error, "CLI error")
        endpoint_result = endpoint_handler(test_error, "Endpoint error")

        # All should return ConfigurationError for FileNotFoundError
        assert isinstance(tool_result, ConfigurationError)
        assert isinstance(cli_result, ConfigurationError)
        assert isinstance(endpoint_result, ConfigurationError)

        # All should have appropriate context
        assert tool_result.context.tool_name == "test_tool"
        assert cli_result.context.tool_name == "cli"
        assert endpoint_result.context.tool_name == "endpoint_manager"

    def test_error_suggestions_consistency(self):
        """Test that error suggestions are consistent and helpful."""
        handler = create_error_handler("test_tool")

        # Test FileNotFoundError suggestions
        file_error = FileNotFoundError("Config file not found")
        result = handler(file_error, "Configuration error")

        assert len(result.suggestions) > 0
        assert any(
            "configuration file" in suggestion.lower()
            for suggestion in result.suggestions
        )
        assert any(
            "permissions" in suggestion.lower() for suggestion in result.suggestions
        )

        # Test PermissionError suggestions
        perm_error = PermissionError("Access denied")
        result = handler(perm_error, "Permission error")

        assert len(result.suggestions) > 0
        assert any(
            "permissions" in suggestion.lower() for suggestion in result.suggestions
        )
        assert any(
            "privileges" in suggestion.lower() for suggestion in result.suggestions
        )

        # Test ConnectionError suggestions
        conn_error = ConnectionError("Connection failed")
        result = handler(conn_error, "Network error")

        assert len(result.suggestions) > 0
        assert any(
            "connectivity" in suggestion.lower() for suggestion in result.suggestions
        )
        assert any(
            "endpoint" in suggestion.lower() for suggestion in result.suggestions
        )


class TestErrorLogging:
    """Test error logging integration."""

    def test_error_logging_in_tools(self):
        """Test that errors are properly logged in tools."""

        class TestTool(CLITool):
            command_name = "test_tool"

            def run(self, args=None):
                return 0

        # Mock config manager
        mock_config = MagicMock(spec=ConfigManager)
        tool = TestTool(mock_config)

        with patch("code_assistant_manager.tools.base.logger") as mock_logger:
            with patch(
                "code_assistant_manager.tools.base.create_error_handler"
            ) as mock_handler:
                mock_error_handler = MagicMock()
                mock_error_handler.return_value = ToolExecutionError(
                    "Tool execution failed", tool_name="test_tool"
                )
                mock_handler.return_value = mock_error_handler

                tool._handle_error("Test error", RuntimeError("Test exception"))

                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Tool error" in mock_logger.error.call_args[0][0]

    def test_error_logging_in_endpoints(self):
        """Test that errors are properly handled in endpoints."""
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get_common_config.return_value = {"cache_ttl_seconds": 3600}
        endpoint_manager = EndpointManager(config_manager)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Test error")

            with patch(
                "code_assistant_manager.endpoints.create_error_handler"
            ) as mock_handler:
                mock_error_handler = MagicMock()
                mock_error_handler.return_value = NetworkError(
                    "Network error", endpoint="test_endpoint"
                )
                mock_handler.return_value = mock_error_handler

                success, models = endpoint_manager.fetch_models(
                    "test_endpoint",
                    {"list_models_cmd": "test command"},
                    use_cache_if_available=False,
                )

                # Verify error was handled properly
                assert success is False
                assert models == []
                mock_handler.assert_called_once_with("model_fetch")


@pytest.mark.parametrize(
    "error_type,expected_class",
    [
        (FileNotFoundError, ConfigurationError),
        (PermissionError, ConfigurationError),
        (ConnectionError, NetworkError),
        (TimeoutError, TimeoutError),
        (ValueError, ValidationError),
        (RuntimeError, CodeAssistantManagerError),
    ],
)
def test_error_type_mapping(error_type, expected_class):
    """Test that error types are correctly mapped to exception classes."""
    handler = create_error_handler("test_tool")
    error = error_type("Test error")

    result = handler(error, "Test message")

    assert isinstance(result, expected_class)
    # For TimeoutError, it's returned as-is, so check the original message
    if isinstance(error, TimeoutError):
        assert "Test error" in result.message
        # TimeoutError returned as-is doesn't have tool_name context
    else:
        assert "Test message" in result.message
        assert result.context.tool_name == "test_tool"
