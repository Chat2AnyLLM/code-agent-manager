
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.skills.qwen import QwenSkillHandler


class TestQwenSkillHandler:
    """Tests for QwenSkillHandler."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield Path(tmpdirname)

    def test_app_name(self):
        """Test app_name property."""
        handler = QwenSkillHandler()
        assert handler.app_name == "qwen"

    def test_default_skills_dir(self):
        """Test default skills directory."""
        handler = QwenSkillHandler()
        assert handler._default_skills_dir == Path.home() / ".qwen" / "skills"

    def test_get_installed_dirs(self, temp_skills_dir):
        """Test getting installed skill directories."""
        handler = QwenSkillHandler(skills_dir_override=temp_skills_dir)
        
        # Create some dummy skill directories with Qwen-specific files
        skill1_dir = temp_skills_dir / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text("# Skill 1\nSkill content for testing")  # Required for recognition

        skill2_dir = temp_skills_dir / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text("# Skill 2\nSkill content for testing")  # Required for recognition

        (temp_skills_dir / "not_a_skill.txt").touch()

        # We need to make sure the base directory exists check passes
        # The BaseSkillHandler looks for specific files to identify skill directories
        installed = handler.get_installed_dirs()
        
        assert len(installed) == 2
        assert any(d.name == "skill1" for d in installed)
        assert any(d.name == "skill2" for d in installed)

    def test_install_skill(self, temp_skills_dir):
        """Test installing a skill."""
        handler = QwenSkillHandler(skills_dir_override=temp_skills_dir)
        
        # Mock skill object
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.directory = "test-skill"
        mock_skill.skills_path = None # Or "skills" if your logic expects it
        mock_skill.source_directory = "test-skill"
        
        # Create source directory with a dummy file
        with tempfile.TemporaryDirectory() as source_dir:
            source_path = Path(source_dir)
            # The structure BaseSkillHandler expects depends on skills_path
            # If skills_path is None, it looks for source_directory relative to repo root
            
            # Let's assume the repo root contains the skill directory directly
            (source_path / "test-skill").mkdir()
            (source_path / "test-skill" / "skill.py").write_text("print('hello')")
            
            # Mock download_repo to return our temp source
            # The second return value of _download_repo is branch name
            with patch.object(handler, "_download_repo", return_value=(source_path, "main")):
                dest_path = handler.install(mock_skill)
                
                assert dest_path.exists()
                assert (dest_path / "skill.py").exists()
                assert (dest_path / "skill.py").read_text() == "print('hello')"

    def test_uninstall_skill(self, temp_skills_dir):
        """Test uninstalling a skill."""
        handler = QwenSkillHandler(skills_dir_override=temp_skills_dir)
        
        # Create a skill to uninstall
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "skill.py").touch()
        
        mock_skill = MagicMock()
        mock_skill.directory = "test-skill"
        
        handler.uninstall(mock_skill)
        assert not skill_dir.exists()
