"""Tests for code_assistant_manager.ui module."""

import pytest
from unittest.mock import patch, MagicMock
import os
import subprocess
import shutil

from code_assistant_manager.ui import get_terminal_size, clear_screen


class TestUI:
    """Test UI utility functions."""

    @patch('code_assistant_manager.ui.shutil.get_terminal_size')
    def test_get_terminal_size_success(self, mock_get_terminal_size):
        """Test successful terminal size retrieval."""
        mock_get_terminal_size.return_value = (120, 30)

        cols, rows = get_terminal_size()

        assert cols == 120
        assert rows == 30
        mock_get_terminal_size.assert_called_once_with((80, 24))

    @patch('code_assistant_manager.ui.shutil.get_terminal_size')
    def test_get_terminal_size_exception(self, mock_get_terminal_size):
        """Test terminal size fallback on exception."""
        mock_get_terminal_size.side_effect = Exception("Terminal error")

        cols, rows = get_terminal_size()

        assert cols == 80
        assert rows == 24

    @patch('code_assistant_manager.ui.subprocess.run')
    @patch('code_assistant_manager.ui.os.name', 'posix')
    def test_clear_screen_posix(self, mock_run):
        """Test screen clearing on POSIX systems."""
        clear_screen()

        mock_run.assert_called_once_with(["clear"], check=False)

    @patch('code_assistant_manager.ui.subprocess.run')
    @patch('code_assistant_manager.ui.os.name', 'nt')
    def test_clear_screen_windows(self, mock_run):
        """Test screen clearing on Windows systems."""
        clear_screen()

        mock_run.assert_called_once_with(["cls"], check=False)