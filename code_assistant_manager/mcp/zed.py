"""Zed MCP client implementation."""

from .base_client import MCPClient


class ZedMCPClient(MCPClient):
    """MCP client for Zed tool."""

    def __init__(self):
        super().__init__("zed")
