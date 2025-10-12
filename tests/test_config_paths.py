"""Tests for config_paths module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from code_assistant_manager.mcp.config_paths import _get_config_locations


class TestGetConfigLocations:
    """Test configuration path discovery."""

    @patch("pathlib.Path.home")
    def test_claude_config_paths(self, mock_home):
        """Test config paths for Claude."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("claude")

        expected_paths = [
            Path("/home/user/.config/Claude/mcp.json"),
            Path("/home/user/.local/share/claude/mcp.json"),
            Path("/home/user/Library/Application Support/Claude/mcp.json"),
            # Common patterns
            Path("/home/user/.config/claude/mcp.json"),
            Path("/home/user/.local/share/claude/mcp.json"),
            Path("/home/user/.claude/mcp.json"),
            Path("/home/user/.claude.config/mcp.json"),
        ]

        for expected_path in expected_paths:
            assert expected_path in paths

    @patch("pathlib.Path.home")
    def test_cursor_config_paths(self, mock_home):
        """Test config paths for Cursor."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("cursor")

        assert Path("/home/user/.cursor/mcp.json") in paths

    @patch("pathlib.Path.home")
    def test_gemini_config_paths(self, mock_home):
        """Test config paths for Gemini."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("gemini")

        gemini_paths = [
            Path("/home/user/.config/Google/Gemini/mcp.json"),
            Path("/home/user/.gemini/mcp.json"),
            Path("/home/user/.gemini/settings.json"),
            Path("/home/jzhu/code-assistant-manager/.gemini/settings.json"),  # CWD path
        ]

        for path in gemini_paths:
            assert path in paths

    @patch("pathlib.Path.home")
    def test_copilot_config_paths(self, mock_home):
        """Test config paths for Copilot."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("copilot")

        copilot_paths = [
            Path("/home/user/.copilot/mcp-config.json"),
            Path("/home/user/.copilot/mcp.json"),
            Path("/home/user/.config/GitHub/Copilot/mcp.json"),
        ]

        for path in copilot_paths:
            assert path in paths

    @patch("pathlib.Path.home")
    def test_codex_config_paths(self, mock_home):
        """Test config paths for Codex."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("codex")

        codex_paths = [
            Path("/home/user/.config/GitHub/Codex/mcp.json"),
            Path("/home/user/.codex/mcp.json"),
        ]

        for path in codex_paths:
            assert path in paths

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    def test_project_level_configs(self, mock_cwd, mock_home):
        """Test project-level config discovery."""
        mock_home.return_value = Path("/home/user")
        mock_cwd.return_value = Path("/home/user/project")

        # Mock exists() to return True for some paths
        with patch.object(Path, "exists", side_effect=lambda: True):
            paths = _get_config_locations("claude")

            # Should include project-level configs
            project_configs = [
                Path("/home/user/project/.mcp.json"),
                Path("/home/user/project/.gemini/settings.json"),
                Path("/home/user/project/mcp.json"),
            ]

            for config in project_configs:
                assert config in paths

    @patch("pathlib.Path.home")
    def test_unknown_tool_config_paths(self, mock_home):
        """Test config paths for unknown tool."""
        mock_home.return_value = Path("/home/user")

        paths = _get_config_locations("unknown-tool")

        # Should still get common patterns
        common_paths = [
            Path("/home/user/.config/unknown-tool/mcp.json"),
            Path("/home/user/.local/share/unknown-tool/mcp.json"),
            Path("/home/user/.unknown-tool/mcp.json"),
        ]

        for path in common_paths:
            assert path in paths

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    def test_parent_directory_traversal(self, mock_cwd, mock_home):
        """Test that config discovery traverses parent directories."""
        mock_home.return_value = Path("/home/user")
        mock_cwd.return_value = Path("/home/user/deep/nested/project")

        with patch.object(Path, "exists", side_effect=lambda: True):
            paths = _get_config_locations("claude")

            # Should include configs from multiple levels up
            parent_configs = [
                Path("/home/user/deep/nested/project/.mcp.json"),
                Path("/home/user/deep/nested/.mcp.json"),
                Path("/home/user/deep/.mcp.json"),
                Path("/home/user/.mcp.json"),
            ]

            for config in parent_configs:
                assert config in paths
