"""Copilot agent handler.

Minimal Copilot agent handler that installs agents (markdown files)
into a user-local Copilot agents directory.
"""

import re
import shutil
from pathlib import Path

import yaml

from .base import BaseAgentHandler, logger


def _normalize_front_matter(front_raw: str) -> dict:
    """Parse YAML front matter, handling malformed values.

    Some agent files have unquoted values containing colons which break
    standard YAML parsing. This function attempts standard parsing first,
    then falls back to line-by-line extraction for simple key: value pairs.
    """
    # Try standard YAML parsing first
    try:
        meta = yaml.safe_load(front_raw)
        if isinstance(meta, dict):
            return meta
    except yaml.YAMLError:
        pass

    # Fallback: extract key-value pairs line by line
    # This handles cases where values contain unquoted colons
    meta = {}
    lines = front_raw.split("\n")
    current_key = None
    current_value_lines = []

    for line in lines:
        # Check if line starts a new key (word followed by colon at start)
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if match:
            # Save previous key-value if exists
            if current_key is not None:
                value = "\n".join(current_value_lines).strip()
                meta[current_key] = _parse_yaml_value(value)
            current_key = match.group(1)
            current_value_lines = [match.group(2)]
        elif current_key is not None:
            # Continuation of previous value
            current_value_lines.append(line)

    # Save last key-value
    if current_key is not None:
        value = "\n".join(current_value_lines).strip()
        meta[current_key] = _parse_yaml_value(value)

    return meta


def _parse_yaml_value(value: str):
    """Parse a YAML value string, handling common types."""
    if not value:
        return None

    # Try to parse as YAML for simple types (numbers, booleans, lists)
    try:
        parsed = yaml.safe_load(value)
        # Only use parsed value for simple types, not if it failed to parse properly
        if isinstance(parsed, (bool, int, float, list)):
            return parsed
    except yaml.YAMLError:
        pass

    # Return as string (handles unquoted strings with colons, etc.)
    return value


class CopilotAgentHandler(BaseAgentHandler):
    """Agent handler for GitHub Copilot CLI.

    Copilot agents are supported as markdown instruction files. By convention
    place them under ~/.copilot/agents/ or the client's agents directory.
    """

    @property
    def app_name(self) -> str:
        return "copilot"

    @property
    def _default_agents_dir(self) -> Path:
        return Path.home() / ".copilot" / "agents"

    def install(self, agent) -> Path:
        """Install a Copilot agent as a Markdown file with normalized YAML frontmatter.

        Copilot agent profiles are Markdown files with YAML frontmatter that specifies
        the agent's name, description, tools, and MCP server configurations.
        """
        if not agent.repo_owner or not agent.repo_name:
            raise ValueError(f"Agent '{agent.key}' has no repository information")

        # Ensure install directory exists
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        # Download repository
        temp_dir, _ = self._download_repo(
            agent.repo_owner, agent.repo_name, agent.repo_branch or "main"
        )

        try:
            if agent.agents_path:
                source_path = temp_dir / agent.agents_path.strip("/") / agent.filename
            else:
                source_path = temp_dir / agent.filename

            if not source_path.exists():
                raise ValueError(f"Agent file not found in repository: {source_path}")

            # Read and transform content
            content = source_path.read_text(encoding="utf-8").lstrip("\ufeff")
            parts = content.split("---", 2)
            if len(parts) >= 3:
                front_raw = parts[1].strip()
                body = parts[2].lstrip("\n")

                # Parse YAML front matter with normalization for malformed values
                meta = _normalize_front_matter(front_raw)

                # Description is required for agent profiles
                if not meta.get("description"):
                    raise ValueError(
                        "Copilot agent profile must include a 'description' in YAML front matter"
                    )

                # Default name to filename (without extension) if not provided
                if not meta.get("name"):
                    meta["name"] = agent.filename.rsplit(".", 1)[0]

                # Normalize tools: allow string (comma separated) or list
                if "tools" in meta:
                    tools_raw = meta.get("tools")
                    if isinstance(tools_raw, str):
                        meta["tools"] = [
                            t.strip() for t in tools_raw.split(",") if t.strip()
                        ]
                    elif isinstance(tools_raw, list):
                        meta["tools"] = tools_raw
                    else:
                        # Unexpected type, remove to allow access to all tools
                        meta.pop("tools", None)

                # Leave mcp-servers, model, target as provided (if any)

                # Render normalized front matter back to YAML
                front_serialized = yaml.safe_dump(meta, sort_keys=False).strip()
                new_content = f"---\n{front_serialized}\n---\n\n{body}"
            else:
                # No front matter: agent profile requires a description, so error
                raise ValueError(
                    "Copilot agent file must include YAML front matter with a 'description' field"
                )

            # Keep as .md file (Copilot agent profiles are Markdown)
            dest_path = self.agents_dir / agent.filename
            dest_path.write_text(new_content, encoding="utf-8")
            logger.info(f"Installed agent to: {dest_path}")
            return dest_path
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
