"""Code Assistant Manager - CLI utilities for working with AI coding assistants.

This package provides a unified interface for interacting with various AI coding
assistants including GitHub Copilot, Claude, Codex, Qwen, and more.

The codebase implements industry-standard design patterns including:
- Value Objects for validated primitives
- Factory Pattern for tool creation
- Strategy Pattern for pluggable algorithms
- Chain of Responsibility for validation
- Repository Pattern for data access
- Service Layer for business logic

See DESIGN_PATTERNS_README.md for detailed documentation.
"""

try:
    import setuptools_scm
    __version__ = setuptools_scm.get_version()
except (ImportError, LookupError):
    __version__ = "1.1.0"  # Fallback to hardcoded version
__author__ = "Code Assistant Manager Contributors"

from .config import ConfigManager
from .domain_models import (
    EndpointConfig,
    ExecutionContext,
    ExecutionResult,
    ProxySettings,
    ToolMetadata,
)
from .endpoints import EndpointManager
from .exceptions import (
    CacheError,
    CodeAssistantManagerError,
    ConfigurationError,
    EndpointError,
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
from .factory import ServiceContainer, ToolFactory, get_container, register_tool
from .menu.base import Colors, FilterableMenu, Menu, SimpleMenu

# Legacy imports (for backward compatibility)
from .menu.menus import display_centered_menu, select_model
from .services import (
    ConfigurationService,
    ExecutionContextBuilder,
    ModelService,
    ToolInstallationService,
)
from .validators import ConfigValidator, ValidationPipeline

# New design pattern imports
from .value_objects import APIKey, ClientName, EndpointName, EndpointURL, ModelID

__all__ = [
    # Legacy exports
    "display_centered_menu",
    "select_model",
    "Menu",
    "SimpleMenu",
    "FilterableMenu",
    "Colors",
    "ConfigManager",
    "EndpointManager",
    # Value Objects
    "EndpointURL",
    "APIKey",
    "ModelID",
    "EndpointName",
    "ClientName",
    # Domain Models
    "ProxySettings",
    "EndpointConfig",
    "ExecutionContext",
    "ExecutionResult",
    "ToolMetadata",
    # Factory
    "ToolFactory",
    "ServiceContainer",
    "register_tool",
    "get_container",
    # Services
    "ConfigurationService",
    "ModelService",
    "ToolInstallationService",
    "ExecutionContextBuilder",
    # Validators
    "ValidationPipeline",
    "ConfigValidator",
    # Exceptions
    "CodeAssistantManagerError",
    "ConfigurationError",
    "ToolExecutionError",
    "ToolInstallationError",
    "EndpointError",
    "ModelFetchError",
    "ValidationError",
    "SecurityError",
    "NetworkError",
    "TimeoutError",
    "CacheError",
    "MCPError",
    "create_error_handler",
]
