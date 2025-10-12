"""Strategy pattern implementations for Code Assistant Manager.

Provides pluggable algorithms for environment setup and tool execution.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict

from .domain_models import EndpointConfig, ExecutionContext


class EnvironmentStrategy(ABC):
    """Strategy for setting up tool environment variables."""

    @abstractmethod
    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """
        Setup and return environment variables for tool execution.

        Args:
            context: Execution context with configuration and models

        Returns:
            Dictionary of environment variables
        """

    def _base_environment(self) -> Dict[str, str]:
        """Get base environment with Node.js TLS disabled."""
        env = os.environ.copy()
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        return env

    def _apply_proxy_settings(
        self, env: Dict[str, str], endpoint_config: EndpointConfig
    ) -> Dict[str, str]:
        """Apply proxy settings if configured."""
        if endpoint_config.should_use_proxy() and endpoint_config.proxy_settings:
            proxy_dict = endpoint_config.proxy_settings.to_dict()
            env.update(proxy_dict)
        return env

    def _remove_proxy_settings(self, env: Dict[str, str]) -> Dict[str, str]:
        """Remove proxy settings from environment."""
        proxy_keys = [
            "http_proxy",
            "HTTP_PROXY",
            "https_proxy",
            "HTTPS_PROXY",
            "no_proxy",
            "NO_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ]
        for key in proxy_keys:
            env.pop(key, None)
        return env


class ClaudeEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for Claude CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup Claude-specific environment variables."""
        if not context.has_multiple_models():
            raise ValueError("Claude requires two models (primary and secondary)")

        primary_model, secondary_model = context.selected_models  # type: ignore
        env = self._base_environment()

        endpoint_config = context.endpoint_config
        env["ANTHROPIC_BASE_URL"] = str(endpoint_config.url)
        env["ANTHROPIC_AUTH_TOKEN"] = endpoint_config.get_api_key_value() or ""
        env["ANTHROPIC_MODEL"] = str(primary_model)
        env["ANTHROPIC_SMALL_FAST_MODEL"] = str(secondary_model)
        env["CLAUDE_MODEL_2"] = str(secondary_model)
        env["CLAUDE_MODELS"] = f"{primary_model},{secondary_model}"
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = str(primary_model)
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = str(primary_model)
        env["DISABLE_NON_ESSENTIAL_MODEL_CALLS"] = "1"
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

        return env


class CodexEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for Codex CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup Codex-specific environment variables."""
        if not context.has_single_model():
            raise ValueError("Codex requires a single model")

        env = self._base_environment()
        endpoint_config = context.endpoint_config

        env["BASE_URL"] = str(endpoint_config.url)
        env["OPENAI_API_KEY"] = endpoint_config.get_api_key_value() or ""

        return env


class QwenEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for Qwen CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup Qwen-specific environment variables."""
        if not context.has_single_model():
            raise ValueError("Qwen requires a single model")

        env = self._base_environment()
        endpoint_config = context.endpoint_config

        env["OPENAI_BASE_URL"] = str(endpoint_config.url)
        env["OPENAI_API_KEY"] = endpoint_config.get_api_key_value() or ""
        env["OPENAI_MODEL"] = str(context.selected_model)

        return env


class CodeBuddyEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for CodeBuddy CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup CodeBuddy-specific environment variables."""
        if not context.has_single_model():
            raise ValueError("CodeBuddy requires a single model")

        env = self._base_environment()
        endpoint_config = context.endpoint_config

        env["CODEBUDDY_BASE_URL"] = str(endpoint_config.url)
        env["CODEBUDDY_API_KEY"] = endpoint_config.get_api_key_value() or ""

        return env


class IfLowEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for iFlow CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup iFlow-specific environment variables."""
        if not context.has_single_model():
            raise ValueError("iFlow requires a single model")

        env = self._base_environment()
        endpoint_config = context.endpoint_config

        env["IFLOW_BASE_URL"] = str(endpoint_config.url)
        env["IFLOW_API_KEY"] = endpoint_config.get_api_key_value() or ""
        env["IFLOW_MODEL_NAME"] = str(context.selected_model)

        return env


class NeovateEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for Neovate CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup Neovate-specific environment variables."""
        if not context.has_single_model():
            raise ValueError("Neovate requires a single model")

        env = self._base_environment()
        endpoint_config = context.endpoint_config

        env["OPENAI_API_KEY"] = endpoint_config.get_api_key_value() or ""
        env["OPENAI_API_BASE"] = str(endpoint_config.url)

        return env


class CopilotEnvironmentStrategy(EnvironmentStrategy):
    """Environment setup strategy for GitHub Copilot CLI."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup Copilot-specific environment variables."""
        env = self._base_environment()

        # Copilot uses GITHUB_TOKEN from environment
        if not os.environ.get("GITHUB_TOKEN"):
            raise ValueError("GITHUB_TOKEN not set in environment")

        # Handle NODE_EXTRA_CA_CERTS if set
        if os.environ.get("NODE_EXTRA_CA_CERTS"):
            env["NODE_EXTRA_CA_CERTS"] = os.environ["NODE_EXTRA_CA_CERTS"]

        return env


class GenericEnvironmentStrategy(EnvironmentStrategy):
    """Generic environment setup strategy for tools without special requirements."""

    def setup_environment(self, context: ExecutionContext) -> Dict[str, str]:
        """Setup basic environment variables."""
        env = self._base_environment()
        return env


class EnvironmentStrategyFactory:
    """Factory for creating environment strategies."""

    _strategies: Dict[str, type] = {
        "claude": ClaudeEnvironmentStrategy,
        "codex": CodexEnvironmentStrategy,
        "qwen": QwenEnvironmentStrategy,
        "codebuddy": CodeBuddyEnvironmentStrategy,
        "iflow": IfLowEnvironmentStrategy,
        "neovate": NeovateEnvironmentStrategy,
        "copilot": CopilotEnvironmentStrategy,
        "gemini": GenericEnvironmentStrategy,
        "qodercli": GenericEnvironmentStrategy,
        "zed": GenericEnvironmentStrategy,
        "droid": GenericEnvironmentStrategy,
    }

    @classmethod
    def get_strategy(cls, tool_name: str) -> EnvironmentStrategy:
        """
        Get environment strategy for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Environment strategy instance
        """
        strategy_class = cls._strategies.get(tool_name, GenericEnvironmentStrategy)
        return strategy_class()

    @classmethod
    def register_strategy(cls, tool_name: str, strategy_class: type):
        """Register a custom strategy for a tool."""
        cls._strategies[tool_name] = strategy_class
