# Interactive Menu Tests

This directory contains tests for the interactive menu system used by Code Assistant Manager tools.

## Test Structure

1. **test_menu_navigation.py** - Basic tests for menu navigation using pexpect
2. **test_interactive_menus.py** - Comprehensive tests for interactive menu functionality
3. **test_tool_integration.py** - Integration tests for tools with mocked interactive components

## Running Tests

```bash
# Run all interactive tests
cd tests/interactive
python3 -m pytest -v

# Run specific test file
python3 -m pytest test_tool_integration.py -v

# Run specific test
python3 -m pytest test_tool_integration.py::TestToolIntegration::test_codex_tool_non_interactive -v
```

## Test Approaches

### 1. Non-Interactive Mode Testing
Tests use the `CODE_ASSISTANT_MANAGER_NONINTERACTIVE=1` environment variable to bypass interactive menus and automatically select default options.

### 2. Key Provider Testing
Menu functions accept a `key_provider` parameter that can be used to programmatically control menu selections during testing.

### 3. Mock-Based Testing
Tool methods are tested with mocked menu functions to verify integration without actual user interaction.

## Writing New Tests

### For Menu Functionality
```python
def key_provider():
    return '1'  # Select first option

success, idx = display_simple_menu(
    "Test Menu",
    ["Option 1", "Option 2"],
    "Cancel",
    key_provider=key_provider
)
```

### For Tool Integration
```python
# Set non-interactive mode
os.environ['CODE_ASSISTANT_MANAGER_NONINTERACTIVE'] = '1'

# Mock dependencies
with patch('code_assistant_manager.tools.base.EndpointManager') as mock_endpoint_manager:
    # Configure mocks
    mock_em_instance = MagicMock()
    mock_endpoint_manager.return_value = mock_em_instance
    mock_em_instance.select_endpoint.return_value = (True, "test_endpoint")

    # Run tool
    tool = CodexTool(config)
    result = tool.run([])
```

## Test Requirements

- `pexpect` - For process interaction testing
- `pytest` - Test framework
- `unittest.mock` - For mocking dependencies
