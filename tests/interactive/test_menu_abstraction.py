"""Tests for menu abstraction and inheritance."""

from abc import ABC, abstractmethod
from unittest.mock import patch

import pytest

from code_assistant_manager.menu.base import FilterableMenu, Menu, SimpleMenu


class TestMenuAbstraction:
    """Test Menu base class abstraction."""

    def test_menu_is_abstract(self):
        """Test that Menu is an abstract base class."""
        # Should not be able to instantiate abstract Menu class
        with pytest.raises(TypeError):
            Menu("Title", ["item1", "item2"])

    def test_menu_abstract_methods(self):
        """Test that Menu has the required abstract methods."""
        # Check that the abstract methods are defined
        assert hasattr(Menu, "_draw_menu_items")
        assert hasattr(Menu, "_get_prompt_text")
        assert hasattr(Menu, "_calculate_menu_height")
        assert hasattr(Menu, "display")

        # Check that they are abstract methods by checking __abstractmethods__ set
        assert "_draw_menu_items" in Menu.__abstractmethods__
        assert "_get_prompt_text" in Menu.__abstractmethods__
        assert "_calculate_menu_height" in Menu.__abstractmethods__
        assert "display" in Menu.__abstractmethods__


class TestSimpleMenuImplementation:
    """Test SimpleMenu implementation of abstract methods."""

    def test_simple_menu_instantiation(self):
        """Test that SimpleMenu can be instantiated."""
        # Should be able to instantiate concrete implementation
        menu = SimpleMenu("Test Menu", ["item1", "item2"])
        assert isinstance(menu, Menu)
        assert isinstance(menu, SimpleMenu)

    def test_simple_menu_implements_abstract_methods(self):
        """Test that SimpleMenu implements all required abstract methods."""
        menu = SimpleMenu("Test Menu", ["item1", "item2"])

        # Should have implementations for all abstract methods
        assert callable(menu._draw_menu_items)
        assert callable(menu._get_prompt_text)
        assert callable(menu._calculate_menu_height)
        assert callable(menu.display)

    def test_simple_menu_draw_menu_items(self):
        """Test SimpleMenu _draw_menu_items method."""
        menu = SimpleMenu("Test Menu", ["item1", "item2"])

        # Test that it can be called without error
        with patch("builtins.print"):
            menu._draw_menu_items()

    def test_simple_menu_get_prompt_text(self):
        """Test SimpleMenu _get_prompt_text method."""
        menu = SimpleMenu("Test Menu", ["item1", "item2"])
        prompt = menu._get_prompt_text()
        assert isinstance(prompt, str)
        assert "↑/↓" in prompt
        assert "Enter" in prompt

    def test_simple_menu_calculate_menu_height(self):
        """Test SimpleMenu _calculate_menu_height method."""
        menu = SimpleMenu("Test Menu", ["item1", "item2", "item3"])
        height = menu._calculate_menu_height()
        assert isinstance(height, int)
        assert height > 0
        # Should be items + 5 (items + title + borders + prompt)
        assert height == 8

    @patch("code_assistant_manager.menu.base.SimpleMenu._clear_screen")
    def test_simple_menu_display(self, mock_clear):
        """Test SimpleMenu display method."""
        menu = SimpleMenu("Test Menu", ["item1", "item2"])

        # Test with mocked input
        with patch("builtins.input", return_value="1"):
            success, idx = menu.display()
            assert success is True
            assert idx == 0


class TestFilterableMenuImplementation:
    """Test FilterableMenu implementation of abstract methods."""

    def test_filterable_menu_instantiation(self):
        """Test that FilterableMenu can be instantiated."""
        # Should be able to instantiate concrete implementation
        menu = FilterableMenu("Test Menu", ["item1", "item2"])
        assert isinstance(menu, Menu)
        assert isinstance(menu, FilterableMenu)

    def test_filterable_menu_inherits_from_simple_menu(self):
        """Test that FilterableMenu inherits from Menu."""
        assert issubclass(FilterableMenu, Menu)

    def test_filterable_menu_implements_abstract_methods(self):
        """Test that FilterableMenu implements all required abstract methods."""
        menu = FilterableMenu("Test Menu", ["item1", "item2"])

        # Should have implementations for all abstract methods
        assert callable(menu._draw_menu_items)
        assert callable(menu._get_prompt_text)
        assert callable(menu._calculate_menu_height)
        assert callable(menu.display)

    def test_filterable_menu_draw_menu_items(self):
        """Test FilterableMenu _draw_menu_items method."""
        menu = FilterableMenu("Test Menu", ["item1", "item2"])

        # Test that it can be called without error
        with patch("builtins.print"):
            menu._draw_menu_items()

    def test_filterable_menu_get_prompt_text(self):
        """Test FilterableMenu _get_prompt_text method."""
        menu = FilterableMenu("Test Menu", ["item1", "item2"])
        prompt = menu._get_prompt_text()
        assert isinstance(prompt, str)
        assert "↑/↓" in prompt
        assert "type to filter" in prompt
        assert "Enter" in prompt

    def test_filterable_menu_calculate_menu_height(self):
        """Test FilterableMenu _calculate_menu_height method."""
        menu = FilterableMenu("Test Menu", ["item1", "item2", "item3"])
        height = menu._calculate_menu_height()
        assert isinstance(height, int)
        assert height > 0
        # Should be items + 6 (items + title + borders + prompt + filter line)
        assert height == 9

    @patch("code_assistant_manager.menu.base.FilterableMenu._clear_screen")
    def test_filterable_menu_display(self, mock_clear):
        """Test FilterableMenu display method."""
        menu = FilterableMenu("Test Menu", ["item1", "item2"])

        # Test with mocked input
        with patch("builtins.input", return_value="1"):
            success, idx = menu.display()
            assert success is True
            assert idx == 0


