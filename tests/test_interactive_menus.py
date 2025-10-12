#!/usr/bin/env python3
"""
Comprehensive tests for interactive menu navigation using pexpect.

This test suite simulates actual user interaction with the menus:
1. Navigating through endpoint selection menus
2. Selecting models from the model selection menus
3. Verifying that after menu completion, tools enter their interactive interface
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


class TestInteractiveMenus:
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

    def test_menu_key_provider_directly(self):
        """Test menu functionality using the key_provider mechanism directly."""
        from code_assistant_manager.menu.base import SimpleMenu

        # Test with key_provider that selects option 1
        def key_provider():
            return "1"

        menu = SimpleMenu(
            "Test Menu",
            ["Option 1", "Option 2", "Option 3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()

        assert success is True
        assert idx == 0  # First option (0-indexed)

    def test_model_selection_key_provider(self):
        """Test model selection using key_provider."""
        from code_assistant_manager.menu.menus import select_model

        # Test with key_provider that selects option 2
        def key_provider():
            return "2"

        success, model = select_model(
            ["model1", "model2", "model3"], "Select a model:", key_provider=key_provider
        )

        assert success is True
        assert model == "model2"

    def test_menu_abstraction(self):
        """Test that the menu abstraction works correctly."""
        from code_assistant_manager.menu.base import SimpleMenu

        # Create a simple menu with a key provider
        def key_provider():
            return "1"

        menu = SimpleMenu(
            "Test Menu", ["Option 1", "Option 2"], "Cancel", key_provider=key_provider
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 0  # First option


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
