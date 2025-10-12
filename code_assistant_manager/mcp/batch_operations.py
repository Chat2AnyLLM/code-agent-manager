"""Batch operation utilities.

Provides functions for performing batch operations on MCP servers.
"""


def _batch_operation_with_scope(
    operation_func, scope: str = "user", operation_name: str = "operation"
) -> bool:
    """
    Generic helper for batch operations (add_all, remove_all) with scope handling.

    Args:
        operation_func: Function to call for each server (should take server_name and server_cfg, return bool)
        scope: Configuration scope
        operation_name: Name of the operation for logging

    Returns:
        bool: Overall success
    """
    # This would need access to tool_configs and print_squared_frame from the main client
    # For now, this is a placeholder that would need to be integrated properly
    return False
