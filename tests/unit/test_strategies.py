"""Tests for code_assistant_manager.strategies module."""

import pytest
from unittest.mock import MagicMock, patch
import os

from code_assistant_manager.strategies import (
    EnvironmentStrategyFactory,
    ClaudeEnvironmentStrategy,
    CodexEnvironmentStrategy,
    CopilotEnvironmentStrategy,
    GenericEnvironmentStrategy,
)
from code_assistant_manager.domain_models import EndpointConfig, ExecutionContext


class TestEnvironmentStrategyFactory:
    """Test the EnvironmentStrategyFactory."""

    def test_get_strategy_known_tool(self):
        """Test getting strategy for known tool."""
        strategy = EnvironmentStrategyFactory.get_strategy("claude")
        assert isinstance(strategy, ClaudeEnvironmentStrategy)

    def test_get_strategy_unknown_tool(self):
        """Test getting strategy for unknown tool defaults to generic."""
        strategy = EnvironmentStrategyFactory.get_strategy("unknown_tool")
        assert isinstance(strategy, GenericEnvironmentStrategy)

    def test_register_strategy(self):
        """Test registering a custom strategy."""
        class CustomStrategy(GenericEnvironmentStrategy):
            pass

        EnvironmentStrategyFactory.register_strategy("custom", CustomStrategy)
        strategy = EnvironmentStrategyFactory.get_strategy("custom")
        assert isinstance(strategy, CustomStrategy)

        # Clean up
        EnvironmentStrategyFactory._strategies.pop("custom", None)


class TestClaudeEnvironmentStrategy:
    """Test Claude environment strategy."""

    def test_setup_environment_success(self):
        """Test successful environment setup for Claude."""
        strategy = ClaudeEnvironmentStrategy()

        # Mock context
        context = MagicMock(spec=ExecutionContext)
        context.has_multiple_models.return_value = True
        context.selected_models = ("claude-3-sonnet", "claude-3-haiku")

        endpoint_config = MagicMock(spec=EndpointConfig)
        endpoint_config.url = "https://api.anthropic.com"
        endpoint_config.get_api_key_value.return_value = "test_key"
        context.endpoint_config = endpoint_config

        env = strategy.setup_environment(context)

        assert env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
        assert env["ANTHROPIC_AUTH_TOKEN"] == "test_key"
        assert env["ANTHROPIC_MODEL"] == "claude-3-sonnet"
        assert env["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"

    def test_setup_environment_single_model_error(self):
        """Test error when Claude doesn't have multiple models."""
        strategy = ClaudeEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)
        context.has_multiple_models.return_value = False

        with pytest.raises(ValueError, match="Claude requires two models"):
            strategy.setup_environment(context)


class TestCodexEnvironmentStrategy:
    """Test Codex environment strategy."""

    def test_setup_environment_success(self):
        """Test successful environment setup for Codex."""
        strategy = CodexEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)
        context.has_single_model.return_value = True

        endpoint_config = MagicMock(spec=EndpointConfig)
        endpoint_config.url = "https://api.openai.com"
        endpoint_config.get_api_key_value.return_value = "openai_key"
        context.endpoint_config = endpoint_config

        env = strategy.setup_environment(context)

        assert env["BASE_URL"] == "https://api.openai.com"
        assert env["OPENAI_API_KEY"] == "openai_key"
        assert env["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"

    def test_setup_environment_multiple_models_error(self):
        """Test error when Codex has multiple models."""
        strategy = CodexEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)
        context.has_single_model.return_value = False

        with pytest.raises(ValueError, match="Codex requires a single model"):
            strategy.setup_environment(context)


class TestCopilotEnvironmentStrategy:
    """Test Copilot environment strategy."""

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_setup_environment_success(self):
        """Test successful environment setup for Copilot."""
        strategy = CopilotEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)

        env = strategy.setup_environment(context)

        assert env["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"

    @patch.dict(os.environ, {}, clear=True)
    def test_setup_environment_missing_github_token(self):
        """Test error when GITHUB_TOKEN is missing."""
        strategy = CopilotEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)

        with pytest.raises(ValueError, match="GITHUB_TOKEN not set in environment"):
            strategy.setup_environment(context)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "NODE_EXTRA_CA_CERTS": "/path/to/cert"})
    def test_setup_environment_with_ca_certs(self):
        """Test environment setup with CA certificates."""
        strategy = CopilotEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)

        env = strategy.setup_environment(context)

        assert env["NODE_EXTRA_CA_CERTS"] == "/path/to/cert"


class TestGenericEnvironmentStrategy:
    """Test generic environment strategy."""

    def test_setup_environment(self):
        """Test basic environment setup."""
        strategy = GenericEnvironmentStrategy()

        context = MagicMock(spec=ExecutionContext)

        env = strategy.setup_environment(context)

        assert env["NODE_TLS_REJECT_UNAUTHORIZED"] == "0"
        assert isinstance(env, dict)