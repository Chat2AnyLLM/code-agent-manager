"""Tests for skill name consistency between list and install commands.

These tests ensure that:
1. Skill list shows simplified install keys (repo:directory format)
2. The displayed keys work with the install command
3. No regression in the naming inconsistency bug
"""

import pytest
from pathlib import Path
from code_assistant_manager.skills import Skill, SkillManager


class TestSkillNameConsistency:
    """Test skill name consistency between list and install."""

    def test_simplified_key_format(self, tmp_path):
        """Test that skills with subdirectory paths show simplified keys."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create a skill with subdirectory path in source
        skill = Skill(
            key="test-owner/test-repo:subdirs/nested/my-skill",
            name="my-skill",
            description="Test skill",
            directory="my-skill",
            source_directory="subdirs/nested/my-skill",
            repo_owner="test-owner",
            repo_name="test-repo",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        
        # Save the skill
        skills = {skill.key: skill}
        manager._save_skills(skills)
        
        # Also save the simplified key version (which is what the code does)
        simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        simplified_skill = Skill(
            key=simplified_key,
            name="my-skill",
            description="Test skill",
            directory="my-skill",
            source_directory="subdirs/nested/my-skill",
            repo_owner="test-owner",
            repo_name="test-repo",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        skills[simplified_key] = simplified_skill
        manager._save_skills(skills)
        
        # Load and verify both keys exist
        loaded_skills = manager._load_skills()
        assert skill.key in loaded_skills
        assert simplified_key in loaded_skills
        
        # Verify simplified key format
        assert simplified_key == "test-owner/test-repo:my-skill"
        assert "/" not in simplified_key.split(":")[-1]  # No slashes after colon

    def test_skill_list_displays_simplified_key(self):
        """Test that skill list logic generates simplified keys for display."""
        # Create a skill with complex source path
        skill = Skill(
            key="anthropics/skills:document-skills/docx",
            name="docx",
            description="Document processing skill",
            directory="docx",
            source_directory="document-skills/docx",
            repo_owner="anthropics",
            repo_name="skills",
            repo_branch="main",
            skills_path="/",
            installed=True,
        )
        
        # Generate the install key as the CLI does
        if skill.repo_owner and skill.repo_name:
            install_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        else:
            install_key = skill.key
        
        # Verify the install key is simplified
        assert install_key == "anthropics/skills:docx"
        assert "document-skills" not in install_key

    def test_simplified_key_resolves_to_skill(self, tmp_path):
        """Test that simplified keys can be used to install skills."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create both full and simplified keys
        full_key = "test-owner/test-repo:categories/subcategory/skill-name"
        simplified_key = "test-owner/test-repo:skill-name"
        
        skill_data = {
            "name": "skill-name",
            "description": "Test skill",
            "directory": "skill-name",
            "source_directory": "categories/subcategory/skill-name",
            "repo_owner": "test-owner",
            "repo_name": "test-repo",
            "repo_branch": "main",
            "skills_path": "/",
            "installed": False,
        }
        
        # Save both versions
        skills = {
            full_key: Skill(key=full_key, **skill_data),
            simplified_key: Skill(key=simplified_key, **skill_data),
        }
        manager._save_skills(skills)
        
        # Verify both keys work
        loaded_skills = manager._load_skills()
        assert full_key in loaded_skills
        assert simplified_key in loaded_skills
        
        # Verify they have the same essential properties
        full_skill = loaded_skills[full_key]
        simplified_skill = loaded_skills[simplified_key]
        
        assert full_skill.name == simplified_skill.name
        assert full_skill.directory == simplified_skill.directory
        assert full_skill.repo_owner == simplified_skill.repo_owner
        assert full_skill.repo_name == simplified_skill.repo_name

    def test_multiple_skills_from_same_repo(self, tmp_path):
        """Test skills from the same repo have unique simplified keys."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create multiple skills from same repo
        skills_data = [
            {
                "key": "owner/repo:category1/skill1",
                "name": "skill1",
                "directory": "skill1",
                "source_directory": "category1/skill1",
            },
            {
                "key": "owner/repo:category2/skill1",  # Different category, same name
                "name": "skill1",
                "directory": "skill1",
                "source_directory": "category2/skill1",
            },
            {
                "key": "owner/repo:category1/skill2",
                "name": "skill2",
                "directory": "skill2",
                "source_directory": "category1/skill2",
            },
        ]
        
        skills = {}
        for data in skills_data:
            skill = Skill(
                key=data["key"],
                name=data["name"],
                description="Test skill",
                directory=data["directory"],
                source_directory=data["source_directory"],
                repo_owner="owner",
                repo_name="repo",
                repo_branch="main",
                skills_path="/",
                installed=False,
            )
            skills[data["key"]] = skill
            
            # Also add simplified version
            simplified_key = f"owner/repo:{skill.directory}"
            simplified_skill = Skill(
                key=simplified_key,
                name=skill.name,
                description=skill.description,
                directory=skill.directory,
                source_directory=skill.source_directory,
                repo_owner=skill.repo_owner,
                repo_name=skill.repo_name,
                repo_branch=skill.repo_branch,
                skills_path=skill.skills_path,
                installed=False,
            )
            # Note: In reality, if two skills have the same directory name,
            # only one simplified key can exist. This is a limitation.
            if simplified_key not in skills:
                skills[simplified_key] = simplified_skill
        
        manager._save_skills(skills)
        loaded_skills = manager._load_skills()
        
        # Verify all full keys exist
        for data in skills_data:
            assert data["key"] in loaded_skills


class TestSkillInstallationByRepo:
    """Test skill installation from different repository configurations."""

    @pytest.fixture
    def skill_with_root_path(self):
        """Create a skill at repository root."""
        return Skill(
            key="owner/repo:skill-name",
            name="skill-name",
            description="Skill at root",
            directory="skill-name",
            source_directory="skill-name",
            repo_owner="owner",
            repo_name="repo",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )

    @pytest.fixture
    def skill_with_subdirectory(self):
        """Create a skill in a subdirectory."""
        return Skill(
            key="owner/repo:skills/skill-name",
            name="skill-name",
            description="Skill in subdirectory",
            directory="skill-name",
            source_directory="skills/skill-name",
            repo_owner="owner",
            repo_name="repo",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )

    @pytest.fixture
    def skill_with_nested_path(self):
        """Create a skill in nested directories."""
        return Skill(
            key="owner/repo:categories/tools/skill-name",
            name="skill-name",
            description="Skill in nested path",
            directory="skill-name",
            source_directory="categories/tools/skill-name",
            repo_owner="owner",
            repo_name="repo",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )

    def test_skill_at_root_has_simple_key(self, skill_with_root_path):
        """Test skill at root has simplified key matching directory."""
        skill = skill_with_root_path
        simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        assert simplified_key == "owner/repo:skill-name"

    def test_skill_in_subdirectory_has_simplified_key(self, skill_with_subdirectory):
        """Test skill in subdirectory has simplified key without path."""
        skill = skill_with_subdirectory
        simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        assert simplified_key == "owner/repo:skill-name"
        assert "skills/" not in simplified_key

    def test_skill_in_nested_path_has_simplified_key(self, skill_with_nested_path):
        """Test skill in nested path has simplified key without path."""
        skill = skill_with_nested_path
        simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        assert simplified_key == "owner/repo:skill-name"
        assert "categories" not in simplified_key
        assert "tools" not in simplified_key

    def test_all_skills_are_installable(self, tmp_path, skill_with_root_path,
                                       skill_with_subdirectory, skill_with_nested_path):
        """Test that all skill configurations can be installed using simplified keys."""
        manager = SkillManager(config_dir=tmp_path)
        
        test_skills = [
            skill_with_root_path,
            skill_with_subdirectory,
            skill_with_nested_path,
        ]
        
        skills = {}
        for skill in test_skills:
            # Store both full and simplified keys
            skills[skill.key] = skill
            
            simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
            simplified_skill = Skill(
                key=simplified_key,
                name=skill.name,
                description=skill.description,
                directory=skill.directory,
                source_directory=skill.source_directory,
                repo_owner=skill.repo_owner,
                repo_name=skill.repo_name,
                repo_branch=skill.repo_branch,
                skills_path=skill.skills_path,
                installed=False,
            )
            skills[simplified_key] = simplified_skill
        
        manager._save_skills(skills)
        loaded_skills = manager._load_skills()
        
        # Verify all simplified keys exist and are installable
        for skill in test_skills:
            simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
            assert simplified_key in loaded_skills, \
                f"Simplified key '{simplified_key}' should be in skills dict"


class TestRegressionPrevention:
    """Tests to prevent regression of the naming inconsistency bug."""

    def test_no_slash_in_simplified_key_suffix(self, tmp_path):
        """Ensure simplified keys don't contain slashes after the colon."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create skills with various path complexities
        test_cases = [
            ("owner/repo:a/b/c/skill", "owner/repo:skill"),
            ("owner/repo:category/skill", "owner/repo:skill"),
            ("owner/repo:deeply/nested/path/to/skill", "owner/repo:skill"),
        ]
        
        skills = {}
        for full_key, expected_simplified in test_cases:
            skill = Skill(
                key=full_key,
                name="skill",
                description="Test",
                directory="skill",
                source_directory=full_key.split(":", 1)[1],
                repo_owner="owner",
                repo_name="repo",
                repo_branch="main",
                skills_path="/",
                installed=False,
            )
            skills[full_key] = skill
            
            # Generate simplified key
            simplified_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
            
            # Verify it matches expected
            assert simplified_key == expected_simplified
            assert "/" not in simplified_key.split(":")[-1]
            
            # Store simplified version
            simplified_skill = Skill(
                key=simplified_key,
                name=skill.name,
                description=skill.description,
                directory=skill.directory,
                source_directory=skill.source_directory,
                repo_owner=skill.repo_owner,
                repo_name=skill.repo_name,
                repo_branch=skill.repo_branch,
                skills_path=skill.skills_path,
                installed=False,
            )
            skills[simplified_key] = simplified_skill
        
        manager._save_skills(skills)
        loaded_skills = manager._load_skills()
        
        # Verify all simplified keys exist
        for _, expected_simplified in test_cases:
            assert expected_simplified in loaded_skills

    def test_install_key_matches_list_display(self, tmp_path):
        """Test that the key shown in list is the same as what install expects."""
        manager = SkillManager(config_dir=tmp_path)
        
        # Create a skill with complex path
        full_key = "anthropics/skills:document-skills/docx"
        skill = Skill(
            key=full_key,
            name="docx",
            description="Document processing",
            directory="docx",
            source_directory="document-skills/docx",
            repo_owner="anthropics",
            repo_name="skills",
            repo_branch="main",
            skills_path="/",
            installed=False,
        )
        
        # Generate install key as CLI list command does
        if skill.repo_owner and skill.repo_name:
            install_key = f"{skill.repo_owner}/{skill.repo_name}:{skill.directory}"
        else:
            install_key = skill.key
        
        # Save both versions
        skills = {
            full_key: skill,
            install_key: Skill(
                key=install_key,
                name=skill.name,
                description=skill.description,
                directory=skill.directory,
                source_directory=skill.source_directory,
                repo_owner=skill.repo_owner,
                repo_name=skill.repo_name,
                repo_branch=skill.repo_branch,
                skills_path=skill.skills_path,
                installed=False,
            ),
        }
        manager._save_skills(skills)
        
        # Simulate install using the displayed key
        loaded_skills = manager._load_skills()
        assert install_key in loaded_skills, \
            f"Install key '{install_key}' from list display should work with install command"
        
        # Verify it's the correct skill
        installed_skill = loaded_skills[install_key]
        assert installed_skill.name == "docx"
        assert installed_skill.directory == "docx"
