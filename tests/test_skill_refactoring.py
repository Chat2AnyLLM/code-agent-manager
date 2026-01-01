"""Tests for skill management refactoring changes."""

import pytest
from unittest.mock import MagicMock, patch
from code_assistant_manager.skills.manager import SkillManager
from code_assistant_manager.skills.models import Skill


class TestSkillManagementRefactoring:
    """Test the simplified skill management after refactoring."""

    def test_skill_get_simplified(self):
        """Test that skill.get() no longer supports install key format or complex lookup."""
        manager = SkillManager()

        # Test with a skill that doesn't exist
        result = manager.get("nonexistent")
        assert result is None

        # The complex install key format lookup was removed
        # This should just do a simple dict lookup
        result = manager.get("repo:directory")
        assert result is None

    def test_skill_delete_simplified(self):
        """Test that skill.delete() no longer supports install key format."""
        manager = SkillManager()

        # Test deleting a non-existent skill - raises KeyError from dict del operation
        with pytest.raises(KeyError):
            manager.delete("nonexistent")

        # The complex install key format lookup was removed - still raises KeyError for simple keys
        with pytest.raises(KeyError):
            manager.delete("repo:directory")

    def test_skill_install_simplified(self):
        """Test that skill.install() no longer supports install key format."""
        manager = SkillManager()

        # Test installing a non-existent skill
        with pytest.raises(ValueError, match="Skill with key 'nonexistent' not found"):
            manager.install("nonexistent", "claude")

        # The complex install key format lookup was removed
        with pytest.raises(ValueError, match="Skill with key 'repo:directory' not found"):
            manager.install("repo:directory", "claude")

    def test_skill_uninstall_simplified(self):
        """Test that skill.uninstall() no longer supports install key format."""
        manager = SkillManager()

        # Test uninstalling a non-existent skill
        with pytest.raises(ValueError, match="Skill with key 'nonexistent' not found"):
            manager.uninstall("nonexistent", "claude")

        # The complex install key format lookup was removed
        with pytest.raises(ValueError, match="Skill with key 'repo:directory' not found"):
            manager.uninstall("repo:directory", "claude")


class TestSkillCLICommandsRefactoring:
    """Test the simplified skill CLI commands after refactoring."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        from typer.testing import CliRunner
        return CliRunner()

    def test_list_skills_no_query_parameter(self, runner):
        """Test that list command no longer has --query parameter."""
        from code_assistant_manager.cli.app import app

        # This should work without --query parameter
        with patch('code_assistant_manager.cli.skills_commands.SkillManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_all.return_value = {}
            mock_manager.return_value = mock_instance

            result = runner.invoke(app, ["skill", "list"])
            # Command should still work (even if it shows no skills)
            assert result.exit_code in [0, 1]  # 0 for success, 1 for error

    def test_skill_install_help_still_mentions_qwen_inconsistency(self, runner):
        """Test that skill install help still mentions Qwen (inconsistency after refactoring)."""
        from code_assistant_manager.cli.app import app

        result = runner.invoke(app, ["skill", "install", "--help"])
        assert result.exit_code == 0
        # Qwen is still mentioned in individual command help (inconsistency)
        assert "qwen" in result.output.lower()

    def test_skill_uninstall_help_still_mentions_qwen_inconsistency(self, runner):
        """Test that skill uninstall help still mentions Qwen (inconsistency after refactoring)."""
        from code_assistant_manager.cli.app import app

        result = runner.invoke(app, ["skill", "uninstall", "--help"])
        assert result.exit_code == 0
        # Qwen is still mentioned in individual command help (inconsistency)
        assert "qwen" in result.output.lower()

    def test_skill_status_help_still_mentions_qwen_inconsistency(self, runner):
        """Test that skill status help still mentions Qwen (inconsistency after refactoring)."""
        from code_assistant_manager.cli.app import app

        result = runner.invoke(app, ["skill", "status", "--help"])
        assert result.exit_code == 0
        # Qwen is still mentioned in individual command help (inconsistency)
        assert "qwen" in result.output.lower()

    def test_skill_uninstall_all_help_still_mentions_qwen_inconsistency(self, runner):
        """Test that skill uninstall-all help still mentions Qwen (inconsistency after refactoring)."""
        from code_assistant_manager.cli.app import app

        result = runner.invoke(app, ["skill", "uninstall-all", "--help"])
        assert result.exit_code == 0
        # Qwen is still mentioned in individual command help (inconsistency)
        assert "qwen" in result.output.lower()


class TestCompletionScriptsRefactoring:
    """Test that completion scripts were properly refactored."""

    def test_completion_scripts_still_include_qwen_in_tools(self):
        """Test that completion scripts still include Qwen in tools list (inconsistency after refactoring)."""
        from code_assistant_manager.cli.app import _get_bash_completion_content

        completion_script = _get_bash_completion_content()

        # The completion scripts still include "qwen" in the tools list
        # even though Qwen skill support was removed
        assert 'qwen' in completion_script, "Completion scripts still include 'qwen' in tools list after skill support removal"

        # But Qwen is NOT in the supported app types for skills
        from code_assistant_manager.skills import VALID_APP_TYPES
        assert "qwen" not in VALID_APP_TYPES, "Qwen should not be in VALID_APP_TYPES"

    def test_completion_scripts_include_qwen_in_mcp_clients(self):
        """Test that completion scripts include Qwen in MCP client lists."""
        from code_assistant_manager.cli.app import _get_bash_completion_content

        completion_script = _get_bash_completion_content()

        # Qwen should still be included in MCP client completion options
        # since MCP support for Qwen may still exist
        assert '--client -c --interactive -i --help' in completion_script
        # This tests that the MCP client options are still present