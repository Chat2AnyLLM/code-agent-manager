"""CLI module for Code Assistant Manager."""

from .app import app


def main():
    """Main entry point for the CLI."""
    app()


__all__ = ["app", "main"]
