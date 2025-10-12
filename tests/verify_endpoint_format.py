#!/usr/bin/env python3
"""Verify the endpoint format in the menu."""

import os
import sys
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_assistant_manager.config import ConfigManager


def _get_config_path(project_root: Path) -> Path:
    """Get the configuration file path."""
    return project_root / "test_settings.json"


def _load_config(config_path: Path) -> ConfigManager:
    """Load the configuration manager."""
    return ConfigManager(str(config_path))


def _filter_endpoints_by_client(config: ConfigManager, client_name: str) -> List[str]:
    """Filter endpoints by client support."""
    endpoints = config.get_sections(exclude_common=True)
    filtered = []

    for ep in endpoints:
        # Simulate _is_client_supported logic
        ep_config = config.get_endpoint_config(ep)
        supported = ep_config.get("supported_client", "")
        if not supported or not client_name:
            filtered.append(ep)
        else:
            clients = [c.strip() for c in supported.split(",")]
            if client_name in clients:
                filtered.append(ep)

    return filtered


def _build_endpoint_choices(config: ConfigManager, endpoints: List[str]) -> List[str]:
    """Build endpoint choices with descriptions."""
    choices = []
    for ep in endpoints:
        ep_config = config.get_endpoint_config(ep)
        ep_url = ep_config.get("endpoint", "")
        ep_desc = ep_config.get("description", "")

        if not ep_desc:
            ep_desc = ep_url

        choices.append(f"{ep} -> {ep_url} -> {ep_desc}")

    return choices


def _display_endpoint_choices(choices: List[str]) -> None:
    """Display endpoint choices."""
    print("\nChoices that would be displayed in the menu:")
    for i, choice in enumerate(choices, 1):
        print(f"  {i}) {choice}")


def main():
    """Verify the endpoint format."""
    # Use the test configuration file
    config_path = _get_config_path(project_root)

    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        return 1

    try:
        # Initialize config
        config = _load_config(config_path)

        print("Verifying endpoint format...")
        print("=" * 50)

        # Simulate the logic from select_endpoint method
        client_name = "droid"
        print(f"Endpoints for {client_name}:")

        # Filter endpoints by client
        endpoints = _filter_endpoints_by_client(config, client_name)

        # Build endpoint choices with descriptions in the format: name -> endpoint -> description
        choices = _build_endpoint_choices(config, endpoints)

        _display_endpoint_choices(choices)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
