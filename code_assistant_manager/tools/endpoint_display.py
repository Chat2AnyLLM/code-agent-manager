"""Utility functions for displaying tool endpoint information."""

from ..config import ConfigManager
from ..endpoints import EndpointManager


def display_tool_endpoints(config_manager: ConfigManager, client_name: str = None):
    """
    Display endpoint information for tools in the format: name -> endpoint -> desc

    Args:
        config_manager: ConfigManager instance
        client_name: Optional client name to filter endpoints (e.g., 'droid', 'claude', etc.)
    """
    endpoint_manager = EndpointManager(config_manager)
    endpoints = config_manager.get_sections(exclude_common=True)

    if not endpoints:
        print("No endpoints configured in settings.conf")
        return

    # Filter endpoints by client if specified
    if client_name:
        filtered = []
        for ep in endpoints:
            if endpoint_manager._is_client_supported(ep, client_name):
                filtered.append(ep)
        endpoints = filtered

        if not endpoints:
            print(
                f"No endpoints configured for client '{client_name}' in settings.conf"
            )
            return

    # Display in the requested format: name -> endpoint -> description
    for ep in endpoints:
        ep_config = config_manager.get_endpoint_config(ep)
        ep_url = ep_config.get("endpoint", "")
        ep_desc = ep_config.get("description", "")

        # If no description, use the endpoint URL
        if not ep_desc:
            ep_desc = ep_url

        print(f"{ep} -> {ep_url} -> {ep_desc}")


def display_all_tool_endpoints(config_manager: ConfigManager):
    """
    Display all endpoint information for all tools.

    Args:
        config_manager: ConfigManager instance
    """
    # Common tools that use endpoint selection
    tools = [
        "claude",
        "codex",
        "qwen",
        "codebuddy",
        "iflow",
        "droid",
        "copilot",
        "gemini",
        "neovate",
    ]

    print("Endpoint Information for All Tools")
    print("=" * 50)

    for tool in tools:
        tool_endpoints = []
        endpoints = config_manager.get_sections(exclude_common=True)
        endpoint_manager = EndpointManager(config_manager)

        # Filter endpoints by client
        if tool != "copilot":  # Copilot doesn't use endpoint selection
            for ep in endpoints:
                if endpoint_manager._is_client_supported(ep, tool):
                    tool_endpoints.append(ep)

        if tool_endpoints:
            print("\n{} ENDPOINTS:".format(tool.upper()))
            display_tool_endpoints(config_manager, tool)
        elif tool == "copilot":
            print("\n{} ENDPOINTS:".format(tool.upper()))
            print(
                "  GitHub Copilot does not use endpoint selection; relies on GITHUB_TOKEN"
            )
