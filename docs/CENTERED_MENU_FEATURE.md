# Centered Menu UI Enhancement

## Overview

The Code Assistant Manager now features an enhanced user experience with centered, visually appealing menus for endpoint and model selection.

## Features

### Visual Enhancements
- **Centered Display**: Menus are automatically centered on the terminal screen
- **Color-Coded Elements**:
  - Cyan borders and frames
  - Blue bold titles
  - Green numbering
  - Yellow item text
- **Unicode Box Drawing**: Professional-looking borders using UTF-8 box-drawing characters
- **Responsive Design**: Automatically adapts to terminal width and height
- **Text Truncation**: Long items are intelligently truncated with ellipsis

### User Experience Improvements
- **Clear Visual Hierarchy**: Title, items, and prompts are clearly separated
- **Easy Selection**: Number-based selection with visual feedback
- **Confirmation Messages**: Selected items are displayed with a checkmark
- **Cancel/Skip Options**: Clear options to exit or skip selections

## Implementation

### Core Function

The `ai_display_centered_menu()` function in `ai_common.sh` provides the centered menu functionality:

```bash
ai_display_centered_menu "Menu Title" items_array "Cancel"
```

**Parameters:**
- `$1`: Title text to display at the top of the menu
- `$2`: Name of the array containing menu items
- `$3`: Text for the cancel/exit option (default: "Cancel")

**Returns:**
- Exit code `0` on successful selection
- Exit code `1` on cancel or invalid input
- Sets `AI_MENU_SELECTION` variable with the 0-based index of selected item

### Updated Functions

The following functions now use the centered menu:

#### 1. `ai_select_model()`
Displays a centered menu for model selection.

**Usage:**
```bash
ai_select_model MODELS_ARRAY "Select your model"
echo "Selected: $SELECTED_MODEL"
```

#### 2. `ai_select_endpoint()`
Displays a centered menu for endpoint selection with client filtering.

**Usage:**
```bash
ai_select_endpoint "claude"
echo "Selected endpoint: $ENDPOINT_NAME"
```

#### 3. `ai_select_model_or_skip()`
Displays a centered menu with a "Skip" option instead of "Cancel".

**Usage:**
```bash
ai_select_model_or_skip MODELS_ARRAY "Select model or skip"
if [ $? -eq 0 ]; then
  echo "Selected: $SELECTED_MODEL"
elif [ $? -eq 2 ]; then
  echo "Skipped"
fi
```

#### 4. `ai_select_two_models()`
Uses centered menus for selecting two models sequentially.

**Usage:**
```bash
ai_select_two_models MODELS_ARRAY "Select primary" "Select secondary"
echo "Primary: $SELECTED_MODEL_PRIMARY"
echo "Secondary: $SELECTED_MODEL_SECONDARY"
```

## Menu Layout

```
                    ╔═══════════════════════════════════════╗
                    ║         Select Your Model             ║
                    ╠═══════════════════════════════════════╣
                    ║  1) claude-3-5-sonnet-20241022       ║
                    ║  2) claude-3-opus-20240229           ║
                    ║  3) gpt-4o                           ║
                    ║  4) gemini-2.0-flash-exp             ║
                    ║  5) Cancel                           ║
                    ╚═══════════════════════════════════════╝

                    Enter selection [1-5]: _
```

## Technical Details

### Terminal Detection
- Automatically detects terminal dimensions using `tput`
- Falls back to 80x24 if terminal detection fails
- Calculates optimal centering based on content length

### Color Codes
The function uses ANSI escape codes for colors:
- `\033[0;34m` - Blue
- `\033[0;36m` - Cyan
- `\033[0;32m` - Green
- `\033[1;33m` - Yellow (Bold)
- `\033[1m` - Bold
- `\033[0m` - Reset

### Width Calculation
- Minimum width: 40 characters
- Maximum width: Terminal width - 10 characters
- Auto-adjusts based on longest menu item

### Height Calculation
- Automatically centers vertically based on terminal height
- Minimum top margin: 1 line
- Calculates space for title, borders, items, and prompt

## Backward Compatibility

The enhanced menus are fully backward compatible with existing code:
- All existing function signatures remain unchanged
- Return codes and variable names are consistent
- No breaking changes to CLI setup scripts

## Testing

### Test Script 1: Basic Menu Rendering
```bash
./test_menu_render.sh
```

### Test Script 2: Full Demo
```bash
./demo_centered_menu.sh
```

## Benefits

1. **Improved Readability**: Centered menus are easier to read and scan
2. **Professional Appearance**: Box-drawing characters and colors create a polished look
3. **Better Focus**: Clear visual separation helps users focus on the task
4. **Reduced Errors**: More intuitive interface reduces selection mistakes
5. **Enhanced UX**: Overall more pleasant and efficient user experience

## Future Enhancements

Potential improvements for future versions:
- Pagination for very long lists
- Search/filter functionality
- Mouse support (for compatible terminals)
- Keyboard shortcuts (arrow keys for navigation)
- Custom color themes
- Multi-column layout for wide terminals
