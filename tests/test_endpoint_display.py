#!/usr/bin/env python3
"""Test script for endpoint display functionality."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.tools.endpoint_display import (
    display_all_tool_endpoints,
    display_tool_endpoints,
)


def main():
    """Test the endpoint display functionality."""
    # Use the example configuration file
    config_path = project_root / "providers.json"

    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        return 1

    try:
        # Initialize config
        config = ConfigManager(str(config_path))

        print("Testing endpoint display functionality...")
        print("=" * 50)

        # Test displaying all tool endpoints
        print("\n1. Displaying all tool endpoints:")
        display_all_tool_endpoints(config)

        # Test displaying specific tool endpoints
        print("\n2. Displaying Droid tool endpoints:")
        display_tool_endpoints(config, "droid")

        print("\n3. Displaying Claude tool endpoints:")
        display_tool_endpoints(config, "claude")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
