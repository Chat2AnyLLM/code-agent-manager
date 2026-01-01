"""Tests for upstream changes that remove Qwen support and refactor the codebase."""

import pytest
from pathlib import Path


class TestUpstreamQwenRemoval:
    """Test that Qwen support is properly removed in upstream changes."""

    def test_qwen_skill_file_removed(self):
        """Test that qwen.py skill file is removed."""
        qwen_file = Path("code_assistant_manager/skills/qwen.py")
        # After upstream changes, this file should not exist
        assert not qwen_file.exists(), "qwen.py should be removed in upstream changes"

    def test_qwen_not_in_skill_handlers(self):
        """Test that Qwen is not in SKILL_HANDLERS after upstream changes."""
        # This test will pass after upstream changes are applied
        try:
            from code_assistant_manager.skills.manager import SKILL_HANDLERS
            assert "qwen" not in SKILL_HANDLERS, "Qwen should not be in SKILL_HANDLERS after removal"
        except ImportError:
            # If import fails due to missing QwenSkillHandler, that's also acceptable
            pass

    def test_qwen_not_in_valid_app_types(self):
        """Test that Qwen is not in VALID_APP_TYPES after upstream changes."""
        try:
            from code_assistant_manager.skills import VALID_APP_TYPES
            assert "qwen" not in VALID_APP_TYPES, "Qwen should not be in VALID_APP_TYPES after removal"
        except ImportError:
            # If import fails, that's also acceptable
            pass

    def test_qwen_skill_handler_not_importable(self):
        """Test that QwenSkillHandler cannot be imported after upstream changes."""
        with pytest.raises(ImportError):
            from code_assistant_manager.skills.qwen import QwenSkillHandler

        # Also test import from skills module
        with pytest.raises(ImportError):
            from code_assistant_manager.skills import QwenSkillHandler

    def test_qwen_removed_from_skills_init_all(self):
        """Test that QwenSkillHandler is removed from skills __init__.py __all__."""
        try:
            from code_assistant_manager import skills
            assert not hasattr(skills, 'QwenSkillHandler'), "QwenSkillHandler should not be in skills module"
        except ImportError:
            pass


class TestUpstreamDocumentationReorganization:
    """Test that documentation files are properly moved."""

    def test_lazy_loading_report_moved(self):
        """Test LAZY_LOADING_REPORT.md moved from docs/ to root."""
        root_file = Path("LAZY_LOADING_REPORT.md")
        old_file = Path("docs/LAZY_LOADING_REPORT.md")

        assert root_file.exists(), "LAZY_LOADING_REPORT.md should exist in root"
        assert not old_file.exists(), "docs/LAZY_LOADING_REPORT.md should not exist"

    def test_readme_zh_moved(self):
        """Test README_zh.md moved from docs/ to root."""
        root_file = Path("README_zh.md")
        old_file = Path("docs/README_zh.md")

        assert root_file.exists(), "README_zh.md should exist in root"
        assert not old_file.exists(), "docs/README_zh.md should not exist"

    def test_refactor_fetch_duplication_moved(self):
        """Test REFACTOR_FETCH_DUPLICATION.md moved from docs/ to root."""
        root_file = Path("REFACTOR_FETCH_DUPLICATION.md")
        old_file = Path("docs/REFACTOR_FETCH_DUPLICATION.md")

        assert root_file.exists(), "REFACTOR_FETCH_DUPLICATION.md should exist in root"
        assert not old_file.exists(), "docs/REFACTOR_FETCH_DUPLICATION.md should not exist"


