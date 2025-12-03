"""Prompt manager that coordinates all tool-specific handlers."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from .base import BasePromptHandler
from .claude import ClaudePromptHandler
from .codebuddy import CodebuddyPromptHandler
from .codex import CodexPromptHandler
from .copilot import CopilotPromptHandler
from .gemini import GeminiPromptHandler
from .models import Prompt

logger = logging.getLogger(__name__)

# Registry of all available prompt handlers
PROMPT_HANDLERS: Dict[str, Type[BasePromptHandler]] = {
    "claude": ClaudePromptHandler,
    "codex": CodexPromptHandler,
    "gemini": GeminiPromptHandler,
    "copilot": CopilotPromptHandler,
    "codebuddy": CodebuddyPromptHandler,
}

# Valid app types
VALID_APP_TYPES = list(PROMPT_HANDLERS.keys())

# Apps that support user-level prompts
USER_LEVEL_APPS = ["claude", "codex", "gemini"]


def generate_unique_id(prefix: str = "prompt") -> str:
    """Generate a unique ID with a short UUID suffix."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}-{short_uuid}"


def get_handler(app_type: str) -> BasePromptHandler:
    """Get a prompt handler instance for the specified app type."""
    handler_class = PROMPT_HANDLERS.get(app_type)
    if not handler_class:
        raise ValueError(f"Unknown app type: {app_type}. Valid: {VALID_APP_TYPES}")
    return handler_class()


