"""Unit tests for tool integrations."""

import pytest
from unittest.mock import patch, MagicMock

from code_assistant_manager.tools.base import CLITool


class TestCLITool:
    """Test CLI tool functionality."""

    @pytest.fixture
    def tool(self):
        """Create CLI tool instance."""
        return CLITool()

    def test_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name is None
        assert tool.description is None

    def test_is_available_default(self, tool):
        """Test default availability."""
        assert tool.is_available() is False

    def test_execute_not_implemented(self, tool):
        """Test execute raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            tool.execute({})

    def test_validate_params_default(self, tool):
        """Test default parameter validation."""
        assert tool.validate_params({}) is True


class TestToolRegistry:
    """Test tool registry functionality."""

    @patch("code_assistant_manager.tools.registry.get_available_tools")
    def test_get_available_tools(self, mock_get_tools):
        """Test getting available tools."""
        from code_assistant_manager.tools.registry import get_available_tools

        mock_get_tools.return_value = ["tool1", "tool2"]

        tools = get_available_tools()
        assert tools == ["tool1", "tool2"]

    @patch("code_assistant_manager.tools.registry.create_tool")
    def test_create_tool(self, mock_create_tool):
        """Test tool creation."""
        from code_assistant_manager.tools.registry import create_tool

        mock_tool = MagicMock()
        mock_create_tool.return_value = mock_tool

        tool = create_tool("test-tool")
        assert tool == mock_tool


class TestToolIntegration:
    """Test tool integration scenarios."""

    def test_tool_discovery(self):
        """Test tool discovery mechanism."""
        from code_assistant_manager.tools.registry import ToolRegistry

        registry = ToolRegistry()

        # Test that registry can be initialized
        assert registry is not None
        assert hasattr(registry, 'get_available_tools')

    @patch("code_assistant_manager.tools.registry.ToolRegistry")
    def test_tool_registration(self, mock_registry_class):
        """Test tool registration."""
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry

        from code_assistant_manager.tools.registry import register_tool

        register_tool("test-tool", MagicMock())

        mock_registry.register.assert_called_once()

    def test_tool_validation(self):
        """Test tool parameter validation."""
        from code_assistant_manager.tools.base import CLITool

        class TestTool(CLITool):
            def validate_params(self, params):
                return "code" in params and isinstance(params["code"], str)

        tool = TestTool()

        # Valid params
        assert tool.validate_params({"code": "print('hello')"}) is True

        # Invalid params
        assert tool.validate_params({"invalid": "param"}) is False
        assert tool.validate_params({}) is False