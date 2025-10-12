"""Service layer for business logic.

Separates business logic from infrastructure and UI concerns.
"""

from typing import Callable, List, Optional, Tuple

from .domain_models import EndpointConfig, ExecutionContext
from .repositories import CacheRepository, ConfigRepository
from .value_objects import ModelID


class ConfigurationService:
    """Service for configuration operations."""

    def __init__(self, config_repository: ConfigRepository):
        """
        Initialize service.

        Args:
            config_repository: Repository for configuration data
        """
        self.config_repository = config_repository

    def get_endpoint(self, name: str) -> Optional[EndpointConfig]:
        """
        Get endpoint configuration by name.

        Args:
            name: Endpoint name

        Returns:
            Endpoint configuration or None
        """
        return self.config_repository.find_by_name(name)

    def get_all_endpoints(self) -> List[EndpointConfig]:
        """Get all endpoint configurations."""
        return self.config_repository.find_all()

    def get_endpoints_for_client(self, client_name: str) -> List[EndpointConfig]:
        """
        Get endpoints that support a specific client.

        Args:
            client_name: Client name to filter by

        Returns:
            List of matching endpoint configurations
        """
        all_endpoints = self.get_all_endpoints()
        return [ep for ep in all_endpoints if ep.supports_client(client_name)]

    def reload_configuration(self):
        """Force reload of configuration from source."""
        if hasattr(self.config_repository, "reload"):
            self.config_repository.reload()


class ModelService:
    """Service for model operations."""

    def __init__(
        self,
        cache_repository: CacheRepository,
        model_fetcher: Optional[Callable[[str, EndpointConfig], List[ModelID]]] = None,
    ):
        """
        Initialize service.

        Args:
            cache_repository: Repository for model cache
            model_fetcher: Optional function to fetch models from API
        """
        self.cache_repository = cache_repository
        self.model_fetcher = model_fetcher

    def get_available_models(
        self,
        endpoint_name: str,
        endpoint_config: EndpointConfig,
        use_cache: bool = True,
    ) -> Tuple[bool, List[ModelID]]:
        """
        Get available models for an endpoint.

        Args:
            endpoint_name: Name of the endpoint
            endpoint_config: Endpoint configuration
            use_cache: Whether to use cached models

        Returns:
            Tuple of (success, list_of_models)
        """
        # Check cache first if requested
        if use_cache:
            cached_models = self.cache_repository.get_models(endpoint_name)
            if cached_models:
                return True, cached_models

        # Fetch from API if no cache or cache disabled
        if not self.model_fetcher:
            return False, []

        try:
            models = self.model_fetcher(endpoint_name, endpoint_config)

            # Save to cache
            if models:
                self.cache_repository.save_models(endpoint_name, models)

            return True, models
        except Exception as e:
            # Try to fall back to cache even if expired
            cached_models = self.cache_repository.get_models(endpoint_name)
            if cached_models:
                return True, cached_models

            return False, []

    def clear_cache(self, endpoint_name: Optional[str] = None):
        """
        Clear model cache.

        Args:
            endpoint_name: Optional endpoint name to clear (None = clear all)
        """
        self.cache_repository.clear(endpoint_name)

    def is_cache_expired(self, endpoint_name: str) -> bool:
        """
        Check if cache for endpoint is expired.

        Args:
            endpoint_name: Endpoint name

        Returns:
            True if expired or not cached
        """
        return self.cache_repository.is_expired(endpoint_name)


class ToolInstallationService:
    """Service for tool installation operations."""

    def __init__(self, command_runner: Optional[Callable[[str], int]] = None):
        """
        Initialize service.

        Args:
            command_runner: Optional function to run installation commands
        """
        self.command_runner = command_runner or self._default_command_runner
        self._installed_tools_cache: set[str] = set()

    def is_installed(self, command_name: str) -> bool:
        """
        Check if a tool is installed.

        Args:
            command_name: Command name to check

        Returns:
            True if installed
        """
        # Check cache first
        if command_name in self._installed_tools_cache:
            return True

        # Check if command exists
        import subprocess

        try:
            subprocess.run(
                ["which", command_name],
                capture_output=True,
                check=True,
            )
            self._installed_tools_cache.add(command_name)
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, install_command: str) -> Tuple[bool, Optional[str]]:
        """
        Install a tool using provided command.

        Args:
            install_command: Installation command to run

        Returns:
            Tuple of (success, error_message)
        """
        try:
            result = self.command_runner(install_command)
            if result == 0:
                return True, None
            else:
                return False, f"Installation failed with exit code {result}"
        except Exception as e:
            return False, str(e)

    def _default_command_runner(self, command: str) -> int:
        """Default command runner implementation."""
        import shlex
        import subprocess

        # Security: Use shlex.split() instead of shell=True to prevent injection
        result = subprocess.run(shlex.split(command), shell=False)
        return result.returncode

    def clear_cache(self):
        """Clear installed tools cache."""
        self._installed_tools_cache.clear()


class ExecutionContextBuilder:
    """Builder for creating execution contexts."""

    def __init__(self, tool_name: str):
        """
        Initialize builder.

        Args:
            tool_name: Name of the tool
        """
        self._tool_name = tool_name
        self._args: List[str] = []
        self._endpoint_config: Optional[EndpointConfig] = None
        self._models: Optional[List[ModelID]] = None
        self._selected_model: Optional[ModelID] = None
        self._selected_models: Optional[tuple] = None
        self._environment: dict = {}

    def with_args(self, args: List[str]) -> "ExecutionContextBuilder":
        """Set command-line arguments."""
        self._args = args
        return self

    def with_endpoint_config(self, config: EndpointConfig) -> "ExecutionContextBuilder":
        """Set endpoint configuration."""
        self._endpoint_config = config
        return self

    def with_models(self, models: List[ModelID]) -> "ExecutionContextBuilder":
        """Set available models."""
        self._models = models
        return self

    def with_selected_model(self, model: ModelID) -> "ExecutionContextBuilder":
        """Set selected model (single)."""
        self._selected_model = model
        return self

    def with_selected_models(self, models: tuple) -> "ExecutionContextBuilder":
        """Set selected models (multiple)."""
        self._selected_models = models
        return self

    def with_environment(self, env: dict) -> "ExecutionContextBuilder":
        """Set environment variables."""
        self._environment = env
        return self

    def build(self) -> ExecutionContext:
        """Build the execution context."""
        if not self._endpoint_config:
            raise ValueError("Endpoint configuration is required")

        return ExecutionContext(
            tool_name=self._tool_name,
            args=self._args,
            endpoint_config=self._endpoint_config,
            models=self._models,
            selected_model=self._selected_model,
            selected_models=self._selected_models,
            environment=self._environment,
        )
