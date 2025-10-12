# Menu Examples

This directory contains examples of how to use and extend the menu system in Code Assistant Manager.

## Custom Menu Example

The `custom_menu_example.py` demonstrates how to create custom menu classes by inheriting from the `Menu` base class.

### Running the Example

```bash
python examples/custom_menu_example.py
```

### Custom Menu Classes

#### 1. ColoredMenu
A menu that displays items with alternating colors (yellow, green, cyan, blue).

```python
from code_assistant_manager.menu import Menu, Colors

class ColoredMenu(Menu):
    """A custom menu that displays items with different colors."""

    def _draw_menu_items(self, highlighted_idx: int = -1):
        # Custom implementation with alternating colors
        ...
```

#### 2. NumberedPrefixMenu
A menu that adds item numbers as prefixes in the display text.

```python
class NumberedPrefixMenu(Menu):
    """A custom menu that adds item numbers to the display."""

    def _draw_menu_items(self, highlighted_idx: int = -1):
        # Add [N] prefix to each item
        ...
```

## Using Built-in Menu Classes

### SimpleMenu
A basic menu with arrow key navigation but no filtering.

```python
from code_assistant_manager.menu import SimpleMenu

menu = SimpleMenu(
    title="Select an Option",
    items=["Option 1", "Option 2", "Option 3"],
    cancel_text="Cancel"
)
success, idx = menu.display()
```

### FilterableMenu
A menu with dynamic filtering capability. Users can type to filter items.

```python
from code_assistant_manager.menu import FilterableMenu

menu = FilterableMenu(
    title="Select a Model",
    items=["gpt-4", "gpt-3.5-turbo", "claude-3", "claude-2"],
    cancel_text="Cancel"
)
success, idx = menu.display()
```

## Creating Your Own Menu Class

To create a custom menu, inherit from `Menu` and implement these abstract methods:

1. **`_calculate_menu_height()`** - Calculate the height of your menu
2. **`_draw_menu_items(highlighted_idx)`** - Draw the menu items
3. **`_get_prompt_text()`** - Return the prompt text for user input
4. **`display()`** - Handle the display and user interaction logic

Optional methods you can override:

- **`_handle_navigation_key(char)`** - Custom navigation key handling
- **`_handle_selection()`** - Custom selection handling
- **`_draw_menu(highlighted_idx)`** - Complete menu drawing logic

### Example Template

```python
from code_assistant_manager.menu import Menu
from typing import Tuple, Optional

class MyCustomMenu(Menu):
    """My custom menu implementation."""

    def _calculate_menu_height(self) -> int:
        # Calculate and return menu height
        return len(self.items) + 5

    def _draw_menu_items(self, highlighted_idx: int = -1):
        # Draw menu items with custom styling
        for i, item in enumerate(self.items):
            # Your custom drawing logic here
            pass

    def _get_prompt_text(self) -> str:
        return "Your custom prompt: "

    def display(self) -> Tuple[bool, Optional[int]]:
        # You can either implement custom display logic
        # or reuse SimpleMenu or FilterableMenu's display method
        from code_assistant_manager.menu import SimpleMenu
        return SimpleMenu.display(self)
```

## Menu Base Class Properties

When creating a custom menu, you have access to these properties:

- `self.title` - Menu title
- `self.items` - List of menu items
- `self.cancel_text` - Text for cancel option
- `self.max_attempts` - Maximum input attempts
- `self.key_provider` - Optional key provider (for testing)
- `self.selected_idx` - Currently selected index
- `self.term_width` - Terminal width
- `self.term_height` - Terminal height
- `self.max_item_len` - Calculated menu width
- `self.left_margin` - Left margin for centering

## Helper Methods Available

- `self._draw_border_top()` - Draw top border
- `self._draw_border_bottom()` - Draw bottom border
- `self._draw_separator()` - Draw horizontal separator
- `self._draw_title()` - Draw menu title
- `self._draw_item(num, item, is_highlighted)` - Draw a single item
- `self._draw_cancel_option(is_highlighted)` - Draw cancel option
- `self._get_key()` - Get a single key from user
- `self._clear_screen()` - Clear the terminal
- `self._redraw_with_prompt()` - Redraw menu with prompt
