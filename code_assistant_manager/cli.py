#!/usr/bin/env python3
"""Code Assistant Manager - CLI utilities for working with AI coding assistants.

Main entry point for the Code Assistant Manager package.
"""

# Import the refactored CLI module
from code_assistant_manager.cli import app, legacy_main

# For backward compatibility, expose the app
__all__ = ["app", "legacy_main"]

if __name__ == "__main__":
    legacy_main()
