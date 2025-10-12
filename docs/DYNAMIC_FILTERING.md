# Dynamic Menu Filtering Feature

## Overview

The menu system in `code_assistant_manager/ui.py` now supports **dynamic filtering** that allows users to filter menu items in real-time by typing characters. This makes it much easier to find and select items from long lists.

## Features

### 1. Real-time Filtering
- As you type, the menu automatically filters to show only items that match your input
- Filtering is **case-insensitive**
- Substring matching - typing "gpt" will match "gpt-4", "gpt-5-mini", "gpt-11-copilot", etc.

### 2. Visual Feedback
- The filter text is displayed at the top of the menu: `Filter: gpt`
- When no filter is active, it shows: `Filter: (type to filter)`
- If no items match the filter, displays: `No matching items`

### 3. Navigation
- **Arrow Keys (↑/↓)**: Navigate through filtered items
- **Type characters**: Filter the list
- **Backspace**: Remove last character from filter
- **Esc**: Clear the entire filter and show all items
- **Enter**: Select the highlighted item

### 4. Smart Index Mapping
- When you select an item from the filtered list, it returns the **original index** from the unfiltered list
- This ensures that the calling code receives the correct item even when filtering is active

## Usage Example

```python
from code_assistant_manager.ui import display_centered_menu

models = [
    "gpt-4.1",
    "gpt-5-mini",
    "claude-3.5-sonnet",
    "gemini-2.0-flash-001",
    # ... more models
]

success, selected_idx = display_centered_menu(
    "Choose a model:",
    models,
    "Cancel"
)

if success and selected_idx is not None:
    print(f"Selected: {models[selected_idx]}")
else:
    print("Selection cancelled")
```

## User Workflow

1. **Launch the menu** - All items are displayed
2. **Start typing** - For example, type "gpt" to see only GPT models
3. **Refine the filter** - Continue typing to narrow down results (e.g., "gpt-4")
4. **Navigate** - Use arrow keys to highlight the desired item
5. **Select** - Press Enter to confirm selection
6. **Clear filter** - Press Esc to clear the filter and see all items again
7. **Cancel** - Navigate to "Cancel" option or press Esc when no filter is active

## Benefits

- **Faster Selection**: No need to scroll through dozens of items
- **Better UX**: Intuitive keyboard-driven interface
- **Flexible**: Works with any list of strings
- **Backward Compatible**: Still supports direct numeric input as fallback

## Keyboard Shortcuts

| Key(s) | Action |
|--------|--------|
| **a-z, 0-9, etc.** | Add character to filter |
| **↑** (Up Arrow) | Move selection up |
| **↓** (Down Arrow) | Move selection down |
| **Backspace** | Remove last filter character |
| **Esc** | Clear entire filter |
| **Enter** | Select highlighted item |
| **1-99** | Direct numeric selection (fallback) |

## Common Filter Patterns

| Filter | Matches |
|--------|---------|
| `gpt` | All GPT models |
| `claude` | All Claude models |
| `gemini` | All Gemini models |
| `mini` | All models with "mini" (any vendor) |
| `4o` | GPT-4o variants |
| `sonnet` | Claude Sonnet models |
| `turbo` | GPT Turbo models |
| `embedding` | Text embedding models |
| `2024` | Models with 2024 in version |

## Example Workflows

### Quick Filter and Select
```
1. Type filter text
2. Press Enter (selects first match)
```

### Careful Selection
```
1. Type filter text
2. Use ↑/↓ to review options
3. Press Enter when highlighted on desired item
```

### Browse Then Filter
```
1. Look at all items first
2. Type partial name of what you want
3. Select from filtered results
```

### Iterate Until Found
```
1. Type initial filter
2. See results
3. Refine filter (add more characters)
4. OR use Backspace to try different filter
5. Select when found
```

## Tips & Best Practices

✅ **Case-insensitive**: `GPT`, `gpt`, and `Gpt` all work the same

✅ **Substring match**: `mini` matches both `gpt-5-mini` and `o3-mini`

✅ **Fast filtering**: Results update instantly as you type

✅ **Visual feedback**: Current filter always shown at top of menu

✅ **Safe navigation**: Can't select item that doesn't exist

✅ **No wildcards needed**: Just type the text you're looking for

## Troubleshooting

**Q: I typed something and see "No matching items"**
A: Your filter doesn't match any items. Press Backspace or Esc to adjust.

**Q: Arrow keys aren't working**
A: Make sure you're not in a filter. Clear filter with Esc first, or use numeric selection.

**Q: How do I go back to seeing all items?**
A: Press Esc to clear the filter, or use Backspace to remove characters.

**Q: Can I use wildcards like * or ??**
A: Not currently - just type the text you want to match. It works as substring match.

**Q: Is the filter case-sensitive?**
A: No! Type in any case and it will match.

## Technical Details

### Filter Implementation

The filtering logic uses Python's substring matching:

```python
def filter_items(filter_text: str) -> List[Tuple[int, str]]:
    """Filter items based on filter text (case-insensitive)."""
    if not filter_text:
        return [(i, item) for i, item in enumerate(original_items)]

    filter_lower = filter_text.lower()
    return [(i, item) for i, item in enumerate(original_items)
            if filter_lower in item.lower()]
```

### Index Mapping

The filtered list contains tuples of `(original_index, item_text)`, ensuring that selections always map back to the correct position in the original list.

### Menu Redrawing

The menu is redrawn on every keystroke to show:
- Updated filter text
- Updated filtered items
- Updated highlighting

This provides immediate visual feedback for a smooth user experience.

## Implementation Details

**File**: `code_assistant_manager/ui.py`
**Function**: `display_centered_menu()`
**Tests**: 16 new tests in `tests/test_filtering.py`
**Backward Compatibility**: 100% - all existing tests pass

## Future Enhancements

Potential improvements for future versions:
- Fuzzy matching (e.g., "gpt4" matches "gpt-4o")
- Multiple filter terms (e.g., "gpt mini" matches items with both words)
- Regular expression support
- Filter history (up arrow to recall previous filters)
- Case-sensitive filtering option
