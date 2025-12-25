"""Tests for CLI agent commands.

This module tests the agent management CLI commands including:
- list_agents: List all available agents
- fetch_agents: Fetch agents from configured repositories
- view_agent: View details of a specific agent
- install_agent: Install an agent to an app's agents directory
- uninstall_agent: Uninstall an agent from an app's agents directory
- list_repos: List configured agent repositories
- add_repo: Add an agent repository
- remove_repo: Remove an agent repository
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from typer.testing import CliRunner

import code_assistant_manager.cli.agents_commands as agents_commands
from code_assistant_manager.agents import VALID_APP_TYPES, Agent, AgentRepo


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    return Agent(
        key="test-agent",
        name="Test Agent",
        description="A test agent for unit testing",
        filename="test_agent.md",
        installed=False,
        tools=["read", "write"],
        color="blue",
        repo_owner="test-owner",
        repo_name="test-repo",
        repo_branch="main",
    )


@pytest.fixture
def mock_agent_installed(mock_agent):
    """Create a mock installed agent."""
    agent = mock_agent
    agent.installed = True
    return agent


@pytest.fixture
def dummy_agent_manager(monkeypatch, tmp_path, mock_agent):
    """Stub AgentManager for CLI tests."""

    class DummyAgentManager:
        def __init__(self):
            self.agents = {"test-agent": mock_agent}
            self.repos = []
            self.synced_apps = []
            self.installed = []
            self.uninstalled = []
            self.added_repos = []
            self.removed_repos = []
            self._handlers = {}

        def sync_installed_status(self):
            self.synced_apps.append("all")

        def get_all(self):
            return self.agents

        def get(self, key):
            return self.agents.get(key)

        def install(self, key, app_type):
            self.installed.append((key, app_type))
            return tmp_path / app_type / f"{key}.md"

        def uninstall(self, key, app_type):
            self.uninstalled.append((key, app_type))

        def get_repos(self):
            return self.repos

        def add_repo(self, repo):
            self.added_repos.append(repo)
            self.repos.append(repo)

        def remove_repo(self, owner, name):
            self.removed_repos.append((owner, name))
            self.repos = [
                r for r in self.repos if not (r.owner == owner and r.name == name)
            ]

        def fetch_agents_from_repos(self):
            return list(self.agents.values())

        def get_handler(self, app_type):
            if app_type not in self._handlers:
                mock_handler = MagicMock()
                mock_handler.agents_dir = tmp_path / app_type / "agents"
                mock_handler.agents_dir.mkdir(parents=True, exist_ok=True)
                self._handlers[app_type] = mock_handler
            return self._handlers[app_type]

    manager = DummyAgentManager()
    monkeypatch.setattr(agents_commands, "_get_agent_manager", lambda: manager)
    return manager


class TestListAgents:
    """Tests for list_agents command."""

    def test_list_agents_empty(self, dummy_agent_manager, capsys):
        """Test listing agents when no agents exist."""
        dummy_agent_manager.agents = {}
        agents_commands.list_agents()
        captured = capsys.readouterr()
        assert "No agents found" in captured.out

    def test_list_agents_with_agents(self, dummy_agent_manager, capsys):
        """Test listing agents with existing agents."""
        agents_commands.list_agents()
        captured = capsys.readouterr()
        assert "Test Agent" in captured.out
        assert "test-agent" in captured.out

    def test_list_agents_shows_installed_status(
        self, dummy_agent_manager, mock_agent_installed, capsys
    ):
        """Test that installed status is shown correctly."""
        dummy_agent_manager.agents["test-agent"] = mock_agent_installed
        agents_commands.list_agents()
        captured = capsys.readouterr()
        assert "✓" in captured.out  # Installed indicator

    def test_list_agents_shows_tools(self, dummy_agent_manager, capsys):
        """Test that tools are displayed."""
        agents_commands.list_agents()
        captured = capsys.readouterr()
        assert "read" in captured.out
        assert "write" in captured.out

    def test_list_agents_truncates_long_descriptions(
        self, dummy_agent_manager, mock_agent, capsys
    ):
        """Test that long descriptions are truncated."""
        mock_agent.description = "A" * 150  # Very long description
        dummy_agent_manager.agents["test-agent"] = mock_agent
        agents_commands.list_agents()
        captured = capsys.readouterr()
        assert "..." in captured.out


class TestFetchAgents:
    """Tests for fetch_agents command."""

    def test_fetch_agents_success(self, dummy_agent_manager, capsys):
        """Test successful agent fetch."""
        agents_commands.fetch_agents(url=None, save=False, agents_path=None)
        captured = capsys.readouterr()
        assert "Found 1 agents" in captured.out
        assert "test-agent" in captured.out

    def test_fetch_agents_error_handling(self, dummy_agent_manager, capsys):
        """Test error handling during fetch."""

        def raise_error():
            raise Exception("Network error")

        dummy_agent_manager.fetch_agents_from_repos = raise_error

        with pytest.raises((SystemExit, click.exceptions.Exit)):
            agents_commands.fetch_agents(url=None, save=False, agents_path=None)

        captured = capsys.readouterr()
        assert "Error fetching agents" in captured.out

    def test_fetch_agents_shows_install_hint(self, dummy_agent_manager, capsys):
        """Test that install hint is shown after fetch."""
        agents_commands.fetch_agents(url=None, save=False, agents_path=None)
        captured = capsys.readouterr()
        assert "cam agent list" in captured.out


class TestViewAgent:
    """Tests for view_agent command."""

    def test_view_agent_exists(self, dummy_agent_manager, capsys):
        """Test viewing an existing agent."""
        agents_commands.view_agent("test-agent")
        captured = capsys.readouterr()
        assert "Test Agent" in captured.out
        assert "A test agent for unit testing" in captured.out

    def test_view_agent_not_found(self, dummy_agent_manager, capsys):
        """Test viewing a non-existent agent."""
        with pytest.raises((SystemExit, click.exceptions.Exit)):
            agents_commands.view_agent("nonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_view_agent_shows_repository(self, dummy_agent_manager, capsys):
        """Test that repository info is displayed."""
        agents_commands.view_agent("test-agent")
        captured = capsys.readouterr()
        assert "test-owner/test-repo" in captured.out

    def test_view_agent_shows_tools(self, dummy_agent_manager, capsys):
        """Test that tools are displayed."""
        agents_commands.view_agent("test-agent")
        captured = capsys.readouterr()
        assert "read" in captured.out
        assert "write" in captured.out


class TestInstallAgent:
    """Tests for install_agent command."""

    def test_install_agent_success(self, dummy_agent_manager, capsys):
        """Test successful agent installation."""
        agents_commands.install_agent("test-agent", app_type="claude")
        assert ("test-agent", "claude") in dummy_agent_manager.installed
        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_install_agent_invalid_agent(self, dummy_agent_manager, capsys):
        """Test installing a non-existent agent."""
        dummy_agent_manager.install = MagicMock(
            side_effect=ValueError("Agent not found")
        )

        with pytest.raises((SystemExit, click.exceptions.Exit)):
            agents_commands.install_agent("nonexistent", app_type="claude")

        captured = capsys.readouterr()
        assert "not found" in captured.out or "Error" in captured.out



class TestUninstallAgent:
    """Tests for uninstall_agent command."""

    def test_uninstall_agent_success(self, dummy_agent_manager, mock_agent_installed):
        """Test successful agent uninstallation."""
        dummy_agent_manager.agents["test-agent"] = mock_agent_installed

        # Mock typer.confirm to return True (user confirms)
        with patch.object(agents_commands.typer, "confirm", return_value=True):
            agents_commands.uninstall_agent("test-agent", app_type="claude", force=True)

        assert ("test-agent", "claude") in dummy_agent_manager.uninstalled

    def test_uninstall_agent_not_found(self, dummy_agent_manager, capsys):
        """Test uninstalling a non-existent agent."""
        with pytest.raises((SystemExit, click.exceptions.Exit)):
            agents_commands.uninstall_agent(
                "nonexistent", app_type="claude", force=True
            )

        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_uninstall_agent_with_confirmation(
        self, dummy_agent_manager, mock_agent_installed
    ):
        """Test that uninstall requires confirmation without force flag."""
        dummy_agent_manager.agents["test-agent"] = mock_agent_installed

        with patch.object(agents_commands.typer, "confirm") as mock_confirm:
            mock_confirm.return_value = True
            agents_commands.uninstall_agent(
                "test-agent", app_type="claude", force=False
            )
            mock_confirm.assert_called_once()


class TestListRepos:
    """Tests for list_repos command."""

    def test_list_repos_empty(self, dummy_agent_manager, capsys):
        """Test listing repos when none configured."""
        agents_commands.list_repos()
        captured = capsys.readouterr()
        assert "No agent repositories" in captured.out

    def test_list_repos_with_repos(self, dummy_agent_manager, capsys):
        """Test listing repos with configured repos."""
        repo = AgentRepo(
            owner="test-owner", name="test-repo", branch="main", enabled=True
        )
        dummy_agent_manager.repos = [repo]

        agents_commands.list_repos()
        captured = capsys.readouterr()
        assert "test-owner/test-repo" in captured.out


class TestAddRepo:
    """Tests for add_repo command."""

    def test_add_repo_success(self, dummy_agent_manager, capsys):
        """Test successful repo addition."""
        agents_commands.add_repo(owner="new-owner", name="new-repo", branch="main")
        assert len(dummy_agent_manager.added_repos) == 1
        assert dummy_agent_manager.added_repos[0].owner == "new-owner"
        captured = capsys.readouterr()
        assert "Repository added" in captured.out

    def test_add_repo_with_agents_path(self, dummy_agent_manager, capsys):
        """Test adding repo with custom agents path."""
        agents_commands.add_repo(
            owner="new-owner",
            name="new-repo",
            branch="main",
            agents_path="custom/path",
        )
        assert dummy_agent_manager.added_repos[0].agents_path == "custom/path"


class TestRemoveRepo:
    """Tests for remove_repo command."""

    def test_remove_repo_success(self, dummy_agent_manager, capsys):
        """Test successful repo removal."""
        repo = AgentRepo(
            owner="test-owner", name="test-repo", branch="main", enabled=True
        )
        dummy_agent_manager.repos = [repo]

        with patch.object(agents_commands.typer, "confirm", return_value=True):
            agents_commands.remove_repo(
                owner="test-owner", name="test-repo", force=True
            )

        assert ("test-owner", "test-repo") in dummy_agent_manager.removed_repos
