"""Tests for menu key provider functionality."""

from unittest.mock import patch

import pytest

from code_assistant_manager.menu.base import FilterableMenu, SimpleMenu


class TestSimpleMenuKeyProvider:
    """Test SimpleMenu with key_provider functionality."""

    def test_simple_menu_with_key_provider_selection(self):
        """Test SimpleMenu selection using key_provider."""
        # Create a key provider that simulates selecting the second option
        keys = iter(["\r"])  # Enter to select (first option is highlighted by default)

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = SimpleMenu(
            "Test Menu",
            ["Option 1", "Option 2", "Option 3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 0  # First option (0-indexed)

    def test_simple_menu_with_key_provider_navigation(self):
        """Test SimpleMenu navigation using key_provider."""
        # Create a key provider that simulates Down Arrow then Enter
        # Arrow sequences: '\x1b', '[', 'B'
        keys = iter(["\x1b", "[", "B", "\r"])  # Down arrow then Enter

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = SimpleMenu(
            "Test Menu",
            ["Option 1", "Option 2", "Option 3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 1  # Second option (0-indexed)

    def test_simple_menu_with_key_provider_cancel(self):
        """Test SimpleMenu cancellation using key_provider."""
        # Create a key provider that simulates navigating to cancel and selecting it
        # Navigate to cancel (3 down arrows for 3 items) then Enter
        keys = iter(["\x1b", "[", "B", "\x1b", "[", "B", "\x1b", "[", "B", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = SimpleMenu(
            "Test Menu", ["Option 1", "Option 2"], "Cancel", key_provider=key_provider
        )

        success, idx = menu.display()
        assert success is False
        assert idx is None

    def test_simple_menu_with_key_provider_escape_sequence(self):
        """Test SimpleMenu with escape sequences using key_provider."""
        # Create a key provider that simulates an incomplete escape sequence
        keys = iter(["\x1b", "x", "\r"])  # Incomplete escape, then Enter first option

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = SimpleMenu(
            "Test Menu", ["Option 1", "Option 2"], "Cancel", key_provider=key_provider
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 0  # First option selected

    def test_simple_menu_with_key_provider_none_return(self):
        """Test SimpleMenu when key_provider returns None."""

        # Create a key provider that returns None immediately
        def key_provider():
            return None

        menu = SimpleMenu(
            "Test Menu", ["Option 1", "Option 2"], "Cancel", key_provider=key_provider
        )

        # Should fall back to regular input, but in test mode we'll mock input
        with patch("builtins.input", return_value="1"):
            success, idx = menu.display()
            assert success is True
            assert idx == 0


class TestFilterableMenuKeyProvider:
    """Test FilterableMenu with key_provider functionality."""

    def test_filterable_menu_with_key_provider_selection(self):
        """Test FilterableMenu selection using key_provider."""
        # Create a key provider that simulates selecting the first option
        keys = iter(["\r"])  # Enter to select

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 0  # First option (0-indexed)

    def test_filterable_menu_with_key_provider_filtering(self):
        """Test FilterableMenu filtering using key_provider."""
        # Create a key provider that simulates typing "model2" then Enter
        keys = iter(["m", "o", "d", "e", "l", "2", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 1  # "model2" is the second option in the original list

    def test_filterable_menu_with_key_provider_backspace(self):
        """Test FilterableMenu backspace using key_provider."""
        # Create a key provider that types "model" then backspace twice then Enter to select "model1"
        keys = iter(["m", "o", "d", "e", "l", "\x7f", "\x7f", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert (
            idx == 0
        )  # After typing "model", backspacing twice gives us "mod" which matches all model1, model2, model3
        # Enter selects the first matching item which is "model1" at index 0

    def test_filterable_menu_with_key_provider_clear_filter(self):
        """Test FilterableMenu filter clearing using key_provider."""
        # Create a key provider that types "model2", clears filter with Esc, then selects first option
        keys = iter(["m", "o", "d", "e", "l", "2", "\x1b", "\x1b", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        assert idx == 0  # First option selected after clearing filter

    def test_filterable_menu_with_key_provider_navigation_filtered(self):
        """Test FilterableMenu navigation with filtered results using key_provider."""
        # Create a key provider that types "model", then navigates down, then Enter
        keys = iter(["m", "o", "d", "e", "l", "\x1b", "[", "B", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3", "other"],
            "Cancel",
            key_provider=key_provider,
        )

        success, idx = menu.display()
        assert success is True
        # After filtering by "model", we have 3 items, navigation goes to second item
        # The second item in filtered results is "model2" which is index 1 in original
        assert idx == 1

    def test_filterable_menu_with_key_provider_no_matches(self):
        """Test FilterableMenu with no matching results using key_provider."""
        # Create a key provider that types "xyz" (no matches), then Enter
        keys = iter(["x", "y", "z", "\r"])

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu",
            ["model1", "model2", "model3"],
            "Cancel",
            key_provider=key_provider,
        )

        # Should select cancel when there are no matches and Enter is pressed
        success, idx = menu.display()
        assert success is False
        assert idx is None

    def test_filterable_menu_with_key_provider_cancel(self):
        """Test FilterableMenu cancellation using key_provider."""
        # Create a key provider that navigates to cancel and selects it
        # Navigate down to cancel option then Enter
        keys = iter(
            [
                "\x1b",
                "[",
                "B",
                "\x1b",
                "[",
                "B",
                "\x1b",
                "[",
                "B",
                "\x1b",
                "[",
                "B",
                "\r",
            ]
        )

        def key_provider():
            try:
                return next(keys)
            except StopIteration:
                return None

        menu = FilterableMenu(
            "Test Menu", ["model1", "model2"], "Cancel", key_provider=key_provider
        )

        success, idx = menu.display()
        assert success is False
        assert idx is None


def make_provider(seq):
    """Helper function to create a key provider from a sequence."""
    it = iter(seq)
    return lambda: next(it, None)


def test_key_provider_helper_function():
    """Test the helper function for creating key providers."""
    provider = make_provider(["a", "b", "c"])
    assert provider() == "a"
    assert provider() == "b"
    assert provider() == "c"
    assert provider() is None  # End of sequence
