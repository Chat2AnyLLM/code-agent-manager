"""Tests for skill management module."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.skills import (
    VALID_APP_TYPES,
    ClaudeSkillHandler,
    Skill,
    SkillManager,
    SkillRepo,
)
from code_assistant_manager.skills.manager import DEFAULT_SKILL_REPOS


class TestSkill:
    """Test Skill class."""

    def test_skill_creation(self):
        """Test creating a skill."""
        skill = Skill(
            key="test",
            name="Test Skill",
            description="Test description",
            directory="/path/to/skill",
            installed=True,
        )
        assert skill.key == "test"
        assert skill.name == "Test Skill"
        assert skill.description == "Test description"
        assert skill.directory == "/path/to/skill"
        assert skill.installed is True

    def test_skill_to_dict(self):
        """Test converting skill to dictionary."""
        skill = Skill(
            key="test",
            name="Test",
            description="Description",
            directory="/path",
            installed=True,
            repo_owner="owner",
            repo_name="name",
            repo_branch="main",
        )
        data = skill.to_dict()
        assert data["key"] == "test"
        assert data["name"] == "Test"
        assert data["repoOwner"] == "owner"
        assert data["repoName"] == "name"
        assert data["repoBranch"] == "main"

    def test_skill_from_dict(self):
        """Test creating skill from dictionary."""
        data = {
            "key": "test",
            "name": "Test",
            "description": "Description",
            "directory": "/path",
            "installed": True,
            "repoOwner": "owner",
            "repoName": "name",
        }
        skill = Skill.from_dict(data)
        assert skill.key == "test"
        assert skill.repo_owner == "owner"
        assert skill.repo_name == "name"

    def test_skill_with_skills_path(self):
        """Test skill with skills_path attribute."""
        skill = Skill(
            key="test",
            name="Test",
            description="Desc",
            directory="skill-dir",
            repo_owner="owner",
            repo_name="repo",
            skills_path="skills/",
        )
        data = skill.to_dict()
        assert data["skillsPath"] == "skills/"

    def test_skill_with_readme_url(self):
        """Test skill with readme_url attribute."""
        skill = Skill(
            key="test",
            name="Test",
            description="Desc",
            directory="skill-dir",
            readme_url="https://github.com/owner/repo/tree/main/skill-dir",
        )
        data = skill.to_dict()
        assert data["readmeUrl"] == "https://github.com/owner/repo/tree/main/skill-dir"


class TestSkillRepo:
    """Test SkillRepo class."""

    def test_repo_creation(self):
        """Test creating a skill repo."""
        repo = SkillRepo(owner="owner", name="repo", branch="main")
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.branch == "main"
        assert repo.enabled is True

    def test_repo_to_dict(self):
        """Test converting repo to dictionary."""
        repo = SkillRepo(
            owner="owner",
            name="repo",
            branch="main",
            enabled=True,
            skills_path="skills/",
        )
        data = repo.to_dict()
        assert data["owner"] == "owner"
        assert data["name"] == "repo"
        assert data["skillsPath"] == "skills/"

    def test_repo_from_dict(self):
        """Test creating repo from dictionary."""
        data = {
            "owner": "owner",
            "name": "repo",
            "branch": "main",
            "enabled": True,
        }
        repo = SkillRepo.from_dict(data)
        assert repo.owner == "owner"
        assert repo.name == "repo"

    def test_repo_disabled(self):
        """Test creating disabled repo."""
        repo = SkillRepo(owner="owner", name="repo", enabled=False)
        assert repo.enabled is False


class TestSkillManager:
    """Test SkillManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_install_dir(self):
        """Create a temporary install directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_manager_get_handler_copilot(self, temp_config_dir):
        """SkillManager registers copilot handler."""
        manager = SkillManager(temp_config_dir)
        handler = manager.get_handler("copilot")
        assert handler.app_name == "copilot"
        assert str(handler.skills_dir).endswith("/.copilot/skills")

    def test_manager_create_skill(self, temp_config_dir):
        """Test creating a skill."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(
            key="test",
            name="Test Skill",
            description="Description",
            directory="/path",
        )
        manager.create(skill)

        loaded = manager.get("test")
        assert loaded is not None
        assert loaded.name == "Test Skill"

    def test_manager_get_all(self, temp_config_dir):
        """Test getting all skills."""
        manager = SkillManager(temp_config_dir)
        skill1 = Skill(
            key="test1", name="Test 1", description="Desc 1", directory="/p1"
        )
        skill2 = Skill(
            key="test2", name="Test 2", description="Desc 2", directory="/p2"
        )

        manager.create(skill1)
        manager.create(skill2)

        all_skills = manager.get_all()
        assert len(all_skills) == 2
        assert "test1" in all_skills
        assert "test2" in all_skills

    def test_manager_upsert(self, temp_config_dir):
        """Test upserting a skill."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(
            key="test", name="Original", description="Desc", directory="/path"
        )
        manager.upsert(skill)

        loaded = manager.get("test")
        assert loaded.name == "Original"

        skill.name = "Updated"
        manager.upsert(skill)

        loaded = manager.get("test")
        assert loaded.name == "Updated"

    def test_manager_delete(self, temp_config_dir):
        """Test deleting a skill."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(key="test", name="Test", description="Desc", directory="/path")
        manager.create(skill)

        manager.delete("test")
        assert manager.get("test") is None

    def test_manager_add_remove_repo(self, temp_config_dir):
        """Test adding and removing skill repos."""
        manager = SkillManager(temp_config_dir)

        # Get initial count (includes default repos)
        initial_repos = manager.get_repos()
        initial_count = len(initial_repos)

        # Use a completely unique repo identifier that won't conflict with defaults
        repo = SkillRepo(owner="test-owner-uniqu3", name="test-repo-uniqu3", branch="main")
        manager.add_repo(repo)

        repos = manager.get_repos()
        # Check that our new repo is in the list instead of just relying on count
        new_repos = manager.get_repos()
        assert any(r.owner == "test-owner-uniqu3" and r.name == "test-repo-uniqu3" for r in new_repos)

        # Also verify that the count increased (this should work if the repo was properly added)
        assert len(new_repos) == initial_count + 1

        manager.remove_repo("test-owner-uniqu3", "test-repo-uniqu3")
        repos_after_removal = manager.get_repos()
        assert len(repos_after_removal) == initial_count
        # Verify the specific repo was removed
        assert not any(r.owner == "test-owner-uniqu3" and r.name == "test-repo-uniqu3" for r in repos_after_removal)

    def test_manager_export_import(self, temp_config_dir):
        """Test exporting and importing skills."""
        manager = SkillManager(temp_config_dir)
        skill1 = Skill(
            key="test1", name="Test 1", description="Desc 1", directory="/p1"
        )
        skill2 = Skill(
            key="test2", name="Test 2", description="Desc 2", directory="/p2"
        )
        manager.create(skill1)
        manager.create(skill2)

        export_file = temp_config_dir / "export.json"
        manager.export_to_file(export_file)
        assert export_file.exists()

        new_config_dir = temp_config_dir / "new"
        new_config_dir.mkdir()
        new_manager = SkillManager(new_config_dir)
        new_manager.import_from_file(export_file)

        all_skills = new_manager.get_all()
        assert len(all_skills) == 2
        assert all_skills["test1"].name == "Test 1"
        assert all_skills["test2"].name == "Test 2"

    def test_manager_duplicate_creation_error(self, temp_config_dir):
        """Test that creating duplicate skill raises error."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(key="test", name="Test", description="Desc", directory="/path")
        manager.create(skill)

        with pytest.raises(ValueError):
            manager.create(skill)

    def test_manager_nonexistent_operations_error(self, temp_config_dir):
        """Test that operating on non-existent skill raises error."""
        manager = SkillManager(temp_config_dir)

        with pytest.raises(ValueError):
            manager.update(
                Skill(
                    key="nonexistent",
                    name="Test",
                    description="Desc",
                    directory="/path",
                )
            )

        with pytest.raises(ValueError):
            manager.install("nonexistent")

        with pytest.raises(ValueError):
            manager.uninstall("nonexistent")

    def test_manager_init_default_repos(self, temp_config_dir):
        """Test initializing default repos."""
        manager = SkillManager(temp_config_dir)

        # Repos are auto-initialized now, so should already have defaults
        repos = manager.get_repos()
        assert len(repos) == len(DEFAULT_SKILL_REPOS)

        # Calling _init_default_repos_file again should be idempotent
        manager._init_default_repos_file()
        repos = manager.get_repos()
        assert len(repos) == len(DEFAULT_SKILL_REPOS)

    def test_manager_sync_installed_status(self, temp_config_dir, temp_install_dir):
        """Test syncing installed status."""
        manager = SkillManager(temp_config_dir)

        # Create skills
        skill1 = Skill(
            key="test1", name="Test 1", description="Desc", directory="skill1"
        )
        skill2 = Skill(
            key="test2", name="Test 2", description="Desc", directory="skill2"
        )
        manager.create(skill1)
        manager.create(skill2)

        # Create a mock handler with temp install directory
        mock_handler = ClaudeSkillHandler(skills_dir_override=temp_install_dir)

        with patch.object(manager, "get_handler", return_value=mock_handler):
            # Create skill1 directory in install location with SKILL.md
            skill1_dir = temp_install_dir / "skill1"
            skill1_dir.mkdir(parents=True)
            (skill1_dir / "SKILL.md").write_text("---\nname: Skill 1\n---\n# Skill 1")

            manager.sync_installed_status("test_app")

            skills = manager.get_all()
            assert skills["test1"].installed is True
            assert skills["test2"].installed is False

    def test_manager_get_installed_skills(self, temp_config_dir, temp_install_dir):
        """Test getting installed skills."""
        manager = SkillManager(temp_config_dir)

        # Create a skill and a skill directory
        skill = Skill(key="test", name="Test", description="Desc", directory="my-skill")
        manager.create(skill)

        # Create a mock handler with temp install directory
        mock_handler = ClaudeSkillHandler(skills_dir_override=temp_install_dir)

        with patch.object(manager, "get_handler", return_value=mock_handler):
            # Create skill directory with SKILL.md
            skill_dir = temp_install_dir / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: My Skill\n---\n# My Skill")

            installed = manager.get_installed_skills("test_app")
            assert len(installed) == 1
            assert installed[0].name == "Test"
            assert installed[0].installed is True

    def test_parse_skill_metadata(self, temp_config_dir):
        """Test parsing SKILL.md metadata."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_config_dir)

        skill_md = temp_config_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: Test Skill
