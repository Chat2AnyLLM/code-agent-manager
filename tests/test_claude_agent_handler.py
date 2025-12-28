"""Unit tests for Claude agent handler."""

import pytest
from pathlib import Path

from code_assistant_manager.agents.claude import ClaudeAgentHandler


class TestClaudeAgentHandler:
    """Test Claude agent handler functionality."""

    @pytest.fixture
    def handler(self):
        """Create Claude agent handler instance."""
        return ClaudeAgentHandler()

    def test_app_name_property(self, handler):
        """Test app name property."""
        assert handler.app_name == "claude"

    def test_default_agents_dir(self, handler):
        """Test default agents directory."""
        agents_dir = handler._default_agents_dir
        assert str(agents_dir).endswith(".claude/agents")

    def test_agents_dir_property(self, handler):
        """Test agents_dir property returns correct path."""
        agents_dir = handler.agents_dir
        assert agents_dir == handler._default_agents_dir

    def test_agents_dir_with_override(self, tmp_path):
        """Test agents_dir property with override."""
        override_dir = tmp_path / "custom_agents"
        handler = ClaudeAgentHandler(agents_dir_override=override_dir)
        assert handler.agents_dir == override_dir
