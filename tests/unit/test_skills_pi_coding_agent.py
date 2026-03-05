"""Tests for Pi Coding Agent skill handler."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from code_assistant_manager.skills.pi_coding_agent import PiCodingAgentSkillHandler


class TestPiCodingAgentSkillHandler:
    """Tests for PiCodingAgentSkillHandler."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield Path(tmpdirname)

    def test_app_name(self):
        """Test app_name property."""
        handler = PiCodingAgentSkillHandler()
        assert handler.app_name == "pi-coding-agent"

    def test_default_skills_dir(self):
        """Test default skills directory."""
        handler = PiCodingAgentSkillHandler()
        assert handler._default_skills_dir == Path.home() / ".pi" / "agent" / "skills"

    def test_skills_dir_with_override(self, temp_skills_dir):
        """Test that skills_dir uses override when provided."""
        handler = PiCodingAgentSkillHandler(skills_dir_override=temp_skills_dir)
        assert handler.skills_dir == temp_skills_dir

    def test_skills_dir_without_override(self):
        """Test that skills_dir returns default when no override."""
        handler = PiCodingAgentSkillHandler()
        assert handler.skills_dir == handler._default_skills_dir

    def test_get_installed_dirs(self, temp_skills_dir):
        """Test getting installed skill directories."""
        handler = PiCodingAgentSkillHandler(skills_dir_override=temp_skills_dir)

        # Create some dummy skill directories with SKILL.md files
        skill1_dir = temp_skills_dir / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text("# Skill 1\nSkill content for testing")

        skill2_dir = temp_skills_dir / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text("# Skill 2\nSkill content for testing")

        (temp_skills_dir / "not_a_skill.txt").touch()

        installed = handler.get_installed_dirs()

        assert len(installed) == 2
        assert any(d.name == "skill1" for d in installed)
        assert any(d.name == "skill2" for d in installed)

    def test_install_skill(self, temp_skills_dir):
        """Test installing a skill."""
        handler = PiCodingAgentSkillHandler(skills_dir_override=temp_skills_dir)

        # Mock skill object
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.directory = "test-skill"
        mock_skill.skills_path = None
        mock_skill.source_directory = "test-skill"

        # Create source directory with a dummy file
        with tempfile.TemporaryDirectory() as source_dir:
            source_path = Path(source_dir)
            (source_path / "test-skill").mkdir()
            (source_path / "test-skill" / "SKILL.md").write_text("# Test Skill\nContent")

            # Mock download_repo to return our temp source
            from unittest.mock import patch
            with patch.object(handler, "_download_repo", return_value=(source_path, "main")):
                dest_path = handler.install(mock_skill)

                assert dest_path.exists()
                assert (dest_path / "SKILL.md").exists()

    def test_uninstall_skill(self, temp_skills_dir):
        """Test uninstalling a skill."""
        handler = PiCodingAgentSkillHandler(skills_dir_override=temp_skills_dir)

        # Create a skill to uninstall
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").touch()

        mock_skill = MagicMock()
        mock_skill.directory = "test-skill"

        handler.uninstall(mock_skill)
        assert not skill_dir.exists()
