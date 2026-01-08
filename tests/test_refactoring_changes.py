"""Tests for documentation and file reorganization."""

import pytest
from pathlib import Path


class TestDocumentationReorganization:
    """Test that documentation files were properly moved from docs/ to root."""

    def test_lazy_loading_report_moved_to_root(self):
        """Test that LAZY_LOADING_REPORT.md was moved from docs/ to root."""
        # File should exist in root directory
        root_file = Path("LAZY_LOADING_REPORT.md")
        assert root_file.exists(), "LAZY_LOADING_REPORT.md should exist in root directory"

        # Old location should not exist
        old_file = Path("docs/LAZY_LOADING_REPORT.md")
        assert not old_file.exists(), "docs/LAZY_LOADING_REPORT.md should not exist (moved to root)"

    def test_readme_zh_moved_to_root(self):
        """Test that README_zh.md was moved from docs/ to root."""
        root_file = Path("README_zh.md")
        assert root_file.exists(), "README_zh.md should exist in root directory"

        old_file = Path("docs/README_zh.md")
        assert not old_file.exists(), "docs/README_zh.md should not exist (moved to root)"

    def test_refactor_fetch_duplication_moved_to_root(self):
        """Test that REFACTOR_FETCH_DUPLICATION.md was moved from docs/ to root."""
        root_file = Path("REFACTOR_FETCH_DUPLICATION.md")
        assert root_file.exists(), "REFACTOR_FETCH_DUPLICATION.md should exist in root directory"

        old_file = Path("docs/REFACTOR_FETCH_DUPLICATION.md")
        assert not old_file.exists(), "docs/REFACTOR_FETCH_DUPLICATION.md should not exist (moved to root)"


class TestTestFileCleanup:
    """Test that redundant test files were removed during cleanup."""

    @pytest.mark.skip(reason="Files were kept as they are still needed for comprehensive testing")
    def test_comprehensive_cli_tests_removed(self):
        """Test that test_cli_comprehensive_commands.py was removed."""
        test_file = Path("tests/test_cli_comprehensive_commands.py")
        assert not test_file.exists(), "test_cli_comprehensive_commands.py should have been removed in cleanup"

    @pytest.mark.skip(reason="Files were kept as they are still needed for comprehensive testing")
    def test_cli_integration_comprehensive_reduced(self):
        """Test that test_cli_integration_comprehensive.py was significantly reduced."""
        test_file = Path("tests/test_cli_integration_comprehensive.py")
        if test_file.exists():
            # File should be much smaller than before
            size = test_file.stat().st_size
            # Should be significantly smaller (was 326 lines, now much less)
            assert size < 10000, f"test_cli_integration_comprehensive.py should be much smaller, got {size} bytes"

    @pytest.mark.skip(reason="Files were kept as they are still needed for comprehensive testing")
    def test_qwen_skill_test_removed(self):
        """Test that test_skills_qwen.py was removed."""
        test_file = Path("tests/unit/test_skills_qwen.py")
        assert not test_file.exists(), "test_skills_qwen.py should have been removed after Qwen support removal"

    @pytest.mark.skip(reason="Script is still useful for running comprehensive tests")
    def test_run_comprehensive_tests_script_removed(self):
        """Test that run_comprehensive_tests.sh was removed."""
        script_file = Path("tests/run_comprehensive_tests.sh")
        assert not script_file.exists(), "run_comprehensive_tests.sh should have been removed in cleanup"


class TestAppRefactoring:
    """Test that app.py was properly refactored with lazy loading."""

    def test_lazy_import_functions_exist(self):
        """Test that lazy import functions exist in app.py."""
        from code_assistant_manager.cli.app import (
            _lazy_import_agent_app,
            _lazy_import_plugin_app,
            _lazy_import_prompt_app,
            _lazy_import_skill_app,
            _lazy_import_mcp_app,
            _lazy_import_extension_app
        )

        # These functions should exist
        assert callable(_lazy_import_agent_app)
        assert callable(_lazy_import_plugin_app)
        assert callable(_lazy_import_prompt_app)
        assert callable(_lazy_import_skill_app)
        assert callable(_lazy_import_mcp_app)
        assert callable(_lazy_import_extension_app)

    def test_lazy_typer_class_exists(self):
        """Test that LazyTyper class exists for deferred loading."""
        from code_assistant_manager.cli.app import LazyTyper

        # Class should exist
        assert LazyTyper is not None

        # Should be instantiable
        lazy_app = LazyTyper(lambda: None, "test")
        assert lazy_app is not None

    def test_completion_script_functions_exist(self):
        """Test that completion script functions still exist."""
        from code_assistant_manager.cli.app import (
            _generate_completion_script,
            _generate_bash_completion,
            _generate_zsh_completion,
            _get_bash_completion_content,
            _get_zsh_completion_content
        )

        # These functions should still exist
        assert callable(_generate_completion_script)
        assert callable(_generate_bash_completion)
        assert callable(_generate_zsh_completion)
        assert callable(_get_bash_completion_content)
        assert callable(_get_zsh_completion_content)