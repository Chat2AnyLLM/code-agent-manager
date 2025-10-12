#!/usr/bin/env python3
"""Code complexity monitoring script for Code Assistant Manager.

This script checks for code quality issues including:
- File size limits
- Complexity metrics
- Import organization
- Code style violations

Usage:
    python scripts/monitor_complexity.py [--ci] [--fix]

Options:
    --ci        Exit with non-zero code on violations (for CI/CD)
    --fix       Attempt to auto-fix issues where possible
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
MAX_FILE_SIZE = 600  # lines
MAX_FUNCTION_LENGTH = 50  # lines
MAX_CLASS_LENGTH = 200  # lines

# Files and directories to monitor
MONITOR_PATHS = [
    "code_assistant_manager/",
]

# Files to exclude from monitoring
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    "dist",
    "build",
    "*.egg-info",
    "node_modules",
    ".venv",
    "tests/",
    "scripts/",
]


class ComplexityMonitor:
    """Monitor code complexity and quality metrics."""

    def __init__(self):
        self.violations: List[str] = []
        self.warnings: List[str] = []

    def check_file_sizes(self) -> None:
        """Check for files exceeding size limits."""
        for path in MONITOR_PATHS:
            if not Path(path).exists():
                continue

            for root, dirs, files in os.walk(path):
                # Skip excluded directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not any(
                        re.match(pattern.replace("*", ".*"), d)
                        for pattern in EXCLUDE_PATTERNS
                    )
                ]

                for file in files:
                    if not file.endswith(".py"):
                        continue

                    filepath = Path(root) / file

                    # Check exclude patterns
                    if any(
                        re.match(pattern.replace("*", ".*"), str(filepath))
                        for pattern in EXCLUDE_PATTERNS
                    ):
                        continue

                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            line_count = len(lines)

                            if line_count > MAX_FILE_SIZE:
                                self.violations.append(
                                    f"File too large: {filepath} ({line_count} lines > {MAX_FILE_SIZE})"
                                )
                    except Exception as e:
                        self.warnings.append(f"Could not read {filepath}: {e}")

    def check_complexity_metrics(self) -> None:
        """Check code complexity using radon."""
        try:
            result = subprocess.run(
                ["radon", "cc", "-a", "-s", "code_assistant_manager/"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.warnings.append(f"Radon complexity check failed: {result.stderr}")
                return

            # Parse radon output for high complexity
            lines = result.stdout.split("\n")
            for line in lines:
                if " - " in line and any(f"C" in line for f in ["C", "D", "E", "F"]):
                    # High complexity found
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        complexity = parts[0].strip()
                        function = parts[1].strip()
                        if any(c in complexity for c in ["D", "E", "F"]):
                            self.violations.append(
                                f"High complexity: {function} ({complexity})"
                            )

        except subprocess.TimeoutExpired:
            self.warnings.append("Complexity analysis timed out")
        except FileNotFoundError:
            self.warnings.append("radon not installed, install with: pip install radon")

    def check_linting(self) -> None:
        """Check for linting violations."""
        try:
            result = subprocess.run(
                [
                    "flake8",
                    "--max-line-length=88",
                    "--extend-ignore=E203,W503",
                    "code_assistant_manager/",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            violation_count = (
                len(result.stdout.split("\n")) - 1
            )  # Subtract 1 for empty line
            if violation_count > 50:  # Allow some violations but flag excessive ones
                self.warnings.append(f"High linting violation count: {violation_count}")
            elif violation_count > 100:
                self.violations.append(
                    f"Excessive linting violations: {violation_count}"
                )

        except subprocess.TimeoutExpired:
            self.warnings.append("Linting check timed out")
        except FileNotFoundError:
            self.warnings.append(
                "flake8 not installed, install with: pip install flake8"
            )

    def check_imports(self) -> None:
        """Check for import organization issues."""
        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", "code_assistant_manager/"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.warnings.append(
                    "Import organization issues found (run 'isort code_assistant_manager/')"
                )

        except subprocess.TimeoutExpired:
            self.warnings.append("Import check timed out")
        except FileNotFoundError:
            self.warnings.append("isort not installed, install with: pip install isort")

    def run_all_checks(self) -> None:
        """Run all complexity and quality checks."""
        print("🔍 Running complexity and quality checks...")

        self.check_file_sizes()
        self.check_complexity_metrics()
        self.check_linting()
        self.check_imports()

    def report(self, ci_mode: bool = False) -> int:
        """Report findings and return exit code."""
        if self.violations:
            print(f"\n❌ VIOLATIONS ({len(self.violations)}):")
            for violation in self.violations:
                print(f"  • {violation}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")

        if not self.violations and not self.warnings:
            print("✅ All checks passed!")
            return 0

        if self.violations:
            print(f"\n💥 {len(self.violations)} violations found")
            return 1 if ci_mode else 0
        else:
            print(f"\n📋 {len(self.warnings)} warnings found")
            return 0

    def auto_fix(self) -> None:
        """Attempt to auto-fix issues where possible."""
        print("🔧 Attempting auto-fixes...")

        # Fix import organization
        try:
            subprocess.run(["isort", "code_assistant_manager/"], check=True, timeout=30)
            print("✅ Fixed import organization")
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            print("⚠️  Could not fix imports (isort not available)")

        # Fix code formatting
        try:
            subprocess.run(
                ["black", "code_assistant_manager/", "--line-length=88"],
                check=True,
                timeout=30,
            )
            print("✅ Fixed code formatting")
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            print("⚠️  Could not fix formatting (black not available)")


def main():
    parser = argparse.ArgumentParser(description="Code complexity monitoring")
    parser.add_argument(
        "--ci", action="store_true", help="CI mode (exit non-zero on violations)"
    )
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fixes")

    args = parser.parse_args()

    monitor = ComplexityMonitor()
    monitor.run_all_checks()

    if args.fix:
        monitor.auto_fix()

    exit_code = monitor.report(ci_mode=args.ci)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
