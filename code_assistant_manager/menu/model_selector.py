"""Unified model selection interface for Code Assistant Manager."""

import os
from typing import Dict, List, Optional, Tuple

from .menus import display_centered_menu


class ModelSelector:
    """Unified model selection interface that includes endpoint information in prompts."""

    @staticmethod
    def _is_non_interactive_mode() -> bool:
        """Check if the tool is running in non-interactive mode."""
        return os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1"

    @staticmethod
    def select_model_with_endpoint_info(
        models: List[str],
        endpoint_name: str,
        endpoint_config: Dict[str, str],
        selection_type: str = "model",
        client_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Select a model with full endpoint information in the prompt.

        Args:
            models: List of available models
            endpoint_name: Name of the endpoint
            endpoint_config: Endpoint configuration dictionary
            selection_type: Type of selection ("model", "primary model", "secondary model")
            client_name: Optional client name for context

        Returns:
            Tuple of (success, selected_model)
        """
        # In non-interactive mode, select the first model automatically
        if ModelSelector._is_non_interactive_mode():
            if models:
                return True, models[0]
            return False, None

        # Create endpoint information string
        ep_url = endpoint_config.get("endpoint", "")
        ep_desc = endpoint_config.get("description", "") or ep_url
        endpoint_info = f"{endpoint_name} -> {ep_url} -> {ep_desc}"

        # Create appropriate prompt based on selection type
        if selection_type == "primary model":
            prompt = f"Choose primary model for {client_name} from {endpoint_info}:"
        elif selection_type == "secondary model":
            prompt = f"Choose secondary model for {client_name} from {endpoint_info}:"
        else:
            prompt = f"Select model from {endpoint_info}:"

        success, idx = display_centered_menu(prompt, models, "Cancel")
        if success and idx is not None:
            return True, models[idx]
        return False, None

    @staticmethod
    def select_two_models_with_endpoint_info(
        models: List[str],
        endpoint_name: str,
        endpoint_config: Dict[str, str],
        client_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[Tuple[str, str]]]:
        """
        Select two models with full endpoint information in the prompts.

        Args:
            models: List of available models
            endpoint_name: Name of the endpoint
            endpoint_config: Endpoint configuration dictionary
            client_name: Optional client name for context

        Returns:
            Tuple of (success, (primary_model, secondary_model))
        """
        # In non-interactive mode, select the first two models automatically
        if ModelSelector._is_non_interactive_mode():
            if len(models) >= 2:
                return True, (models[0], models[1])
            elif len(models) == 1:
                return True, (models[0], models[0])
            return False, None

        # Select primary model
        success1, primary = ModelSelector.select_model_with_endpoint_info(
            models, endpoint_name, endpoint_config, "primary model", client_name
        )
        if not success1 or primary is None:
            return False, None

        # Select secondary model
        success2, secondary = ModelSelector.select_model_with_endpoint_info(
            models, endpoint_name, endpoint_config, "secondary model", client_name
        )
        if not success2 or secondary is None:
            return False, None

        return True, (primary, secondary)
