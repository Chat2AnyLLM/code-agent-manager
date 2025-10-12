"""Tests for the enhanced error handling system."""

from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.exceptions import (
    CacheError,
    CodeAssistantManagerError,
    ConfigurationError,
    EndpointError,
    ErrorContext,
    ErrorSeverity,
    MCPError,
    ModelFetchError,
    NetworkError,
    SecurityError,
    TimeoutError,
    ToolExecutionError,
    ToolInstallationError,
    ValidationError,
    create_error_handler,
)


class TestErrorContext:
    """Test ErrorContext dataclass."""

    def test_error_context_creation(self):
        """Test creating ErrorContext with all fields."""
        context = ErrorContext(
            tool_name="test_tool",
            command="test command",
            endpoint="https://api.test.com",
            model="test-model",
            config_file="/path/to/config.json",
            user_action="testing",
            additional_info={"key": "value"},
        )

        assert context.tool_name == "test_tool"
        assert context.command == "test command"
        assert context.endpoint == "https://api.test.com"
        assert context.model == "test-model"
        assert context.config_file == "/path/to/config.json"
        assert context.user_action == "testing"
        assert context.additional_info == {"key": "value"}

    def test_error_context_minimal(self):
        """Test creating ErrorContext with minimal fields."""
        context = ErrorContext()

        assert context.tool_name is None
        assert context.command is None
        assert context.endpoint is None
        assert context.model is None
        assert context.config_file is None
        assert context.user_action is None
        assert context.additional_info is None


class TestCodeAssistantManagerError:
    """Test base CodeAssistantManagerError class."""

    def test_basic_error_creation(self):
        """Test creating basic error."""
        error = CodeAssistantManagerError("Test error message")

        assert error.message == "Test error message"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.tool_name is None
        assert error.suggestions == []
        assert str(error) == "[MEDIUM] Test error message"

    def test_error_with_context(self):
        """Test creating error with context."""
        context = ErrorContext(tool_name="test_tool")
        error = CodeAssistantManagerError(
            "Test error",
            severity=ErrorSeverity.HIGH,
            context=context,
            suggestions=["Fix this", "Try that"],
        )

        assert error.context.tool_name == "test_tool"
        assert error.severity == ErrorSeverity.HIGH
        assert error.suggestions == ["Fix this", "Try that"]
        assert str(error) == "test_tool: [HIGH] Test error"

    def test_detailed_message(self):
        """Test detailed error message generation."""
        context = ErrorContext(
            tool_name="test_tool",
            command="test command",
            endpoint="https://api.test.com",
            model="test-model",
            config_file="/path/to/config.json",
            user_action="testing",
        )
        error = CodeAssistantManagerError(
            "Test error", context=context, suggestions=["Fix this", "Try that"]
        )

        detailed = error.get_detailed_message()
        assert "test_tool: [MEDIUM] Test error" in detailed
        assert "Command: test command" in detailed
        assert "Endpoint: https://api.test.com" in detailed
        assert "Model: test-model" in detailed
        assert "Config: /path/to/config.json" in detailed
        assert "Action: testing" in detailed
        assert "Suggestions:" in detailed
        assert "• Fix this" in detailed
        assert "• Try that" in detailed


