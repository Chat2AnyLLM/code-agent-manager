"""Custom exception classes for Code Assistant Manager."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors."""

    tool_name: Optional[str] = None
    command: Optional[str] = None
    endpoint: Optional[str] = None
    model: Optional[str] = None
    config_file: Optional[str] = None
    user_action: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class CodeAssistantManagerError(Exception):
    """Base exception for all Code Assistant Manager errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        suggestions: Optional[List[str]] = None,
    ):
        self.message = message
        self.severity = severity
        self.context = context or ErrorContext()
        self.suggestions = suggestions or []
        super().__init__(self.message)

    def __str__(self) -> str:
        base_msg = f"[{self.severity.value.upper()}] {self.message}"
        if self.context.tool_name:
            base_msg = f"{self.context.tool_name}: {base_msg}"
        return base_msg

    def get_detailed_message(self) -> str:
        """Get detailed error message with context and suggestions."""
        lines = [str(self)]

        if self.context.command:
            lines.append(f"Command: {self.context.command}")
        if self.context.endpoint:
            lines.append(f"Endpoint: {self.context.endpoint}")
        if self.context.model:
            lines.append(f"Model: {self.context.model}")
        if self.context.config_file:
            lines.append(f"Config: {self.context.config_file}")
        if self.context.user_action:
            lines.append(f"Action: {self.context.user_action}")

        if self.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  • {suggestion}")

        return "\n".join(lines)


class ConfigurationError(CodeAssistantManagerError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_file: Optional[str] = None,
        field: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                config_file=config_file,
                additional_info={"field": field} if field else None,
            )
        else:
            # Merge additional info if provided
            if field:
                if context.additional_info is None:
                    context.additional_info = {}
                context.additional_info["field"] = field
            if config_file:
                context.config_file = config_file

        super().__init__(message, ErrorSeverity.HIGH, context, **kwargs)


class ToolExecutionError(CodeAssistantManagerError):
    """Tool execution-related errors."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                tool_name=tool_name,
                command=command,
                additional_info=(
                    {"exit_code": exit_code, "stderr": stderr}
                    if exit_code is not None
                    else None
                ),
            )
        else:
            if tool_name:
                context.tool_name = tool_name
            if command:
                context.command = command
            if exit_code is not None or stderr:
                if context.additional_info is None:
                    context.additional_info = {}
                if exit_code is not None:
                    context.additional_info["exit_code"] = exit_code
                if stderr:
                    context.additional_info["stderr"] = stderr

        super().__init__(message, ErrorSeverity.HIGH, context, **kwargs)


class ToolInstallationError(CodeAssistantManagerError):
    """Tool installation-related errors."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        install_command: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(tool_name=tool_name, command=install_command)
        else:
            if tool_name:
                context.tool_name = tool_name
            if install_command:
                context.command = install_command

        super().__init__(message, ErrorSeverity.HIGH, context, **kwargs)


class EndpointError(CodeAssistantManagerError):
    """Endpoint-related errors."""

    def __init__(
        self,
        message: str,
        endpoint: str,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(endpoint=endpoint)
        else:
            if endpoint:
                context.endpoint = endpoint

        super().__init__(message, ErrorSeverity.HIGH, context, **kwargs)


class ModelFetchError(CodeAssistantManagerError):
    """Model fetching-related errors."""

    def __init__(
        self,
        message: str,
        endpoint: str,
        command: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(endpoint=endpoint, command=command)
        else:
            if endpoint:
                context.endpoint = endpoint
            if command:
                context.command = command

        super().__init__(message, ErrorSeverity.MEDIUM, context, **kwargs)


class ValidationError(CodeAssistantManagerError):
    """Validation-related errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                additional_info={"field": field, "value": value} if field else None
            )
        else:
            if field or value:
                if context.additional_info is None:
                    context.additional_info = {}
                if field:
                    context.additional_info["field"] = field
                if value:
                    context.additional_info["value"] = value

        super().__init__(message, ErrorSeverity.MEDIUM, context, **kwargs)


