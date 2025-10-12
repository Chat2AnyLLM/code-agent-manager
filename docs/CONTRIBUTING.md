# Contributing to Code Assistant Manager

Thank you for your interest in contributing to code-assistant-manager! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Quality Standards](#code-quality-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [AI-Assisted Development](#ai-assisted-development)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/code-assistant-manager.git
   cd code-assistant-manager
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/yourorg/code-assistant-manager.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip and virtualenv
- Git
- Node.js and npm (for some AI coding assistants)

### Setting Up Development Environment

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode with all dependencies:
   ```bash
   make dev-install
   ```

   Or manually:
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

3. Verify the installation:
   ```bash
   code-assistant-manager --version
   pytest tests/ -v
   ```

## Code Quality Standards

We use automated code quality tools to maintain consistent, high-quality code. These tools are enforced via pre-commit hooks.

### Tools Used

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (compatible with Black)
- **Flake8**: Linting with plugins (bugbear, comprehensions, simplify)
- **mypy**: Type checking
- **Bandit**: Security vulnerability scanning
- **interrogate**: Docstring coverage checking

### Running Quality Checks

Use the Makefile for convenience:

```bash
# Format code automatically
make format

# Check formatting without changes
make format-check

# Run linting
make lint

# Run type checking
make type-check

# Run security checks
make security

# Run all checks (format-check, lint, type-check, test)
make check
```

### Pre-commit Hooks

Pre-commit hooks automatically run before each commit. To run them manually:

```bash
# Run on all files
make pre-commit-run

# Update hook versions
make pre-commit-update
```

If you need to bypass hooks temporarily (not recommended):
```bash
git commit --no-verify -m "message"
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
pytest tests/test_config.py -v

# Run tests matching a pattern
pytest tests/ -k "test_endpoint" -v
```

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for multiple components
- `tests/interactive/` - Interactive tests requiring manual verification

### Writing Tests

- Use pytest fixtures for setup/teardown
- Use appropriate markers: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
- Aim for >80% code coverage
- Mock external dependencies (API calls, file system, etc.)

Example:
```python
import pytest
from code_assistant_manager.config import ConfigManager

def test_config_loading(tmp_path):
    """Test configuration file loading."""
    config_file = tmp_path / "providers.json"
    config_file.write_text('{"endpoints": {}}')

    config = ConfigManager(str(config_file))
    assert config.config_data == {"endpoints": {}}
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following code quality standards

3. **Write/update tests** for your changes

4. **Run all quality checks**:
   ```bash
   make check
   ```

5. **Update documentation** if needed (README, docstrings, etc.)

6. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `style:` - Formatting changes
   - `chore:` - Maintenance tasks

### Submitting the PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request** on GitHub with:
   - Clear title and description
   - Reference to related issues (if any)
   - Screenshots/examples (if applicable)
   - Test results confirmation

3. **Address review feedback** promptly

4. **Ensure CI passes** (when available)

### PR Requirements

- ✅ All tests pass
- ✅ Code quality checks pass (lint, type-check, format)
- ✅ New code has tests
- ✅ Documentation updated
- ✅ Commit messages are clear and conventional
- ✅ No merge conflicts with main branch

## AI-Assisted Development

This project welcomes AI-assisted contributions. Please follow these additional guidelines when using AI coding assistants:

### Guidelines from CLAUDE.md

1. **Always seek approval before git commit and push**
2. **Always run tests** before completing development of new changes
3. **Always test CLI usages** to ensure functionality
4. **After any changes**, reinstall the project:
   ```bash
   rm -rf dist/*
   ./install.sh uninstall
   ./install.sh
   cp ~/.config/code-assistant-manager/providers.json.bak ~/.config/code-assistant-manager/providers.json
   ```

### Attribution

When using AI assistance for significant contributions, add attribution in your commit message:

```
feat: implement new feature

Co-Authored-By: Claude <noreply@anthropic.com>
```

or for other AI assistants:

```
feat: implement new feature

AI-Assisted: [Tool Name]
```

## Code Style Guidelines

### Python Style

- Follow PEP 8 (enforced by Flake8)
- Use type hints where appropriate
- Maximum line length: 88 characters (Black default)
- Prefer descriptive variable names over comments
- Use docstrings for all public functions, classes, and modules

### Documentation Style

- Use Google-style docstrings
- Include parameter types and return types
- Provide usage examples for complex functions

Example:
```python
def get_endpoint_config(self, endpoint_name: str) -> Dict[str, str]:
    """
    Get full configuration for an endpoint.

    Args:
        endpoint_name: Name of the endpoint

    Returns:
        Dictionary with endpoint configuration

    Example:
        >>> config.get_endpoint_config("anthropic")
        {'endpoint': 'https://api.anthropic.com', 'api_key_env': 'ANTHROPIC_API_KEY'}
    """
    # implementation
```

## Design Patterns

This project uses industry-standard design patterns. When adding new code:

- Use **Value Objects** for validated primitives (see `value_objects.py`)
- Use **Factory Pattern** for creating tools (see `factory.py`)
- Use **Strategy Pattern** for pluggable algorithms (see `strategies.py`)
- Use **Repository Pattern** for data access (see `repositories.py`)
- Use **Service Layer** for business logic (see `services.py`)

See `docs/DESIGN_PATTERNS_README.md` for detailed guidance.

## Questions or Issues?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues and PRs before creating new ones

Thank you for contributing! 🎉