class TestMenuInheritanceHierarchy:
    """Test the inheritance hierarchy of menu classes."""

    def test_menu_inheritance_structure(self):
        """Test that menu classes have the correct inheritance structure."""
        # Menu should be abstract base class
        assert hasattr(Menu, "__abstractmethods__")

        # SimpleMenu should inherit from Menu
        assert issubclass(SimpleMenu, Menu)

        # FilterableMenu should inherit from Menu
        assert issubclass(FilterableMenu, Menu)

        # SimpleMenu and FilterableMenu should not be the same class
        assert SimpleMenu is not FilterableMenu

    def test_menu_method_override(self):
        """Test that subclasses properly override abstract methods."""
        simple_menu = SimpleMenu("Test", ["item"])
        filterable_menu = FilterableMenu("Test", ["item"])

        # Methods should be different implementations
        assert simple_menu._draw_menu_items != filterable_menu._draw_menu_items
        assert simple_menu._get_prompt_text != filterable_menu._get_prompt_text
        assert (
            simple_menu._calculate_menu_height != filterable_menu._calculate_menu_height
        )


class TestMenuPolymorphism:
    """Test polymorphic behavior of menu classes."""

    def test_menu_polymorphic_usage(self):
        """Test that menus can be used polymorphically."""
        simple_menu = SimpleMenu("Simple Menu", ["item1", "item2"])
        filterable_menu = FilterableMenu("Filterable Menu", ["item1", "item2"])

        # Both should be instances of Menu
        menus = [simple_menu, filterable_menu]
        for menu in menus:
            assert isinstance(menu, Menu)

            # All should have the required methods
            assert hasattr(menu, "_draw_menu_items")
            assert hasattr(menu, "_get_prompt_text")
            assert hasattr(menu, "_calculate_menu_height")
            assert hasattr(menu, "display")

    @patch("code_assistant_manager.menu.base.SimpleMenu._clear_screen")
    @patch("code_assistant_manager.menu.base.FilterableMenu._clear_screen")
    def test_menu_polymorphic_behavior(self, mock_clear1, mock_clear2):
        """Test polymorphic behavior in action."""
        menus = [
            SimpleMenu("Simple Menu", ["item1", "item2"]),
            FilterableMenu("Filterable Menu", ["item1", "item2"]),
        ]

        for menu in menus:
            # All should be able to display (with mocked input)
            with patch("builtins.input", return_value="1"):
                success, idx = menu.display()
                assert success is True
                assert idx == 0


class TestMenuInterfaceConsistency:
    """Test that menu interfaces are consistent."""

    def test_menu_interface_consistency(self):
        """Test that all menu classes have consistent interfaces."""
        # Test constructor signatures
        simple_menu = SimpleMenu("Title", ["item1", "item2"], "Cancel", 3)
        filterable_menu = FilterableMenu("Title", ["item1", "item2"], "Cancel", 3)

        # Both should have the same basic attributes
        assert hasattr(simple_menu, "title")
        assert hasattr(filterable_menu, "title")
        assert hasattr(simple_menu, "items")
        assert hasattr(filterable_menu, "items")
        assert hasattr(simple_menu, "cancel_text")
        assert hasattr(filterable_menu, "cancel_text")
        assert hasattr(simple_menu, "max_attempts")
        assert hasattr(filterable_menu, "max_attempts")

    def test_menu_return_value_consistency(self):
        """Test that menu methods return consistent types."""
        simple_menu = SimpleMenu("Test", ["item1", "item2"])
        filterable_menu = FilterableMenu("Test", ["item1", "item2"])

        # display() method should return consistent tuple format
        with patch("builtins.input", return_value="1"):
            simple_result = simple_menu.display()
            filterable_result = filterable_menu.display()

            assert isinstance(simple_result, tuple)
            assert isinstance(filterable_result, tuple)
            assert len(simple_result) == 2
            assert len(filterable_result) == 2

            # First element should be boolean
            assert isinstance(simple_result[0], bool)
            assert isinstance(filterable_result[0], bool)

            # Second element should be int or None
            assert isinstance(simple_result[1], (int, type(None)))
            assert isinstance(filterable_result[1], (int, type(None)))
