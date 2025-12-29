from typing import List

from .base import CLITool


class QoderCLITool(CLITool):
    """Qoder CLI wrapper."""

    command_name = "qodercli"
    tool_key = "qodercli"
    install_description = "Qoder CLI"

    def run(self, args: List[str] = None) -> int:
        """
        Run the Qoder CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Qoder CLI

        Returns:
            Exit code of the Qoder CLI process
        """
        args = args or []
        # Load environment variables
        load_env = __import__(
            "code_assistant_manager.env_loader", fromlist=["load_env"]
        ).load_env
        load_env()

        # Ensure the Qoder CLI tool is installed
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        # Set up environment for Qoder CLI
        env = __import__("os").environ.copy()
        # Set TLS environment for Node.js
        self._set_node_tls_env(env)

        # Notify user that Qoder CLI is starting
        print("Starting Qoder CLI...")

        # Execute the Qoder CLI with the provided arguments
        try:
            command = ["qodercli"] + args

            # Display the complete command
            args_str = " ".join(args) if args else ""
            command_str = f"qodercli {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            return self._run_tool_with_env(command, env, "qodercli", interactive=True)
        except Exception as e:
            # This shouldn't happen since _run_tool_with_env handles the try/except
            return self._handle_error("Error running qodercli", e)
