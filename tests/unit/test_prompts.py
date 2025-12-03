"""Tests for prompt management module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from code_assistant_manager.prompts import PROMPT_FILE_PATHS, Prompt, PromptManager


class TestPrompt:
    """Test Prompt class."""

    def test_prompt_creation(self):
        """Test creating a prompt."""
        prompt = Prompt(
            id="test",
            name="Test Prompt",
            content="Test content",
            description="Test description",
        )
        assert prompt.id == "test"
        assert prompt.name == "Test Prompt"
        assert prompt.content == "Test content"
        assert prompt.description == "Test description"
        assert prompt.is_default is False  # Default is False

    def test_prompt_to_dict(self):
        """Test converting prompt to dictionary."""
        prompt = Prompt(
            id="test",
            name="Test",
            content="Content",
            description="Description",
            is_default=False,
        )
        data = prompt.to_dict()
        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert data["content"] == "Content"
        assert data["description"] == "Description"
        assert data["isDefault"] is False

    def test_prompt_from_dict(self):
        """Test creating prompt from dictionary."""
        data = {
            "id": "test",
            "name": "Test",
            "content": "Content",
            "description": "Description",
            "isDefault": True,
        }
        prompt = Prompt.from_dict(data)
        assert prompt.id == "test"
        assert prompt.name == "Test"
        assert prompt.content == "Content"
        assert prompt.description == "Description"
        assert prompt.is_default is True

    def test_prompt_from_dict_with_old_enabled_field(self):
        """Test migration from old 'enabled' field to 'isDefault'."""
        data = {
            "id": "test",
            "name": "Test",
            "content": "Content",
            "enabled": True,  # Old field
        }
        prompt = Prompt.from_dict(data)
        assert prompt.is_default is True  # Should be migrated

    def test_prompt_timestamps(self):
        """Test prompt timestamps are set automatically."""
        prompt = Prompt(id="test", name="Test", content="Content")
        assert prompt.created_at is not None
        assert prompt.updated_at is not None
        assert isinstance(prompt.created_at, int)
        assert isinstance(prompt.updated_at, int)


class TestPromptManager:
    """Test PromptManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_prompt_file(self):
        """Create a temporary prompt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "CLAUDE.md"
            yield prompt_file

    def test_manager_create_prompt(self, temp_config_dir):
        """Test creating a prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(
            id="test",
            name="Test Prompt",
            content="Test content",
        )
        manager.create(prompt)

        # Verify it was saved
        loaded = manager.get("test")
        assert loaded is not None
        assert loaded.name == "Test Prompt"

    def test_manager_get_all(self, temp_config_dir):
        """Test getting all prompts."""
        manager = PromptManager(temp_config_dir)
        prompt1 = Prompt(id="test1", name="Test 1", content="Content 1")
        prompt2 = Prompt(id="test2", name="Test 2", content="Content 2")

        manager.create(prompt1)
        manager.create(prompt2)

        all_prompts = manager.get_all()
        assert len(all_prompts) == 2
        assert "test1" in all_prompts
        assert "test2" in all_prompts

    def test_manager_update_prompt(self, temp_config_dir):
        """Test updating a prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Original", content="Content")
        manager.create(prompt)

        prompt.name = "Updated"
        manager.update(prompt)

        loaded = manager.get("test")
        assert loaded.name == "Updated"

    def test_manager_delete_prompt(self, temp_config_dir):
        """Test deleting a prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Test", content="Content")
        manager.create(prompt)

        manager.delete("test")
        assert manager.get("test") is None

    def test_manager_upsert(self, temp_config_dir):
        """Test upserting a prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Original", content="Content")
        manager.upsert(prompt)

        loaded = manager.get("test")
        assert loaded.name == "Original"

        prompt.name = "Updated"
        manager.upsert(prompt)

        loaded = manager.get("test")
        assert loaded.name == "Updated"

    def test_manager_export_import(self, temp_config_dir):
        """Test exporting and importing prompts."""
        manager = PromptManager(temp_config_dir)
        prompt1 = Prompt(id="test1", name="Test 1", content="Content 1")
        prompt2 = Prompt(id="test2", name="Test 2", content="Content 2")
        manager.create(prompt1)
        manager.create(prompt2)

        # Export
        export_file = temp_config_dir / "export.json"
        manager.export_to_file(export_file)
        assert export_file.exists()

        # Create new manager and import
        new_config_dir = temp_config_dir / "new"
        new_config_dir.mkdir()
        new_manager = PromptManager(new_config_dir)
        new_manager.import_from_file(export_file)

        all_prompts = new_manager.get_all()
        assert len(all_prompts) == 2
        assert all_prompts["test1"].name == "Test 1"
        assert all_prompts["test2"].name == "Test 2"

    def test_manager_duplicate_creation_error(self, temp_config_dir):
        """Test that creating duplicate prompt raises error."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Test", content="Content")
        manager.create(prompt)

        with pytest.raises(ValueError):
            manager.create(prompt)

    def test_manager_nonexistent_update_error(self, temp_config_dir):
        """Test that updating non-existent prompt raises error."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="nonexistent", name="Test", content="Content")

        with pytest.raises(ValueError):
            manager.update(prompt)


class TestPromptDefaultAndSync:
    """Test prompt default and sync functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_prompt_dir(self):
        """Create a temporary prompt file directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_set_default_prompt(self, temp_config_dir):
        """Test setting a prompt as default."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Test", content="My test content")
        manager.create(prompt)

        manager.set_default("test")

        # Check prompt is marked as default
        loaded = manager.get("test")
        assert loaded.is_default is True

    def test_set_default_clears_other_defaults(self, temp_config_dir):
        """Test setting a prompt as default clears other defaults."""
        manager = PromptManager(temp_config_dir)
        prompt1 = Prompt(
            id="test1", name="Test 1", content="Content 1", is_default=True
        )
        prompt2 = Prompt(id="test2", name="Test 2", content="Content 2")
        manager.create(prompt1)
        manager.create(prompt2)

        manager.set_default("test2")

        # Check prompt1 is no longer default
        loaded1 = manager.get("test1")
        assert loaded1.is_default is False

        # Check prompt2 is now default
        loaded2 = manager.get("test2")
        assert loaded2.is_default is True

    def test_get_default(self, temp_config_dir):
        """Test getting the default prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Test", content="Content", is_default=True)
        manager.create(prompt)

        default = manager.get_default()
        assert default is not None
        assert default.id == "test"

    def test_clear_default(self, temp_config_dir):
        """Test clearing the default prompt."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Test", content="Content", is_default=True)
        manager.create(prompt)

        manager.clear_default()

        loaded = manager.get("test")
        assert loaded.is_default is False

    def test_sync_to_app(self, temp_config_dir, temp_prompt_dir):
        """Test syncing a prompt to an app."""
        prompt_file = temp_prompt_dir / "CLAUDE.md"
        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )
        prompt = Prompt(id="test", name="Test", content="My test content")
        manager.create(prompt)

        manager.sync_to_app("test", "claude")

        # Check prompt was synced to file (with ID marker)
        assert prompt_file.exists()
        content = prompt_file.read_text()
        assert "My test content" in content
        assert "<!-- cam-prompt-id: test -->" in content

    def test_sync_to_app_project_level(self, temp_config_dir, temp_prompt_dir):
        """Project-level sync writes to project CLAUDE.md."""
        manager = PromptManager(temp_config_dir)
        prompt = Prompt(id="test", name="Proj", content="Project scoped content")
        manager.create(prompt)

        project_dir = temp_prompt_dir / "project"
        project_dir.mkdir()

        manager.sync_to_app("test", "claude", level="project", project_dir=project_dir)

        prompt_file = project_dir / "CLAUDE.md"
        assert prompt_file.exists()
        content = prompt_file.read_text()
        assert "Project scoped content" in content
        assert "<!-- cam-prompt-id: test -->" in content

    def test_get_live_content(self, temp_config_dir, temp_prompt_dir):
        """Test getting live prompt content."""
        prompt_file = temp_prompt_dir / "CLAUDE.md"
        prompt_file.write_text("Live content here")

        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )

        content = manager.get_live_content("claude")
        assert content == "Live content here"

    def test_get_live_content_project_level(self, temp_config_dir, temp_prompt_dir):
        """Test getting project-level live content."""
        manager = PromptManager(temp_config_dir)

        project_dir = temp_prompt_dir / "project"
        project_dir.mkdir()
        prompt_file = project_dir / "CLAUDE.md"
        prompt_file.write_text("Project content")

        content = manager.get_live_content(
            "claude", level="project", project_dir=project_dir
        )
        assert content == "Project content"

    def test_get_live_content_missing_file(self, temp_config_dir, temp_prompt_dir):
        """Test getting live content when file doesn't exist."""
        prompt_file = temp_prompt_dir / "NONEXISTENT.md"

        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )

        content = manager.get_live_content("claude")
        assert content is None

    def test_import_from_live(self, temp_config_dir, temp_prompt_dir):
        """Test importing from live prompt file."""
        prompt_file = temp_prompt_dir / "CLAUDE.md"
        prompt_file.write_text("Imported content")

        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )

        prompt_id = manager.import_from_live("claude", "My Import")

        assert prompt_id is not None
        loaded = manager.get(prompt_id)
        assert loaded.name == "My Import"
        assert loaded.content == "Imported content"

    def test_import_from_live_project_level(self, temp_config_dir, temp_prompt_dir):
        """Test importing project-level prompt files."""
        manager = PromptManager(temp_config_dir)

        project_dir = temp_prompt_dir / "project"
        project_dir.mkdir()
        prompt_file = project_dir / "CLAUDE.md"
        prompt_file.write_text("Project prompt content")

        prompt_id = manager.import_from_live(
            "claude",
            name="Project Prompt",
            level="project",
            project_dir=project_dir,
        )

        assert prompt_id is not None
        loaded = manager.get(prompt_id)
        assert loaded.name == "Project Prompt"
        assert loaded.content == "Project prompt content"

    def test_import_from_live_returns_existing_prompt(
        self, temp_config_dir, temp_prompt_dir
    ):
        """Importing same content should return existing prompt ID."""
        prompt_file = temp_prompt_dir / "CLAUDE.md"
        prompt_file.write_text("Deduplicated content")

        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )

        first_id = manager.import_from_live("claude", "First Import")
        second_id = manager.import_from_live("claude", "Second Import")

        assert first_id == second_id

    def test_import_from_live_empty(self, temp_config_dir, temp_prompt_dir):
        """Test importing from empty live file returns None."""
        prompt_file = temp_prompt_dir / "CLAUDE.md"
        prompt_file.write_text("")

        manager = PromptManager(
            temp_config_dir,
            handler_overrides={"claude": {"user_path": prompt_file}},
        )

        prompt_id = manager.import_from_live("claude")
        assert prompt_id is None

    def test_sync_default_to_all(self, temp_config_dir, temp_prompt_dir):
        """Test syncing default prompt to all apps."""
        manager = PromptManager(
            temp_config_dir,
            handler_overrides={
                "claude": {"user_path": temp_prompt_dir / "CLAUDE.md"},
                "codex": {"user_path": temp_prompt_dir / "AGENTS.md"},
                "gemini": {"user_path": temp_prompt_dir / "GEMINI.md"},
            },
        )
        prompt = Prompt(
            id="test",
            name="Test",
            content="Sync content",
            is_default=True,
        )
        manager.create(prompt)

        results = manager.sync_default_to_all()

        assert results["claude"] is not None
        assert results["codex"] is not None
        assert results["gemini"] is not None
        assert (temp_prompt_dir / "CLAUDE.md").exists()
        assert (temp_prompt_dir / "CLAUDE.md").read_text() == "Sync content"


class TestPromptConstants:
    """Test prompt module constants."""

    def test_prompt_file_paths(self):
        """Test PROMPT_FILE_PATHS contains expected apps."""
        assert "claude" in PROMPT_FILE_PATHS
        assert "codex" in PROMPT_FILE_PATHS
        assert "gemini" in PROMPT_FILE_PATHS

    def test_prompt_file_paths_values(self):
        """Test PROMPT_FILE_PATHS has correct file names."""
        assert PROMPT_FILE_PATHS["claude"].name == "CLAUDE.md"
        assert PROMPT_FILE_PATHS["codex"].name == "AGENTS.md"
        assert PROMPT_FILE_PATHS["gemini"].name == "GEMINI.md"