class PromptManager:
    """Manages prompts storage and retrieval across all tools."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        handler_overrides: Optional[Dict[str, Dict]] = None,
    ):
        """Initialize prompt manager.

        Args:
            config_dir: Configuration directory for prompt storage
            handler_overrides: Dict of app_type -> {'user_path': Path, 'project_filename': str}
                              for testing purposes
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "code-assistant-manager"
        self.config_dir = Path(config_dir)
        self.prompts_file = self.config_dir / "prompts.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize handlers with optional overrides
        self._handlers: Dict[str, BasePromptHandler] = {}
        for name, cls in PROMPT_HANDLERS.items():
            overrides = (handler_overrides or {}).get(name, {})
            self._handlers[name] = cls(
                user_path_override=overrides.get("user_path"),
                project_filename_override=overrides.get("project_filename"),
            )

    def get_handler(self, app_type: str) -> BasePromptHandler:
        """Get the handler for a specific app type."""
        handler = self._handlers.get(app_type)
        if not handler:
            raise ValueError(f"Unknown app type: {app_type}. Valid: {VALID_APP_TYPES}")
        return handler

    @property
    def copilot(self) -> CopilotPromptHandler:
        """Get the Copilot handler for Copilot-specific operations."""
        return self._handlers["copilot"]  # type: ignore

    # ==================== Prompt Storage Operations ====================

    def _load_data(self) -> Tuple[Dict[str, Prompt], Dict[str, str]]:
        """Load prompts and active prompts mapping from file."""
        if not self.prompts_file.exists():
            return {}, {}

        try:
            with open(self.prompts_file, "r") as f:
                data = json.load(f)

            prompts = {}
            active_prompts = {}

            # Extract prompts
            for prompt_id, prompt_data in data.items():
                if prompt_id != "_activePrompts":
                    prompts[prompt_id] = Prompt.from_dict(prompt_data)

            # Extract active prompts mapping
            if "_activePrompts" in data:
                active_prompts = data["_activePrompts"]

            return prompts, active_prompts
        except Exception as e:
            logger.warning(f"Failed to load prompts: {e}")
            return {}, {}

    def _load_prompts(self) -> Dict[str, Prompt]:
        """Load prompts from file."""
        prompts, _ = self._load_data()
        return prompts

    def _load_active_prompts(self) -> Dict[str, str]:
        """Load active prompts mapping from file."""
        _, active_prompts = self._load_data()
        return active_prompts

    def get_all(self) -> Dict[str, Prompt]:
        """Get all prompts."""
        return self._load_prompts()

    def get(self, prompt_id: str) -> Optional[Prompt]:
        """Get a specific prompt."""
        prompts = self._load_prompts()
        return prompts.get(prompt_id)

    def get_active_prompt(
        self, app_type: str, level: str = "user", project_dir: Optional[Path] = None
    ) -> Optional[str]:
        """Get the active prompt ID for a specific app/level combination."""
        active_prompts = self._load_active_prompts()
        key = self._make_active_key(app_type, level, project_dir)
        return active_prompts.get(key)

    def set_active_prompt(
        self,
        prompt_id: str,
        app_type: str,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> None:
        """Set the active prompt for a specific app/level combination."""
        prompts = self._load_prompts()
        active_prompts = self._load_active_prompts()

        if prompt_id not in prompts:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")

        key = self._make_active_key(app_type, level, project_dir)
        active_prompts[key] = prompt_id
        self._save_data(prompts, active_prompts)
        logger.info(f"Set active prompt: {prompt_id} for {app_type} ({level})")

    def _make_active_key(
        self, app_type: str, level: str, project_dir: Optional[Path]
    ) -> str:
        """Create a key for the active prompts mapping."""
        if level == "project":
            # For project level, include project path to distinguish different projects
            project_path = str(project_dir or Path.cwd())
            return f"{app_type}:{level}:{project_path}"
        else:
            return f"{app_type}:{level}"

    def _save_data(
        self, prompts: Dict[str, Prompt], active_prompts: Dict[str, str]
    ) -> None:
        """Save prompts and active prompts mapping to file."""
        try:
            data = {
                prompt_id: prompt.to_dict() for prompt_id, prompt in prompts.items()
            }
            # Always include activePrompts
            data["_activePrompts"] = active_prompts
            with open(self.prompts_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(
                f"Saved {len(prompts)} prompts and {len(active_prompts)} active mappings to {self.prompts_file}"
            )
        except Exception as e:
            logger.error(f"Failed to save prompts: {e}")
            raise

    def create(self, prompt: Prompt) -> None:
        """Create a new prompt."""
        prompts = self._load_prompts()
        if prompt.id in prompts:
            raise ValueError(f"Prompt with id '{prompt.id}' already exists")
        prompts[prompt.id] = prompt
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(f"Created prompt: {prompt.id}")

    def update(self, prompt: Prompt) -> None:
        """Update an existing prompt."""
        prompts = self._load_prompts()
        if prompt.id not in prompts:
            raise ValueError(f"Prompt with id '{prompt.id}' not found")
        prompt.updated_at = int(datetime.now().timestamp() * 1000)
        prompts[prompt.id] = prompt
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(f"Updated prompt: {prompt.id}")

    def upsert(self, prompt: Prompt) -> None:
        """Create or update a prompt."""
        prompts = self._load_prompts()
        prompt.updated_at = int(datetime.now().timestamp() * 1000)
        prompts[prompt.id] = prompt
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(f"Upserted prompt: {prompt.id}")

    def delete(self, prompt_id: str) -> None:
        """Delete a prompt."""
        prompts = self._load_prompts()
        if prompt_id not in prompts:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")
        del prompts[prompt_id]
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(f"Deleted prompt: {prompt_id}")

    def import_from_file(self, file_path: Path) -> None:
        """Import prompts from a JSON file."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            prompts = self._load_prompts()
            imported_count = 0

            if isinstance(data, dict):
                # Format: {"id": {...}, "id2": {...}}
                for prompt_id, prompt_data in data.items():
                    if isinstance(prompt_data, dict):
                        prompt = Prompt.from_dict(prompt_data)
                        prompts[prompt.id] = prompt
                        imported_count += 1
            elif isinstance(data, list):
                # Format: [{...}, {...}]
                for prompt_data in data:
                    if isinstance(prompt_data, dict):
                        prompt = Prompt.from_dict(prompt_data)
                        prompts[prompt.id] = prompt
                        imported_count += 1

            active_prompts = self._load_active_prompts()
            self._save_data(prompts, active_prompts)
            logger.info(f"Imported {imported_count} prompts from {file_path}")
        except Exception as e:
            logger.error(f"Failed to import prompts: {e}")
            raise

    def export_to_file(self, file_path: Path) -> None:
        """Export prompts to a JSON file."""
        try:
            prompts = self._load_prompts()
            data = {
                prompt_id: prompt.to_dict() for prompt_id, prompt in prompts.items()
            }
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported {len(prompts)} prompts to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export prompts: {e}")
            raise

    # ==================== Default Prompt Operations ====================

    def set_default(self, prompt_id: str) -> None:
        """Set a prompt as the default prompt.

        Only one prompt can be the default at a time.
        """
        prompts = self._load_prompts()
        if prompt_id not in prompts:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")

        # Clear default from all other prompts
        for p in prompts.values():
            p.is_default = False

        # Set the specified prompt as default
        prompts[prompt_id].is_default = True
        prompts[prompt_id].updated_at = int(datetime.now().timestamp() * 1000)

        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(f"Set default prompt: {prompt_id}")

    def clear_default(self) -> None:
        """Clear the default prompt setting."""
        prompts = self._load_prompts()
        for p in prompts.values():
            if p.is_default:
                p.is_default = False
                p.updated_at = int(datetime.now().timestamp() * 1000)

        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info("Cleared default prompt")

    def get_default(self) -> Optional[Prompt]:
        """Get the default prompt."""
        prompts = self._load_prompts()
        for prompt in prompts.values():
            if prompt.is_default:
                return prompt
        return None

    # ==================== Tool Sync Operations ====================

    def sync_to_app(
        self,
        prompt_id: str,
        app_type: str,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Path:
        """
        Sync a prompt to a specific app's prompt file.

        Args:
            prompt_id: The prompt identifier
            app_type: The app type (claude, codex, gemini, copilot)
            level: Target scope ("user" or "project")
            project_dir: Project directory when targeting project scope

        Returns:
            The path to the synced file
        """
        if level not in ("user", "project"):
            raise ValueError(f"Invalid level: {level}")

        handler = self.get_handler(app_type)
        prompts = self._load_prompts()

        if prompt_id not in prompts:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")

        prompt = prompts[prompt_id]

        # Check if level is supported
        target_file = handler.get_prompt_file_path(level, project_dir)
        if not target_file:
            raise ValueError(f"Tool '{app_type}' does not support level '{level}'")

        # Sync to the target prompt file using the handler
        handler.sync_prompt(prompt.content, level, project_dir)

        # Record this prompt as active for this app/level
        self.set_active_prompt(prompt_id, app_type, level, project_dir)

        logger.info(
            f"Synced prompt: {prompt_id} to {app_type} ({level} -> {target_file})"
        )
        return target_file

    def sync_to_apps(
        self,
        prompt_id: str,
        app_types: List[str],
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """
        Sync a prompt to multiple apps.

        Args:
            prompt_id: The prompt identifier
            app_types: List of app types to sync to
            level: Target scope ("user" or "project")
            project_dir: Project directory when targeting project scope

        Returns:
            Dict mapping app_type to synced file path
        """
        results = {}
        for app_type in app_types:
            try:
                file_path = self.sync_to_app(prompt_id, app_type, level, project_dir)
                results[app_type] = file_path
            except Exception as e:
                logger.error(f"Failed to sync to {app_type}: {e}")
                raise
        return results

    def sync_default_to_all(
        self,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Dict[str, Optional[Path]]:
        """
        Sync the default prompt to all supported apps.

        Args:
            level: Target scope ("user" or "project")
            project_dir: Project directory when targeting project scope

        Returns:
            Dict mapping app_type to synced file path (None if skipped)
        """
        default_prompt = self.get_default()
        if not default_prompt:
            raise ValueError("No default prompt set. Use 'set-default' first.")

        results = {}

        # Determine which apps to sync to based on level
        if level == "user":
            target_apps = USER_LEVEL_APPS
        else:
            target_apps = VALID_APP_TYPES

        for app_type in target_apps:
            handler = self.get_handler(app_type)
            target_file = handler.get_prompt_file_path(level, project_dir)

            if not target_file:
                results[app_type] = None
                continue

            try:
                handler.sync_prompt(default_prompt.content, level, project_dir)
                # Record this prompt as active for this app/level
                self.set_active_prompt(default_prompt.id, app_type, level, project_dir)
                results[app_type] = target_file
                logger.info(f"Synced default prompt to {app_type} ({level})")
            except Exception as e:
                logger.error(f"Failed to sync to {app_type}: {e}")
                results[app_type] = None

        return results

    def get_live_content(
        self,
        app_type: str,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Get the current content of the app's prompt file."""
        handler = self.get_handler(app_type)
        return handler.get_live_content(level, project_dir)

    def import_from_live(
        self,
        app_type: str,
        name: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Import the current live prompt file as a new prompt."""
        handler = self.get_handler(app_type)
        result = handler.import_from_live(level, project_dir)

        if not result:
            return None

        content = result["content"]
        file_path = result["file_path"]

        prompts = self._load_prompts()
        stripped_content = content.strip()
        for prompt in prompts.values():
            if prompt.content.strip() == stripped_content:
                logger.info(
                    "Live prompt content already stored as prompt %s", prompt.id
                )
                return prompt.id

        prompt_id = generate_unique_id(f"{app_type}-{level}")

        if not name:
            level_label = "User" if level == "user" else "Project"
            name = f"Imported from {level_label} {app_type.capitalize()} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        prompt = Prompt(
            id=prompt_id,
            name=name,
            content=content,
            description=f"Imported from {file_path}",
            is_default=False,
        )

        prompts[prompt_id] = prompt
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)

        logger.info(f"Imported prompt: {prompt_id}")
        return prompt_id

    # ==================== Copilot-Specific Operations ====================

    def sync_copilot_instructions(
        self,
        prompt_id: str,
        instruction_type: str = "repo-wide",
        apply_to: Optional[str] = None,
        exclude_agent: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> None:
        """
        Sync a prompt to Copilot instructions file.

        Args:
            prompt_id: The prompt identifier
            instruction_type: "repo-wide" or "path-specific"
            apply_to: Glob pattern (required for path-specific)
            exclude_agent: Optional agent to exclude
            project_dir: Project directory (defaults to current working directory)
        """
        if project_dir is None:
            project_dir = Path.cwd()

        prompts = self._load_prompts()
        if prompt_id not in prompts:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")

        prompt = prompts[prompt_id]
        prompt.instruction_type = instruction_type
        prompt.apply_to = apply_to
        prompt.exclude_agent = exclude_agent

        copilot = self.copilot

        if instruction_type == "repo-wide":
            copilot.sync_repo_wide(prompt.content, project_dir)
        elif instruction_type == "path-specific":
            if not apply_to:
                raise ValueError("apply_to is required for path-specific instructions")
            copilot.sync_path_specific(
                prompt.id, prompt.content, apply_to, exclude_agent, project_dir
            )
        else:
            raise ValueError(f"Unknown instruction type: {instruction_type}")

        # Record this prompt as active for copilot
        self.set_active_prompt(prompt_id, "copilot", "project", project_dir)

        prompt.updated_at = int(datetime.now().timestamp() * 1000)
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)
        logger.info(
            f"Synced prompt {prompt_id} to Copilot {instruction_type} instructions"
        )

    def import_copilot_instructions(
        self,
        instruction_type: str = "repo-wide",
        name: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Import Copilot instructions as a new prompt."""
        if project_dir is None:
            project_dir = Path.cwd()

        if instruction_type != "repo-wide":
            raise ValueError(
                "Only 'repo-wide' import is supported. For path-specific, import individual files."
            )

        result = self.copilot.import_repo_wide(project_dir)
        if not result:
            return None

        content = result["content"]
        file_path = result["file_path"]

        prompts = self._load_prompts()
        stripped_content = content.strip()
        for prompt in prompts.values():
            if (
                prompt.content.strip() == stripped_content
                and prompt.instruction_type == instruction_type
            ):
                logger.info(
                    "Copilot instructions already stored as prompt %s", prompt.id
                )
                return prompt.id

        prompt_id = generate_unique_id(f"copilot-{instruction_type}")

        if not name:
            name = f"Copilot {instruction_type} instructions ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        prompt = Prompt(
            id=prompt_id,
            name=name,
            content=content,
            description=f"Imported from {file_path}",
            is_default=False,
            instruction_type=instruction_type,
        )

        prompts[prompt_id] = prompt
        active_prompts = self._load_active_prompts()
        self._save_data(prompts, active_prompts)

        logger.info(f"Imported Copilot instructions: {prompt_id}")
        return prompt_id

    def get_copilot_instructions(
        self, project_dir: Optional[Path] = None, instruction_type: str = "repo-wide"
    ) -> Optional[str]:
        """Get current Copilot instructions content from file."""
        if instruction_type == "repo-wide":
            return self.copilot.get_repo_wide_content(project_dir)
        else:
            # For path-specific, just return the directory path info
            return None

    # ==================== CLI Compatibility Methods ====================
    # These methods provide the API expected by the CLI commands

    def list_prompts(
        self,
        app: Optional[str] = None,
        level: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> List[Prompt]:
        """List prompts, optionally filtered by app and level.

        Note: Currently returns all prompts as storage doesn't track app/level.
        Filtering would require storing app/level metadata with each prompt.
        """
        prompts = self._load_prompts()
        return list(prompts.values())

    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Get a specific prompt by ID. Alias for get()."""
        return self.get(prompt_id)

    def create_prompt(
        self,
        prompt_id: str,
        app: str,
        level: str,
        content: str,
        description: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> Prompt:
        """Create a new prompt with the given parameters."""
        prompt = Prompt(
            id=prompt_id,
            name=prompt_id,
            content=content,
            description=description or "",
            is_default=False,
        )
        self.create(prompt)
        return prompt

    def update_prompt(
        self,
        prompt_id: str,
        content: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Prompt:
        """Update an existing prompt."""
        prompt = self.get(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt with id '{prompt_id}' not found")

        if content is not None:
            prompt.content = content
        if description is not None:
            prompt.description = description
        if name is not None:
            prompt.name = name

        self.update(prompt)
        return prompt

    def remove_prompt(self, prompt_id: str) -> None:
        """Remove a prompt. Alias for delete()."""
        self.delete(prompt_id)

    def get_default_prompt(
        self,
        app: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Get the default prompt ID for an app/level combination.

        Note: Currently returns the global default prompt ID.
        App/level-specific defaults would require additional storage.
        """
        default = self.get_default()
        return default.id if default else None

    def set_default_prompt(
        self,
        app: str,
        level: str,
        prompt_id: str,
        project_dir: Optional[Path] = None,
    ) -> None:
        """Set a prompt as the default for an app/level combination.

        Note: Currently sets the global default prompt.
        """
        self.set_default(prompt_id)

    def clear_default_prompt(
        self,
        app: str,
        level: str,
        project_dir: Optional[Path] = None,
    ) -> None:
        """Clear the default prompt for an app/level combination.

        Note: Currently clears the global default prompt.
        """
        self.clear_default()

    def unsync_prompt_aliases(
        self,
        app: str,
        level: str,
        project_dir: Optional[Path] = None,
    ) -> int:
        """Remove synced prompt aliases for an app. Returns count of removed aliases."""
        # This is a placeholder - actual implementation would depend on how aliases are stored
        return 0

    def install_from_url(
        self,
        url: str,
        app: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
        force: bool = False,
    ) -> int:
        """Install prompts from a URL. Returns count of installed prompts."""
        # Placeholder implementation
        raise NotImplementedError("URL installation not yet implemented")

    def install_from_file(
        self,
        file_path: Path,
        app: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
        force: bool = False,
    ) -> int:
        """Install prompts from a file. Returns count of installed prompts."""
        self.import_from_file(file_path)
        return len(self._load_prompts())

    def import_prompts_from_file(
        self,
        file_path: Path,
        app: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
        force: bool = False,
    ) -> int:
        """Import prompts from a JSON file. Returns count of imported prompts."""
        before_count = len(self._load_prompts())
        self.import_from_file(file_path)
        after_count = len(self._load_prompts())
        return after_count - before_count

    def export_prompts_to_file(
        self,
        file_path: Path,
        app: Optional[str] = None,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> int:
        """Export prompts to a JSON file. Returns count of exported prompts."""
        self.export_to_file(file_path)
        return len(self._load_prompts())

    def sync_prompts_as_aliases(
        self,
        source_app: str,
        target_app: str,
        level: str = "user",
        project_dir: Optional[Path] = None,
        force: bool = False,
    ) -> int:
        """Sync prompts from one app to another as aliases. Returns count of synced prompts."""
        # Placeholder implementation
        return 0
