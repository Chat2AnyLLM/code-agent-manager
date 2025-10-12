import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.skills import Skill, SkillManager, SkillRepo


class TestRecursiveSkillDiscovery:
    @pytest.fixture
    def skill_manager(self):
        with tempfile.TemporaryDirectory() as tmp_config:
            return SkillManager(config_dir=Path(tmp_config))

    @patch("code_assistant_manager.skills.manager.BaseSkillHandler._download_repo")
    def test_fetch_skills_recursive(self, mock_download, skill_manager):
        # Setup mock repo structure
        # temp_dir/
        #   skills/ (skills_path)
        #     skill1/
        #       SKILL.md
        #     category/
        #       skill2/
        #         SKILL.md

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            mock_download.return_value = (temp_dir, "main")

            skills_root = temp_dir / "skills"
            skills_root.mkdir()

            # Skill 1 (flat)
            skill1_dir = skills_root / "skill1"
            skill1_dir.mkdir()
            (skill1_dir / "SKILL.md").write_text(
                "---\nname: Skill One\n---\n", encoding="utf-8"
            )

            # Skill 2 (nested)
            skill2_dir = skills_root / "category" / "skill2"
            skill2_dir.mkdir(parents=True)
            (skill2_dir / "SKILL.md").write_text(
                "---\nname: Skill Two\n---\n", encoding="utf-8"
            )

            repo = SkillRepo(owner="owner", name="repo", skills_path="skills")

            # Get a handler for the test
            handler = skill_manager.get_handler("claude")
            skills = skill_manager._fetch_skills_from_repo(repo, handler)

            # Verify results
            assert len(skills) == 2

            # directory is now just the skill folder name for installation
            skill_map = {s.directory: s for s in skills}

            # Check Skill 1
            assert "skill1" in skill_map
            s1 = skill_map["skill1"]
            assert s1.name == "Skill One"
            assert s1.key == "owner/repo:skill1"
            assert s1.source_directory == "skill1"
            assert s1.readme_url.endswith("/skills/skill1")

            # Check Skill 2
            # directory is just the folder name, source_directory has full path
            assert "skill2" in skill_map
            s2 = skill_map["skill2"]
            assert s2.name == "Skill Two"
            assert s2.key == "owner/repo:category/skill2"
            assert s2.source_directory == "category/skill2"
            assert s2.readme_url.endswith("/skills/category/skill2")

    @patch("code_assistant_manager.skills.manager.BaseSkillHandler._download_repo")
    def test_fetch_skills_root_structure(self, mock_download, skill_manager):
        # Test when skills_path is root ("/") or None

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            mock_download.return_value = (temp_dir, "main")

            # Skill at root (now supported)
            (temp_dir / "SKILL.md").write_text(
                "---\nname: Root Skill\n---\n", encoding="utf-8"
            )

            # Nested skill
            (temp_dir / "nested" / "skill").mkdir(parents=True)
            (temp_dir / "nested" / "skill" / "SKILL.md").write_text(
                "---\nname: Nested\n---\n", encoding="utf-8"
            )

            repo = SkillRepo(owner="owner", name="repo", skills_path=None)

            # Get a handler for the test
            handler = skill_manager.get_handler("claude")
            skills = skill_manager._fetch_skills_from_repo(repo, handler)

            # Should find both root skill and nested skill
            assert len(skills) == 2
            skill_map = {s.key: s for s in skills}

            # Check root skill
            root_key = "owner/repo:."
            assert root_key in skill_map
            root_skill = skill_map[root_key]
            assert root_skill.name == "Root Skill"
            assert root_skill.directory == "repo"  # Uses repo name for root skills
            assert root_skill.source_directory == "."

            # Check nested skill
            nested_key = "owner/repo:nested/skill"
            assert nested_key in skill_map
            nested_skill = skill_map[nested_key]
            assert nested_skill.name == "Nested"
            assert nested_skill.directory == "skill"
            assert nested_skill.source_directory == "nested/skill"
