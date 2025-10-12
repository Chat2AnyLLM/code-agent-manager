# Code Quality Tools Setup

This document describes the code quality tools and enforcement mechanisms in place for code-assistant-manager.

## Overview

The project uses automated code quality tools to ensure consistent, maintainable, and secure code. These tools are integrated with:

- **Pre-commit hooks** - Run automatically before each commit
- **Makefile commands** - Run manually or in CI/CD pipelines
- **Editor integration** - Can be configured in IDEs/editors

## Tools Used

### 1. **Black** - Code Formatting
- **Version**: 24.3.0+
- **Configuration**: `pyproject.toml` → `[tool.black]`
- **Line length**: 88 characters
- **Purpose**: Automatically formats Python code for consistency

**Usage**:
```bash
# Format all code
make format

# Check formatting without changes
make format-check

# Manual usage
black code_assistant_manager/ tests/
```

### 2. **isort** - Import Sorting
- **Version**: 5.13.0+
- **Configuration**: `pyproject.toml` → `[tool.isort]`
- **Profile**: black-compatible
- **Purpose**: Sorts and organizes imports consistently

**Usage**:
```bash
# Sort imports (included in make format)
isort code_assistant_manager/ tests/

# Check only
isort --check-only code_assistant_manager/ tests/
```

### 3. **Flake8** - Linting
- **Version**: 7.0.0+
- **Configuration**: `.flake8`
- **Plugins**:
  - `flake8-bugbear` - Additional bug checks
  - `flake8-comprehensions` - Comprehension improvements
  - `flake8-simplify` - Code simplification suggestions
- **Purpose**: Detects style violations, bugs, and code smells

**Usage**:
```bash
# Run linting
make lint

# Manual usage
flake8 code_assistant_manager/
```

**Common Flake8 Codes**:
- `E***` - PEP 8 errors
- `W***` - PEP 8 warnings
- `F***` - PyFlakes (unused imports, undefined names)
- `B***` - flake8-bugbear (potential bugs)
- `C901` - Complexity (McCabe)

### 4. **mypy** - Type Checking
- **Version**: 1.11.0+
- **Configuration**: `pyproject.toml` → `[tool.mypy]`
- **Mode**: Progressive typing (non-strict for gradual adoption)
- **Purpose**: Static type checking for type safety

**Usage**:
```bash
# Run type checking
make type-check

# Manual usage
mypy code_assistant_manager/
```

**Type checking features enabled**:
- `check_untyped_defs` - Check even untyped functions
- `warn_return_any` - Warn on `Any` returns
- `warn_unused_ignores` - Detect unnecessary `# type: ignore`
- `strict_equality` - Strict type comparison

### 5. **Bandit** - Security Scanner
- **Version**: 1.7.8+
- **Configuration**: `pyproject.toml` → `[tool.bandit]`
- **Purpose**: Scans code for common security vulnerabilities

**Usage**:
```bash
# Run security checks
make security

# Manual usage
bandit -r code_assistant_manager/ -c pyproject.toml
```

**Checks for**:
- Hardcoded passwords
- SQL injection risks
- Shell injection risks
- Insecure crypto usage
- Assert usage in production

### 6. **interrogate** - Docstring Coverage
- **Version**: 1.7.0+
- **Configuration**: `pyproject.toml` → `[tool.interrogate]`
- **Minimum coverage**: 50%
- **Purpose**: Ensures code documentation quality

**Usage**:
```bash
# Check docstring coverage
make docstring-check

# Manual usage
interrogate code_assistant_manager/ -c pyproject.toml
```

## Pre-commit Hooks

Pre-commit hooks automatically run quality checks before each commit.

### Installation

```bash
# One-time setup
make dev-install

# Or manually
pip install pre-commit
pre-commit install
```

### Running Hooks

```bash
# Run on all files
make pre-commit-run

# Update hook versions
make pre-commit-update

# Run specific hook
pre-commit run black --all-files
```

### Bypassing Hooks (Not Recommended)

```bash
# Skip hooks temporarily (emergency only)
git commit --no-verify -m "urgent fix"
```

## Makefile Commands

