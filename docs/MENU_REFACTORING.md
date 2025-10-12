# Menu System Refactoring

This document describes the refactoring of the menu system into a class-based architecture.

## Overview

The menu functionality has been refactored from standalone functions into a class hierarchy, making it easier to create custom menus and extend existing functionality.

## Changes Made

### New File: `code_assistant_manager/menu.py`

Created a new module containing the menu class hierarchy:

1. **`Menu` (Abstract Base Class)**
   - Base class for all menu implementations
   - Provides common functionality for terminal UI
   - Defines abstract methods that subclasses must implement
   - Includes helper methods for drawing borders, items, and handling input

2. **`SimpleMenu`**
   - Basic menu with arrow key navigation
   - No filtering capability
   - Suitable for small lists of options

3. **`FilterableMenu`**
   - Advanced menu with dynamic filtering
   - Users can type to filter items in real-time
   - Supports Esc key to clear filter
   - Preserves original indices when returning selections

### Updated: `code_assistant_manager/ui.py`

- Simplified to use the new menu classes
- `display_centered_menu()` now uses `FilterableMenu`
- `display_simple_menu()` now uses `SimpleMenu`
- Maintains backward compatibility with existing API
- Added back `get_terminal_size()` and `clear_screen()` for compatibility
- Re-exports `Colors` from menu module

### Updated: `code_assistant_manager/__init__.py`

- Exports new menu classes: `Menu`, `SimpleMenu`, `FilterableMenu`
- Exports `Colors` class
- Maintains all existing exports for backward compatibility

## Benefits

### 1. Extensibility
Custom menus can be created by inheriting from the `Menu` base class:

```python
from code_assistant_manager.menu import Menu

class MyCustomMenu(Menu):
    def _draw_menu_items(self, highlighted_idx: int = -1):
        # Custom item rendering
        pass

    def _calculate_menu_height(self) -> int:
        # Calculate menu height
        return len(self.items) + 5

    def _get_prompt_text(self) -> str:
        return "Select an option: "

    def display(self):
        # Display logic
        pass
```

### 2. Code Reusability
Common functionality is centralized in the base class:
- Border drawing
- Item rendering
- Input handling
- Terminal size calculations
- Centering logic

### 3. Separation of Concerns
Each menu type focuses on its specific behavior:
- `SimpleMenu`: Basic navigation
- `FilterableMenu`: Filtering + navigation
- Custom classes: Whatever you need

### 4. Testing
Easier to test individual components:
- Can mock `key_provider` for testing keyboard input
- Can test menu classes in isolation
- Better code coverage

### 5. Maintainability
- Less code duplication
- Clear inheritance hierarchy
- Well-defined interfaces
- Easier to add new menu types

## Backward Compatibility

All existing code continues to work without changes:

```python
# Old code still works
from code_assistant_manager.ui import display_centered_menu

success, idx = display_centered_menu("Title", items)
```

New code can use classes directly:

```python
# New way - using classes
from code_assistant_manager.menu import FilterableMenu

menu = FilterableMenu("Title", items)
success, idx = menu.display()
```

## Examples

See the `examples/` directory for:
- `custom_menu_example.py` - Demonstrates creating custom menu classes
- `README.md` - Documentation on using and extending menus

## Test Coverage

All existing tests pass, confirming backward compatibility:
- `tests/test_ui.py` - UI function tests
- `tests/test_filtering.py` - Filter functionality tests
- `tests/test_ui_key_provider.py` - Key provider tests
- `tests/test_ui_numeric_fallback.py` - Numeric input tests
- `tests/test_endpoints.py` - Endpoint selection tests

Total: 76 tests covering menu and UI functionality.

## Migration Guide

### For Users
No changes needed! Existing code continues to work.

### For Developers
To create a custom menu:

1. Inherit from `Menu` base class
2. Implement required abstract methods:
   - `_calculate_menu_height()`
   - `_draw_menu_items(highlighted_idx)`
   - `_get_prompt_text()`
   - `display()`
3. Optionally override helper methods for custom behavior

See `examples/custom_menu_example.py` for complete examples.

## Future Enhancements

Possible future improvements:
- Menu with multi-select capability
- Menu with nested submenus
- Menu with custom key bindings
- Menu with icons/emojis
- Menu with pagination for very long lists
- Menu with search highlighting
- Menu with categorized sections
