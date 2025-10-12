# CLAUDE.md — Repository guidelines for AI-assisted edits

This file documents repository-level expectations and instructions intended to guide contributors and AI-assisted editing tools (like Claude Code) when making changes in this project.

## Core Guidelines

- **Ask for approval before any git commit and push**
- **Always run tests** before completing all development of new changes
- **Always test the CLI usages** to ensure functionality works end-to-end
- **Run code quality checks** before committing (see below)

## Development Workflow

### After Any Changes

Reinstall the project to test in production-like environment:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
cp ~/.config/code-assistant-manager/providers.json.bak ~/.config/code-assistant-manager/providers.json
```

### Code Quality Requirements

Before committing, ensure all quality checks pass:

```bash
# Quick check (formatting + linting + type-check + tests)
make check

# Or run individually:
make format          # Auto-format code with Black and isort
make lint            # Check code style with Flake8
make type-check      # Verify type hints with mypy
make security        # Scan for security issues with Bandit
make test            # Run test suite
```

**Pre-commit hooks** are automatically installed with `make dev-install` and will run these checks before each commit.

### Code Style Standards

- **Formatting**: Use Black (line length: 88)
- **Import sorting**: Use isort (Black-compatible profile)
- **Linting**: Follow Flake8 rules (see `.flake8`)
- **Type hints**: Add type hints for new code (checked with mypy)
- **Docstrings**: Use Google-style docstrings for public functions/classes
- **Security**: No hardcoded secrets, follow Bandit recommendations

### Testing Requirements

- Write tests for all new functionality
- Maintain or improve test coverage
- Use appropriate test markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
- Mock external dependencies (APIs, file system, network)

## Quick Reference

### Setup Development Environment

```bash
# One-time setup
make dev-install     # Install with dev dependencies + pre-commit hooks
```

### Common Commands

```bash
make help            # Show all available commands
make format          # Auto-format code
make check           # Run all quality checks
make test            # Run test suite
make test-cov        # Run tests with coverage report
```

### Before Submitting Code

1. ✅ Run `make check` - All checks must pass
2. ✅ Run `make test` - All tests must pass
3. ✅ Test CLI manually - Ensure functionality works
4. ✅ Update documentation - If adding/changing features
5. ✅ Review changes - Use `git diff` before committing

## Documentation

- See `CONTRIBUTING.md` for detailed contribution guidelines
- See `docs/CODE_QUALITY.md` for comprehensive code quality tool documentation
- See `docs/DESIGN_PATTERNS_README.md` for architecture patterns

## Attribution

When using AI assistance for code generation, add attribution in commit messages:

```bash
git commit -m "feat: implement new feature

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Questions?

- Review this document and `CONTRIBUTING.md`
- Check code quality documentation in `docs/CODE_QUALITY.md`
- Consult design patterns guide in `docs/DESIGN_PATTERNS_README.md`
