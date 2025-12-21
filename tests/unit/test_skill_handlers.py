"""Tests for skill handlers module.

This module tests the skill handler implementations which manage
skill installation/uninstallation for different app types.

Key test areas:
- ClaudeSkillHandler: Claude Code skill management
- BaseSkillHandler abstract base class
- Directory management and skills_dir property
- Handler instantiation with overrides
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from code_assistant_manager.skills.base import BaseSkillHandler
from code_assistant_manager.skills.claude import ClaudeSkillHandler
from code_assistant_manager.skills.codex import CodexSkillHandler
from code_assistant_manager.skills.copilot import CopilotSkillHandler
from code_assistant_manager.skills.droid import DroidSkillHandler
from code_assistant_manager.skills.gemini import GeminiSkillHandler
from code_assistant_manager.skills.models import Skill


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create a temporary skills directory."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return skills_dir


@pytest.fixture
def mock_skill():
    """Create a mock skill for testing."""
    return Skill(
        key="test-skill",
        name="Test Skill",
        description="A test skill",
        directory="test-skill",
        installed=False,
        repo_owner="test-owner",
        repo_name="test-repo",
        repo_branch="main",
    )


class TestBaseSkillHandler:
    """Tests for BaseSkillHandler abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseSkillHandler cannot be instantiated directly."""
        # BaseSkillHandler is abstract and should not be instantiated
        with pytest.raises(TypeError):
            BaseSkillHandler()

    def test_abstract_methods_defined(self):
        """Test that abstract methods are defined."""
        # Check that app_name and _default_skills_dir are abstract
        assert hasattr(BaseSkillHandler, "app_name")
        assert hasattr(BaseSkillHandler, "_default_skills_dir")


class TestClaudeSkillHandler:
    """Tests for ClaudeSkillHandler."""

    def test_app_name(self):
        """Test that app_name returns 'claude'."""
        handler = ClaudeSkillHandler()
        assert handler.app_name == "claude"

    def test_default_skills_dir(self):
        """Test that _default_skills_dir returns the correct path."""
        handler = ClaudeSkillHandler()
        expected_path = Path.home() / ".claude" / "skills"
        assert handler._default_skills_dir == expected_path

    def test_skills_dir_with_override(self, temp_skills_dir):
        """Test that skills_dir uses override when provided."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)
        assert handler.skills_dir == temp_skills_dir

    def test_skills_dir_without_override(self):
        """Test that skills_dir returns default when no override."""
        handler = ClaudeSkillHandler()
        assert handler.skills_dir == handler._default_skills_dir

    def test_handler_initialization(self, temp_skills_dir):
        """Test handler initialization with override."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)
        assert handler._skills_dir_override == temp_skills_dir


class TestCodexSkillHandler:
    """Tests for CodexSkillHandler."""

    def test_app_name(self):
        """Test that app_name returns 'codex'."""
        handler = CodexSkillHandler()
        assert handler.app_name == "codex"

    def test_default_skills_dir(self):
        """Test that _default_skills_dir returns the correct path."""
        handler = CodexSkillHandler()
        expected_path = Path.home() / ".codex" / "skills"
        assert handler._default_skills_dir == expected_path


class TestCopilotSkillHandler:
    """Tests for CopilotSkillHandler."""

    def test_app_name(self):
        """Test that app_name returns 'copilot'."""
        handler = CopilotSkillHandler()
        assert handler.app_name == "copilot"

    def test_default_skills_dir(self):
        """Test that _default_skills_dir returns the correct path."""
        handler = CopilotSkillHandler()
        expected_path = Path.home() / ".copilot" / "skills"
        assert handler._default_skills_dir == expected_path


class TestGeminiSkillHandler:
    """Tests for GeminiSkillHandler."""

    def test_app_name(self):
        """Test that app_name returns 'gemini'."""
        handler = GeminiSkillHandler()
        assert handler.app_name == "gemini"

    def test_default_skills_dir(self):
        """Test that _default_skills_dir returns the correct path."""
        handler = GeminiSkillHandler()
        expected_path = Path.home() / ".gemini" / "skills"
        assert handler._default_skills_dir == expected_path


class TestDroidSkillHandler:
    """Tests for DroidSkillHandler."""

    def test_app_name(self):
        """Test that app_name returns 'droid'."""
        handler = DroidSkillHandler()
        assert handler.app_name == "droid"

    def test_default_skills_dir(self):
        """Test that _default_skills_dir returns the correct path."""
        handler = DroidSkillHandler()
        expected_path = Path.home() / ".factory" / "skills"
        assert handler._default_skills_dir == expected_path


class TestSkillInstallation:
    """Tests for skill installation functionality."""

    def test_install_requires_repo_info(self, temp_skills_dir):
        """Test that install raises error without repo info."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)

        skill_no_repo = Skill(
            key="no-repo-skill",
            name="No Repo Skill",
            description="No repo",
            directory="no-repo",
        )

        with pytest.raises(ValueError, match="no repository information"):
            handler.install(skill_no_repo)

    def test_install_creates_skills_dir(self, tmp_path, mock_skill):
        """Test that install creates the skills directory if needed."""
        non_existent_dir = tmp_path / "new_skills"
        handler = ClaudeSkillHandler(skills_dir_override=non_existent_dir)

        assert not non_existent_dir.exists()

        # Mock the download to avoid network call
        with patch.object(handler, "_download_repo") as mock_download:
            mock_download.return_value = (tmp_path / "temp", "main")

            # Will fail at copy step but directory should be created
            try:
                handler.install(mock_skill)
            except Exception:
                pass  # Expected to fail at copy step

        assert non_existent_dir.exists()


