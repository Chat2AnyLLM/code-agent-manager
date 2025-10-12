"""Factory pattern implementation for Code Assistant Manager.

Provides centralized tool creation and registration.
"""

from typing import Any, Callable, Dict, List, Optional, Type


class ToolFactory:
    """Factory for creating CLI tools with registration system."""

    _registry: Dict[str, Type[Any]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, tool_class: Type, metadata: Optional[dict] = None):
        """
        Register a tool class with the factory.

        Args:
            name: Tool identifier
            tool_class: Class to instantiate
            metadata: Optional metadata about the tool
        """
        cls._registry[name] = tool_class
        if metadata:
            cls._metadata[name] = metadata

    @classmethod
    def create(cls, name: str, *args, **kwargs):
        """
        Create a tool instance by name.

        Args:
            name: Tool identifier
            *args: Positional arguments for tool constructor
            **kwargs: Keyword arguments for tool constructor

        Returns:
            Tool instance

        Raises:
            ValueError: If tool name not registered
        """
        if name not in cls._registry:
            raise ValueError(
                f"Unknown tool: {name}. Available tools: {cls.get_available_tools()}"
            )

        tool_class = cls._registry[name]
        return tool_class(*args, **kwargs)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a tool is registered."""
        return name in cls._registry

    @classmethod
    def get_available_tools(cls) -> List[str]:
        """Get list of available tool names."""
        return sorted(cls._registry.keys())

    @classmethod
    def get_metadata(cls, name: str) -> Optional[dict]:
        """Get metadata for a tool."""
        return cls._metadata.get(name)

    @classmethod
    def clear_registry(cls):
        """Clear all registered tools (useful for testing)."""
        cls._registry.clear()
        cls._metadata.clear()

    @classmethod
    def get_tools_for_client(cls, client_name: str) -> List[str]:
        """
        Get tools that support a specific client.

        Args:
            client_name: Name of the client

        Returns:
            List of tool names that support the client
        """
        matching_tools = []
        for name, metadata in cls._metadata.items():
            if not metadata:
                continue
            supported = metadata.get("supported_clients", [])
            if not supported or client_name in supported:
                matching_tools.append(name)
        return matching_tools


def register_tool(name: str, metadata: Optional[dict] = None):
    """
    Decorator to register a tool class with the factory.

    Usage:
        @register_tool('claude', metadata={'description': 'Claude CLI'})
        class ClaudeTool(CLITool):
            pass

    Args:
        name: Tool identifier
        metadata: Optional metadata about the tool
    """

    def decorator(tool_class: Type):
        ToolFactory.register(name, tool_class, metadata)
        return tool_class

    return decorator


class ServiceContainer:
    """Dependency injection container for services."""

    def __init__(self):
        """Initialize empty container."""
        self._services: Dict[str, object] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, object] = {}

    def register_singleton(self, name: str, instance: object):
        """
        Register a singleton service instance.

        Args:
            name: Service identifier
            instance: Service instance to register
        """
        self._singletons[name] = instance

    def register_factory(self, name: str, factory: Callable[[], Any]):
        """
        Register a factory function for creating service instances.

        Args:
            name: Service identifier
            factory: Callable that returns a service instance
        """
        self._factories[name] = factory

    def register(self, name: str, service: object):
        """
        Register a service (transient - new instance each time).

        Args:
            name: Service identifier
            service: Service instance or factory
        """
        self._services[name] = service

    def get(self, name: str) -> object:
        """
        Get a service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]

        # Check factories
        if name in self._factories:
            return self._factories[name]()

        # Check transient services
        if name in self._services:
            service = self._services[name]
            # If it's callable, call it to get instance
            if callable(service):
                return service()
            return service

        raise KeyError(f"Service not registered: {name}")

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return (
            name in self._singletons
            or name in self._factories
            or name in self._services
        )

    def clear(self):
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


# Global service container instance
_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the global service container."""
    return _container


def reset_container():
    """Reset the global service container (useful for testing)."""
    global _container
    _container = ServiceContainer()
