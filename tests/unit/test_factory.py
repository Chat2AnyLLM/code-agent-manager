"""Unit tests for factory pattern."""

import pytest

from code_assistant_manager.factory import ServiceContainer, ToolFactory, register_tool


class DummyTool:
    """Dummy tool for testing."""

    def __init__(self, config):
        self.config = config


class TestToolFactory:
    """Tests for ToolFactory."""

    def setup_method(self):
        """Setup before each test."""
        ToolFactory.clear_registry()

    def teardown_method(self):
        """Cleanup after each test."""
        ToolFactory.clear_registry()

    def test_register_and_create(self):
        """Test registering and creating a tool."""
        ToolFactory.register("dummy", DummyTool)

        tool = ToolFactory.create("dummy", "test_config")
        assert isinstance(tool, DummyTool)
        assert tool.config == "test_config"

    def test_create_unknown_tool_raises_error(self):
        """Test creating unknown tool raises ValueError."""
        with pytest.raises(ValueError):
            ToolFactory.create("unknown", "config")

    def test_is_registered(self):
        """Test checking if tool is registered."""
        ToolFactory.register("dummy", DummyTool)

        assert ToolFactory.is_registered("dummy")
        assert not ToolFactory.is_registered("unknown")

    def test_get_available_tools(self):
        """Test getting list of available tools."""
        ToolFactory.register("tool1", DummyTool)
        ToolFactory.register("tool2", DummyTool)

        tools = ToolFactory.get_available_tools()
        assert "tool1" in tools
        assert "tool2" in tools
        assert len(tools) == 2

    def test_register_with_metadata(self):
        """Test registering tool with metadata."""
        metadata = {"description": "Test tool", "version": "1.0"}
        ToolFactory.register("dummy", DummyTool, metadata)

        retrieved_metadata = ToolFactory.get_metadata("dummy")
        assert retrieved_metadata == metadata

    def test_decorator_registration(self):
        """Test registering tool using decorator."""

        @register_tool("decorated", metadata={"test": True})
        class DecoratedTool:
            def __init__(self, config):
                self.config = config

        assert ToolFactory.is_registered("decorated")
        tool = ToolFactory.create("decorated", "config")
        assert isinstance(tool, DecoratedTool)


class TestServiceContainer:
    """Tests for ServiceContainer."""

    def setup_method(self):
        """Setup before each test."""
        self.container = ServiceContainer()

    def test_register_and_get_singleton(self):
        """Test registering and getting singleton service."""
        service = DummyTool("test")
        self.container.register_singleton("service", service)

        retrieved = self.container.get("service")
        assert retrieved is service

    def test_register_and_get_factory(self):
        """Test registering and getting service from factory."""
        self.container.register_factory("service", lambda: DummyTool("test"))

        service1 = self.container.get("service")
        service2 = self.container.get("service")

        assert isinstance(service1, DummyTool)
        assert isinstance(service2, DummyTool)
        assert service1 is not service2  # Different instances

    def test_register_callable(self):
        """Test registering callable service."""
        self.container.register("service", lambda: DummyTool("test"))

        service = self.container.get("service")
        assert isinstance(service, DummyTool)

    def test_get_unknown_service_raises_error(self):
        """Test getting unknown service raises KeyError."""
        with pytest.raises(KeyError):
            self.container.get("unknown")

    def test_has_service(self):
        """Test checking if service exists."""
        self.container.register_singleton("service", DummyTool("test"))

        assert self.container.has("service")
        assert not self.container.has("unknown")

    def test_clear(self):
        """Test clearing all services."""
        self.container.register_singleton("service1", DummyTool("test1"))
        self.container.register_singleton("service2", DummyTool("test2"))

        self.container.clear()

        assert not self.container.has("service1")
        assert not self.container.has("service2")
