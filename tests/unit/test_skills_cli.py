"""CLI tests for skill commands."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import code_assistant_manager.cli.skills_commands as skills_commands
from code_assistant_manager.skills import VALID_APP_TYPES, Skill


@pytest.fixture
def dummy_skill_manager(monkeypatch, tmp_path):
    """Stub SkillManager for CLI tests."""

    class DummyManager:
        def __init__(self):
            self.synced = []
            self.installs = []
            self.uninstalls = []
            self.skills = {}
            self.created_skills = []
            self.updated_skills = []
            self.deleted_skills = []
            self._handlers = {}

        def sync_installed_status(self, app):
            self.synced.append(app)

        def get_all(self):
            return self.skills

        def get(self, key):
            return self.skills.get(key)

        def install(self, key, app):
            self.installs.append((key, app))

        def uninstall(self, key, app):
            self.uninstalls.append((key, app))

        def create(self, skill):
            self.created_skills.append(skill)
            self.skills[skill.key] = skill

        def update(self, skill):
            self.updated_skills.append(skill)
            self.skills[skill.key] = skill

        def delete(self, key):
            self.deleted_skills.append(key)
            if key in self.skills:
                del self.skills[key]

        def get_handler(self, app):
            if app not in self._handlers:
                mock_handler = MagicMock()
                mock_handler.skills_dir = tmp_path / app
                mock_handler.skills_dir.mkdir(exist_ok=True)
                self._handlers[app] = mock_handler
            return self._handlers[app]

    manager = DummyManager()
    monkeypatch.setattr(skills_commands, "_get_skill_manager", lambda: manager)
    return manager


def test_skill_list_all_apps(dummy_skill_manager):
    skills_commands.list_skills(app_type="all")
    assert dummy_skill_manager.synced == VALID_APP_TYPES


def test_skill_install_multiple_apps(dummy_skill_manager, tmp_path, monkeypatch):
    skills_commands.install_skill("demo-skill", app_type="claude,codex")
    assert dummy_skill_manager.installs == [
        ("demo-skill", "claude"),
        ("demo-skill", "codex"),
    ]


def test_skill_installed_all_apps(monkeypatch, tmp_path, capsys):
    install_dirs = {}
    handlers = {}
    for app in VALID_APP_TYPES:
        app_dir = tmp_path / app
        app_dir.mkdir()
        (app_dir / "example").mkdir()
        install_dirs[app] = app_dir
        mock_handler = MagicMock()
        mock_handler.skills_dir = app_dir
        handlers[app] = mock_handler

    class Manager:
        def get_all(self):
            return {}

        def get_handler(self, app):
            return handlers.get(app)

    monkeypatch.setattr(skills_commands, "_get_skill_manager", lambda: Manager())

    skills_commands.list_installed_skills(app_type="all")
    captured = capsys.readouterr().out
    for app in VALID_APP_TYPES:
        assert f"{app.capitalize()}" in captured


# Additional tests for skill commands


def test_list_skills_empty(dummy_skill_manager, capsys):
    """list_skills shows message when no skills exist."""
    skills_commands.list_skills(app_type="claude")
    captured = capsys.readouterr().out
    assert "No skills found" in captured


def test_list_skills_with_skills(dummy_skill_manager, capsys):
    """list_skills shows all skills with their status."""
    dummy_skill_manager.skills = {
        "test-skill": Skill(
            key="test-skill",
            name="Test Skill",
            description="A test skill",
            directory="/path/to/skill",
            installed=True,
        ),
        "another-skill": Skill(
            key="another-skill",
            name="Another Skill",
            description="Another skill",
            directory="/path/to/another",
            installed=False,
        ),
    }

    skills_commands.list_skills(app_type="claude")
    captured = capsys.readouterr().out
    assert "Test Skill" in captured
    assert "Another Skill" in captured
    assert "test-skill" in captured
    assert "another-skill" in captured


def test_view_skill_success(dummy_skill_manager, capsys):
    """view_skill displays skill content."""
    dummy_skill_manager.skills = {
        "test-skill": Skill(
            key="test-skill",
            name="Test Skill",
            description="A test skill description",
            directory="/path/to/skill",
            repo_owner="owner",
            repo_name="repo",
            installed=True,
        )
    }

    skills_commands.view_skill("test-skill")
    captured = capsys.readouterr().out
    assert "Test Skill" in captured
    assert "A test skill description" in captured
    assert "owner/repo" in captured


def test_view_skill_not_found(dummy_skill_manager, capsys):
    """view_skill raises exit when skill not found."""
    with pytest.raises(skills_commands.typer.Exit):
        skills_commands.view_skill("nonexistent")

    captured = capsys.readouterr().out
    assert "not found" in captured


def test_create_skill_success(dummy_skill_manager, capsys):
    """create_skill creates a new skill."""
    skills_commands.create_skill(
        skill_key="new-skill",
        name="New Skill",
        description="A new skill",
        directory="/path/to/skill",
    )

    captured = capsys.readouterr().out
    assert "created" in captured.lower()
    assert len(dummy_skill_manager.created_skills) == 1
    assert dummy_skill_manager.created_skills[0].key == "new-skill"


def test_delete_skill_success(dummy_skill_manager, capsys):
    """delete_skill removes a skill."""
    dummy_skill_manager.skills = {
        "test-skill": Skill(
            key="test-skill",
            name="Test Skill",
            description="A test skill",
            directory="/path/to/skill",
        )
    }

    skills_commands.delete_skill("test-skill", force=True)
    captured = capsys.readouterr().out
    assert "deleted" in captured.lower()
    assert "test-skill" in dummy_skill_manager.deleted_skills


def test_delete_skill_not_found(dummy_skill_manager, capsys):
    """delete_skill fails when skill not found."""
    with pytest.raises(skills_commands.typer.Exit):
        skills_commands.delete_skill("nonexistent", force=True)

    captured = capsys.readouterr().out
    assert "not found" in captured


def test_uninstall_skill_success(dummy_skill_manager, tmp_path, monkeypatch):
    """uninstall_skill removes skill from app."""
    skills_commands.uninstall_skill("test-skill", app_type="claude")
    assert dummy_skill_manager.uninstalls == [("test-skill", "claude")]


def test_uninstall_skill_multiple_apps(dummy_skill_manager, tmp_path, monkeypatch):
    """uninstall_skill removes skill from multiple apps."""
    skills_commands.uninstall_skill("test-skill", app_type="claude,codex")
    assert dummy_skill_manager.uninstalls == [
        ("test-skill", "claude"),
        ("test-skill", "codex"),
    ]


def test_list_repos(dummy_skill_manager, capsys, monkeypatch):
    """list_repos shows configured skill repositories."""

    # Create a mock repos file
    class MockManager:
        def get_repos(self):
            return []

    monkeypatch.setattr(skills_commands, "_get_skill_manager", lambda: MockManager())

    skills_commands.list_repos()
    captured = capsys.readouterr().out
    # Should show header or "No repositories" message
    assert "repo" in captured.lower() or captured.strip() != ""
