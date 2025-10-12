"""MCP Server Schema and Configuration Models

Based on the mcpm.sh project methodology for managing MCP servers.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class BaseServerConfig(BaseModel):
    """Base server configuration class"""

    name: str
    profile_tags: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def add_profile_tag(self, tag: str) -> None:
        """Add a profile tag to this server if not already present."""
        if tag not in self.profile_tags:
            self.profile_tags.append(tag)

    def remove_profile_tag(self, tag: str) -> None:
        """Remove a profile tag from this server if present."""
        if tag in self.profile_tags:
            self.profile_tags.remove(tag)

    def has_profile_tag(self, tag: str) -> bool:
        """Check if this server has a specific profile tag."""
        return tag in self.profile_tags


class STDIOServerConfig(BaseServerConfig):
    """Configuration for STDIO-based MCP servers"""

    command: str
    args: List[str] = []
    env: Dict[str, str] = {}

    def get_filtered_env_vars(self, env: Dict[str, str]) -> Dict[str, str]:
        """Get filtered environment variables with empty values removed

        This is a utility for clients to filter out empty environment
        variables, regardless of client-specific formatting.

        Args:
            env: Dictionary of environment variables to use for resolving
                 ${VAR_NAME} references.

        Returns:
            Dictionary of non-empty environment variables
        """
        if not self.env:
            return {}

        # Use provided environment without falling back to os.environ
        environment = env

        # Keep all environment variables, including empty strings
        filtered_env = {}
        for key, value in self.env.items():
            # For environment variable references like ${VAR_NAME}, check if the variable exists
            # and has a non-empty value. If it doesn't exist or is empty, exclude it.
            if value is not None and isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # Extract the variable name from ${VAR_NAME}
                    env_var_name = value[2:-1]
                    env_value = environment.get(env_var_name, "")
                    # Include all values, even empty ones
                    filtered_env[key] = env_value
                else:
                    # Include all values, even empty ones
                    filtered_env[key] = value

        return filtered_env


class RemoteServerConfig(BaseServerConfig):
    """Configuration for remote HTTP/SSE-based MCP servers"""

    url: str
    headers: Dict[str, Any] = {}

    def to_mcp_proxy_stdio(self) -> STDIOServerConfig:
        proxy_args = [
            "mcp-proxy",
            self.url,
        ]
        if self.headers:
            proxy_args.append("--headers")
            for key, value in self.headers.items():
                proxy_args.append(f"{key}")
                proxy_args.append(f"{value}")

        return STDIOServerConfig(
            name=self.name,
            command="uvx",
            args=proxy_args,
        )


class CustomServerConfig(BaseServerConfig):
    """Configuration for non-standard MCP servers in client configurations.

    This class is used for parsing non-standard MCP configs that appear in client
    configuration files (like Claude Desktop, Goose, etc.) but don't fit into the
    standard STDIO or HTTP/SSE server models. These configs are client-specific
    and are not processed by MCPM's proxy system.

    Examples might include:
    - Built-in servers in specific clients
    - Client-specific transport mechanisms
    - Proprietary server configurations

    The `config` field stores the raw configuration as-is from the client config file.
    """

    config: Dict[str, Any]


ServerConfig = Union[STDIOServerConfig, RemoteServerConfig, CustomServerConfig]


# Profile metadata - servers are now associated via virtual tags
class ProfileMetadata(BaseModel):
    """Metadata for virtual profiles"""

    name: str
    api_key: Optional[str] = None
    description: Optional[str] = None
    # Additional metadata can be added here (sharing settings, etc.)


class InstallationMethod(BaseModel):
    """Installation method for an MCP server"""

    type: str  # npm, docker, uvx, http, python, cli, custom, etc.
    command: Optional[str] = None
    args: List[str] = []
    package: Optional[str] = None
    env: Dict[str, str] = {}
    url: Optional[str] = None
    headers: Dict[str, str] = {}
    description: Optional[str] = None
    recommended: bool = False


class ServerSchema(BaseModel):
    """Schema for an MCP server as defined in the registry"""

    name: str
    display_name: Optional[str] = None
    description: str = ""
    repository: Optional[Union[str, Dict[str, str]]] = (
        None  # Support both string and object format
    )
    license: Optional[str] = None
    homepage: Optional[str] = None
    author: Optional[Union[str, Dict[str, Any]]] = (
        None  # Support both string and object format
    )
    installations: Dict[str, InstallationMethod] = {}
    arguments: Dict[str, Dict[str, Any]] = {}
    tools: Union[List[str], List[Dict[str, Any]]] = (
        []
    )  # Support both simple strings and detailed objects
    resources: Union[List[str], List[Dict[str, Any]]] = (
        []
    )  # Support both simple strings and detailed objects
    prompts: Union[List[str], List[Dict[str, Any]]] = (
        []
    )  # Support both simple strings and detailed objects
    categories: List[str] = []
    tags: List[str] = []
    examples: List[Dict[str, str]] = []  # Richer examples with title/description/prompt
    is_official: bool = False
    is_archived: bool = False
    docker_url: Optional[str] = None

    def get_tools_list(self) -> List[str]:
        """Get tools as a simple list of strings for backward compatibility"""
        if isinstance(self.tools, list) and self.tools:
            if isinstance(self.tools[0], str):
                return self.tools
            elif isinstance(self.tools[0], dict):
                return [
                    tool.get("name", "")
                    for tool in self.tools
                    if isinstance(tool, dict)
                ]
        return []

    def get_resources_list(self) -> List[str]:
        """Get resources as a simple list of strings for backward compatibility"""
        if isinstance(self.resources, list) and self.resources:
            if isinstance(self.resources[0], str):
                return self.resources
            elif isinstance(self.resources[0], dict):
                return [
                    res.get("name", "")
                    for res in self.resources
                    if isinstance(res, dict)
                ]
        return []

    def get_prompts_list(self) -> List[str]:
        """Get prompts as a simple list of strings for backward compatibility"""
        if isinstance(self.prompts, list) and self.prompts:
            if isinstance(self.prompts[0], str):
                return self.prompts
            elif isinstance(self.prompts[0], dict):
                return [
                    prompt.get("name", "")
                    for prompt in self.prompts
                    if isinstance(prompt, dict)
                ]
        return []
