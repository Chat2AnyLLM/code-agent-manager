# Code Assistant Manager Developer Guide

This guide provides comprehensive documentation for developers who want to contribute to or extend the Code Assistant Manager project.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Code Structure](#code-structure)
4. [Adding New Tools](#adding-new-tools)
5. [Configuration System](#configuration-system)
6. [Testing](#testing)
7. [Security Considerations](#security-considerations)
8. [Performance Optimization](#performance-optimization)
9. [Contributing](#contributing)

## Project Overview

Code Assistant Manager is a Python-based command-line interface that provides unified access to various AI providers (Claude, Codex, Qwen, etc.) with interactive model selection and endpoint configuration. The project aims to provide a consistent and secure way to interact with different AI services through a single interface.

Key features:
- Interactive model selection with dynamic filtering
- Centralized configuration management
- Secure API key handling
- Extensible tool framework
- Comprehensive test suite

## Architecture

The project follows a modular architecture with the following key components:

### Core Components

1. **CLI Interface (`code_assistant_manager/cli/`)**
   - **Main Entry Point (`app.py`)**: Typer-based CLI with sub-apps for different functionality
   - **Command Classes (`base_commands.py`)**: Standardized base classes for consistent CLI behavior
     - `BaseCommand`: Common functionality, error handling, logging
     - `AppAwareCommand`: Commands that work with AI apps
     - `PluginCommand`: Plugin-specific operations
     - `PromptCommand`: Prompt management operations
   - **Sub-Apps**: Modular command groups (agents, plugins, prompts, skills, MCP)
   - **Options & Utils**: Shared CLI utilities and option definitions

2. **Configuration Management (`code_assistant_manager/config.py`)**
   - JSON-based configuration parsing
   - Endpoint configuration management
   - Environment variable integration
   - Configuration validation

3. **MCP System (`code_assistant_manager/mcp/`)**
   - **Base Classes**: Common MCP functionality and client implementations
   - **Client Implementations**: Tool-specific MCP clients (Claude, Copilot, etc.)
   - **Registry System**: MCP server registry and management
   - **Installation System**: Automated MCP server installation and management

4. **Prompts System (`code_assistant_manager/prompts.py`)**
   - Centralized prompt storage and management
   - Multi-level support (user, project, Copilot-specific)
   - Sync functionality across different AI assistants
   - Template system for reusable prompt components

5. **Plugin System (`code_assistant_manager/plugins.py`)**
   - Marketplace-based plugin distribution
   - Repository management for plugin sources
   - Installation and management across AI assistants
   - Version compatibility checking

### CLI Architecture Patterns

#### Command Structure
```python
# New standardized pattern using base classes
class MyCommand(BaseCommand):
    def execute(self) -> int:
        self.log_command_start("my_command")
        try:
            # Command logic here
            self.show_success("Operation completed")
            return 0
        except Exception as e:
            self.handle_error(e, "Command failed")
            return 1
```

#### Error Handling
- Consistent error messages with color coding
- Structured logging for debugging
- User-friendly error descriptions
- Automatic cleanup on failures

#### Validation
- Input validation with descriptive error messages
- Type checking and constraint validation
- Choice validation for enumerated options
- File/path existence checking

### Recent Improvements

#### Code Quality Enhancements
- **Complexity Monitoring**: CI pipeline checks cyclomatic complexity and maintainability index
- **File Size Limits**: Automated checks ensure files stay under 500 lines
- **Security Audits**: Regular scanning for command injection vulnerabilities
- **Test Coverage**: Comprehensive test suite with helper functions for CLI testing

#### Refactoring Completed
- **Monolithic Function Breakdown**: `show_live_prompt()` split into focused helper functions
- **MCP Client Consolidation**: Reduced duplication in client implementations
- **Base Command Classes**: Standardized CLI command patterns
- **Helper Function Extraction**: Common functionality moved to reusable utilities

## Code Structure

```
code-assistant-manager/
├── code_assistant_manager/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py                 # Main Typer app with sub-apps
│   │   ├── base_commands.py       # Standardized command base classes
│   │   ├── commands.py            # Legacy command definitions
│   │   ├── option_utils.py        # Shared CLI utilities
│   │   ├── options.py             # Common CLI option definitions
│   │   ├── prompts_commands.py    # Prompt management commands
│   │   ├── plugin_commands.py     # Plugin command orchestration
│   │   ├── plugins/               # Plugin subcommand modules
│   │   │   ├── plugin_discovery_commands.py
│   │   │   ├── plugin_install_commands.py
│   │   │   └── plugin_marketplace_commands.py
│   │   └── skills_commands.py     # Skills management commands
│   ├── mcp/
│   │   ├── base.py               # MCP base classes and utilities
│   │   ├── base_client.py        # MCP client base class
│   │   ├── clients.py            # Individual MCP client implementations
│   │   └── [tool]_client.py      # Tool-specific MCP clients
│   ├── config.py                 # Configuration management
│   ├── endpoints.py              # Endpoint handling
│   ├── prompts.py                # Prompt storage and sync logic
│   ├── plugins.py                # Plugin system core
│   └── tools.py                  # Tool implementations
├── docs/                         # Documentation
├── scripts/                      # Utility scripts (file size checks, etc.)
├── tests/                        # Comprehensive test suite
└── .github/workflows/            # CI/CD pipelines with quality checks
```

## Adding New CLI Commands

To add a new CLI command, follow the standardized patterns using the base command classes:

### Using Base Command Classes

```python
from code_assistant_manager.cli.base_commands import BaseCommand, AppAwareCommand

class MyNewCommand(AppAwareCommand):
    """Example command using the standardized base class."""

    def execute(self) -> int:
        """Execute the command with proper error handling and logging."""
        self.log_command_start("my_new_command")

        # Validate inputs
        app_type = self.resolve_app_type(self.app_type_option)
        self.validate_app_installed(app_type)

        try:
            # Command logic here
            result = self.perform_operation(app_type)

            self.show_success(f"Operation completed for {app_type}")
            return 0

        except Exception as e:
            self.handle_error(e, f"Failed to execute command for {app_type}")
            return 1

    def perform_operation(self, app_type: str) -> bool:
        """Actual command implementation."""
        # Implementation here
        pass
```

### Registering Commands

Add the command to the appropriate CLI module and register it in the app:

```python
# In your command module
from code_assistant_manager.cli.base_commands import create_command_handler

@prompt_app.command("my-command")
def my_command_handler(
    param1: str = typer.Option(..., help="Parameter description"),
    app_type: str = typer.Option("claude", help="App type"),
) -> None:
    """Command docstring."""
    command = MyNewCommand()
    exit_code = command.execute(param1=param1, app_type=app_type)
    raise typer.Exit(exit_code)
```

### Error Handling Patterns

- Use `self.handle_error()` for exceptions that should terminate the command
- Use `self.show_warning()` for non-critical issues that should be displayed but allow continuation
- Use `self.show_success()` for successful operations
- All logging is automatically handled by the base classes

To add a new tool to Code Assistant Manager, follow these steps:

### 1. Create the Tool Class

Extend the `CLITool` base class in `code_assistant_manager/tools.py`:

```python
class NewTool(CLITool):
    """Description of the new tool."""

    command_name = "newtool"
    tool_key = "newtool-key"
    install_description = "New Tool Description"

    def run(self, args: List[str] = []) -> int:
        """Run the new tool."""
        # Implementation here
        pass
```

### 2. Register the Tool

The tool is automatically registered through class inheritance. The `get_registered_tools()` function will discover it.

### 3. Add CLI Entry Point

Add the entry point function in `code_assistant_manager/cli.py`:

```python
def newtool_main():
    """Entry point for 'newtool' command."""
    sys.argv.insert(1, 'newtool')
    sys.exit(main())
```

### 4. Update setup.py

Add the console script entry point in `setup.py`:

```python
entry_points={
    'console_scripts': [
        # ... existing entries
        "newtool=code_assistant_manager.cli:newtool_main",
    ]
}
```

### 5. Configure External Tool

Add the tool configuration to `tools.yaml`:

```yaml
newtool-key:
  enabled: true  # Set to false to hide from menus
  install_cmd: npm install -g newtool
  cli_command: newtool
  description: "New Tool description"
  env:
    exported:
      NEWTOOL_API_KEY: "Resolved API key"
  configuration:
    required:
      endpoint: "Base URL for the API"
      list_models_cmd: "Command to list models"
```

### Tool Visibility (enabled/disabled)

Tools can be shown or hidden from the interactive menu using the `enabled` key in `tools.yaml`:

- `enabled: true` (default) - Tool appears in menus and can be launched
- `enabled: false` - Tool is hidden from menus (useful for tools under development)

If the `enabled` key is not specified, it defaults to `true` for backward compatibility.

Example - disabling a tool:
```yaml
my-experimental-tool:
  enabled: false  # Hidden from menu
  install_cmd: npm install -g my-tool
  cli_command: mytool
  description: "Experimental tool - not ready yet"
```

## Configuration System

The configuration system uses JSON format with two main sections:

### Common Section

Global settings that apply to all endpoints:

```json
{
  "common": {
    "http_proxy": "http://proxy.example.com:3128/",
    "https_proxy": "http://proxy.example.com:3128/",
    "no_proxy": "localhost,127.0.0.1",
    "cache_ttl_seconds": 3600
  }
}
```

### Endpoints Section

Individual endpoint configurations:

```json
{
  "endpoints": {
    "endpoint-name": {
      "endpoint": "https://api.example.com",
      "api_key": "your-api-key",
      "api_key_env": "API_KEY_NAME",
      "list_models_cmd": "echo model1 model2",
      "keep_proxy_config": false,
      "use_proxy": true,
      "description": "Endpoint description",
      "supported_client": "tool1,tool2"
    }
  }
}
```

## Testing

The project uses pytest for testing with the following structure:

### Test Organization

- `tests/test_cli.py`: CLI interface tests
- `tests/test_config.py`: Configuration management tests
- `tests/test_endpoints.py`: Endpoint handling tests
- `tests/test_tools.py`: Tool implementation tests
- `tests/test_ui.py`: UI component tests
- `tests/test_integration.py`: Integration tests

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config.py

# Run with coverage
python -m pytest --cov=code_assistant_manager tests/
```

### Writing Tests

Follow these guidelines when writing tests:

1. Use pytest fixtures for test data
2. Mock external dependencies
3. Test both success and error cases
4. Include edge case testing
5. Use descriptive test names

Example test:

```python
def test_config_reload_updates_data(self, temp_config):
    """Test that reloading config updates the data."""
    config = ConfigManager(temp_config)

    # Test initial state
    sections_before = config.get_sections()
    assert 'test-endpoint' in sections_before

    # Modify config
    # ... modification code ...

    # Reload and verify
    config.reload()
    sections_after = config.get_sections()
    # ... assertions ...
```

## Security Considerations

### Command Validation

The `validate_command` function in `config.py` provides comprehensive validation of shell commands:

- Dangerous pattern detection
- File path validation
- Executable whitelisting
- Argument sanitization

### API Key Handling

- Environment variable precedence
- Secure masking in output
- Multiple resolution methods
- File permission checks

### Input Validation

All user inputs are validated:
- URL format validation
- API key format validation
- Model ID validation
- Boolean value validation

## Performance Optimization

### Caching Strategy

Model lists are cached with TTL to reduce API calls:

- Cache location: `${XDG_CACHE_HOME:-$HOME/.cache}/code-assistant-manager`
- Configurable TTL in seconds
- Atomic cache file operations
- Cache validation and refresh options

### Memory Management

- Efficient data structures
- Proper resource cleanup
- Minimal memory footprint
- Lazy loading where appropriate

## Contributing

### Development Setup

1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Run tests to verify setup

```bash
git clone https://github.com/your-org/code-assistant-manager.git
cd code-assistant-manager
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
python -m pytest tests/
```

### Code Style

Follow these guidelines:

1. Use type hints for all functions
2. Write docstrings for all public functions
3. Follow PEP 8 style guide
4. Keep functions focused and small
5. Use meaningful variable names

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Update documentation
6. Run all tests
7. Submit pull request

### Issue Reporting

When reporting issues, include:

1. Clear description of the problem
2. Steps to reproduce
3. Expected vs actual behavior
4. Environment information
5. Relevant configuration
6. Error messages or logs

## Additional Resources

- [Configuration Migration Guide](CONFIG_MIGRATION.md)
- [Testing Documentation](TESTING.md)
- [API Documentation](PYTHON_INDEX.md)
- [Feature Implementation Guides](TOOLS_IMPLEMENTATION_COMPLETE.md)
