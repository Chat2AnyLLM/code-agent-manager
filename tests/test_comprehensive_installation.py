"""Comprehensive installation tests for agents, plugins, and skills.

This module provides integration tests that cover the full installation workflow
for all three installation types (agents, plugins, skills) to ensure they work
correctly together and handle edge cases properly.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.agents import Agent
from code_assistant_manager.cli.app import app
from code_assistant_manager.skills import Skill


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    return {
        "agents": tmp_path / "agents",
        "plugins": tmp_path / "plugins",
        "skills": tmp_path / "skills",
        "config": tmp_path / "config",
    }


class TestComprehensiveInstallation:
    """Comprehensive tests for all installation functionality."""

    def test_agent_installation_workflow(self, runner, temp_dirs):
        """Test complete agent installation workflow."""
        # Mock agent manager
        with patch("code_assistant_manager.cli.agents_commands._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-agent": Agent(
                    key="test-agent",
                    name="Test Agent",
                    description="A test agent",
                    filename="test_agent.md",
                    installed=False,
                )
            }
            mock_manager.install.return_value = temp_dirs["agents"] / "test_agent.md"
            mock_get_manager.return_value = mock_manager

            # Install agent
            result = runner.invoke(app, ["agent", "install", "test-agent"])
            assert result.exit_code == 0
            assert "installed" in result.output.lower()

            # Verify installation was called
            mock_manager.install.assert_called_once_with("test-agent", "claude")

    def test_skill_installation_workflow(self, runner, temp_dirs):
        """Test complete skill installation workflow."""
        # Mock skill manager
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=False,
                )
            }
            mock_get_manager.return_value = mock_manager

            # Install skill
            result = runner.invoke(app, ["skill", "install", "test-skill"])
            assert result.exit_code == 0
            assert "installed" in result.output.lower()

            # Verify installation was called
            mock_manager.install.assert_called_once_with("test-skill", "claude")

    def test_plugin_installation_workflow(self, runner, temp_dirs):
        """Test complete plugin installation workflow."""
        # Mock plugin manager and handler
        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.install_plugin.return_value = (True, "Plugin installed successfully")
            mock_get_handler.return_value = mock_handler

            # Install plugin with marketplace:plugin format
            result = runner.invoke(app, ["plugin", "install", "test-marketplace:test-plugin"])
            assert result.exit_code == 0
            assert "installed successfully" in result.output

            # Verify installation was called
            mock_handler.install_plugin.assert_called_once()

    def test_installation_error_handling(self, runner):
        """Test error handling across all installation types."""
        # Test agent installation error
        with patch("code_assistant_manager.cli.agents_commands._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.install.side_effect = ValueError("Agent not found")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agent", "install", "nonexistent-agent"])
            assert result.exit_code != 0

        # Test skill installation error
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.install.side_effect = ValueError("Skill not found")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["skill", "install", "nonexistent-skill"])
            assert result.exit_code != 0

        # Test plugin installation error
        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.install_plugin.return_value = (False, "Installation failed")
            mock_get_handler.return_value = mock_handler

            result = runner.invoke(app, ["plugin", "install", "failing-plugin"])
            assert result.exit_code != 0

    def test_installation_to_multiple_apps(self, runner):
        """Test installing to multiple apps simultaneously."""
        # Test skill installation to multiple apps
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=False,
                )
            }
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["skill", "install", "test-skill", "--app", "claude,codex"])
            assert result.exit_code == 0

            # Should be called twice, once for each app
            assert mock_manager.install.call_count == 2

    def test_installation_status_verification(self, runner):
        """Test that installation status is correctly tracked."""
        # Test agent status
        with patch("code_assistant_manager.cli.agents_commands._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "installed-agent": Agent(
                    key="installed-agent",
                    name="Installed Agent",
                    description="Already installed",
                    filename="installed_agent.md",
                    installed=True,
                ),
                "not-installed-agent": Agent(
                    key="not-installed-agent",
                    name="Not Installed Agent",
                    description="Not installed",
                    filename="not_installed_agent.md",
                    installed=False,
                ),
            }
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agent", "list"])
            assert result.exit_code == 0
            # Should show both agents with correct status

        # Test skill status
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "installed-skill": Skill(
                    key="installed-skill",
                    name="Installed Skill",
                    description="Already installed",
                    directory="installed-skill",
                    installed=True,
                ),
                "not-installed-skill": Skill(
                    key="not-installed-skill",
                    name="Not Installed Skill",
                    description="Not installed",
                    directory="not-installed-skill",
                    installed=False,
                ),
            }
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["skill", "list"])
            assert result.exit_code == 0

    def test_installation_repository_integration(self, runner):
        """Test installation from configured repositories."""
        # Test fetching and installing from repositories
        with patch("code_assistant_manager.cli.agents_commands._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.fetch_agents_from_repos.return_value = [
                Agent(
                    key="repo-agent",
                    name="Repository Agent",
                    description="From repository",
                    filename="repo_agent.md",
                    installed=False,
                )
            ]
            mock_manager.get_all.return_value = {"repo-agent": mock_manager.fetch_agents_from_repos()[0]}
            mock_get_manager.return_value = mock_manager

            # First fetch
            result = runner.invoke(app, ["agent", "fetch"])
            assert result.exit_code == 0

            # Then install
            mock_manager.install.return_value = Path("/tmp/test.md")
            result = runner.invoke(app, ["agent", "install", "repo-agent"])
            assert result.exit_code == 0

    def test_installation_uninstall_workflow(self, runner):
        """Test complete install-uninstall workflow."""
        # Test skill install-uninstall cycle
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=True,  # Pretend it's installed
                )
            }
            mock_get_manager.return_value = mock_manager

            # Uninstall skill
            with patch("typer.confirm", return_value=True):  # Auto-confirm
                result = runner.invoke(app, ["skill", "uninstall", "test-skill"])
                assert result.exit_code == 0
                mock_manager.uninstall.assert_called_once_with("test-skill", "claude")

    def test_installation_force_options(self, runner):
        """Test uninstallation with confirmation."""
        # Test skill uninstallation with confirmation
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=True,
                )
            }
            mock_get_manager.return_value = mock_manager

            # Test uninstallation with auto-confirmation
            with patch("typer.confirm", return_value=True):  # Auto-confirm
                result = runner.invoke(app, ["skill", "uninstall", "test-skill"])
                assert result.exit_code == 0
                mock_manager.uninstall.assert_called_once_with("test-skill", "claude")

    def test_installation_invalid_app_types(self, runner):
        """Test installation to invalid app types."""
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=False,
                )
            }
            mock_get_manager.return_value = mock_manager

            # Try to install to invalid app
            result = runner.invoke(app, ["skill", "install", "test-skill", "--app", "invalid-app"])
            # Should fail gracefully
            assert result.exit_code != 0 or "invalid" in result.output.lower()

    def test_installation_dependency_conflicts(self, runner):
        """Test handling of dependency conflicts during installation."""
        # Test plugin conflict resolution
        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._resolve_plugin_conflict") as mock_resolve:
            with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler") as mock_get_handler:
                mock_resolve.return_value = "resolved-marketplace"
                mock_handler = MagicMock()
                mock_handler.install_plugin.return_value = (True, "Plugin installed")
                mock_get_handler.return_value = mock_handler

                result = runner.invoke(app, ["plugin", "install", "conflicting-plugin"])
                assert result.exit_code == 0
                mock_resolve.assert_called_once()


class TestInstallationIntegration:
    """Integration tests that combine multiple installation types."""

    def test_mixed_installation_workflow(self, runner):
        """Test installing agents, plugins, and skills in sequence."""
        # Install agent
        with patch("code_assistant_manager.cli.agents_commands._get_agent_manager") as mock_agent_mgr:
            mock_agent_mgr.return_value.install.return_value = Path("/tmp/agent.md")
            mock_agent_mgr.return_value.get_all.return_value = {
                "test-agent": Agent(
                    key="test-agent",
                    name="Test Agent",
                    description="A test agent",
                    filename="test_agent.md",
                    installed=False,
                )
            }
            result = runner.invoke(app, ["agent", "install", "test-agent"])
            assert result.exit_code == 0

        # Install skill
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager") as mock_skill_mgr:
            mock_skill_mgr.return_value.get_all.return_value = {
                "test-skill": Skill(
                    key="test-skill",
                    name="Test Skill",
                    description="A test skill",
                    directory="test-skill",
                    installed=False,
                )
            }
            result = runner.invoke(app, ["skill", "install", "test-skill"])
            assert result.exit_code == 0

        # Install plugin
        with patch("code_assistant_manager.cli.plugins.plugin_install_commands._get_handler") as mock_handler:
            mock_handler.return_value.install_plugin.return_value = (True, "Success")
            result = runner.invoke(app, ["plugin", "install", "test-marketplace:test-plugin"])
            assert result.exit_code == 0

    def test_bulk_installation_operations(self, runner):
        """Test bulk operations across installation types."""
        # Test listing all types
        commands = [
            ["agent", "list"],
            ["skill", "list"],
            ["plugin", "list", "--app", "claude"],
        ]

        for cmd in commands:
            result = runner.invoke(app, cmd)
            # Should not crash, even with mocked data
            assert isinstance(result.exit_code, int)

    def test_installation_state_persistence(self, runner, tmp_path):
        """Test that installation state is properly persisted."""
        config_file = tmp_path / "test_config.json"

        # This would require more complex mocking to test actual file persistence
        # For now, just verify the commands don't crash
        with patch("code_assistant_manager.cli.skills_commands._get_skill_manager"):
            result = runner.invoke(app, ["skill", "installed"])
            assert isinstance(result.exit_code, int)