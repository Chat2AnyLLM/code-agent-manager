"""Tests for code_assistant_manager.mcp.base module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from code_assistant_manager.mcp.base import find_mcp_config, find_project_root


class TestFindProjectRoot:
    """Test find_project_root function."""

    def test_find_project_root_from_package_dir(self):
        """Test finding project root from package directory."""
        # The function should find the project root (containing pyproject.toml)
        root = find_project_root()
        assert root.is_dir()
        assert (root / "pyproject.toml").exists()

    def test_find_project_root_with_start_path(self, tmp_path):
        """Test finding project root with explicit start path."""
        # Create a mock project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("")

        subdir = project_root / "subdir"
        subdir.mkdir()

        root = find_project_root(subdir)
        assert root == project_root

    def test_find_project_root_no_indicators(self, tmp_path):
        """Test find_project_root when no project indicators exist."""
        isolated_dir = tmp_path / "isolated"
        isolated_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="Project root not found"):
            find_project_root(isolated_dir)


class TestFindMcpConfig:
    """Test find_mcp_config function."""

    def test_find_mcp_config_exists(self, tmp_path):
        """Test finding MCP config when it exists."""
        # Create a mock MCP config in current directory
        config_file = tmp_path / "mcp.json"
        config_data = {"servers": {}}
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config_path = find_mcp_config()
            assert config_path == config_file

    def test_find_mcp_config_not_found(self, tmp_path):
        """Test find_mcp_config when no config exists."""
        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch.dict("os.environ", {}, clear=True),
        ):
            with pytest.raises(FileNotFoundError):
                find_mcp_config()

    def test_find_mcp_config_in_project_root(self, tmp_path):
        """Test finding MCP config in project root."""
        # Create config in project root
        config_file = tmp_path / "mcp.json"
        config_data = {"servers": {}}
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Mock to return our test directory as project root
        with (
            patch("pathlib.Path.cwd", return_value=tmp_path / "subdir"),
            patch(
                "code_assistant_manager.mcp.base.find_project_root",
                return_value=tmp_path,
            ),
        ):
            config_path = find_mcp_config()
            assert config_path == config_file


class TestMcpBaseUtilities:
    """Test other MCP base utilities."""

    def test_print_squared_frame(self, capsys):
        """Test print_squared_frame function."""
        from code_assistant_manager.mcp.base import print_squared_frame

        print_squared_frame("Test Title", "Test content")

        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "Test content" in captured.out
        # Check that it produces output
        assert len(captured.out.strip()) > 0