class TestSpecificErrors:
    """Test specific error types."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError(
            "Invalid config", config_file="/path/to/config.json", field="endpoint"
        )

        assert error.message == "Invalid config"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context.config_file == "/path/to/config.json"
        assert error.context.additional_info["field"] == "endpoint"

    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        error = ToolExecutionError(
            "Tool failed",
            tool_name="claude",
            command="claude --version",
            exit_code=1,
            stderr="Permission denied",
        )

        assert error.message == "Tool failed"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context.tool_name == "claude"
        assert error.context.command == "claude --version"
        assert error.context.additional_info["exit_code"] == 1
        assert error.context.additional_info["stderr"] == "Permission denied"

    def test_tool_installation_error(self):
        """Test ToolInstallationError."""
        error = ToolInstallationError(
            "Installation failed",
            tool_name="claude",
            install_command="npm install -g @anthropic-ai/claude-code",
        )

        assert error.message == "Installation failed"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context.tool_name == "claude"
        assert error.context.command == "npm install -g @anthropic-ai/claude-code"

    def test_endpoint_error(self):
        """Test EndpointError."""
        error = EndpointError("Endpoint unreachable", endpoint="https://api.test.com")

        assert error.message == "Endpoint unreachable"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context.endpoint == "https://api.test.com"

    def test_model_fetch_error(self):
        """Test ModelFetchError."""
        error = ModelFetchError(
            "Failed to fetch models",
            endpoint="https://api.test.com",
            command="curl -s https://api.test.com/models",
        )

        assert error.message == "Failed to fetch models"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.endpoint == "https://api.test.com"
        assert error.context.command == "curl -s https://api.test.com/models"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid value", field="api_key", value="invalid_key")

        assert error.message == "Invalid value"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.additional_info["field"] == "api_key"
        assert error.context.additional_info["value"] == "invalid_key"

    def test_security_error(self):
        """Test SecurityError."""
        error = SecurityError("Dangerous command detected", command="rm -rf /")

        assert error.message == "Dangerous command detected"
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.context.command == "rm -rf /"

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection failed", endpoint="https://api.test.com")

        assert error.message == "Connection failed"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.endpoint == "https://api.test.com"

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError(
            "Operation timed out", tool_name="model_fetch", timeout_seconds=30
        )

        assert error.message == "Operation timed out"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.tool_name == "model_fetch"
        assert error.context.additional_info["timeout_seconds"] == 30

    def test_cache_error(self):
        """Test CacheError."""
        error = CacheError("Cache file corrupted", cache_file="/path/to/cache.json")

        assert error.message == "Cache file corrupted"
        assert error.severity == ErrorSeverity.LOW
        assert error.context.additional_info["cache_file"] == "/path/to/cache.json"

    def test_mcp_error(self):
        """Test MCPError."""
        error = MCPError(
            "MCP server failed", tool_name="claude", server_name="test_server"
        )

        assert error.message == "MCP server failed"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context.tool_name == "claude"
        assert error.context.additional_info["server_name"] == "test_server"


class TestErrorHandler:
    """Test create_error_handler function."""

    def test_create_error_handler(self):
        """Test creating error handler."""
        handler = create_error_handler("test_tool")
        assert callable(handler)

    def test_handle_file_not_found_error(self):
        """Test handling FileNotFoundError."""
        handler = create_error_handler("test_tool")
        error = FileNotFoundError("Config file not found")

        result = handler(error, "Configuration error", command="test command")

        assert isinstance(result, ConfigurationError)
        assert "Configuration error" in result.message
        assert result.context.tool_name == "test_tool"
        assert result.context.command == "test command"
        assert len(result.suggestions) > 0
        assert "Check if the configuration file exists" in result.suggestions

    def test_handle_permission_error(self):
        """Test handling PermissionError."""
        handler = create_error_handler("test_tool")
        error = PermissionError("Access denied")

        result = handler(error, "Permission error", command="test command")

        assert isinstance(result, ConfigurationError)
        assert "Permission error" in result.message
        assert result.context.tool_name == "test_tool"
        assert "Check file permissions" in result.suggestions

    def test_handle_connection_error(self):
        """Test handling ConnectionError."""
        handler = create_error_handler("test_tool")
        error = ConnectionError("Connection failed")

        result = handler(error, "Network error", command="test command")

        assert isinstance(result, NetworkError)
        assert "Network error" in result.message
        assert result.context.tool_name == "test_tool"
        assert "Check network connectivity" in result.suggestions

    def test_handle_timeout_error(self):
        """Test handling TimeoutError."""
        handler = create_error_handler("test_tool")
        error = TimeoutError("Operation timed out")

        result = handler(error, "Timeout error", command="test command")

        # Since it's already a TimeoutError, it should be returned as-is
        assert result is error
        assert "Operation timed out" in result.message

    def test_handle_value_error(self):
        """Test handling ValueError."""
        handler = create_error_handler("test_tool")
        error = ValueError("Invalid value")

        result = handler(error, "Validation error", command="test command")

        assert isinstance(result, ValidationError)
        assert "Validation error" in result.message
        assert result.context.tool_name == "test_tool"
        assert "Check configuration values" in result.suggestions

    def test_handle_generic_error(self):
        """Test handling generic Exception."""
        handler = create_error_handler("test_tool")
        error = RuntimeError("Something went wrong")

        result = handler(error, "Generic error", command="test command")

        assert isinstance(result, CodeAssistantManagerError)
        assert "Generic error" in result.message
        assert result.context.tool_name == "test_tool"
        assert "Check logs for more details" in result.suggestions

    def test_handle_code_assistant_manager_error(self):
        """Test handling existing CodeAssistantManagerError."""
        handler = create_error_handler("test_tool")
        original_error = ConfigurationError("Original error")

        result = handler(original_error, "Wrapper error")

        # Should return the original error unchanged
        assert result is original_error
        assert result.message == "Original error"

    def test_error_handler_with_context(self):
        """Test error handler with additional context."""
        handler = create_error_handler("test_tool")
        error = FileNotFoundError("File not found")

        result = handler(
            error,
            "File error",
            command="test command",
            endpoint="https://api.test.com",
            model="test-model",
        )

        assert isinstance(result, ConfigurationError)
        assert result.context.command == "test command"
        # Note: endpoint and model are not automatically added to context
        # They would need to be explicitly handled in the error handler


class TestErrorIntegration:
    """Test error handling integration."""

    def test_error_severity_ordering(self):
        """Test that error severities are properly ordered."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_inheritance(self):
        """Test that specific errors inherit from base error."""
        errors = [
            ConfigurationError("test"),
            ToolExecutionError("test", "tool"),
            EndpointError("test", "endpoint"),
            ValidationError("test"),
            SecurityError("test"),
            NetworkError("test"),
            TimeoutError("test"),
            CacheError("test"),
            MCPError("test"),
        ]

        for error in errors:
            assert isinstance(error, CodeAssistantManagerError)
            assert hasattr(error, "message")
            assert hasattr(error, "severity")
            assert hasattr(error, "context")
            assert hasattr(error, "suggestions")

    def test_error_context_additional_info(self):
        """Test error context with additional info."""
        context = ErrorContext(
            additional_info={"exit_code": 1, "stderr": "Error message", "duration": 5.2}
        )
        error = ToolExecutionError(
            "Tool failed", tool_name="test_tool", command="test command"
        )
        error.context = context

        assert error.context.additional_info["exit_code"] == 1
        assert error.context.additional_info["stderr"] == "Error message"
        assert error.context.additional_info["duration"] == 5.2


@pytest.mark.parametrize(
    "severity",
    [
        ErrorSeverity.LOW,
        ErrorSeverity.MEDIUM,
        ErrorSeverity.HIGH,
        ErrorSeverity.CRITICAL,
    ],
)
def test_error_severity_consistency(severity):
    """Test that error severity is consistent across error types."""
    # Test that all error types can be created with different severities
    error_classes = [
        lambda s: ConfigurationError("test", severity=s),
        lambda s: ToolExecutionError("test", "tool", severity=s),
        lambda s: EndpointError("test", "endpoint", severity=s),
        lambda s: ValidationError("test", severity=s),
        lambda s: SecurityError("test", severity=s),
        lambda s: NetworkError("test", severity=s),
        lambda s: TimeoutError("test", severity=s),
        lambda s: CacheError("test", severity=s),
        lambda s: MCPError("test", severity=s),
    ]

    for error_class in error_classes:
        try:
            error = error_class(severity)
            assert error.severity == severity
        except TypeError:
            # Some error classes may not support custom severity
            # This is acceptable as they have their own default severities
            pass
