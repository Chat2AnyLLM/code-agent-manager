"""Tests for filterable menu with simulated input."""

from unittest.mock import patch

import pytest

from code_assistant_manager.menu.base import FilterableMenu


class TestFilterableMenuFiltering:
    """Test FilterableMenu filtering functionality."""

    def test_filterable_menu_basic_filtering(self):
        """Test basic filtering functionality."""
        menu = FilterableMenu(
            "Test Menu", ["apple", "banana", "cherry", "date"], "Cancel"
        )

        # Test filtering
        menu.filter_text = "a"
        filtered = menu._filter_items()
        # Should match "apple", "banana", "date"
        assert len(filtered) == 3
        assert filtered[0][1] == "apple"
        assert filtered[1][1] == "banana"
        assert filtered[2][1] == "date"

    def test_filterable_menu_case_insensitive_filtering(self):
        """Test case-insensitive filtering."""
        menu = FilterableMenu("Test Menu", ["Apple", "BANANA", "Cherry"], "Cancel")

        # Test case-insensitive filtering
        menu.filter_text = "a"
        filtered = menu._filter_items()
        # Should match "Apple" and "BANANA"
        assert len(filtered) == 2
        assert filtered[0][1] == "Apple"
        assert filtered[1][1] == "BANANA"

    def test_filterable_menu_empty_filter(self):
        """Test empty filter returns all items."""
        items = ["item1", "item2", "item3"]
        menu = FilterableMenu("Test Menu", items, "Cancel")

        # Test empty filter
        menu.filter_text = ""
        filtered = menu._filter_items()
        assert len(filtered) == 3
        assert [item[1] for item in filtered] == items

    def test_filterable_menu_no_matches(self):
        """Test filtering with no matches."""
        menu = FilterableMenu("Test Menu", ["apple", "banana", "cherry"], "Cancel")

        # Test no matches
        menu.filter_text = "xyz"
        filtered = menu._filter_items()
        assert len(filtered) == 0

    def test_filterable_menu_partial_matches(self):
        """Test partial string matching."""
        menu = FilterableMenu(
            "Test Menu", ["model-1", "model-2", "other-model"], "Cancel"
        )

        # Test partial match
        menu.filter_text = "model"
        filtered = menu._filter_items()
        assert len(filtered) == 3
        assert filtered[0][1] == "model-1"
        assert filtered[1][1] == "model-2"
        assert filtered[2][1] == "other-model"

    def test_filterable_menu_special_characters(self):
        """Test filtering with special characters."""
        menu = FilterableMenu(
            "Test Menu", ["model_v1", "model-v2", "model v3"], "Cancel"
        )

        # Test underscore match
        menu.filter_text = "_"
        filtered = menu._filter_items()
        assert len(filtered) == 1
        assert filtered[0][1] == "model_v1"

    def test_filterable_menu_update_filter_dynamically(self):
        """Test dynamic filter updates."""
        menu = FilterableMenu(
            "Test Menu", ["apple", "apricot", "banana", "blueberry"], "Cancel"
        )

        # Initial filter
        menu.filter_text = "ap"
        filtered = menu._filter_items()
        assert len(filtered) == 2
        assert filtered[0][1] == "apple"
        assert filtered[1][1] == "apricot"

        # Update filter
        menu.filter_text = "app"
        filtered = menu._filter_items()
        assert len(filtered) == 1
        assert filtered[0][1] == "apple"

    def test_filterable_menu_clear_filter(self):
        """Test clearing the filter."""
        menu = FilterableMenu("Test Menu", ["apple", "banana", "cherry"], "Cancel")

        # Apply filter
        menu.filter_text = "a"
        filtered = menu._filter_items()
        assert len(filtered) == 2

        # Clear filter
        menu.filter_text = ""
        filtered = menu._filter_items()
        assert len(filtered) == 3