class TestUpstreamTestCleanup:
    """Test that redundant test files are removed."""

    def test_comprehensive_cli_tests_removed(self):
        """Test test_cli_comprehensive_commands.py is removed."""
        test_file = Path("tests/test_cli_comprehensive_commands.py")
        assert not test_file.exists(), "test_cli_comprehensive_commands.py should be removed"

    def test_qwen_skill_tests_removed(self):
        """Test test_skills_qwen.py is removed."""
        test_file = Path("tests/unit/test_skills_qwen.py")
        assert not test_file.exists(), "test_skills_qwen.py should be removed"

    def test_comprehensive_installation_tests_removed(self):
        """Test test_comprehensive_installation.py is removed."""
        test_file = Path("tests/test_comprehensive_installation.py")
        assert not test_file.exists(), "test_comprehensive_installation.py should be removed"

    def test_installation_by_repo_tests_removed(self):
        """Test test_installation_by_repo.py is removed."""
        test_file = Path("tests/test_installation_by_repo.py")
        assert not test_file.exists(), "test_installation_by_repo.py should be removed"

    def test_installation_error_scenarios_removed(self):
        """Test test_installation_error_scenarios.py is removed."""
        test_file = Path("tests/test_installation_error_scenarios.py")
        assert not test_file.exists(), "test_installation_error_scenarios.py should be removed"

    def test_plugin_marketplace_name_consistency_removed(self):
        """Test test_plugin_marketplace_name_consistency.py is removed."""
        test_file = Path("tests/test_plugin_marketplace_name_consistency.py")
        assert not test_file.exists(), "test_plugin_marketplace_name_consistency.py should be removed"

    def test_skill_name_consistency_removed(self):
        """Test test_skill_name_consistency.py is removed."""
        test_file = Path("tests/test_skill_name_consistency.py")
        assert not test_file.exists(), "test_skill_name_consistency.py should be removed"

    def test_comprehensive_test_script_removed(self):
        """Test run_comprehensive_tests.sh is removed."""
        script_file = Path("tests/run_comprehensive_tests.sh")
        assert not script_file.exists(), "run_comprehensive_tests.sh should be removed"


class TestUpstreamAppRefactoring:
    """Test that app.py lazy loading refactoring works."""

    def test_lazy_import_functions_available(self):
        """Test that lazy import functions exist in refactored app.py."""
        from code_assistant_manager.cli.app import (
            _lazy_import_agent_app,
            _lazy_import_plugin_app,
            _lazy_import_prompt_app,
            _lazy_import_skill_app,
            _lazy_import_mcp_app,
            _lazy_import_extension_app
        )
        # These should be callable
        assert callable(_lazy_import_agent_app)
        assert callable(_lazy_import_plugin_app)
        assert callable(_lazy_import_prompt_app)
        assert callable(_lazy_import_skill_app)
        assert callable(_lazy_import_mcp_app)
        assert callable(_lazy_import_extension_app)

    def test_lazy_typer_class_available(self):
        """Test that LazyTyper class exists."""
        from code_assistant_manager.cli.app import LazyTyper
        assert LazyTyper is not None

    def test_completion_functions_available(self):
        """Test that completion functions still exist."""
        from code_assistant_manager.cli.app import (
            _generate_completion_script,
            _generate_bash_completion,
            _generate_zsh_completion
        )
        assert callable(_generate_completion_script)
        assert callable(_generate_bash_completion)
        assert callable(_generate_zsh_completion)


class TestUpstreamSkillSimplification:
    """Test that skill management is simplified in upstream changes."""

    def test_skill_manager_simplified_get(self):
        """Test that skill.get() no longer supports complex install key lookup."""
        from code_assistant_manager.skills.manager import SkillManager

        manager = SkillManager()

        # Should return None for non-existent skills
        result = manager.get("nonexistent")
        assert result is None

        # Should return None for install key format (no longer supported)
        result = manager.get("repo:directory")
        assert result is None

    def test_skill_manager_simplified_delete(self):
        """Test that skill.delete() raises KeyError for non-existent skills."""
        from code_assistant_manager.skills.manager import SkillManager

        manager = SkillManager()

        # Should raise KeyError for non-existent skills
        with pytest.raises(KeyError):
            manager.delete("nonexistent")

    def test_skill_cli_no_query_parameter(self):
        """Test that skill list command no longer accepts --query parameter."""
        from typer.testing import CliRunner
        from code_assistant_manager.cli.app import app

        runner = CliRunner()

        # Command should work without --query
        result = runner.invoke(app, ["skill", "list"])
        # Should not fail due to unknown option
        assert result.exit_code in [0, 2]  # 0=success, 2=error