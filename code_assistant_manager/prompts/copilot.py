"""Copilot-specific prompt handler."""

import logging
from pathlib import Path
from typing import Dict, Optional

from .base import BasePromptHandler

logger = logging.getLogger(__name__)

# Copilot instructions paths
COPILOT_REPO_INSTRUCTIONS = ".github/copilot-instructions.md"
COPILOT_INSTRUCTIONS_DIR = ".github/instructions"


def parse_copilot_frontmatter(content: str) -> tuple[Optional[Dict], str]:
    """
    Parse YAML-style frontmatter from Copilot instructions file.

    Args:
        content: The file content with potential frontmatter

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
    """
    if not content.startswith("---"):
        return None, content

    # Find closing ---
    end_index = content.find("\n---\n", 4)
    if end_index == -1:
        return None, content

    frontmatter_text = content[4:end_index]
    body = content[end_index + 5 :].lstrip("\n")

    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            frontmatter[key] = value

    return frontmatter, body


def format_copilot_frontmatter(
    apply_to: str, exclude_agent: Optional[str] = None
) -> str:
    """
    Format frontmatter for Copilot instructions file.

    Args:
        apply_to: Glob pattern(s) for the file
        exclude_agent: Optional agent to exclude ("coding-agent" or "code-review")

    Returns:
        Formatted frontmatter string
    """
    frontmatter = f'---\napplyTo: "{apply_to}"'
    if exclude_agent:
        frontmatter += f'\nexcludeAgent: "{exclude_agent}"'
    frontmatter += "\n---\n"
    return frontmatter


class CopilotPromptHandler(BasePromptHandler):
    """Prompt handler for GitHub Copilot CLI.

    Copilot uses a different structure:
    - Repository-wide: .github/copilot-instructions.md
    - Path-specific: .github/instructions/NAME.instructions.md (with frontmatter)

    Copilot does not have user-level prompts, only project-level.
    """

    @property
    def tool_name(self) -> str:
        return "copilot"

    @property
    def _default_user_prompt_path(self) -> Optional[Path]:
        """Copilot doesn't support user-level prompts."""
        return None

    @property
    def _default_project_prompt_filename(self) -> Optional[str]:
        """Return the repository-wide instructions filename."""
        return COPILOT_REPO_INSTRUCTIONS

    def get_instructions_path(
        self, project_dir: Optional[Path] = None, repo_wide: bool = True
    ) -> Path:
        """
        Get the path to Copilot instructions file.

        Args:
            project_dir: Project directory (defaults to current working directory)
            repo_wide: If True, returns path to .github/copilot-instructions.md;
                       If False, returns path to .github/instructions directory

        Returns:
            Path to the Copilot instructions location
        """
        if project_dir is None:
            project_dir = Path.cwd()

        if repo_wide:
            return project_dir / COPILOT_REPO_INSTRUCTIONS
        return project_dir / COPILOT_INSTRUCTIONS_DIR

    def sync_repo_wide(
        self,
        content: str,
        project_dir: Optional[Path] = None,
    ) -> Path:
        """
        Sync content to repository-wide Copilot instructions.

        Args:
            content: The instruction content
            project_dir: Project directory (defaults to current working directory)

        Returns:
            Path to the synced file
        """
        if project_dir is None:
            project_dir = Path.cwd()

        file_path = self.get_instructions_path(project_dir, repo_wide=True)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = file_path.with_suffix(".tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(file_path)
            logger.info(f"Synced to Copilot repo-wide instructions: {file_path}")
            return file_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def sync_path_specific(
        self,
        prompt_id: str,
        content: str,
        apply_to: str,
        exclude_agent: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> Path:
        """
        Sync content to path-specific Copilot instructions.

        Args:
            prompt_id: The prompt identifier (used for filename)
            content: The instruction content
            apply_to: Glob pattern(s) for the files this applies to
            exclude_agent: Optional agent to exclude
            project_dir: Project directory (defaults to current working directory)

        Returns:
            Path to the synced file
        """
        if project_dir is None:
            project_dir = Path.cwd()

        instructions_dir = self.get_instructions_path(project_dir, repo_wide=False)
        instructions_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from prompt ID
        filename = f"{prompt_id}.instructions.md"
        file_path = instructions_dir / filename

        # Add frontmatter
        frontmatter = format_copilot_frontmatter(apply_to, exclude_agent)
        full_content = frontmatter + content

        temp_path = file_path.with_suffix(".tmp")
        try:
            temp_path.write_text(full_content, encoding="utf-8")
            temp_path.replace(file_path)
            logger.info(f"Synced to Copilot path-specific instructions: {file_path}")
            return file_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def get_repo_wide_content(
        self, project_dir: Optional[Path] = None
    ) -> Optional[str]:
        """
        Get current repository-wide Copilot instructions content.

        Args:
            project_dir: Project directory (defaults to current working directory)

        Returns:
            The content of the instructions file, or None if it doesn't exist
        """
        file_path = self.get_instructions_path(project_dir, repo_wide=True)
        if not file_path.exists():
            return None

        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read Copilot instructions: {e}")
            return None

    def import_repo_wide(self, project_dir: Optional[Path] = None) -> Optional[Dict]:
        """
        Import repository-wide Copilot instructions.

        Args:
            project_dir: Project directory (defaults to current working directory)

        Returns:
            Dict with 'content' and 'file_path' keys, or None if file doesn't exist
        """
        file_path = self.get_instructions_path(project_dir, repo_wide=True)
        if not file_path.exists():
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
            logger.warning(f"Failed to read instructions file {file_path}: {e}")
            return None

    def list_path_specific(self, project_dir: Optional[Path] = None) -> list[Dict]:
        """
        List all path-specific instruction files.

        Args:
            project_dir: Project directory (defaults to current working directory)

        Returns:
            List of dicts with 'filename', 'file_path', 'frontmatter', 'content' keys
        """
        instructions_dir = self.get_instructions_path(project_dir, repo_wide=False)
        if not instructions_dir.exists():
            return []

        results = []
        for file_path in instructions_dir.glob("*.instructions.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                frontmatter, body = parse_copilot_frontmatter(content)
                results.append(
                    {
                        "filename": file_path.name,
                        "file_path": file_path,
                        "frontmatter": frontmatter,
                        "content": body,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")

        return results
