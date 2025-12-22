"""Environment variable loader for Code Assistant Manager.

Loads .env files from standard locations using python-dotenv.
"""

from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv

# Module-level flag to prevent redundant loading
_ENV_LOADED = False


class EnvLoader:
    """Environment variable loader class with prefix filtering support."""

    def __init__(self, prefix: Optional[str] = None):
        """Initialize EnvLoader with optional prefix filtering.

        Args:
            prefix: If provided, only environment variables starting with this prefix
                   will be accessible (prefix will be stripped from keys).
        """
        self.prefix = prefix

    def get(self, key: str) -> Optional[str]:
        """Get environment variable value.

        Args:
            key: Environment variable name

        Returns:
            Value of the environment variable, or None if not found
        """
        import os

        # Apply prefix filtering
        if self.prefix:
            full_key = f"{self.prefix}{key}"
        else:
            full_key = key

        # Try exact case first
        value = os.environ.get(full_key)
        if value is not None:
            return value

        # Try case-insensitive lookup
        for env_key, env_value in os.environ.items():
            if env_key.lower() == full_key.lower():
                return env_value

        return None


def find_env_file(
    custom_path: Optional[str] = None, strict: bool = False
) -> Optional[Path]:
    """
    Find .env file in standard locations.

    Uses dotenv.find_dotenv which searches in:
    1. Custom path (if provided)
    2. Current working directory
    3. Parent directories (up to root or .git)

    Args:
        custom_path: Optional custom path to .env file
        strict: If True and custom_path is provided but not found, return None

    Returns:
        Path to .env file if found, None otherwise
    """
    if custom_path:
        custom_path_obj = Path(custom_path)
        if custom_path_obj.exists() and custom_path_obj.is_file():
            return custom_path_obj
        elif strict:
            return None

    # Use dotenv's find_dotenv which searches smart locations
    env_file = find_dotenv(raise_error_if_not_found=False)
    if env_file:
        return Path(env_file)

    # Also check home directory and config directory as fallback
    locations = [
        Path.home() / ".env",
        Path.home() / ".config" / "code-assistant-manager" / ".env",
    ]

    for env_file in locations:
        if env_file.exists() and env_file.is_file():
            return env_file

    return None


def load_env(custom_path: Optional[str] = None, force: bool = False) -> bool:
    """
    Load environment variables from .env file using python-dotenv.

    Args:
        custom_path: Optional custom path to .env file
        force: If True, reload even if already loaded

    Returns:
        True if env file was loaded, False otherwise
    """
    global _ENV_LOADED

    if _ENV_LOADED and not force:
        return False

    env_file = find_env_file(custom_path)
    if not env_file:
        return False

    try:
        # Use python-dotenv to load the file
        load_dotenv(dotenv_path=env_file, override=True)
        _ENV_LOADED = True
        return True
    except Exception:
        return False


def is_loaded() -> bool:
    """Check if environment has been loaded."""
    return _ENV_LOADED


def reset() -> None:
    """Reset the loaded flag (useful for testing)."""
    global _ENV_LOADED
    _ENV_LOADED = False


if __name__ == "__main__":
    # When run as a script, load env and print status
    if load_env():
        exit(0)
    else:
        exit(1)