The project includes a comprehensive Makefile for common tasks:

```bash
# Show all available commands
make help

# Development setup
make dev-install        # Install with dev dependencies + pre-commit

# Code quality
make format             # Format code (black + isort)
make format-check       # Check formatting without changes
make lint               # Run flake8 linting
make type-check         # Run mypy type checking
make security           # Run bandit security scan
make docstring-check    # Check docstring coverage

# Combined checks
make check              # Run all checks (format-check + lint + type-check + test)

# Testing
make test               # Run test suite
make test-cov           # Run tests with coverage report

# Building
make build              # Build distribution packages
make release            # Full release workflow (clean + check + build)

# Maintenance
make clean              # Remove build artifacts and caches
```

## CI/CD Integration (Future)

When CI is set up, quality checks will run automatically:

```yaml
# Example GitHub Actions workflow
- name: Run code quality checks
  run: |
    make format-check
    make lint
    make type-check
    make security
    make test
```

## Editor Integration

### VS Code

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm

1. Go to: **Preferences → Tools → Black**
2. Enable: "Run Black on save"
3. Go to: **Preferences → Tools → External Tools**
4. Add tools for: isort, flake8, mypy

### Vim/Neovim

Use plugins like:
- `psf/black` for formatting
- `dense-analysis/ale` for linting
- `neovim/nvim-lspconfig` with `pylsp` for type checking

## Configuration Files

### `.pre-commit-config.yaml`
Central configuration for all pre-commit hooks.

### `pyproject.toml`
Configuration for:
- `[tool.black]` - Black formatting
- `[tool.isort]` - Import sorting
- `[tool.mypy]` - Type checking
- `[tool.bandit]` - Security scanning
- `[tool.interrogate]` - Docstring coverage

### `.flake8`
Flake8 linting configuration (INI format, as Flake8 doesn't support pyproject.toml natively).

### `Makefile`
Convenience commands for running all tools.

## Troubleshooting

### "Black would reformat X files"
Run `make format` to auto-fix formatting issues.

### "Imports are incorrectly sorted"
Run `isort code_assistant_manager/ tests/` to fix import ordering.

### Flake8 errors
- Review the error codes and fix manually
- Some errors (like complexity C901) may require refactoring
- Use `# noqa: <code>` comments sparingly for false positives

### Mypy type errors
- Add type hints gradually
- Use `# type: ignore` for third-party library issues
- Configure `[[tool.mypy.overrides]]` in pyproject.toml for specific modules

### Pre-commit hook failures
- Review the error output
- Run `make format` for auto-fixable issues
- Fix remaining issues manually
- Re-run `git commit`

### Update hook versions
```bash
pre-commit autoupdate
```

## Best Practices

1. **Run checks before committing**:
   ```bash
   make check
   ```

2. **Fix formatting first** (easiest):
   ```bash
   make format
   ```

3. **Address linting issues** (important):
   ```bash
   make lint
   # Fix reported issues
   ```

4. **Add type hints gradually** (optional but recommended):
   ```bash
   make type-check
   # Add type hints for new code
   ```

5. **Never ignore security warnings**:
   ```bash
   make security
   # Review and fix all bandit warnings
   ```

6. **Keep docstrings up to date**:
   ```bash
   make docstring-check
   # Add docstrings to public functions
   ```

## Contributing

When contributing code:

1. ✅ Install dev dependencies: `make dev-install`
2. ✅ Make your changes
3. ✅ Run quality checks: `make check`
4. ✅ Fix any issues
5. ✅ Commit (hooks will run automatically)
6. ✅ Push and create PR

See `CONTRIBUTING.md` for detailed guidelines.

## Questions?

- Check this document first
- Review configuration files (`.flake8`, `pyproject.toml`)
- Consult tool documentation:
  - [Black](https://black.readthedocs.io/)
  - [isort](https://pycqa.github.io/isort/)
  - [Flake8](https://flake8.pycqa.org/)
  - [mypy](https://mypy.readthedocs.io/)
  - [Bandit](https://bandit.readthedocs.io/)
  - [pre-commit](https://pre-commit.com/)
