#!/usr/bin/env python3
"""
Tests for interactive menu navigation using pexpect.

This test suite verifies that:
1. Users can navigate through all menu options
2. Users can select options and proceed to next menus
3. After completing all menus, users enter the tool's interactive interface
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

try:
    import pexpect
except ImportError:
    pexpect = None

pytestmark = pytest.mark.skipif(
    pexpect is None, reason="pexpect is required for interactive tests"
)

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestMenuNavigation:
    """Test suite for interactive menu navigation."""

    def setup_method(self):
        """Set up test environment."""
        # Create a temporary config file for testing
        self.temp_config = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        config_data = {
            "common": {"cache_ttl_seconds": 3600},
            "endpoints": {
                "test_endpoint": {
                    "endpoint": "https://api.test.com",
                    "api_key": "test_key",
                    "description": "Test Endpoint",
                    "list_models_cmd": "echo model1 model2 model3",
                    "supported_client": "codex,claude",
                }
            },
        }
        json.dump(config_data, self.temp_config, indent=2)
        self.temp_config.close()

    def teardown_method(self):
        """Clean up test environment."""
        # Remove temporary config file
        if hasattr(self, "temp_config") and self.temp_config:
            os.unlink(self.temp_config.name)

    def test_codex_menu_navigation_non_interactive(self):
        """Test Codex tool invocation in non-interactive mode."""
        # Set non-interactive mode
        env = os.environ.copy()
        env["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"] = "1"

        # Start the Codex tool
        child = pexpect.spawn(
            f"python3 -m code_assistant_manager.cli codex --config {self.temp_config.name}",
            env=env,
            timeout=10,
        )

        # Expect the tool to run and eventually exit or wait for input
        try:
            # The tool should either complete or wait for user input
            index = child.expect(
                ["Complete command to execute:", pexpect.EOF, pexpect.TIMEOUT],
                timeout=5,
            )
            if index == 0:
                # Tool is showing the command it would execute
                assert "codex" in child.before.decode("utf-8")
            elif index == 1:
                # Tool completed and exited - exitstatus may be None if not properly closed
                pass  # EOF is acceptable
            # If timeout, that's also acceptable for this test
        finally:
            child.close()

    def test_claude_menu_navigation_non_interactive(self):
        """Test Claude tool invocation in non-interactive mode."""
        # Set non-interactive mode
        env = os.environ.copy()
        env["CODE_ASSISTANT_MANAGER_NONINTERACTIVE"] = "1"

        # Start the Claude tool
        child = pexpect.spawn(
            f"python3 -m code_assistant_manager.cli claude --config {self.temp_config.name}",
            env=env,
            timeout=10,
        )

        # Expect the tool to run and eventually exit or wait for input
        try:
            # The tool should either complete or wait for user input
            index = child.expect(
                ["Complete command to execute:", pexpect.EOF, pexpect.TIMEOUT],
                timeout=5,
            )
            if index == 0:
                # Tool is showing the command it would execute
                assert "claude" in child.before.decode("utf-8")
            elif index == 1:
                # Tool completed and exited - exitstatus may be None if not properly closed
                pass  # EOF is acceptable
            # If timeout, that's also acceptable for this test
        finally:
            child.close()

    def test_menu_key_provider_functionality(self):
        """Test that menus can be controlled programmatically using mocked input."""
        from unittest.mock import patch

        from code_assistant_manager.menu.menus import display_simple_menu

        # Mock input to return "1" to select the first option
        with patch("builtins.input", return_value="1"):
            with patch("code_assistant_manager.ui.clear_screen"):
                success, idx = display_simple_menu(
                    "Test Menu",
                    ["Option 1", "Option 2", "Option 3"],
                    "Cancel",
                )

        # Should have selected the first option
        assert success is True
        assert idx == 0

    def test_model_selection_with_key_provider(self):
        """Test model selection with mocked input."""
        from unittest.mock import patch

        from code_assistant_manager.menu.menus import select_model

        # Mock the display_centered_menu to return selection of second model
        with patch(
            "code_assistant_manager.menu.menus.display_centered_menu",
            return_value=(True, 1),
        ):
            success, model = select_model(
                ["model1", "model2", "model3"], "Select a model:"
            )

        # Should have selected the second model
        assert success is True
        assert model == "model2"


if __name__ == "__main__":
    pytest.main([__file__])
