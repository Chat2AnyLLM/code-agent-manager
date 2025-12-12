"""MCP (Model Context Protocol) management package.

This package provides a well-structured, object-oriented approach to managing
MCP servers across different AI tools with proper inheritance and separation of concerns.
"""

from .base import MCPBase
from .base_client import MCPClient
from .clients import (
    ClaudeMCPClient,
    CodeBuddyMCPClient,
    CodexMCPClient,
    ContinueMCPClient,
    CopilotMCPClient,
    CrushMCPClient,
    CursorAgentMCPClient,
    DroidMCPClient,
    GeminiMCPClient,
    IflowMCPClient,
    NeovateMCPClient,
    OpenCodeMCPClient,
    QoderCLIMCPClient,
    QwenMCPClient,
    ZedMCPClient,
)
from .manager import MCPManager

__all__ = [
    "MCPBase",
    "MCPClient",
    "MCPManager",
    "ClaudeMCPClient",
    "CodexMCPClient",
    "GeminiMCPClient",
    "QwenMCPClient",
    "CopilotMCPClient",
    "CodeBuddyMCPClient",
    "CrushMCPClient",
    "CursorAgentMCPClient",
    "DroidMCPClient",
    "IflowMCPClient",
    "ZedMCPClient",
    "QoderCLIMCPClient",
    "NeovateMCPClient",
    "OpenCodeMCPClient",
    "ContinueMCPClient",
]
