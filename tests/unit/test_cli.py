"""Tests for code_assistant_manager.cli module."""

class TestCLIModule:
    """Test the CLI module functionality."""

    def test_cli_module_can_be_imported(self):
        """Test that the CLI module can be imported successfully."""
        # This should import without errors
        from code_assistant_manager.cli import app, main

        assert app is not None
        assert main is not None
        assert callable(main)

    def test_cli_app_has_expected_name(self):
        """Test that the CLI app has the expected name."""
        from code_assistant_manager.cli import app

        assert app.info.name == "cam"