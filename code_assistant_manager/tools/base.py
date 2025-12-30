import logging
import os
import subprocess
from typing import Dict, List, Optional, Tuple, Union

from ..config import ConfigManager
from ..env_loader import load_env
from ..exceptions import create_error_handler
from .registry import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class CLITool:
    @staticmethod
    def _is_test_mode() -> bool:
        """Return True when running under pytest to suppress noisy prints during tests."""
        import sys

        return bool(os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules)

    command_name: str = ""
    tool_key: Optional[str] = None
    install_description: str = ""

    def __init__(self, config_manager: ConfigManager):
        cfg_path = getattr(config_manager, "config_path", "<mock>")
        logger.debug(f"Initializing {self.__class__.__name__} with config: {cfg_path}")
        self.config: ConfigManager = config_manager
        # Import EndpointManager from the code_assistant_manager.tools package so tests
        # that patch `code_assistant_manager.tools.EndpointManager` will be effective.
        from code_assistant_manager.tools import EndpointManager  # type: ignore

        self.endpoint_manager: EndpointManager = EndpointManager(config_manager)
        self.tool_registry = TOOL_REGISTRY
        # Instance variable to track upgrade decisions during this session
        self._upgrade_decisions: Dict[str, bool] = {}
        logger.debug(f"{self.__class__.__name__} initialized successfully")

    def run(self, args: List[str] = None) -> int:
        args = args or []

        raise NotImplementedError

    def _handle_error(
        self, message: str, exception: Optional[Exception] = None, exit_code: int = 1
    ) -> int:
        """Handle errors with structured error reporting."""
        if exception:
            error_handler = create_error_handler(self.command_name)
            structured_error = error_handler(exception, message)
            print(structured_error.get_detailed_message())
            logger.error(f"Tool error: {structured_error}")
        else:
            print(f"Error: {message}")
            logger.error(f"Tool error: {message}")
        return exit_code

    def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with standardized error handling.

        Args:
            command: The command to execute as a list of strings
            **kwargs: Additional arguments to pass to subprocess.run

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If the command fails
        """
        logger.debug(f"Executing command: {' '.join(command)}")
        return subprocess.run(command, **kwargs)

    def _check_command_available(self, command: str) -> bool:
        """Check if a command is available in the system PATH."""
        logger.debug(f"Checking if command '{command}' is available")
        try:
            self._run_command(["which", command], capture_output=True, check=True)
            logger.debug(f"Command '{command}' is available")
            return True
        except subprocess.CalledProcessError:
            logger.debug(f"Command '{command}' is not available")
            return False

    def _run_tool_with_env(
        self, command: List[str], env: dict, tool_name: str, interactive: bool = False
    ) -> int:
        """
        Run a tool command with the given environment variables and handle common errors.

        Args:
            command: The command to execute as a list of strings
            env: Environment variables dictionary
            tool_name: Name of the tool for error messages
            interactive: If True, allow interactive I/O (stdin/stdout/stderr)

        Returns:
            Exit code (0 for success, 130 for KeyboardInterrupt, 1 for other errors)
        """
        try:
            logger.debug(f"Executing command: {' '.join(command)}")
            if interactive:

                import sys

                result = subprocess.run(
                    command,
                    env=env,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            else:
                result = subprocess.run(
                    command, env=env, capture_output=True, text=True
                )

            if result.returncode != 0 and not interactive:
                error_handler = create_error_handler(tool_name)
                structured_error = error_handler(
                    Exception(f"Command failed with exit code {result.returncode}"),
                    "Tool execution failed",
                    command=" ".join(command),
                )
                print(structured_error.get_detailed_message())
                if result.stderr:
                    print(f"Error output: {result.stderr}")
                logger.error(f"Tool execution failed: {structured_error}")
                return result.returncode

            return result.returncode if result.returncode is not None else 0
        except KeyboardInterrupt:
            logger.info("Tool execution interrupted by user")
            return 130
        except Exception as e:
            return self._handle_error(f"Error running {tool_name}", e)

    def _get_version(self, command: Optional[str] = None) -> str:
        """Attempt to retrieve a tool's version string.

        Strategy:
        1. Try `<command> --version`
        2. Try `<command> -v`
        3. Try `<command> version`
        Returns full output from stdout or stderr on success, else 'unknown'.
        Note: Callers should use _format_version() to clean and extract version from output.
        """
        cmd = command or self.command_name
        if not cmd:
            return "unknown"
        try:
            version_attempts = [
                [cmd, "--version"],
                [cmd, "-v"],
                [cmd, "version"],
            ]
            for args in version_attempts:
                try:
                    res = self._run_command(args, capture_output=True, text=True)
                    if res.returncode == 0:
                        output = (res.stdout or res.stderr).strip()
                        if output:
                            # Return full output, let _format_version() clean it up
                            return output
                except subprocess.CalledProcessError:
                    continue
            return "unknown"
        except Exception:
            return "unknown"

    def _is_non_interactive_mode(self) -> bool:
        """Check if the tool is running in non-interactive mode."""
        result = os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1"
        logger.debug(f"Non-interactive mode check: {result}")
        return result

    def _prompt_for_upgrade(self, desc: str) -> bool:
        """Prompt user to upgrade an installed tool."""
        from ..menu.base import Colors

        # Respect non-interactive mode
        if self._is_non_interactive_mode():
            print(f"{Colors.GREEN}✓ {desc} is installed{Colors.RESET}")
            return True

        # Try interactive menu first, fall back to text prompt if needed
        try:
            from ..menu.menus import display_simple_menu

            success, idx = display_simple_menu(
                f"{desc} is installed - Upgrade?",
                ["Yes, upgrade to latest version", "No, use current version"],
                "Skip",
            )
        except Exception:
            success = False
            idx = None

        # If user selected "Skip", proceed to next menu without prompting
        if not success:
            print(f"{Colors.GREEN}✓ Using current version of {desc}{Colors.RESET}")
            return False  # Return False to indicate we should skip upgrade

        return idx == 0

    def _perform_upgrade(self, desc: str, install_cmd: str) -> dict:
        """Perform the actual upgrade of a tool.

        Returns a structured dict with keys:
        - success: bool
        - messages: list[str]
        - error: optional str

        This function avoids printing to stdout directly so the CLI
        orchestration layer can control user-visible output.
        """
        from ..upgrades.command_runner import CommandRunner
        from ..upgrades.installer_factory import pick_installer

        messages = []
        messages.append(f"Starting upgrade for {desc}")

        # Use the new upgrade system
        try:
            # Create the appropriate installer
            installer = pick_installer(
                name=self.tool_key or self.command_name,
                install_cmd=install_cmd,
                command_name=self.command_name,
                executor=CommandRunner(),
                logger=logger,
            )

            # Run the upgrade
            result = installer.run()
            if result.get("status") == "success":
                messages.append(f"{desc} upgraded successfully")
                return {"success": True, "messages": messages}
            else:
                messages.append(f"Error: Failed to upgrade {desc}")
                return {
                    "success": False,
                    "messages": messages,
                    "error": "upgrade_failed",
                }
        except Exception as e:
            logger.exception(f"Exception while upgrading {desc}: {e}")
            return {"success": False, "messages": messages, "error": str(e)}

    def _cleanup_npm_package(self, install_cmd: str, messages: list) -> None:
        """Clean up existing npm package before upgrade."""
        try:
            # Extract package name from npm install command
            clean_cmd = install_cmd.replace('"', "").replace("'", "")
            parts = clean_cmd.split()

            # Skip npm/install flags and find package
            i = 0
            while i < len(parts) and parts[i] in [
                "npm",
                "install",
                "i",
                "-g",
                "--global",
            ]:
                i += 1

            if i < len(parts):
                package_part = parts[i]
                # Split on @ but handle scoped packages correctly
                name_parts = package_part.split("@")
                if name_parts[0] == "" and len(name_parts) > 1:
                    # Scoped package like @scope/name@version
                    package_name = "@" + name_parts[1]
                else:
                    # Regular package like name@version
                    package_name = name_parts[0]

                # Get npm root
                try:
                    npm_root_result = self._run_command(
                        ["npm", "root", "-g"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    npm_root = npm_root_result.stdout.strip()
                except subprocess.CalledProcessError:
                    npm_root = None

                # Remove existing package if we can determine path
                if npm_root:
                    if package_name.startswith("@"):
                        # Scoped package like @scope/package
                        scope, name = package_name.split("/", 1)
                        package_path = os.path.join(npm_root, scope, name)
                    else:
                        # Regular package
                        package_path = os.path.join(npm_root, package_name)

                    if os.path.exists(package_path):
                        messages.append(
                            f"Removing existing {package_name} package from {package_path}"
                        )
                        try:
                            self._run_command(["rm", "-rf", package_path], check=True)
                            messages.append(
                                f"Pre-upgrade cleanup completed for {package_name}"
                            )
                        except subprocess.CalledProcessError as e:
                            messages.append(f"Warning: Pre-upgrade cleanup failed: {e}")

        except Exception as e:
            # Don't fail upgrade due to cleanup parsing errors
            messages.append(f"Warning: Failed to parse npm install command: {e}")

    def _prompt_for_installation(self, desc: str) -> bool:
        """Prompt user to install a missing tool."""
        from ..menu.base import Colors
        from ..menu.menus import display_centered_menu

        # Respect non-interactive mode
        if self._is_non_interactive_mode():
            print(
                f"{Colors.YELLOW}{desc} not found and non-interactive mode set. Skipping installation.{Colors.RESET}"
            )
            return False

        success, idx = display_centered_menu(
            f"{desc} not found - Install?", ["Yes, install now", "No, cancel"], "Cancel"
        )
        return success and idx == 0

    def _perform_installation(self, command: str, desc: str, install_cmd: str) -> bool:
        """Perform the actual installation of a tool."""
        from ..menu.base import Colors
        from ..upgrades.command_runner import CommandRunner
        from ..upgrades.installer_factory import pick_installer

        print(f"\nInstalling {desc}...")
        try:
            # Create the appropriate installer
            installer = pick_installer(
                name=self.tool_key or self.command_name,
                install_cmd=install_cmd,
                command_name=command,
                executor=CommandRunner(),
                logger=logger,
            )

            # Run the installation (upgrade classes work for both install and upgrade)
            result = installer.run()
            if result.get("status") == "success":
                print(f"{Colors.GREEN}✓ {desc} installed successfully{Colors.RESET}")
                return True
            else:
                print(f"Error: Failed to install {desc}")
                return False
        except Exception as e:
            logger.exception(f"Exception while installing {desc}: {e}")
            error_handler = create_error_handler(self.command_name)
            structured_error = error_handler(
                e, f"Failed to install {desc}", command=install_cmd
            )
            print(structured_error.get_detailed_message())
            return False

    def _ensure_tool_installed(
        self, command: str, tool_key: Optional[str], desc: str
    ) -> bool:
        """Ensure a tool is installed, prompting for installation or upgrade if needed."""
        from ..menu.base import Colors

        resolved_key = tool_key or command
        install_cmd = (
            self.tool_registry.get_install_command(resolved_key)
            if resolved_key
            else None
        )

        if not command:
            raise ValueError("command must be provided to check tool availability")

        if install_cmd is None:
            return self._check_command_available(command)

        # Check if we already made a decision for this tool in this session
        tool_identifier = f"{command}:{resolved_key or ''}"
        if tool_identifier in self._upgrade_decisions:
            # Use the cached decision to avoid prompting again
            if not self._upgrade_decisions[tool_identifier]:
                # User previously chose to skip upgrade
                return self._check_command_available(command)
            # User previously chose to upgrade, verify tool is still available
            return self._check_command_available(command)

        if self._check_command_available(command):
            # Tool is installed - check if user wants to upgrade
            if self._prompt_for_upgrade(desc):
                result = self._perform_upgrade(desc, install_cmd)
                # Normalize result: support both dict (new) and bool (legacy)
                if isinstance(result, dict):
                    success = bool(result.get("success"))
                else:
                    success = bool(result)
                # Cache the boolean decision
                self._upgrade_decisions[tool_identifier] = success
                return success
            else:
                print(f"{Colors.GREEN}✓ Using current version of {desc}{Colors.RESET}")
                # Cache the decision to skip upgrade
                self._upgrade_decisions[tool_identifier] = False
                return True

        # Tool is not installed - prompt to install
        if self._prompt_for_installation(desc):
            result = self._perform_installation(command, desc, install_cmd)
            return result

        print(
            f"\n{Colors.YELLOW}Installation cancelled. {desc} is required to proceed.{Colors.RESET}"
        )
        return False

    def _set_node_tls_env(self, env: dict) -> None:
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

    def _load_environment(self) -> None:
        """Load environment variables."""
        load_env()

    def _select_endpoint(self, client_name: str) -> Tuple[bool, Optional[str]]:
        """Select an endpoint for the client."""
        try:
            res = self.endpoint_manager.select_endpoint(client_name)
        except Exception:
            return False, None

        if not res or not isinstance(res, tuple) or len(res) != 2:
            return False, None

        success, endpoint_name = res
        if not success or not endpoint_name:
            return False, None

        return True, endpoint_name

    def _get_endpoint_config(
        self, endpoint_name: str
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Get the configuration for an endpoint."""
        success, endpoint_config = self.endpoint_manager.get_endpoint_config(
            endpoint_name
        )
        return success, endpoint_config if success else None

    def _fetch_models(
        self, endpoint_name: str, endpoint_config: Dict[str, str]
    ) -> Tuple[bool, Optional[List[str]]]:
        """Fetch available models from an endpoint."""
        success, models = self.endpoint_manager.fetch_models(
            endpoint_name, endpoint_config
        )
        if not success or not models:
            self._handle_error("Failed to fetch models")
            return False, None
        return True, models

    def _select_models(
        self,
        models: List[str],
        endpoint_name: str,
        endpoint_config: Dict[str, str],
        client_name: str,
        select_multiple: bool,
    ) -> Tuple[bool, Union[str, Tuple[str, str], None]]:
        """Select model(s) with endpoint information."""
        from ..menu.model_selector import ModelSelector

        if select_multiple:
            success, models_selected = (
                ModelSelector.select_two_models_with_endpoint_info(
                    models, endpoint_name, endpoint_config, client_name
                )
            )
            return success, models_selected if success else None
        else:
            success, model = ModelSelector.select_model_with_endpoint_info(
                models, endpoint_name, endpoint_config, "model", client_name
            )
            return success, model if success else None

    def _setup_endpoint_and_models(
        self, client_name: str, select_multiple: bool = False
    ) -> Tuple[
        bool,
        Union[
            Tuple[Dict[str, str], str, Union[str, Tuple[str, str]]],
            Tuple[None, None, None],
        ],
    ]:
        """Set up endpoint and models for a client."""
        # Load environment
        self._load_environment()

        # Check if command is available
        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return False, (None, None, None)

        # Select endpoint
        success, endpoint_name = self._select_endpoint(client_name)
        if not success or not endpoint_name:
            return False, (None, None, None)

        # Get endpoint config
        success, endpoint_config = self._get_endpoint_config(endpoint_name)
        if not success or not endpoint_config:
            return False, (None, None, None)

        # Fetch models
        success, models = self._fetch_models(endpoint_name, endpoint_config)
        if not success or not models:
            return False, (None, None, None)

        # Select model(s) with endpoint information
        success, selected_models = self._select_models(
            models, endpoint_name, endpoint_config, client_name, select_multiple
        )
        if not success or not selected_models:
            return False, (None, None, None)

        return True, (endpoint_config, endpoint_name, selected_models)

    def _validate_and_setup_tool(
        self, tool_name: str, select_multiple: bool = False
    ) -> Tuple[bool, Tuple[Dict[str, str], str, Union[str, Tuple[str, str]]]]:
        """
        Common validation and setup pattern used by all CLI tools.

        This method encapsulates the repeated pattern of setting up endpoint and models,
        and unpacking the results, which was duplicated across all tool implementations.

        Args:
            tool_name: Name of the tool for endpoint selection
            select_multiple: Whether to select multiple models (for tools like Claude)

        Returns:
            Tuple of (success, (endpoint_config, endpoint_name, model(s)))
            Returns (False, None) on failure
        """
        success, result = self._setup_endpoint_and_models(tool_name, select_multiple)
        if not success:
            return False, (None, None, None)

        return True, result
