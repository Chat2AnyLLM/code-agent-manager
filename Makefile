.PHONY: help install dev-install clean test lint format type-check security check pre-commit-install pre-commit-run build release

# Default target
help:
	@echo "Available commands:"
	@echo "  make install          - Install package for production use"
	@echo "  make dev-install      - Install package with development dependencies"
	@echo "  make clean            - Remove build artifacts and caches"
	@echo "  make test             - Run test suite"
	@echo "  make lint             - Run linting (flake8)"
	@echo "  make format           - Format code (black, isort)"
	@echo "  make type-check       - Run type checking (mypy)"
	@echo "  make security         - Run security checks (bandit)"
	@echo "  make check            - Run all quality checks (lint, type-check, test)"
	@echo "  make pre-commit-install - Install pre-commit hooks"
	@echo "  make pre-commit-run   - Run pre-commit on all files"
	@echo "  make build            - Build distribution packages"
	@echo "  make release          - Full release workflow (clean, test, build)"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	$(MAKE) pre-commit-install

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .tox/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.orig" -delete

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=code_assistant_manager --cov-report=html --cov-report=term

# Code quality
lint:
	@echo "Running flake8..."
	flake8 code_assistant_manager/

format:
	@echo "Running isort..."
	isort code_assistant_manager/ tests/
	@echo "Running black..."
	black code_assistant_manager/ tests/

format-check:
	@echo "Checking isort..."
	isort --check-only code_assistant_manager/ tests/
	@echo "Checking black..."
	black --check code_assistant_manager/ tests/

type-check:
	@echo "Running mypy..."
	mypy code_assistant_manager/

security:
	@echo "Running bandit..."
	bandit -r code_assistant_manager/ -c pyproject.toml

docstring-check:
	@echo "Checking docstring coverage..."
	interrogate code_assistant_manager/ -c pyproject.toml

# Combined checks
check: format-check lint type-check test
	@echo "All checks passed!"

# Pre-commit
pre-commit-install:
	pre-commit install
	@echo "Pre-commit hooks installed successfully!"

pre-commit-run:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate

# Building
build: clean
	python3 setup.py bdist_wheel

# Release workflow
release: clean check build
	@echo "Release build completed successfully!"
	@echo "Distribution files:"
	@ls -lh dist/

# Docker commands (future)
docker-build:
	@echo "Docker build not yet implemented"

docker-run:
	@echo "Docker run not yet implemented"