class TestFilterableMenuWithSimulatedInput:
    """Test FilterableMenu with simulated user input."""

    def test_filterable_menu_simulated_typing(self):
        """Test FilterableMenu with simulated typing input."""
        # Create a key provider that simulates typing "ban" then Enter
        keys = iter(["b", "a", "n", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["apple", "banana", "cherry", "date"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 1  # "banana" is the second item in the original list

    def test_filterable_menu_simulated_backspace(self):
        """Test FilterableMenu with simulated backspace input."""
        # Create a key provider that types "ban" then backspace twice then "ch" then Enter
        # This results in filter "bch" which matches no items, so cancel is selected
        keys = iter(["b", "a", "n", "\x7f", "\x7f", "c", "h", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["apple", "banana", "cherry", "date"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is False
        assert idx is None  # No matches for "bch", so cancel is selected

    def test_filterable_menu_simulated_filter_clear(self):
        """Test FilterableMenu with simulated filter clearing."""
        # Create a key provider that types "ban", clears with Esc, then types "ch" then Enter
        keys = iter(["b", "a", "n", "\x1b", "\x1b", "c", "h", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["apple", "banana", "cherry", "date"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 2  # "cherry" is the third item in the original list

    def test_filterable_menu_simulated_navigation_with_filter(self):
        """Test FilterableMenu navigation with active filter."""
        # Create a key provider that types "a", navigates down, then Enter
        keys = iter(["a", "\x1b", "[", "B", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["apple", "banana", "cherry", "date"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        # Filter by "a" gives ["apple", "banana", "date"]
        # Navigate down selects "banana" which is index 1 in original list
        assert idx == 1

    def test_filterable_menu_simulated_complex_sequence(self):
        """Test FilterableMenu with complex input sequence."""
        # Create a key provider that:
        # 1. Types "a"
        # 2. Navigates down twice (to "date")
        # 3. Clears filter with Esc
        # 4. Navigates down to "banana"
        # 5. Selects with Enter
        keys = iter(
            [
                "a",  # Type "a"
                "\x1b",
                "[",
                "B",  # Down arrow
                "\x1b",
                "[",
                "B",  # Down arrow again
                "\x1b",
                "\x1b",  # Clear filter with double Esc
                "\x1b",
                "[",
                "B",  # Down arrow to "cherry"
                "\r",  # Enter
            ]
        )

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["apple", "banana", "cherry", "date"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert (
            idx == 1
        )  # "banana" is the second item in the original list after navigation


class TestFilterableMenuEdgeCases:
    """Test FilterableMenu edge cases."""

    def test_filterable_menu_with_empty_items(self):
        """Test FilterableMenu with empty item list."""
        menu = FilterableMenu("Test Menu", [], "Cancel")

        # Should handle empty list gracefully
        filtered = menu._filter_items()
        assert len(filtered) == 0

    def test_filterable_menu_with_single_item(self):
        """Test FilterableMenu with single item."""
        menu = FilterableMenu("Test Menu", ["only-item"], "Cancel")

        # Test with matching filter
        menu.filter_text = "only"
        filtered = menu._filter_items()
        assert len(filtered) == 1
        assert filtered[0][1] == "only-item"

        # Test with non-matching filter
        menu.filter_text = "xyz"
        filtered = menu._filter_items()
        assert len(filtered) == 0

    def test_filterable_menu_with_long_items(self):
        """Test FilterableMenu with long item texts."""
        long_items = [
            "very_long_item_name_that_exceeds_normal_length",
            "another_very_long_item_name_for_testing_purposes",
            "short",
        ]
        menu = FilterableMenu("Test Menu", long_items, "Cancel")

        # Test filtering with partial match on long items
        menu.filter_text = "very_long"
        filtered = menu._filter_items()
        assert len(filtered) == 2
        assert filtered[0][1] == long_items[0]
        assert filtered[1][1] == long_items[1]

    def test_filterable_menu_with_unicode_characters(self):
        """Test FilterableMenu with unicode characters."""
        unicode_items = ["café", "naïve", "résumé", "Zürich"]
        menu = FilterableMenu("Test Menu", unicode_items, "Cancel")

        # Test filtering with unicode
        menu.filter_text = "é"
        filtered = menu._filter_items()
        assert len(filtered) == 2
        assert filtered[0][1] == "café"
        assert filtered[1][1] == "résumé"


class TestFilterableMenuDisplayElements:
    """Test FilterableMenu display elements."""

    @patch("code_assistant_manager.menu.base.FilterableMenu._clear_screen")
    @patch("code_assistant_manager.menu.base.FilterableMenu._get_terminal_size")
    def test_filterable_menu_draw_filter_line(self, mock_terminal_size, mock_clear):
        """Test drawing of filter line."""
        mock_terminal_size.return_value = (80, 24)

        menu = FilterableMenu("Test Menu", ["item1", "item2"], "Cancel")

        # Test with empty filter
        menu.filter_text = ""
        # This would normally draw to stdout, but we're just ensuring it doesn't crash
        menu._draw_filter_line()

        # Test with filter text
        menu.filter_text = "test"
        menu._draw_filter_line()

    @patch("code_assistant_manager.menu.base.FilterableMenu._clear_screen")
    @patch("code_assistant_manager.menu.base.FilterableMenu._get_terminal_size")
    def test_filterable_menu_draw_no_matches(self, mock_terminal_size, mock_clear):
        """Test drawing when no matches are found."""
        mock_terminal_size.return_value = (80, 24)

        menu = FilterableMenu("Test Menu", ["item1", "item2"], "Cancel")

        # Clear filtered items to simulate no matches
        menu.filtered_items = []
        # This would normally draw to stdout, but we're just ensuring it doesn't crash
        menu._draw_menu_items(0)
