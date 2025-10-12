"""Terminal UI components for Code Assistant Manager."""

import os
import shutil
import subprocess
from typing import Tuple


def get_terminal_size() -> Tuple[int, int]:
    """Get terminal width and height."""
    try:
        cols, rows = shutil.get_terminal_size((80, 24))
        return cols, rows
    except Exception:
        return 80, 24


def clear_screen():
    """Clear the terminal screen."""
    subprocess.run(["clear"] if os.name == "posix" else ["cls"], check=False)
