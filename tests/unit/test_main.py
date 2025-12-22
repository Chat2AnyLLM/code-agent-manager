"""Tests for code_assistant_manager.__main__ module."""

import subprocess
import sys
from unittest.mock import patch

import pytest


class TestMainModule:
    """Test the main module entry point."""

    def test_main_module_calls_cli_main(self):
        """Test that running the module calls the CLI main function."""
        # Mock the cli.main function
        with patch('code_assistant_manager.cli.main') as mock_main:
            # Simulate running the module by setting __name__ to "__main__"
            # and executing the module code
            import types
            main_module = types.ModuleType('code_assistant_manager.__main__')
            main_module.__name__ = '__main__'  # Simulate running as main module

            # Execute the module code in the simulated context
            exec(open('code_assistant_manager/__main__.py').read(), main_module.__dict__)

            # Verify that cli.main was called
            mock_main.assert_called_once()

    def test_main_module_structure(self):
        """Test that the main module has the expected structure."""
        import code_assistant_manager.__main__

        # Verify the module can be imported
        assert hasattr(code_assistant_manager.__main__, '__doc__')
        assert 'Entry point for running code_assistant_manager as a module' in code_assistant_manager.__main__.__doc__

        # Verify it imports the cli module
        assert hasattr(code_assistant_manager.__main__, 'main')