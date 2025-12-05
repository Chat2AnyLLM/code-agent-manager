#!/usr/bin/env python3
"""Check that source files don't exceed maximum line limits."""

import os
import sys
from pathlib import Path

# Maximum allowed lines per file
MAX_LINES = 750

# File extensions to check
SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".go",
    ".rs",
}

# Directories to exclude
EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    ".next",
    ".nuxt",
    "target",  # Rust/Cargo
    "bin",
    "obj",
    ".vscode",
    ".idea",
}


def should_check_file(file_path: Path) -> bool:
    """Check if a file should be included in the size check."""
    # Check extension
    if file_path.suffix not in SOURCE_EXTENSIONS:
        return False

    # Check if in excluded directory
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False

    return True


def count_lines(file_path: Path) -> int:
    """Count lines in a file, handling encoding issues."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def main():
    """Main entry point."""
    repo_root = Path.cwd()
    violations = []

    # Walk through all files
    for root, dirs, files in os.walk(repo_root):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            file_path = Path(root) / file
            if should_check_file(file_path):
                line_count = count_lines(file_path)
                if line_count > MAX_LINES:
                    violations.append((file_path.relative_to(repo_root), line_count))

    if violations:
        print(f"❌ Found {len(violations)} file(s) exceeding {MAX_LINES} lines:")
        print()
        for file_path, lines in sorted(violations):
            print(f"  {file_path}: {lines} lines")
        print()
        print(f"💡 Consider breaking large files into smaller modules.")
        print(f"   Maximum allowed: {MAX_LINES} lines per file")
        sys.exit(1)
    else:
        print(f"✅ All source files are within the {MAX_LINES} line limit!")
        sys.exit(0)


if __name__ == "__main__":
    main()
