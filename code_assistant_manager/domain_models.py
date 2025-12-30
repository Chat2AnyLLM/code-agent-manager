"""Domain models for Code Assistant Manager.

Rich domain objects that encapsulate business logic.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .value_objects import APIKey, ClientName, EndpointName, EndpointURL, ModelID


@dataclass(frozen=True)
class ProxySettings:
    """Proxy configuration settings."""

    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for environment variables."""
        result = {}
        if self.http_proxy:
            result["http_proxy"] = self.http_proxy
        if self.https_proxy:
            result["https_proxy"] = self.https_proxy
        if self.no_proxy:
            result["no_proxy"] = self.no_proxy
        return result

    def is_enabled(self) -> bool:
        """Check if proxy is configured."""
        return bool(self.http_proxy or self.https_proxy)


@dataclass(frozen=True)
class EndpointConfig:
    """Immutable endpoint configuration with validation."""

    name: EndpointName
    url: EndpointURL
    description: str
    supported_clients: List[ClientName] = field(default_factory=list)
    api_key: Optional[APIKey] = None
    proxy_settings: Optional[ProxySettings] = None
    use_proxy: bool = False
    keep_proxy_config: bool = False
    list_models_cmd: Optional[str] = None
    list_of_models: Optional[List[str]] = None
    cache_ttl_seconds: int = 86400

    def supports_client(self, client_name: str) -> bool:
        """Check if this endpoint supports a given client."""
        if not self.supported_clients:
            return True  # No restriction means all clients supported

        try:
            client = ClientName(client_name)
            return client in self.supported_clients
        except ValueError:
            return False

    def get_api_key_value(self) -> Optional[str]:
        """Get the actual API key value if available."""
        return self.api_key.get_value() if self.api_key else None

    def has_list_command(self) -> bool:
        """Check if endpoint has a model list command configured."""
        return bool(self.list_models_cmd and self.list_models_cmd.strip())
    
    def has_static_models(self) -> bool:
        """Check if endpoint has a static list of models configured."""
        return bool(self.list_of_models and len(self.list_of_models) > 0)

    def should_use_proxy(self) -> bool:
        """Determine if proxy should be used."""
        return self.use_proxy and self.proxy_settings is not None


@dataclass
class ExecutionContext:
    """Context for tool execution."""

    tool_name: str
    args: List[str]
    endpoint_config: EndpointConfig
    models: Optional[List[ModelID]] = None
    selected_model: Optional[ModelID] = None
    selected_models: Optional[Tuple[ModelID, ...]] = (
        None  # For tools requiring multiple models
    )
    environment: Dict[str, str] = field(default_factory=dict)

    def has_single_model(self) -> bool:
        """Check if single model is selected."""
        return self.selected_model is not None

    def has_multiple_models(self) -> bool:
        """Check if multiple models are selected."""
        return self.selected_models is not None

    def get_primary_model(self) -> Optional[ModelID]:
        """Get the primary model (single or first of multiple)."""
        if self.selected_model:
            return self.selected_model
        if self.selected_models and len(self.selected_models) > 0:
            return self.selected_models[0]
        return None


@dataclass
class ExecutionResult:
    """Result of tool execution."""

    exit_code: int
    tool_name: str
    success: bool = field(init=False)
    error_message: Optional[str] = None

    def __post_init__(self):
        """Set success flag based on exit code."""
        object.__setattr__(self, "success", self.exit_code == 0)

    @classmethod
    def success_result(cls, tool_name: str) -> "ExecutionResult":
        """Create a successful result."""
        return cls(exit_code=0, tool_name=tool_name)

    @classmethod
    def failure_result(
        cls, tool_name: str, exit_code: int = 1, error_message: Optional[str] = None
    ) -> "ExecutionResult":
        """Create a failure result."""
        return cls(
            exit_code=exit_code, tool_name=tool_name, error_message=error_message
        )


@dataclass
class ToolMetadata:
    """Metadata about a CLI tool."""

    name: str
    command_name: str
    description: str
    requires_model_selection: bool = True
    requires_multiple_models: bool = False
    requires_installation: bool = True
    install_command: Optional[str] = None
    supported_endpoints: List[str] = field(default_factory=list)

    def can_be_installed(self) -> bool:
        """Check if tool can be automatically installed."""
        return self.install_command is not None and self.install_command.strip() != ""
