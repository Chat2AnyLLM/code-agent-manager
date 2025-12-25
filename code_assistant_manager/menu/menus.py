"""Menu utility functions for Code Assistant Manager."""

import time
from typing import Callable, List, Optional, Tuple

from .base import FilterableMenu, SimpleMenu


def display_centered_menu(
    title: str,
    items: List[str],
    cancel_text: str = "Cancel",
    max_attempts: int = 3,
    key_provider: Optional[Callable[[], Optional[str]]] = None,
) -> Tuple[bool, Optional[int]]:
    """
    Display a centered menu with enhanced UX and dynamic filtering.

    Args:
        title: Menu title
        items: List of menu items
        cancel_text: Text for cancel option
        max_attempts: Maximum input attempts
        key_provider: Optional function to provide keyboard input (for testing)

    Returns:
        Tuple of (success, selected_index)
        If cancelled, returns (False, None)
        If selected, returns (True, index) where index is 0-based
        Note: The index refers to the original items list, not the filtered list
    """
    menu = FilterableMenu(title, items, cancel_text, max_attempts, key_provider)
    return menu.display()


def display_simple_menu(
    title: str, items: List[str], cancel_text: str = "Cancel", max_attempts: int = 3
) -> Tuple[bool, Optional[int]]:
    """
    Display a simple centered menu without dynamic filtering.

    Args:
        title: Menu title
        items: List of menu items
        cancel_text: Text for cancel option
        max_attempts: Maximum input attempts

    Returns:
        Tuple of (success, selected_index)
        If cancelled, returns (False, None)
        If selected, returns (True, index) where index is 0-based
    """
    menu = SimpleMenu(title, items, cancel_text, max_attempts)
    return menu.display()


def select_model(
    models: List[str],
    prompt: str = "Select model:",
    cancel_text: str = "Cancel",
    key_provider: Optional[Callable[[], Optional[str]]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Select a single model from a list.

    Args:
        models: List of available models
        prompt: Selection prompt
        cancel_text: Text for cancel option
        key_provider: Optional function to provide keyboard input (for testing)

    Returns:
        Tuple of (success, selected_model)
    """
    success, idx = display_centered_menu(
        prompt, models, cancel_text, key_provider=key_provider
    )
    if success and idx is not None:
        return True, models[idx]
    return False, None


def select_two_models(
    models: List[str],
    primary_prompt: str = "Select primary model:",
    secondary_prompt: str = "Select secondary model:",
    cancel_text: str = "Cancel",
) -> Tuple[bool, Optional[Tuple[str, str]]]:
    """
    Select two models from the same list.

    Args:
        models: List of available models
        primary_prompt: Prompt for primary model
        secondary_prompt: Prompt for secondary model
        cancel_text: Text for cancel option

    Returns:
        Tuple of (success, (primary_model, secondary_model))
    """
    success1, primary = select_model(models, primary_prompt, cancel_text)
    if not success1 or primary is None:
        return False, None

    time.sleep(1)  # Brief pause between selections

    success2, secondary = select_model(models, secondary_prompt, cancel_text)
    if not success2 or secondary is None:
        return False, None

    return True, (primary, secondary)


def select_multiple_models(
    models: List[str],
    prompt: str = "Select models (press Cancel to finish):",
    cancel_text: str = "Cancel",
    key_provider: Optional[Callable[[], Optional[str]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Select multiple models from a list until user selects Cancel.

    Args:
        models: List of available models
        prompt: Selection prompt
        cancel_text: Text for cancel option
        key_provider: Optional function to provide keyboard input (for testing)

    Returns:
        Tuple of (success, list_of_selected_models)
        If no models selected, returns (False, [])
        If models selected, returns (True, [models...])
    """
    selected_models = []
    remaining_models = models.copy()

    while remaining_models:
        # Show current selections if any
        if selected_models:
            display_prompt = f"{prompt} (Selected: {len(selected_models)})"
        else:
            display_prompt = prompt

        success, idx = display_centered_menu(
            display_prompt, remaining_models, cancel_text, key_provider=key_provider
        )

        if not success or idx is None:
            # User cancelled - return what we have so far
            break

        # Add selected model to list
        selected_model = remaining_models[idx]
        selected_models.append(selected_model)

        # Remove from remaining
        remaining_models.pop(idx)

        # Brief pause before next iteration
        if remaining_models:
            time.sleep(0.5)

    if selected_models:
        return True, selected_models
    return False, []
