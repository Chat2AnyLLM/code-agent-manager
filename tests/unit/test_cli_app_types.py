"""Tests for CLI app type support across different commands.

This module tests that each CLI module correctly supports the expected
app types and rejects invalid ones.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_assistant_manager.agents import VALID_APP_TYPES as AGENT_APP_TYPES
from code_assistant_manager.plugins import VALID_APP_TYPES as PLUGIN_APP_TYPES
from code_assistant_manager.skills import VALID_APP_TYPES as SKILL_APP_TYPES


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestSupportedAppTypes:
    """Test that each module exposes the correct supported app types."""

    def test_skill_valid_app_types(self):
        """Test skill module supports all 7 app types."""
        expected = {"claude", "codex", "copilot", "gemini", "droid", "codebuddy", "qwen"}
        assert set(SKILL_APP_TYPES) == expected

    def test_agent_valid_app_types(self):
        """Test agent module supports all 7 app types."""
        expected = {"claude", "codex", "gemini", "droid", "codebuddy", "copilot", "opencode"}
        assert set(AGENT_APP_TYPES) == expected

    def test_plugin_valid_app_types(self):
        """Test plugin module supports claude, codebuddy, codex, and copilot."""
        expected = {"claude", "codebuddy", "codex", "copilot"}
        assert set(PLUGIN_APP_TYPES) == expected


class TestSkillAppTypeValidation:
    """Test skill CLI commands validate app types correctly."""

    def test_skill_install_accepts_valid_app(self, runner):
        """Test skill install accepts valid app types."""
        from code_assistant_manager.cli.skills_commands import skill_app

        with patch(
            "code_assistant_manager.cli.skills_commands._get_skill_manager"
        ) as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get.return_value = MagicMock()
            mock_instance.get_handler.return_value = MagicMock(skills_dir="/tmp/skills")
            mock_manager.return_value = mock_instance

            # Should accept all valid app types
            for app in ["claude", "codex", "copilot", "gemini", "droid", "codebuddy", "qwen"]:
                result = runner.invoke(skill_app, ["install", "test-skill", "-a", app])
                # Should not fail with "Invalid value" error
                assert "Invalid value" not in result.output

    def test_skill_install_rejects_invalid_app(self, runner):
        """Test skill install rejects invalid app types."""
        from code_assistant_manager.cli.skills_commands import skill_app

        result = runner.invoke(
            skill_app, ["install", "test-skill", "-a", "invalid-app"]
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_skill_list_accepts_all_keyword(self, runner):
        """Test skill list accepts 'all' as app type."""
        from code_assistant_manager.cli.skills_commands import skill_app

        with patch(
            "code_assistant_manager.cli.skills_commands._get_skill_manager"
        ) as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_all.return_value = {}
            mock_instance.sync_installed_status = MagicMock()
            mock_manager.return_value = mock_instance

            result = runner.invoke(skill_app, ["list", "-a", "all"])
            assert "Invalid value" not in result.output


class TestAgentAppTypeValidation:
    """Test agent CLI commands validate app types correctly."""

    def test_agent_install_accepts_valid_app(self, runner):
        """Test agent install accepts valid app types."""
        from code_assistant_manager.cli.agents_commands import agent_app

        with patch(
            "code_assistant_manager.cli.agents_commands._get_agent_manager"
        ) as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get.return_value = MagicMock()
            mock_instance.get_handler.return_value = MagicMock(agents_dir="/tmp/agents")
            mock_manager.return_value = mock_instance

            # Should accept all valid app types
            for app in ["claude", "codex", "gemini", "droid", "codebuddy", "copilot", "opencode"]:
                result = runner.invoke(agent_app, ["install", "test-agent", "-a", app])
                # Should not fail with "Invalid value" error
                assert "Invalid value" not in result.output

    def test_agent_install_rejects_invalid_app(self, runner):
        """Test agent install rejects invalid app types."""
        from code_assistant_manager.cli.agents_commands import agent_app

        result = runner.invoke(
            agent_app, ["install", "test-agent", "-a", "invalid-app"]
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


class TestPluginAppTypeValidation:
    """Test plugin CLI commands validate app types correctly."""

    def test_plugin_install_accepts_claude(self, runner):
        """Test plugin install accepts claude app type."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_handler:
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch(
                    "code_assistant_manager.plugins.PluginManager"
                ) as mock_manager:
                    handler = MagicMock()
                    handler.install_plugin.return_value = (True, "Installed")
                    handler.get_known_marketplaces.return_value = []
                    mock_handler.return_value = handler
                    mock_manager.return_value.get_repo.return_value = None

                    result = runner.invoke(
                        plugin_app, ["install", "test-plugin", "-a", "claude"]
                    )
                    assert "Invalid" not in result.output

    def test_plugin_install_accepts_codebuddy(self, runner):
        """Test plugin install accepts codebuddy app type."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_handler:
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch(
                    "code_assistant_manager.plugins.PluginManager"
                ) as mock_manager:
                    handler = MagicMock()
                    handler.install_plugin.return_value = (True, "Installed")
                    handler.get_known_marketplaces.return_value = []
                    mock_handler.return_value = handler
                    mock_manager.return_value.get_repo.return_value = None

                    result = runner.invoke(
                        plugin_app, ["install", "test-plugin", "-a", "codebuddy"]
                    )
                    assert "Invalid" not in result.output

    def test_plugin_install_accepts_codex(self, runner):
        """Test plugin install accepts codex app type."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_handler:
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch("code_assistant_manager.plugins.PluginManager") as mock_manager:
                    handler = MagicMock()
                    # Local-install codepath calls install_from_github; CLI codepath calls install_plugin
                    handler.uses_cli_plugin_commands = False
                    handler.install_from_github.return_value = MagicMock()
                    mock_handler.return_value = handler
                    mock_manager.return_value.get_repo.return_value = None

                    result = runner.invoke(
                        plugin_app, ["install", "test-plugin", "-a", "codex"]
                    )
                    assert "Invalid value" not in result.output

    def test_plugin_install_accepts_copilot(self, runner):
        """Test plugin install accepts copilot app type."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_handler:
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                with patch("code_assistant_manager.plugins.PluginManager") as mock_manager:
                    handler = MagicMock()
                    handler.uses_cli_plugin_commands = False
                    handler.install_from_github.return_value = MagicMock()
                    mock_handler.return_value = handler
                    mock_manager.return_value.get_repo.return_value = None

                    result = runner.invoke(
                        plugin_app, ["install", "test-plugin", "-a", "copilot"]
                    )
                    assert "Invalid value" not in result.output

    def test_plugin_install_rejects_gemini(self, runner):
        """Test plugin install rejects gemini (not supported for plugins)."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        result = runner.invoke(plugin_app, ["install", "test-plugin", "-a", "gemini"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_plugin_install_rejects_droid(self, runner):
        """Test plugin install rejects droid (not supported for plugins)."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        result = runner.invoke(plugin_app, ["install", "test-plugin", "-a", "droid"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_plugin_install_rejects_invalid_app(self, runner):
        """Test plugin install rejects completely invalid app types."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        result = runner.invoke(
            plugin_app, ["install", "test-plugin", "-a", "invalid-app"]
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_plugin_list_accepts_claude(self, runner):
        """Test plugin list accepts claude app type."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        with patch(
            "code_assistant_manager.cli.plugins.plugin_install_commands._get_handler"
        ) as mock_handler:
            with patch(
                "code_assistant_manager.cli.plugins.plugin_install_commands._check_app_cli"
            ):
                handler = MagicMock()
                handler.get_enabled_plugins.return_value = {}
                mock_handler.return_value = handler

                result = runner.invoke(plugin_app, ["list", "-a", "claude"])
                assert "Invalid value" not in result.output

    def test_plugin_list_rejects_gemini(self, runner):
        """Test plugin list rejects gemini (not supported for plugins)."""
        from code_assistant_manager.cli.plugin_commands import plugin_app

        result = runner.invoke(plugin_app, ["list", "-a", "gemini"])
        assert result.exit_code != 0
        # Check for error message about invalid app type
        assert "Invalid" in result.output or "invalid" in result.output.lower()
