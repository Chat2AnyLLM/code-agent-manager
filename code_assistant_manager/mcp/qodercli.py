"""QoderCLI MCP client implementation."""

from .base_client import MCPClient


class QoderCLIMCPClient(MCPClient):
    """MCP client for QoderCLI tool."""

    def __init__(self):
        super().__init__("qodercli")
