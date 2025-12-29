import logging
import os
from pathlib import Path
from typing import List

from code_assistant_manager.tools.config_writers.codex import upsert_codex_profile

from .base import CLITool

logger = logging.getLogger(__name__)


class CodexTool(CLITool):
    """Codex CLI wrapper."""

    command_name = "codex"
    tool_key = "openai-codex"
    install_description = "OpenAI Codex CLI"

    def _write_profile(
        self,
        *,
        endpoint_name: str,
        endpoint_config: dict,
        model: str,
        profile_name: str,
        env_key: str,
        reasoning_effort: str = "low",
    ) -> Path:
        config_path = Path.home() / ".codex" / "config.toml"
        result = upsert_codex_profile(
            config_path=config_path,
            provider=endpoint_name,
            base_url=endpoint_config.get("endpoint", ""),
            env_key=env_key,
            profile=profile_name,
            model=model,
            reasoning_effort=reasoning_effort,
            project_path=Path.cwd().resolve(),
        )

        if result.get("changed"):
            provider_action = "Updated" if result.get("provider_existed") else "Added"
            profile_action = "Updated" if result.get("profile_existed") else "Added"
            print(f"[code-assistant-manager] {provider_action} model provider '{endpoint_name}'")
            print(f"[code-assistant-manager] {profile_action} profile '{profile_name}'")
        else:
            print("[code-assistant-manager] Codex config already up to date")

        return config_path

    def _read_existing_profiles(self, config_path: Path) -> list[str]:
        """Read existing profiles from Codex config.toml."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return []

        if not config_path.exists():
            return []

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            profiles = list(config.get("profiles", {}).keys())
            return profiles
        except Exception as e:
            logger.debug(f"Failed to read existing profiles from {config_path}: {e}")
            return []

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Run the OpenAI Codex CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Codex CLI

        Returns:
            Exit code of the Codex CLI process
        """

        # If caller explicitly selected a Codex profile, do not override it.
        if "-p" in args or "--profile" in args:
            self._load_environment()
            env = os.environ.copy()
            self._set_node_tls_env(env)

            # Display the complete command
            command = ["codex"] + args
            args_str = " ".join(args) if args else ""
            command_str = f"codex {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(command_str)
            print("")

            return self._run_tool_with_env(command, env, "codex", interactive=True)

        # Multi-provider flow: prompt each provider (endpoint) once, then choose which profile to run.
        from code_assistant_manager.menu.menus import display_centered_menu

        self._load_environment()

        if not self._ensure_tool_installed(
            self.command_name, self.tool_key, self.install_description
        ):
            return 1

        endpoints = self.config.get_sections(exclude_common=True)
        endpoints = [
            ep for ep in endpoints if self.endpoint_manager._is_client_supported(ep, "codex")
        ]
        if not endpoints:
            return self._handle_error("No endpoints configured for codex")

        config_path = Path.home() / ".codex" / "config.toml"
        existing_profiles = self._read_existing_profiles(config_path)

        configured_profiles: list[str] = []
        profile_env: dict[str, tuple[str, str]] = {}

        for endpoint_name in endpoints:
            ok, endpoint_config = self.endpoint_manager.get_endpoint_config(endpoint_name)
            if not ok or not endpoint_config:
                continue

            ok, models = self.endpoint_manager.fetch_models(
                endpoint_name, endpoint_config, use_cache_if_available=False
            )
            if not ok or not models:
                continue

            ep_url = endpoint_config.get("endpoint", "")
            ep_desc = endpoint_config.get("description", "") or ep_url
            endpoint_info = f"{endpoint_name} -> {ep_url} -> {ep_desc}"

            if os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1":
                if not models:
                    continue
                selected_models = [models[0]]
            else:
                from code_assistant_manager.menu.menus import select_multiple_models

                ok, selected_models = select_multiple_models(
                    models,
                    f"Select models from {endpoint_info} (Cancel to skip):",
                    cancel_text="Skip",
                )
                if not ok or not selected_models:
                    print(f"Skipped {endpoint_name}\n")
                    continue

            env_key = (
                self.config.get_endpoint_config(endpoint_name).get("api_key_env")
                or "OPENAI_API_KEY"
            )

            # Create profiles for each selected model
            for model in selected_models:
                profile_name = model
                try:
                    self._write_profile(
                        endpoint_name=endpoint_name,
                        endpoint_config=endpoint_config,
                        model=model,
                        profile_name=profile_name,
                        env_key=env_key,
                    )
                except Exception as e:
                    return self._handle_error("Failed to write ~/.codex/config.toml", e)

                configured_profiles.append(profile_name)
            if endpoint_config.get("actual_api_key"):
                profile_env[profile_name] = (env_key, endpoint_config.get("actual_api_key"))

        all_profiles = sorted(set(existing_profiles + configured_profiles))

        if not all_profiles:
            return 0

        profiles = all_profiles
        if len(profiles) == 1:
            selected_profile = profiles[0]
        elif os.environ.get("CODE_ASSISTANT_MANAGER_NONINTERACTIVE") == "1":
            selected_profile = profiles[0]
        else:
            ok, idx = display_centered_menu(
                "Select Codex profile to run:", profiles, "Cancel"
            )
            if not ok or idx is None:
                return 0
            selected_profile = profiles[idx]

        env = os.environ.copy()
        if selected_profile in profile_env:
            env_key, api_key = profile_env[selected_profile]
            if api_key and env_key and not env.get(env_key):
                env[env_key] = api_key
        self._set_node_tls_env(env)

        command = ["codex", "-p", selected_profile] + args

        # Display the complete command
        args_str = " ".join(args) if args else ""
        command_str = f"codex -p {selected_profile} {args_str}".strip()
        print("")
        print("Complete command to execute:")
        print(command_str)
        print("")

        return self._run_tool_with_env(command, env, "codex", interactive=True)
