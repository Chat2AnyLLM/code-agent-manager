import os
from typing import Dict, Optional


class ToolEnvironmentBuilder:
    """
    Builder class for constructing environment variables for CLI tools.

    This centralizes common environment variable setup patterns used across
    different AI coding assistant tools, reducing code duplication.
    """

    def __init__(
        self,
        endpoint_config: Dict[str, str],
        model_vars: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the environment builder.

        Args:
            endpoint_config: Dictionary containing endpoint configuration
                           (endpoint URL, API key, etc.)
            model_vars: Optional dictionary of model-related environment variables
        """
        self.endpoint_config = endpoint_config
        self.model_vars = model_vars or {}
        self.env = os.environ.copy()

    def set_base_url(self, env_var: str) -> "ToolEnvironmentBuilder":
        """Set base URL environment variable."""
        self.env[env_var] = self.endpoint_config["endpoint"]
        return self

    def set_api_key(self, env_var: str) -> "ToolEnvironmentBuilder":
        """Set API key environment variable."""
        self.env[env_var] = self.endpoint_config["actual_api_key"]
        return self

    def set_model(
        self, env_var: str, model_key: str = "primary_model"
    ) -> "ToolEnvironmentBuilder":
        """Set model environment variable."""
        if model_key in self.model_vars:
            self.env[env_var] = self.model_vars[model_key]
        return self

    def set_multiple_models(
        self, model_vars: Dict[str, str]
    ) -> "ToolEnvironmentBuilder":
        """Set multiple model-related environment variables."""
        for env_var, model_key in model_vars.items():
            if model_key in self.model_vars:
                self.env[env_var] = self.model_vars[model_key]
            elif "," in model_key:
                # Handle concatenation like 'primary_model,secondary_model'
                parts = model_key.split(",")
                values = []
                for part in parts:
                    part = part.strip()
                    if part in self.model_vars:
                        values.append(self.model_vars[part])
                if values:
                    self.env[env_var] = ",".join(values)
        return self

    def set_custom_var(self, env_var: str, value: str) -> "ToolEnvironmentBuilder":
        """Set a custom environment variable."""
        self.env[env_var] = value
        return self

    def set_node_tls_reject_unauthorized(
        self, value: str = "0"
    ) -> "ToolEnvironmentBuilder":
        """Set Node.js TLS rejection override."""
        self.env["NODE_TLS_REJECT_UNAUTHORIZED"] = value
        return self

    def build(self) -> Dict[str, str]:
        """Return the constructed environment dictionary."""
        return self.env
