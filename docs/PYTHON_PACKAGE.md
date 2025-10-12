"""Code Assistant Manager Python Package

This Python package provides a modular, production-ready version of the Code Assistant Manager
shell scripts. All functionality has been preserved with an improved architecture.

## Installation

### From source
```bash
cd /path/to/code-assistant-manager
pip install -e .
```

### Using pip directly
```bash
pip install -e .
```

## Usage

### As a Python package
```python
from code_assistant_manager import ConfigManager, EndpointManager
from code_assistant_manager.ui import display_centered_menu

# Initialize config
config = ConfigManager()

# Get endpoints
endpoints = config.get_sections()
print(endpoints)
```

### As CLI commands

After installation, you can use individual commands:

```bash
# Interactive Claude wrapper
claude

# Interactive Codex wrapper
codex

# Droid wrapper
droid

# Qwen wrapper
qwen

# CodeBuddy wrapper
codebuddy

# GitHub Copilot setup
copilot

# Google Gemini setup
gemini
```

Or use the main entry point:

```bash
code-assistant-manager claude
code-assistant-manager codex
code-assistant-manager droid
```

## Configuration

The package uses the same `settings.conf` format as the shell version:

```ini
[common]
http_proxy=http://proxy.example.com:3128/
https_proxy=http://proxy.example.com:3128/
cache_ttl_seconds=3600

[litellm]
endpoint=https://example.com:4142
api_key_env=API_KEY_LITELLM
list_models_cmd=curl -s 'https://example.com:4142/v1/models' | jq -r '.data.[].id'
use_proxy=false
description=LiteLLM endpoint
```

## Project Structure

```
code_assistant_manager/
├── __init__.py           # Package initialization
├── cli.py               # Command-line interface entry points
├── config.py            # Configuration management
├── endpoints.py         # Endpoint and model management
├── tools.py             # CLI tool wrappers (Claude, Codex, etc.)
└── ui.py               # Terminal UI components
```

## Features

- **Modular architecture**: Each component is independent and testable
- **Type hints**: Full Python type annotations for better IDE support
- **Configuration management**: INI-based settings with sensible defaults
- **Endpoint selection**: Interactive menu for choosing endpoints
- **Model fetching**: Automatic model list fetching with caching
- **Terminal UI**: Centered menus with color support and validation
- **API key management**: Support for environment variables and config files
- **Proxy support**: Built-in HTTP/HTTPS proxy configuration

## Compatibility

The Python package maintains full compatibility with the shell version:
- Same configuration file format (settings.conf)
- Same endpoint configuration options
- Same model fetching and caching behavior
- Same UI styling and interaction patterns

## Development

### Running tests
```bash
python -m pytest
```

### Code style
```bash
# Format code
black code_assistant_manager/

# Type checking
mypy code_assistant_manager/

# Linting
flake8 code_assistant_manager/
```

## Migration from Shell Version

If you're migrating from the shell version:

1. Install the Python package: `pip install -e .`
2. Your existing `settings.conf` will work as-is
3. Replace shell scripts with Python commands
4. Update `.bashrc` aliases to use the new commands

### Before (shell)
```bash
source ai_tool_setup.sh
claude
```

### After (Python)
```bash
claude
```

## Troubleshooting

### "Command not found: claude"
Install the package in development mode:
```bash
pip install -e .
```

### "Configuration file not found"
Place `settings.conf` in one of these locations:
- Current directory
- ~/.config/code-assistant-manager/settings.conf
- Same directory as the script

### "Failed to fetch models"
Check that:
1. Your endpoint is accessible
2. Your API key is valid
3. You have internet connectivity
4. The `list_models_cmd` is correctly configured

## Contributing

Contributions are welcome! Areas for improvement:
- Arrow key support in terminal menus
- Additional endpoint types
- More comprehensive error handling
- Performance optimizations

## License

Same as the original Code Assistant Manager project.
"""

if __name__ == '__main__':
    print(__doc__)
