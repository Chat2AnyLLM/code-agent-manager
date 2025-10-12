"""Configuration path management utilities.

Provides functions for finding and managing MCP configuration file paths.
"""

from pathlib import Path
from typing import List


def _get_config_locations(tool_name: str) -> List[Path]:
    """Get possible MCP configuration file locations for a tool."""
    locations = []
    home = Path.home()

    # Common config directory patterns
    config_patterns = [
        home / ".config" / tool_name.capitalize() / "mcp.json",
        home / ".config" / tool_name / "mcp.json",
        home / ".local" / "share" / tool_name.capitalize() / "mcp.json",
        home / ".local" / "share" / tool_name / "mcp.json",
        home / f".{tool_name}" / "mcp.json",
        home / f".{tool_name}.config" / "mcp.json",
    ]

    # Tool-specific locations
    tool_specific = {
        "cursor": [home / ".cursor" / "mcp.json"],
        "claude": [
            home / ".config" / "Claude" / "mcp.json",
            home / ".local" / "share" / "claude" / "mcp.json",
            home / "Library" / "Application Support" / "Claude" / "mcp.json",
        ],
        "gemini": [
            home / ".config" / "Google" / "Gemini" / "mcp.json",
            home / ".gemini" / "mcp.json",
            home / ".gemini" / "settings.json",
            Path.cwd() / ".gemini" / "settings.json",
        ],
        "copilot": [
            home / ".copilot" / "mcp-config.json",
            home / ".copilot" / "mcp.json",
            home / ".config" / "GitHub" / "Copilot" / "mcp.json",
        ],
        "codex": [
            home / ".config" / "GitHub" / "Codex" / "mcp.json",
            home / ".codex" / "mcp.json",
        ],
    }

    # Add tool-specific locations if available
    if tool_name in tool_specific:
        locations.extend(tool_specific[tool_name])

    # Add common patterns
    locations.extend(config_patterns)

    # Add project-level configs (check current directory and parent directories)
    try:
        current_dir = Path.cwd()
        for _ in range(5):  # Check up to 5 levels up
            # Common project config files
            project_configs = [
                current_dir / ".mcp.json",
                current_dir / ".gemini" / "settings.json",
                current_dir / "mcp.json",
            ]
            for config in project_configs:
                if config.exists():
                    locations.append(config)
            current_dir = current_dir.parent
            if current_dir == current_dir.parent:  # Reached root
                break
    except:
        pass

    return locations
