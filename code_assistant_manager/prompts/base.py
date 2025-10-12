"""Base class for tool-specific prompt handlers."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BasePromptHandler(ABC):
    """Abstract base class for tool-specific prompt handlers.

    Each AI tool (Claude, Codex, Gemini, Copilot) has its own implementation
    that defines how prompts are stored and synced.
    """

    def __init__(
        self,
        user_path_override: Optional[Path] = None,
        project_filename_override: Optional[str] = None,
    ):
        """
        Initialize the handler with optional path overrides for testing.

        Args:
            user_path_override: Override the user-level prompt path
            project_filename_override: Override the project-level filename
        """
        self._user_path_override = user_path_override
        self._project_filename_override = project_filename_override

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of the tool (e.g., 'claude', 'codex', 'gemini', 'copilot')."""

    @property
    @abstractmethod
    def _default_user_prompt_path(self) -> Optional[Path]:
        """Return the default user-level prompt file path, or None if not supported."""

    @property
    @abstractmethod
    def _default_project_prompt_filename(self) -> Optional[str]:
        """Return the default project-level prompt filename, or None if not supported."""

    @property
    def user_prompt_path(self) -> Optional[Path]:
        """Return the user-level prompt file path, or None if not supported."""
        if self._user_path_override is not None:
            return self._user_path_override
        return self._default_user_prompt_path

    @property
    def project_prompt_filename(self) -> Optional[str]:
        """Return the project-level prompt filename, or None if not supported."""
        if self._project_filename_override is not None:
            return self._project_filename_override
        return self._default_project_prompt_filename

    def get_prompt_file_path(
        self, level: str = "user", project_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Get the prompt file path for the specified level.

        Args:
            level: Either "user" or "project"
            project_dir: Project directory (defaults to current working directory)

        Returns:
            Path to the prompt file, or None if invalid
        """
        if level == "user":
            return self.user_prompt_path
        elif level == "project":
            filename = self.project_prompt_filename
            if not filename:
                return None
            if project_dir is None:
                project_dir = Path.cwd()
            return project_dir / filename
        return None

    def _strip_metadata_header(self, content: str) -> str:
        """
        Strip internal metadata header if present.

        The metadata header typically looks like:
        Prompt: ...
        Description: ...
        Status: ...
        ID: ...

        Content:

        Args:
            content: The prompt content

        Returns:
            Content with metadata header removed
        """
        lines = content.splitlines()

        # Find the "Content:" line
        content_line_idx = -1
        for i, line in enumerate(lines[:30]):  # Check first 30 lines
            if line.strip() == "Content:":
                content_line_idx = i
                break

        if content_line_idx != -1:
            # Check if preceding lines look like metadata
            # At least one line should start with known metadata keys
            header_slice = lines[:content_line_idx]
            has_metadata = False
            for line in header_slice:
                if line.startswith(
                    ("Prompt:", "ID:", "Description:", "Status:", "Imported from")
                ):
                    has_metadata = True
                    break

            if has_metadata:
                # Return content starting after "Content:" line
                # Skip "Content:" line
                start_idx = content_line_idx + 1

                # Skip subsequent empty lines
                while start_idx < len(lines) and not lines[start_idx].strip():
                    start_idx += 1

                if start_idx < len(lines):
                    return "\n".join(lines[start_idx:])

        return content

    def _normalize_header(self, content: str, filename: Optional[str] = None) -> str:
        """
        Normalize the first line header to match this tool's name.

        If the content starts with a markdown header like '# Gemini Code Assistant',
        it will be updated to match this tool (e.g., '# Claude Code Assistant').

        Args:
            content: The prompt content
            filename: The filename of the prompt file (e.g. GEMINI.md)

        Returns:
            Content with normalized header
        """
        import re

        lines = content.split("\n", 1)
        if not lines:
            return content

        first_line = lines[0]
        # Match markdown headers like "# Gemini Code Assistant Instructions"
        # or "# Claude Code Assistant" etc.
        header_pattern = r"^#\s+(Claude|Codex|Gemini|Copilot|GitHub Copilot)(\s+.*)?"
        match = re.match(header_pattern, first_line, re.IGNORECASE)

        if match:
            # Get the tool name with proper capitalization
            tool_display_name = self.tool_name.capitalize()
            if self.tool_name == "copilot":
                tool_display_name = "GitHub Copilot"

            if filename:
                new_header = (
                    f"# {filename} — {tool_display_name} Code Assistant Instructions"
                )
            else:
                suffix = match.group(2) or ""
                new_header = f"# {tool_display_name}{suffix}"

            if len(lines) > 1:
                return new_header + "\n" + lines[1]
            return new_header

        return content

    def sync_prompt(
        self,
        content: str,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Path:
        """
        Write prompt content to the tool's prompt file.

        Args:
            content: The prompt content
            level: Target scope ("user" or "project")
            project_dir: Project directory when targeting project scope

        Returns:
            Path to the synced file

        Raises:
            ValueError: If level is invalid or tool doesn't support the level
        """
        file_path = self.get_prompt_file_path(level, project_dir)
        if not file_path:
            raise ValueError(
                f"Tool '{self.tool_name}' does not support level '{level}'"
            )

        # Strip metadata header if present
        content = self._strip_metadata_header(content)

        # Normalize header to match this tool's name
        content = self._normalize_header(content, filename=file_path.name)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically using temp file
        temp_path = file_path.with_suffix(".tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(file_path)
            logger.info(f"Synced prompt to: {file_path}")
            return file_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def get_live_content(
        self,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Get the current content of the tool's prompt file.

        Args:
            level: Prompt level ("user" or "project")
            project_dir: Optional project directory for project level prompts

        Returns:
            The content of the prompt file, or None if it doesn't exist
        """
        file_path = self.get_prompt_file_path(level, project_dir)
        if not file_path or not file_path.exists():
            return None

        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read live prompt for {self.tool_name}: {e}")
            return None

    def import_from_live(
        self,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> Optional[Dict]:
        """
        Import the current live prompt file content.

        Args:
            level: Prompt level ("user" or "project")
            project_dir: Optional project directory for project level prompts

        Returns:
            Dict with 'content' and 'file_path' keys, or None if file doesn't exist
        """
        file_path = self.get_prompt_file_path(level, project_dir)
        if not file_path or not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            if not content or not content.strip():
                return None
            return {
                "content": content,
                "file_path": file_path,
            }
        except Exception as e:
            logger.warning(f"Failed to read prompt file {file_path}: {e}")
            return None

    def clear_prompt(
        self,
        level: str = "user",
        project_dir: Optional[Path] = None,
    ) -> bool:
        """
        Clear the prompt file content.

        Args:
            level: Prompt level ("user" or "project")
            project_dir: Optional project directory for project level prompts

        Returns:
            True if successful, False otherwise
        """
        file_path = self.get_prompt_file_path(level, project_dir)
        if not file_path or not file_path.exists():
            return False

        try:
            file_path.write_text("", encoding="utf-8")
            logger.info(f"Cleared prompt file: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear prompt file {file_path}: {e}")
            return False
