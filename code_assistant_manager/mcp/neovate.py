"""Neovate MCP client implementation."""

from .base_client import MCPClient


class NeovateMCPClient(MCPClient):
    """MCP client for Neovate tool."""

    def __init__(self):
        super().__init__("neovate")
