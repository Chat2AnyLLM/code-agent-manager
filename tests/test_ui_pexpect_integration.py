import os
import shutil
import subprocess
import sys
import textwrap

import pytest

pexpect = pytest.importorskip("pexpect")


SCRIPT = textwrap.dedent(
    """
from code_assistant_manager.menu.menus import display_centered_menu
success, idx = display_centered_menu("Pick", ["alpha","beta","gamma"], max_attempts=1)
print("RESULT:", success, idx)
"""
)


def test_pexpect_arrow_selection(tmp_path):
    script_file = tmp_path / "spawn_menu.py"
    script_file.write_text(SCRIPT)

    child = pexpect.spawnu(sys.executable, [str(script_file)], timeout=5)
    try:
        child.expect("Use ↑/↓ to navigate")
        # Send Down arrow
        child.send("\x1b[B")
        child.send("\r")
        child.expect("RESULT:")
        out = child.read().strip()
        assert "True" in out
    finally:
        child.close()
