# Arrow Key Navigation Feature

## Overview

The menu selection system now supports two methods of input:

1. **Direct Number Input** - Type the number and press Enter
2. **Arrow Key Navigation** - Use ↑/↓ arrows to highlight and Enter to select

## How It Works

### Direct Number Input (Original Method)

Simply type the number corresponding to your choice and press Enter:

```
Enter selection [1-39] or use ↑↓ arrows: 5
```

### Arrow Key Navigation (New Method)

1. Use the **↑ (Up Arrow)** to move highlight up
2. Use the **↓ (Down Arrow)** to move highlight down
3. Press **Enter** to select the highlighted option

The currently highlighted option will be shown with reverse video (inverted colors).

### Seamless Switching Between Methods

Users can now freely switch between input methods during the same interaction:
- Start with arrow keys, then switch to typing numbers
- Start typing numbers, then switch to using arrow keys
- Switch back and forth as needed

When switching from typing numbers to arrow keys, any typed numbers are automatically cleared and erased from the prompt line.

## Visual Feedback

When using arrow keys, the selected menu item will be highlighted:

```
╔════════════════════════════════════════════════════╗
║              Choose model for Codex:               ║
╠════════════════════════════════════════════════════╣
║  1) gpt-4.1                                        ║
║  2) gpt-5-mini                                     ║
║  3) █████████████████████████████████████         ║  ← Highlighted
║  4) gpt-3.5-turbo                                  ║
║  5) Cancel                                         ║
╚════════════════════════════════════════════════════╝
```

## Implementation Details

### Key Technical Features

- **Seamless Switching**: Users can freely switch between arrow keys and direct number input during the same interaction
- **Real-time Highlighting**: Menu items are redrawn with highlighting as you navigate
- **Boundary Protection**: Cannot scroll above first item or below last item
- **Terminal Compatibility**: Falls back to simple input if terminal doesn't support interactive features
- **Escape Sequence Handling**: Properly handles ANSI escape sequences for arrow keys
- **Input Buffer Management**: Automatically clears typed numbers when switching to arrow key navigation

### Escape Sequences

- `\x1b[A` - Up Arrow
- `\x1b[B` - Down Arrow
- `\x1b` - Escape key (start of sequence)

### Terminal Control

- `tput sc` - Save cursor position
- `tput rc` - Restore cursor position
- `tput cup` - Move cursor to specific position
- `\033[7m` - Reverse video (highlighting)
- `\033[27m` - Normal video (unhighlight)

## Testing

Run the test script to try out the arrow key navigation:

```bash
./test_arrow_navigation.sh
```

## Compatibility

- **Bash 4.0+**: Required for nameref support
- **Interactive Terminal**: Arrow keys only work in interactive terminals (TTY)
- **Fallback Mode**: Non-interactive environments automatically use direct input mode

## Files Modified

- `ai_common.sh` - Enhanced `ai_display_centered_menu()` function
  - Added arrow key detection and handling
  - Added menu redraw with highlighting
  - Added mode switching between arrow keys and direct input
  - Added RED color code for error messages

## Usage Example

```bash
# In any script that uses ai_display_centered_menu
source ai_common.sh

declare -a MY_OPTIONS=("Option 1" "Option 2" "Option 3")

if ai_display_centered_menu "Select an option:" MY_OPTIONS "Cancel"; then
    echo "Selected: ${MY_OPTIONS[$AI_MENU_SELECTION]}"
fi
```

The user can now:
- Type `1`, `2`, or `3` and press Enter
- Use arrow keys to highlight and press Enter
- Type `4` or arrow to "Cancel" and press Enter
- **Switch between methods during the same interaction** - Start with arrow keys then type numbers, or start typing numbers then use arrow keys

## Future Enhancements

Potential improvements for future versions:

- Page Up/Page Down for long lists
- Home/End keys to jump to first/last item
- Type-ahead search (type letters to jump to matching items)
- Mouse support for click selection
- Customizable key bindings