class SecurityError(CodeAssistantManagerError):
    """Security-related errors."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(command=command)
        else:
            if command:
                context.command = command

        super().__init__(message, ErrorSeverity.CRITICAL, context, **kwargs)


class NetworkError(CodeAssistantManagerError):
    """Network-related errors."""

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(endpoint=endpoint)
        else:
            if endpoint:
                context.endpoint = endpoint

        super().__init__(message, ErrorSeverity.MEDIUM, context, **kwargs)


class TimeoutError(CodeAssistantManagerError):
    """Timeout-related errors."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                tool_name=tool_name,
                additional_info=(
                    {"timeout_seconds": timeout_seconds} if timeout_seconds else None
                ),
            )
        else:
            if tool_name:
                context.tool_name = tool_name
            if timeout_seconds:
                if context.additional_info is None:
                    context.additional_info = {}
                context.additional_info["timeout_seconds"] = timeout_seconds

        super().__init__(message, ErrorSeverity.MEDIUM, context, **kwargs)


class CacheError(CodeAssistantManagerError):
    """Cache-related errors."""

    def __init__(
        self,
        message: str,
        cache_file: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                additional_info={"cache_file": cache_file} if cache_file else None
            )
        else:
            if cache_file:
                if context.additional_info is None:
                    context.additional_info = {}
                context.additional_info["cache_file"] = cache_file

        super().__init__(message, ErrorSeverity.LOW, context, **kwargs)


class MCPError(CodeAssistantManagerError):
    """MCP (Model Context Protocol) related errors."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs,
    ):
        if context is None:
            context = ErrorContext(
                tool_name=tool_name,
                additional_info={"server_name": server_name} if server_name else None,
            )
        else:
            if tool_name:
                context.tool_name = tool_name
            if server_name:
                if context.additional_info is None:
                    context.additional_info = {}
                context.additional_info["server_name"] = server_name

        super().__init__(message, ErrorSeverity.MEDIUM, context, **kwargs)


def create_error_handler(tool_name: str):
    """Create a context-aware error handler for a specific tool."""

    def handle_error(
        error: Exception, message: str, command: Optional[str] = None, **kwargs
    ) -> CodeAssistantManagerError:
        """Convert generic exceptions to structured errors."""

        if isinstance(error, CodeAssistantManagerError):
            return error

        # Map common exception types to our error classes
        if isinstance(error, FileNotFoundError):
            context = ErrorContext(tool_name=tool_name, command=command)
            return ConfigurationError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check if the configuration file exists",
                    "Verify file permissions",
                    "Run 'code-assistant-manager doctor' to diagnose issues",
                ],
            )

        elif isinstance(error, PermissionError):
            context = ErrorContext(tool_name=tool_name, command=command)
            return ConfigurationError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check file permissions",
                    "Run with appropriate user privileges",
                    "Verify write access to required directories",
                ],
            )

        elif isinstance(error, ConnectionError):
            context = ErrorContext(tool_name=tool_name, command=command)
            return NetworkError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check network connectivity",
                    "Verify endpoint URL is correct",
                    "Check proxy settings if applicable",
                ],
            )

        elif isinstance(error, TimeoutError):
            context = ErrorContext(tool_name=tool_name, command=command)
            return TimeoutError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check network connectivity",
                    "Try again with a longer timeout",
                    "Verify endpoint is responsive",
                ],
            )

        elif isinstance(error, ValueError):
            context = ErrorContext(tool_name=tool_name, command=command)
            return ValidationError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check configuration values",
                    "Verify input format",
                    "Run 'code-assistant-manager doctor' to validate config",
                ],
            )

        else:
            # Generic error handling
            context = ErrorContext(tool_name=tool_name, command=command)
            return CodeAssistantManagerError(
                f"{message}: {error}",
                context=context,
                suggestions=[
                    "Check logs for more details",
                    "Run 'code-assistant-manager doctor' to diagnose issues",
                    "Report this error if it persists",
                ],
            )

    return handle_error