description: A test skill description
---

# Test Skill

This is the skill content.
"""
        )

        meta = handler.parse_skill_metadata(skill_md)
        assert meta.get("name") == "Test Skill"
        assert meta.get("description") == "A test skill description"

    def test_parse_skill_metadata_no_frontmatter(self, temp_config_dir):
        """Test parsing SKILL.md without frontmatter."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_config_dir)

        skill_md = temp_config_dir / "SKILL.md"
        skill_md.write_text("# Just Content\n\nNo frontmatter here.")

        meta = handler.parse_skill_metadata(skill_md)
        assert meta == {}

    def test_parse_skill_metadata_invalid_yaml(self, temp_config_dir):
        """Test parsing SKILL.md with invalid YAML."""
        handler = ClaudeSkillHandler(skills_dir_override=temp_config_dir)

        skill_md = temp_config_dir / "SKILL.md"
        skill_md.write_text("---\ninvalid: yaml: content:\n---\n# Content")

        meta = handler.parse_skill_metadata(skill_md)
        assert meta == {}


class TestSkillInstallation:
    """Test skill installation functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_install_dir(self):
        """Create a temporary install directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_skill_repo(self, temp_config_dir):
        """Create a mock skill repository structure."""
        repo_dir = temp_config_dir / "mock_repo"

        # Create skill structure
        skill_dir = repo_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: My Skill
