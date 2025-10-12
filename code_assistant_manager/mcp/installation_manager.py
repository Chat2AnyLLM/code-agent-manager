import json
import os
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.prompt import Prompt

from .registry_manager import LocalRegistryManager
from .schema import RemoteServerConfig, ServerSchema, STDIOServerConfig

console = Console()
registry_manager = LocalRegistryManager()


class InstallationManager:
    """Manages installation of MCP servers to specific tools/clients"""

    def __init__(self):
        self.registry_manager = registry_manager

    def install_server(
        self,
        server_name: str,
        client_name: str,
        installation_method: Optional[str] = None,
        force: bool = False,
        scope: str = "user",
        interactive: bool = True,
    ) -> bool:
        """Install an MCP server to a specific client.

        Args:
            server_name: Name of the server to install
            client_name: Name of the client to install to
            installation_method: Specific installation method to use (optional)
            force: Whether to force installation if server already exists
            scope: Configuration scope ("user" or "project")
            interactive: Whether to prompt user for method selection when multiple methods available

        Returns:
            bool: Success or failure
        """
        # Get server schema
        schema = self.registry_manager.get_server_schema(server_name)
        if not schema:
            console.print(
                f"[red]Error:[/] Server '{server_name}' not found in the local registry."
            )
            return False

        # Get the MCP manager and client
        from .manager import MCPManager

        manager = MCPManager()
        client = manager.get_client(client_name)
        if not client:
            console.print(f"[red]Error:[/] Client '{client_name}' is not supported.")
            return False

        # Select installation method
        method = self._select_installation_method(
            schema, installation_method, interactive
        )
        if not method:
            console.print(
                f"[red]Error:[/] No valid installation method found for '{server_name}'."
            )
            return False

        # Check if server is already installed
        if client.is_server_installed(client_name, server_name):
            console.print(
                f"[yellow]Server '{server_name}' is already installed for {client_name}.[/]"
            )
            return True

        # For now, we'll use the existing client's add_server method
        # This requires the server to be in the tool config, so we'll need to add it first
        # But we need to pass the proper configuration from the schema
        server_config = self._configure_server(schema, method)
        if not server_config:
            console.print(f"[red]Error:[/] Failed to configure server '{server_name}'.")
            return False

        success = client.add_server_with_config(server_name, server_config, scope)
        if success:
            console.print(
                f"[green]Successfully installed '{server_name}' to {client_name}![/]"
            )
        else:
            console.print(
                f"[red]Failed to install '{server_name}' to {client_name}.[/]"
            )

        return success

    def _select_installation_method(
        self,
        schema: ServerSchema,
        installation_method: Optional[str] = None,
        interactive: bool = True,
    ) -> Optional[Dict]:
        """Select an installation method for the server.

        Args:
            schema: Server schema
            installation_method: Specific method to use (optional)
            interactive: Whether to prompt user for selection when multiple methods available

        Returns:
            Installation method configuration or None if not found
        """
        if installation_method:
            return schema.installations.get(installation_method)

        # If only one installation method, use it
        if len(schema.installations) == 1:
            return list(schema.installations.values())[0]

        # Multiple installation methods available
        if len(schema.installations) > 1:
            if not interactive:
                # Non-interactive mode: use first method (for tests/backward compatibility)
                return list(schema.installations.values())[0]

            # Interactive mode: prompt user to choose
            console.print(
                f"\n[bold]Multiple installation methods available for '{schema.name}':[/]"
            )

            # Display available methods
            methods_list = list(schema.installations.items())
            for i, (method_name, method) in enumerate(methods_list, 1):
                recommended = " [green](recommended)[/]" if method.recommended else ""
                console.print(
                    f"  {i}. {method_name}: {method.description}{recommended}"
                )

            # Prompt user for selection
            while True:
                try:
                    choice = Prompt.ask(
                        f"Select installation method (1-{len(methods_list)})",
                        default="1",
                    )
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(methods_list):
                        selected_method = methods_list[choice_idx][1]
                        console.print(f"Selected: {methods_list[choice_idx][0]}")
                        return selected_method
                    else:
                        console.print(
                            f"[red]Invalid choice. Please select 1-{len(methods_list)}.[/]"
                        )
                except ValueError:
                    console.print("[red]Invalid input. Please enter a number.[/]")

        return None

    def _configure_server(
        self, schema: ServerSchema, method
    ) -> Optional[STDIOServerConfig]:
        """Configure server with required arguments.

        Args:
            schema: Server schema
            method: Installation method configuration

        Returns:
            Configured server configuration or None if failed
        """
        # For HTTP servers
        if method.type == "http" and method.url:
            return RemoteServerConfig(
                name=schema.name, url=method.url, headers=method.headers
            )

        # For STDIO servers
        # Get required arguments from environment or prompt user
        env_vars = {}
        for arg_name, arg_info in schema.arguments.items():
            # Check if argument is in environment
            env_value = os.environ.get(arg_name)
            if env_value:
                env_vars[arg_name] = env_value
            else:
                # Prompt user for required arguments
                if arg_info.get("required", False):
                    example = arg_info.get("example", "")
                    description = arg_info.get("description", "")
                    if description:
                        console.print(f"[dim]{description}[/]")
                    value = input(f"{arg_name} [{example}]: ").strip()
                    if value:
                        env_vars[arg_name] = value
                    else:
                        console.print(
                            f"[red]Error:[/] Required argument '{arg_name}' not provided."
                        )
                        return None

        return STDIOServerConfig(
            name=schema.name,
            command=method.command or "echo",
            args=method.args,
            env=env_vars,
        )

    def _get_client_manager(self, client_name: str):
        """Get the appropriate client manager for the specified client.

        Args:
            client_name: Name of the client

        Returns:
            Client manager instance or None if not supported
        """
        # Import client managers dynamically to avoid circular imports
        try:
            if client_name == "claude":
                from .claude import ClaudeMCPClient

                return ClaudeMCPClient()
            elif client_name == "codex":
                from .codex import CodexMCPClient

                return CodexMCPClient()
            elif client_name == "droid":
                from .droid import DroidMCPClient

                return DroidMCPClient()
            elif client_name == "copilot":
                from .copilot import CopilotMCPClient

                return CopilotMCPClient()
            elif client_name == "gemini":
                from .gemini import GeminiMCPClient

                return GeminiMCPClient()
            elif client_name == "iflow":
                from .iflow import IflowMCPClient

                return IflowMCPClient()
            elif client_name == "qwen":
                from .qwen import QwenMCPClient

                return QwenMCPClient()
            elif client_name == "codebuddy":
                from .codebuddy import CodeBuddyMCPClient

                return CodeBuddyMCPClient()
            elif client_name == "zed":
                from .zed import ZedMCPClient

                return ZedMCPClient()
            elif client_name == "qodercli":
                from .qodercli import QoderCLIMCPClient

                return QoderCLIMCPClient()
            elif client_name == "neovate":
                from .neovate import NeovateMCPClient

                return NeovateMCPClient()
            else:
                console.print(f"[red]Error:[/] Unsupported client '{client_name}'.")
                return None
        except ImportError as e:
            console.print(
                f"[red]Error:[/] Failed to import client manager for '{client_name}': {e}"
            )
            return None


