from pathlib import Path

import pytest

from code_assistant_manager.prompts.claude import ClaudePromptHandler
from code_assistant_manager.prompts.gemini import GeminiPromptHandler


class TestPromptHeaderStripping:

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def test_strip_metadata_header(self, temp_dir):
        handler = GeminiPromptHandler(user_path_override=temp_dir / "GEMINI.md")

        content_with_header = """Prompt: Imported from User Gemini (2025-11-27 00:04)
Description: Imported from /home/jzhu/.gemini/GEMINI.md
Status: not default
ID: gemini-user-f50022f5

Content:

# Gemini Code Assistant Instructions

## Role
You are an expert.
"""

        # Sync the prompt
        synced_path = handler.sync_prompt(content_with_header, level="user")

        # Read the file
        synced_content = synced_path.read_text()

        # Verify header is gone
        assert "Prompt: Imported from User" not in synced_content
        assert "Status: not default" not in synced_content
        assert "Content:" not in synced_content

        # Verify content starts with the markdown header
        assert synced_content.startswith(
            "# GEMINI.md — Gemini Code Assistant Instructions"
        )
        assert "## Role" in synced_content

    def test_normalize_header_after_stripping(self, temp_dir):
        # Use Claude handler to verify header renaming
        handler = ClaudePromptHandler(user_path_override=temp_dir / "CLAUDE.md")

        content_with_header = """Prompt: Some Prompt
ID: 123

Content:

# Gemini Code Assistant Instructions

Some content.
"""

        synced_path = handler.sync_prompt(content_with_header, level="user")
        synced_content = synced_path.read_text()

        # Verify header is stripped
        assert "Prompt: Some Prompt" not in synced_content

        # Verify header is renamed to Claude and uses standard format
        assert synced_content.startswith(
            "# CLAUDE.md — Claude Code Assistant Instructions"
        )

    def test_no_header_strip_if_no_content_delimiter(self, temp_dir):
        handler = GeminiPromptHandler(user_path_override=temp_dir / "GEMINI.md")

        content_simple = """# Just a normal prompt

With some content.
"""

        synced_path = handler.sync_prompt(content_simple, level="user")
        synced_content = synced_path.read_text()

        assert synced_content == content_simple