description: A test skill
---
# My Skill
Content here.
"""
        )
        (skill_dir / "config.json").write_text('{"key": "value"}')

        return repo_dir

    def test_install_skill_no_repo_info(self, temp_config_dir, temp_install_dir):
        """Test installing skill without repo info raises error."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(key="test", name="Test", description="Desc", directory="my-skill")
        manager.create(skill)

        # Create a mock handler with temp install directory
        mock_handler = ClaudeSkillHandler(skills_dir_override=temp_install_dir)

        with patch.object(manager, "get_handler", return_value=mock_handler):
            with pytest.raises(ValueError, match="no repository information"):
                manager.install("test", "claude")

    def test_uninstall_skill(self, temp_config_dir, temp_install_dir):
        """Test uninstalling a skill."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(
            key="test",
            name="Test",
            description="Desc",
            directory="my-skill",
            installed=True,
            repo_owner="owner",
            repo_name="repo",
        )
        manager.create(skill)

        # Create the skill directory
        skill_dir = temp_install_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill")

        # Create a mock handler with temp install directory
        mock_handler = ClaudeSkillHandler(skills_dir_override=temp_install_dir)

        with patch.object(manager, "get_handler", return_value=mock_handler):
            manager.uninstall("test", "claude")

            # Check skill directory was removed
            assert not skill_dir.exists()

            # Check skill is marked as uninstalled
            loaded = manager.get("test")
            assert loaded.installed is False

    def test_uninstall_nonexistent_directory(self, temp_config_dir, temp_install_dir):
        """Test uninstalling skill with no directory."""
        manager = SkillManager(temp_config_dir)
        skill = Skill(
            key="test",
            name="Test",
            description="Desc",
            directory="my-skill",
            installed=True,
            repo_owner="owner",
            repo_name="repo",
        )
        manager.create(skill)

        # Create a mock handler with temp install directory
        mock_handler = ClaudeSkillHandler(skills_dir_override=temp_install_dir)

        with patch.object(manager, "get_handler", return_value=mock_handler):
            # Should not raise even if directory doesn't exist
            manager.uninstall("test", "claude")

            loaded = manager.get("test")
            assert loaded.installed is False


class TestSkillConstants:
    """Test skill module constants."""

    def test_valid_app_types(self):
        """Test VALID_APP_TYPES contains expected apps."""
        assert "claude" in VALID_APP_TYPES
        assert "codex" in VALID_APP_TYPES
        assert "gemini" in VALID_APP_TYPES
        assert "droid" in VALID_APP_TYPES

    def test_default_skill_repos(self):
        """Test DEFAULT_SKILL_REPOS has expected structure."""
        assert len(DEFAULT_SKILL_REPOS) >= 1
        for repo in DEFAULT_SKILL_REPOS:
            assert "owner" in repo
            assert "name" in repo
            assert "branch" in repo