class TestSkillUninstallation:
    """Tests for skill uninstallation functionality."""

    def test_uninstall_existing_skill(self, temp_skills_dir, mock_skill):
        """Test uninstalling an existing skill."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)

        # Create a skill directory
        skill_dir = temp_skills_dir / mock_skill.key
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text("test content")

        assert skill_dir.exists()

        handler.uninstall(mock_skill)

        assert not skill_dir.exists()

    def test_uninstall_nonexistent_skill(self, temp_skills_dir, mock_skill):
        """Test uninstalling a skill that doesn't exist (should not raise)."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)

        # Should not raise any exception
        handler.uninstall(mock_skill)


class TestIsInstalled:
    """Tests for checking if a skill is installed."""

    def test_is_installed_true(self, temp_skills_dir, mock_skill):
        """Test is_installed returns True when skill exists."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)

        # Create the skill directory with SKILL.md file (required by is_installed check)
        skill_dir = temp_skills_dir / mock_skill.directory
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        assert handler.is_installed(mock_skill) is True

    def test_is_installed_false(self, temp_skills_dir, mock_skill):
        """Test is_installed returns False when skill doesn't exist."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_skills_dir)

        assert handler.is_installed(mock_skill) is False


class TestHandlerRegistry:
    """Tests for handler registration pattern."""

    def test_all_handlers_have_unique_app_names(self):
        """Test that all handlers have unique app names."""
        handlers = [
            ClaudeSkillHandler(),
            CodexSkillHandler(),
            GeminiSkillHandler(),
            DroidSkillHandler(),
        ]

        app_names = [h.app_name for h in handlers]

        # All names should be unique
        assert len(app_names) == len(set(app_names))

    def test_all_handlers_have_different_default_dirs(self):
        """Test that all handlers have different default directories."""
        handlers = [
            ClaudeSkillHandler(),
            CodexSkillHandler(),
            GeminiSkillHandler(),
            DroidSkillHandler(),
        ]

        default_dirs = [h._default_skills_dir for h in handlers]

        # All directories should be unique
        assert len(default_dirs) == len(set(default_dirs))
