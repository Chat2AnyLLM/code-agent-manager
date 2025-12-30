import os
from typing import List, Tuple

from .base import CLITool


class GeminiTool(CLITool):
    """Google Gemini CLI wrapper."""

    command_name = "gemini"
    tool_key = "gemini-cli"
    install_description = "Google Gemini CLI"

    def _check_gemini_auth(self) -> Tuple[bool, str]:
        """
        Check if Gemini authentication is available via environment variables.

        Returns:
            Tuple of (has_auth, auth_type) where auth_type describes which method is used
        """
        # Check for direct API key
        if os.environ.get("GEMINI_API_KEY"):
            return True, "GEMINI_API_KEY"

        # Check for Vertex AI configuration
        vertex_vars = [
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_GENAI_USE_VERTEXAI",
        ]
        missing_vars = [var for var in vertex_vars if not os.environ.get(var)]

        if not missing_vars:
            return True, "Vertex AI"

        # If we have some but not all Vertex AI vars, provide details
        if any(os.environ.get(var) for var in vertex_vars):
            return (
                False,
                f"Partial Vertex AI configuration (missing: {', '.join(missing_vars)})",
            )

        return False, "No authentication detected"

    def _print_auth_hints(self) -> None:
        """Print authentication hints when no valid auth is detected."""
        has_auth, auth_type = self._check_gemini_auth()

        # Only print hints when we don't have valid authentication
        if not has_auth:
            # If we have partial configuration, show what's missing
            if "Partial Vertex AI" in auth_type:
                print(f"  {auth_type}")
            else:
                # No authentication at all, show full hints
                print("  Please set one of the following:")
                print("    1. Direct API key: export GEMINI_API_KEY='your-api-key'")
                print("    2. Vertex AI configuration:")
                print(
                    "       export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'"
                )
                print("       export GOOGLE_CLOUD_PROJECT='your-project-id'")
                print("       export GOOGLE_CLOUD_LOCATION='your-location'")
                print("       export GOOGLE_GENAI_USE_VERTEXAI='true'")

    def run(self, args: List[str] = None) -> int:
        """
        Run the Google Gemini CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Gemini CLI

        Returns:
            Exit code of the Gemini CLI process
        """
        args = args or []
        # Load environment variables first
        self._load_environment()

        # Skip upgrade check for extension commands to avoid the menu
        is_extension_command = args and args[0] == "extensions"
        if not is_extension_command:
            # Check if the tool is installed and prompt for upgrade if needed
            if not self._ensure_tool_installed(
                self.command_name, self.tool_key, self.install_description
            ):
                return 1
        else:
            # For extension commands, just check if the tool is available (no upgrade prompt)
            if not self._check_command_available(self.command_name):
                print(f"Error: {self.command_name} is not installed. Please install {self.install_description} first.")
                return 1

        # Check if we have authentication available via environment variables
        has_auth, auth_type = self._check_gemini_auth()
        if has_auth:
            # Use environment variables directly
            env = os.environ.copy()
            # Respect optional GEMINI_BASE_URL from env, default to empty
            env.setdefault("GEMINI_BASE_URL", os.environ.get("GEMINI_BASE_URL", ""))
            # Set TLS environment for Node.js
            self._set_node_tls_env(env)
            command = ["gemini", *args]

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"gemini {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            return self._run_tool_with_env(command, env, "gemini", interactive=True)

        # If we don't have valid authentication, provide hints and exit
        print("Error: No valid Gemini authentication detected")
        self._print_auth_hints()
        return 1

        # Set up endpoint and model using the endpoint manager
        success, result = self._setup_endpoint_and_models(
            "gemini", select_multiple=False
        )
        if not success:
            return 1

        # Extract endpoint configuration and selected model
        endpoint_config, endpoint_name, model = result

        # Set up environment variables for Gemini
        env = os.environ.copy()
        env["GEMINI_BASE_URL"] = endpoint_config["endpoint"]
        env["GEMINI_API_KEY"] = endpoint_config["actual_api_key"]
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Execute the Gemini CLI with the configured environment
        command = ["gemini", *args]

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"gemini {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "gemini", interactive=True)