class BaseClientManager:
    """Base class for client-specific MCP server management"""

    def __init__(self):
        pass

    def server_exists(self, server_name: str) -> bool:
        """Check if a server is already installed for this client.

        Args:
            server_name: Name of the server

        Returns:
            bool: True if server exists, False otherwise
        """
        raise NotImplementedError

    def add_server(self, server_config, force: bool = False) -> bool:
        """Add a server configuration to this client.

        Args:
            server_config: Server configuration to add
            force: Whether to force installation if server already exists

        Returns:
            bool: Success or failure
        """
        raise NotImplementedError


class JSONClientManager(BaseClientManager):
    """Base class for clients that use JSON configuration files"""

    def __init__(self, config_path: str):
        super().__init__()
        self.config_path = Path(config_path)

    def _load_config(self) -> Dict:
        """Load client configuration file.

        Returns:
            Dict containing the client configuration
        """
        if not self.config_path.exists():
            return {"mcpServers": {}}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            console.print(
                f"[red]Error:[/] Failed to load config file {self.config_path}: {e}"
            )
            return {"mcpServers": {}}

    def _save_config(self, config: Dict) -> bool:
        """Save configuration to client config file.

        Args:
            config: Configuration to save

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            console.print(
                f"[red]Error:[/] Failed to save config file {self.config_path}: {e}"
            )
            return False

    def server_exists(self, server_name: str) -> bool:
        """Check if a server is already installed for this client.

        Args:
            server_name: Name of the server

        Returns:
            bool: True if server exists, False otherwise
        """
        config = self._load_config()
        return server_name in config.get("mcpServers", {})

    def add_server(self, server_config, force: bool = False) -> bool:
        """Add a server configuration to this client.

        Args:
            server_config: Server configuration to add
            force: Whether to force installation if server already exists

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Check if server already exists
        if server_config.name in config.get("mcpServers", {}) and not force:
            console.print(
                f"[yellow]Warning:[/] Server '{server_config.name}' already exists."
            )
            return False

        # Convert server config to client format
        client_config = self._to_client_format(server_config)

        # Add server to config
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        config["mcpServers"][server_config.name] = client_config

        # Save config
        return self._save_config(config)

    def _to_client_format(self, server_config) -> Dict:
        """Convert server configuration to client-specific format.

        Args:
            server_config: Server configuration

        Returns:
            Dict containing client-specific configuration
        """
        if hasattr(server_config, "url") and server_config.url:
            # Remote server
            return {
                "url": server_config.url,
                "headers": getattr(server_config, "headers", {}),
            }
        else:
            # STDIO server
            result = {
                "command": getattr(server_config, "command", "echo"),
                "args": getattr(server_config, "args", []),
            }
            env_vars = getattr(server_config, "env", {})
            if env_vars:
                result["env"] = env_vars
            return result
