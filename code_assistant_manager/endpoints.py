"""Endpoint management for Code Assistant Manager."""

import contextlib
import importlib
import io
import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import ConfigManager, validate_api_key, validate_model_id, validate_url
from .exceptions import EndpointError, TimeoutError, create_error_handler
from .menu.menus import display_centered_menu


@dataclass
class CacheResult:
    """Result from cache operations."""

    is_valid: bool
    models: List[str]
    should_use: bool = False


class ModelCache:
    """Handles model list caching operations."""

    def __init__(self, cache_dir: Path, config: ConfigManager):
        self.cache_dir = cache_dir
        self.config = config

    def get_cache_file(self, endpoint_name: str) -> Path:
        """Get the cache file path for an endpoint."""
        return (
            self.cache_dir / f"code_assistant_manager_models_cache_{endpoint_name}.txt"
        )

    def get_ttl(self) -> int:
        """Get cache TTL in seconds."""
        return int(self.config.get_common_config().get("cache_ttl_seconds", 86400))

    def read_cache(self, endpoint_name: str) -> CacheResult:
        """
        Read models from cache if valid.

        Returns:
            CacheResult with validity status and models if valid
        """
        cache_file = self.get_cache_file(endpoint_name)
        if not cache_file.exists():
            return CacheResult(is_valid=False, models=[])

        try:
            with open(cache_file, "r") as f:
                lines = f.readlines()

            if not lines:
                return CacheResult(is_valid=False, models=[])

            # First line should be timestamp, rest are models
            cache_time_str = lines[0].strip()
            if not cache_time_str.isdigit():
                return CacheResult(is_valid=False, models=[])

            cache_time = int(cache_time_str)
            current_time = int(time.time())

            if (current_time - cache_time) >= self.get_ttl():
                return CacheResult(is_valid=False, models=[])

            # Cache is valid
            models = [line.strip() for line in lines[1:] if line.strip()]
            return CacheResult(is_valid=True, models=models)

        except Exception as e:
            print(f"Warning: Error reading cache: {e}")
            return CacheResult(is_valid=False, models=[])

    def write_cache(self, endpoint_name: str, models: List[str]) -> None:
        """Write models to cache with timestamp."""
        cache_file = self.get_cache_file(endpoint_name)
        with open(cache_file, "w") as f:
            f.write(f"{int(time.time())}\n")
            for model in models:
                f.write(f"{model}\n")

    def prompt_use_cache(self, cache_result: CacheResult) -> CacheResult:
        """
        Prompt user whether to use cached data.

        Returns:
            CacheResult with should_use set based on user choice
        """
        success, idx = display_centered_menu(
            "Model List Cache Available",
            ["Use cached model list", "Refresh from server"],
            "Cancel",
        )

        if success and idx == 0:
            return CacheResult(
                is_valid=cache_result.is_valid,
                models=cache_result.models,
                should_use=True,
            )

        return CacheResult(
            is_valid=cache_result.is_valid, models=cache_result.models, should_use=False
        )


