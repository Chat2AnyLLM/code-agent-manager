"""Tests for code_assistant_manager.ui module."""

from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.menu.base import Colors
from code_assistant_manager.menu.menus import (
    display_centered_menu,
    select_model,
    select_two_models,
)
from code_assistant_manager.ui import get_terminal_size


class TestColors:
    """Test Colors class."""

    def test_colors_exist(self):
        """Test that all color codes exist."""
        assert hasattr(Colors, "BLUE")
        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "YELLOW")
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "BOLD")
        assert hasattr(Colors, "RESET")

    def test_colors_are_ansi_codes(self):
        """Test that colors are ANSI escape codes."""
        assert Colors.BLUE.startswith("\033[")
        assert Colors.RESET == "\033[0m"


class TestGetTerminalSize:
    """Test get_terminal_size function."""

    def test_get_terminal_size_returns_tuple(self):
        """Test that get_terminal_size returns a tuple."""
        size = get_terminal_size()
        assert isinstance(size, tuple)
        assert len(size) == 2

    def test_get_terminal_size_returns_positive_values(self):
        """Test that terminal size values are positive."""
        width, height = get_terminal_size()
        assert width > 0
        assert height > 0

    def test_get_terminal_size_defaults(self):
        """Test default terminal size."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.side_effect = Exception("Error")
            width, height = get_terminal_size()
            assert width == 80
            assert height == 24


class TestDisplayCenteredMenu:
    """Test display_centered_menu function."""

    @patch("builtins.input", return_value="1")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_basic(self, mock_clear, mock_input):
        """Test basic menu display."""
        items = ["Option 1", "Option 2", "Option 3"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is True
        assert idx == 0

    @patch("builtins.input", return_value="2")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_selection(self, mock_clear, mock_input):
        """Test menu selection."""
        items = ["Option 1", "Option 2", "Option 3"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is True
        assert idx == 1

    @patch("builtins.input", return_value="4")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_cancel(self, mock_clear, mock_input):
        """Test menu cancellation (selecting cancel option)."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is False
        assert idx is None

    @patch("builtins.input", side_effect=["invalid", "", "1"])
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_invalid_input(self, mock_clear, mock_input):
        """Test menu with invalid input retry."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is True
        assert idx == 0

    @patch("builtins.input", side_effect=["99", "100", "101"])
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_out_of_range(self, mock_clear, mock_input):
        """Test menu with out of range selection (max attempts exceeded)."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items, max_attempts=3)
        assert success is False
        assert idx is None

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_keyboard_interrupt(self, mock_clear, mock_input):
        """Test menu with keyboard interrupt."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is False
        assert idx is None

    @patch("builtins.input", side_effect=EOFError())
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_eof(self, mock_clear, mock_input):
        """Test menu with EOF."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is False
        assert idx is None

    @patch("builtins.input", return_value="1")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_custom_cancel_text(self, mock_clear, mock_input):
        """Test menu with custom cancel text."""
        items = ["Option 1", "Option 2"]
        success, idx = display_centered_menu("Test Menu", items, cancel_text="Quit")
        assert success is True
        assert idx == 0

    @patch("builtins.input", return_value="1")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_single_item(self, mock_clear, mock_input):
        """Test menu with single item."""
        items = ["Only Option"]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is True
        assert idx == 0

    @patch("builtins.input", return_value="1")
    @patch("code_assistant_manager.ui.clear_screen")
    def test_display_centered_menu_many_items(self, mock_clear, mock_input):
        """Test menu with many items."""
        items = [f"Option {i}" for i in range(1, 21)]
        success, idx = display_centered_menu("Test Menu", items)
        assert success is True
        assert idx == 0


class TestSelectModel:
    """Test select_model function."""

    @patch("code_assistant_manager.tools.display_centered_menu")
    def test_select_model_success(self, mock_menu):
        """Test successful model selection."""
        mock_menu.return_value = (True, 1)
        models = ["gpt-4", "gpt-3.5", "claude-3"]
        success, model = select_model(models)
        assert success is True
        assert model == "gpt-3.5"

    @patch("code_assistant_manager.tools.display_centered_menu")
    def test_select_model_cancelled(self, mock_menu):
        """Test cancelled model selection."""
        mock_menu.return_value = (False, None)
        models = ["gpt-4", "gpt-3.5", "claude-3"]
        success, model = select_model(models)
        assert success is False
        assert model is None

    @patch("code_assistant_manager.tools.display_centered_menu")
    def test_select_model_custom_prompt(self, mock_menu):
        """Test model selection with custom prompt."""
        mock_menu.return_value = (True, 0)
        models = ["model1", "model2"]
        select_model(models, prompt="Choose your model:")
        mock_menu.assert_called_once()
        call_args = mock_menu.call_args
        assert call_args[0][0] == "Choose your model:"


class TestSelectTwoModels:
    """Test select_two_models function."""

    @patch("code_assistant_manager.menu.menus.select_model")
    @patch("time.sleep")
    def test_select_two_models_success(self, mock_sleep, mock_select):
        """Test successful two model selection."""
        mock_select.side_effect = [(True, "gpt-4"), (True, "gpt-3.5")]
        models = ["gpt-4", "gpt-3.5"]
        success, result = select_two_models(models)
        assert success is True
        assert result == ("gpt-4", "gpt-3.5")

    @patch("code_assistant_manager.menu.menus.select_model")
    def test_select_two_models_first_cancelled(self, mock_select):
        """Test two model selection with first cancelled."""
        mock_select.return_value = (False, None)
        models = ["gpt-4", "gpt-3.5"]
        success, result = select_two_models(models)
        assert success is False
        assert result is None

    @patch("code_assistant_manager.menu.menus.select_model")
    @patch("time.sleep")
    def test_select_two_models_second_cancelled(self, mock_sleep, mock_select):
        """Test two model selection with second cancelled."""
        mock_select.side_effect = [(True, "gpt-4"), (False, None)]
        models = ["gpt-4", "gpt-3.5"]
        success, result = select_two_models(models)
        assert success is False
        assert result is None

    @patch("code_assistant_manager.menu.menus.select_model")
    @patch("time.sleep")
    def test_select_two_models_custom_prompts(self, mock_sleep, mock_select):
        """Test two model selection with custom prompts."""
        mock_select.side_effect = [(True, "primary"), (True, "secondary")]
        models = ["model1", "model2"]
        select_two_models(
            models,
            primary_prompt="Select primary:",
            secondary_prompt="Select secondary:",
        )
        assert mock_select.call_count == 2
