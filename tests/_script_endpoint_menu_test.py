#!/usr/bin/env python3
"""Test script for endpoint menu display functionality."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_assistant_manager.config import ConfigManager
from code_assistant_manager.endpoints import EndpointManager


def main():
    """Test the endpoint menu display functionality."""
    # Use the test configuration file
    config_path = project_root / "test_settings.json"

    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        return 1

    try:
        # Initialize config
        config = ConfigManager(str(config_path))
        endpoint_manager = EndpointManager(config)

        print("Testing endpoint menu display functionality...")
        print("=" * 50)

        # Test the endpoint selection menu for droid
        print("\n1. Testing endpoint selection menu for 'droid':")
        result = endpoint_manager.select_endpoint("droid")
        print(f"Result: {result}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