class EndpointManager:
    """Manages AI provider endpoints and model fetching."""

    # Supported internal modules for model listing
    INTERNAL_MODEL_MODULES = (
        "code_assistant_manager.v1_models",
    )

    # Proxy environment variables to manage
    PROXY_ENV_VARS = [
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "no_proxy",
        "NO_PROXY",
    ]

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize EndpointManager.

        Args:
            config_manager: ConfigManager instance
        """
        self.config: ConfigManager = config_manager
        self.cache_dir: Path = (
            Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            / "code-assistant-manager"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._model_cache = ModelCache(self.cache_dir, config_manager)

    def select_endpoint(
        self, client_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Display endpoint selection menu.

        Args:
            client_name: Optional client name to filter endpoints

        Returns:
            Tuple of (success, endpoint_name)
        """
        endpoints = self.config.get_sections(exclude_common=True)

        if not endpoints:
            print("Error: No endpoints configured in settings.conf")
            return False, None

        # Filter endpoints by client if specified
        if client_name:
            filtered = []
            for ep in endpoints:
                if self._is_client_supported(ep, client_name):
                    filtered.append(ep)
            endpoints = filtered

            if not endpoints:
                print(
                    f"Error: No endpoints configured for client '{client_name}' in settings.conf"
                )
                return False, None

        # Build endpoint choices with descriptions
        choices = []
        for ep in endpoints:
            ep_config = self.config.get_endpoint_config(ep)
            ep_url = ep_config.get("endpoint", "")
            ep_desc = ep_config.get("description", "") or ep_url
            choices.append(f"{ep} -> {ep_url} -> {ep_desc}")

        # Display menu
        title = (
            f"Select Endpoint for {client_name}" if client_name else "Select Endpoint"
        )
        success, idx = display_centered_menu(title, choices, "Cancel")

        if success and idx is not None:
            return True, endpoints[idx]

        return False, None

    def get_endpoint_config(self, endpoint_name: str) -> Tuple[bool, Dict[str, str]]:
        """
        Get complete endpoint configuration.

        Args:
            endpoint_name: Name of the endpoint

        Returns:
            Tuple of (success, config_dict)
        """
        config = self.config.get_endpoint_config(endpoint_name)
        if not config:
            print(f"Error: Endpoint '{endpoint_name}' not found in configuration")
            return False, {}

        # Validate endpoint URL
        endpoint_url = config.get("endpoint", "")
        if not validate_url(endpoint_url):
            error = EndpointError(
                f"Endpoint URL failed validation: {endpoint_url}",
                endpoint=endpoint_name,
                suggestions=[
                    "Check that the endpoint URL is properly formatted",
                    "Ensure the URL starts with http:// or https://",
                    "Verify the endpoint is accessible",
                ],
            )
            print(error.get_detailed_message())
            return False, {}

        # Get API key
        actual_api_key = self._resolve_api_key(endpoint_name, config)

        # Validate API key if present
        if actual_api_key and not validate_api_key(actual_api_key):
            error = EndpointError(
                "API key failed validation",
                endpoint=endpoint_name,
                suggestions=[
                    "Check that the API key is properly formatted",
                    "Verify the API key is valid and not expired",
                    "Ensure the API key has the required permissions",
                ],
            )
            print(error.get_detailed_message())
            return False, {}

        # Get proxy settings if use_proxy is true
        proxy_settings = {}
        use_proxy_value = config.get("use_proxy", "false")
        use_proxy = str(use_proxy_value).lower() == "true"
        if use_proxy:
            common_config = self.config.get_common_config()
            proxy_settings = {
                "http_proxy": common_config.get("http_proxy", ""),
                "https_proxy": common_config.get("https_proxy", ""),
                "no_proxy": common_config.get("no_proxy", ""),
            }

        # Display confirmation
        desc = config.get("description", endpoint_url)
        print(f"Using endpoint '{endpoint_name}' ({desc}) -> {endpoint_url}")

        result = {
            **config,
            "actual_api_key": actual_api_key,
            "proxy_settings": json.dumps(proxy_settings),
        }

        return True, result

    def fetch_models(
        self,
        endpoint_name: str,
        endpoint_config: Dict[str, str],
        use_cache_if_available: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Fetch available models from endpoint.

        Args:
            endpoint_name: Name of the endpoint
            endpoint_config: Endpoint configuration
            use_cache_if_available: If True, prompt user about using cache

        Returns:
            Tuple of (success, models_list)
        """
        # Check cache first
        if use_cache_if_available:
            cache_result = self._check_and_use_cache(endpoint_name)
            if cache_result.should_use:
                return True, cache_result.models

        # Check if static list of models is provided
        list_of_models = endpoint_config.get("list_of_models", None)
        if list_of_models is not None:
            if isinstance(list_of_models, list):
                print(f"Using static model list ({len(list_of_models)} models)")
                models = [m for m in list_of_models if validate_model_id(str(m))]
                self._model_cache.write_cache(endpoint_name, models)
                return True, models
            else:
                print("Warning: list_of_models is not a list, ignoring")

        # Fetch fresh models using command
        list_cmd = endpoint_config.get("list_models_cmd", "")
        if not list_cmd:
            print("Warning: No list_models_cmd or list_of_models configured, using empty model list")
            return True, []

        print("Fetching model list...")
        print("Executing configured list command (redacted)")

        # Prepare environment
        env = self._prepare_environment(endpoint_config)

        try:
            output = self._execute_model_command(list_cmd, env)
            if output is None:
                return True, []

            models = self._parse_models_output(output)
            self._model_cache.write_cache(endpoint_name, models)
            return True, models

        except subprocess.TimeoutExpired:
            return self._handle_timeout_error(endpoint_name)
        except Exception as e:
            return self._handle_fetch_error(e, endpoint_name, list_cmd)

    def _check_and_use_cache(self, endpoint_name: str) -> CacheResult:
        """Check cache and optionally prompt user to use it."""
        cache_result = self._model_cache.read_cache(endpoint_name)
        if cache_result.is_valid:
            return self._model_cache.prompt_use_cache(cache_result)
        return cache_result

    def _prepare_environment(self, endpoint_config: Dict[str, str]) -> Dict[str, str]:
        """Prepare environment variables for model fetch command."""
        env = os.environ.copy()
        env["endpoint"] = endpoint_config.get("endpoint", "")
        env["api_key"] = endpoint_config.get("actual_api_key", "")

        keep_proxy_value = endpoint_config.get("keep_proxy_config", "false")
        keep_proxy = str(keep_proxy_value).lower() == "true"

        if keep_proxy and endpoint_config.get("proxy_settings"):
            self._apply_proxy_settings(env, endpoint_config)
        else:
            self._remove_proxy_settings(env)

        return env

    def _apply_proxy_settings(
        self, env: Dict[str, str], endpoint_config: Dict[str, str]
    ) -> None:
        """Apply proxy settings to environment."""
        try:
            proxy_settings = json.loads(endpoint_config.get("proxy_settings", "{}"))
            for key, value in proxy_settings.items():
                if value:
                    env[key] = value
        except json.JSONDecodeError:
            pass

    def _remove_proxy_settings(self, env: Dict[str, str]) -> None:
        """Remove proxy settings from environment."""
        for key in self.PROXY_ENV_VARS:
            env.pop(key, None)

    def _execute_model_command(
        self, list_cmd: str, env: Dict[str, str]
    ) -> Optional[str]:
        """
        Execute the model listing command.

        Returns:
            Command output string, or None if command failed
        """
        tokens = shlex.split(list_cmd)
        if not tokens:
            return None

        # Try internal module execution
        if self._is_internal_module_command(tokens):
            return self._execute_internal_module(tokens[2], env)

        # Try literal model list (command not found on PATH)
        if shutil.which(tokens[0]) is None:
            return " ".join(tokens).strip()

        # Execute as subprocess
        return self._execute_subprocess(tokens, env)

    def _is_internal_module_command(self, tokens: List[str]) -> bool:
        """Check if command is an internal module invocation."""
        return (
            len(tokens) >= 3
            and tokens[1] == "-m"
            and tokens[2] in self.INTERNAL_MODEL_MODULES
        )

    def _execute_internal_module(self, module_name: str, env: Dict[str, str] = None) -> Optional[str]:
        """Execute an internal Python module for model listing."""
        try:
            mod = importlib.import_module(module_name)

            # Temporarily set environment variables if provided
            old_env = {}
            if env:
                for key, value in env.items():
                    if key in os.environ:
                        old_env[key] = os.environ[key]
                    os.environ[key] = value

            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    mod.list_models()
                return buf.getvalue().strip()
            finally:
                # Restore original environment variables
                for key, value in old_env.items():
                    os.environ[key] = value
                for key in env.keys():
                    if key not in old_env and key in os.environ:
                        del os.environ[key]

        except Exception as e:
            print(f"Warning: Failed to load module {module_name}: {e}")
            return None

    def _execute_subprocess(
        self, tokens: List[str], env: Dict[str, str]
    ) -> Optional[str]:
        """Execute command as subprocess."""
        toolbox_dir = Path(__file__).parent.parent
        result = subprocess.run(
            tokens,
            shell=False,
            capture_output=True,
            text=True,
            cwd=toolbox_dir,
            env=env,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"Warning: Command failed with return code {result.returncode}")
            if result.stderr:
                print(f"Command stderr: {result.stderr}")
            return None

        output = result.stdout.strip()
        if not output:
            print("Warning: Command returned no output")
            return None

        return output

    def _handle_timeout_error(self, endpoint_name: str) -> Tuple[bool, List[str]]:
        """Handle timeout error with optional cache fallback."""
        error = TimeoutError(
            f"Model fetch command timed out for endpoint '{endpoint_name}'",
            tool_name="model_fetch",
            timeout_seconds=60,
            suggestions=[
                "Check network connectivity",
                "Verify the endpoint is responsive",
                "Try again with a longer timeout",
                "Check if the endpoint requires authentication",
            ],
        )
        print(error.get_detailed_message())
        return self._try_cache_fallback(endpoint_name, "timeout")

    def _handle_fetch_error(
        self, e: Exception, endpoint_name: str, list_cmd: str
    ) -> Tuple[bool, List[str]]:
        """Handle general fetch error with optional cache fallback."""
        error_handler = create_error_handler("model_fetch")
        structured_error = error_handler(
            e,
            f"Error fetching models from endpoint '{endpoint_name}'",
            command=list_cmd,
            endpoint=endpoint_name,
        )
        print(structured_error.get_detailed_message())
        return self._try_cache_fallback(endpoint_name, "error")

    def _try_cache_fallback(
        self, endpoint_name: str, reason: str
    ) -> Tuple[bool, List[str]]:
        """Try to use cache as fallback after an error."""
        cache_result = self._model_cache.read_cache(endpoint_name)
        if cache_result.is_valid:
            print(f"Using cached model list due to {reason}")
            return True, cache_result.models
        return False, []

    def _resolve_api_key(
        self, endpoint_name: str, endpoint_config: Dict[str, str]
    ) -> str:
        """
        Resolve API key from various sources.

        Priority order:
        1. api_key_env environment variable
        2. Dynamic env var API_KEY_<ENDPOINT_NAME>
        3. Special cases (copilot-api, litellm)
        4. Generic API_KEY
        5. Config file value
        """
        # 1. Check api_key_env variable
        api_key_env = endpoint_config.get("api_key_env", "")
        if api_key_env and api_key_env in os.environ:
            val = os.environ.get(api_key_env, "")
            if val:
                return val

        # 2. Check dynamic env var API_KEY_<ENDPOINT_NAME>
        dynamic_var = f"API_KEY_{endpoint_name.upper().replace('-', '_')}"
        if dynamic_var in os.environ:
            val = os.environ.get(dynamic_var, "")
            if val:
                return val

        # 3. Check special cases
        if endpoint_name == "copilot-api" and "API_KEY_COPILOT" in os.environ:
            val = os.environ.get("API_KEY_COPILOT", "")
            if val:
                return val
        if endpoint_name == "litellm" and "API_KEY_LITELLM" in os.environ:
            val = os.environ.get("API_KEY_LITELLM", "")
            if val:
                return val

        # 4. Check generic API_KEY
        if "API_KEY" in os.environ:
            val = os.environ.get("API_KEY", "")
            if val:
                return val

        # 5. Check config file value
        return endpoint_config.get("api_key", "")

    def _is_client_supported(self, endpoint_name: str, client_name: str) -> bool:
        """Check if endpoint supports a client."""
        endpoint_config = self.config.get_endpoint_config(endpoint_name)
        supported = endpoint_config.get("supported_client", "")

        # If no restriction or empty client name, allow all
        if not supported or not client_name:
            return True

        # Check if client is in the comma-separated list
        clients = [c.strip() for c in supported.split(",")]
        return client_name in clients

    def _parse_models_output(self, output: str) -> List[str]:
        """Parse model list from various output formats."""
        # Try JSON parsing first
        try:
            data = json.loads(output)
            models = self._parse_json_models(data)
            if models:
                return models
        except json.JSONDecodeError:
            pass

        # Fall back to text parsing
        return self._parse_text_models(output)

    def _parse_json_models(self, data) -> List[str]:
        """Parse models from JSON data."""
        models = []

        if isinstance(data, dict) and "data" in data:
            # OpenAI format
            items = data["data"]
        elif isinstance(data, list):
            items = data
        else:
            return []

        for item in items:
            if isinstance(item, dict) and "id" in item:
                model_id = item["id"]
                if validate_model_id(model_id):
                    models.append(model_id)

        return models

    def _parse_text_models(self, output: str) -> List[str]:
        """Parse model list from text output (space or newline separated)."""
        # Check if output looks like an error message
        if "expected" in output.lower() or "error" in output.lower():
            return []

        models = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try space-separated values
            for token in line.split():
                token = token.strip()
                if token and validate_model_id(token):
                    models.append(token)

        return models
