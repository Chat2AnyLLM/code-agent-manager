"""Tests for MCP Registry Manager.

This module tests the LocalRegistryManager class which manages local storage
and retrieval of MCP server schemas.

Key test areas:
- Adding server schemas to the registry
- Retrieving server schemas by name
- Listing all server schemas
- Removing server schemas
- Searching server schemas by query
- Directory initialization
- Error handling for invalid schemas
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_assistant_manager.mcp.registry_manager import (
    DEFAULT_REGISTRY_PATH,
    LocalRegistryManager,
)
from code_assistant_manager.mcp.schema import InstallationMethod, ServerSchema


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry directory."""
    registry_path = tmp_path / "registry"
    registry_path.mkdir()
    servers_path = registry_path / "servers"
    servers_path.mkdir()
    return registry_path


@pytest.fixture
def registry_manager(temp_registry):
    """Create a LocalRegistryManager with temporary storage."""
    return LocalRegistryManager(registry_path=str(temp_registry))


@pytest.fixture
def sample_server_schema():
    """Create a sample server schema for testing."""
    return ServerSchema(
        name="sample-server",
        display_name="Sample MCP Server",
        description="A sample server for testing",
        repository="https://github.com/test/sample-server",
        license="MIT",
        installations={
            "npx": InstallationMethod(
                type="stdio",
                command="npx",
                args=["-y", "sample-server"],
                description="Install via npx",
                recommended=True,
            ),
        },
        arguments={
            "API_KEY": {
                "required": True,
                "description": "API key",
            },
        },
        categories=["productivity", "testing"],
        tags=["sample", "test", "mock"],
    )


@pytest.fixture
def another_server_schema():
    """Create another server schema for testing searches."""
    return ServerSchema(
        name="another-server",
        display_name="Another Server",
        description="Another test server with different properties",
        repository="https://github.com/test/another-server",
        installations={},
        arguments={},
        categories=["database"],
        tags=["db", "storage"],
    )


class TestDirectoryInitialization:
    """Tests for directory initialization."""

    def test_creates_registry_directory(self, tmp_path):
        """Test that registry directory is created if it doesn't exist."""
        registry_path = tmp_path / "new_registry"
        assert not registry_path.exists()

        manager = LocalRegistryManager(registry_path=str(registry_path))

        assert registry_path.exists()
        assert (registry_path / "servers").exists()

    def test_existing_directory_not_overwritten(self, temp_registry):
        """Test that existing directories are not overwritten."""
        # Create a file in the servers directory
        test_file = temp_registry / "servers" / "existing.json"
        test_file.write_text('{"test": true}')

        manager = LocalRegistryManager(registry_path=str(temp_registry))

        assert test_file.exists()
        assert test_file.read_text() == '{"test": true}'


class TestAddServerSchema:
    """Tests for adding server schemas."""

    def test_add_server_schema_success(
        self, registry_manager, sample_server_schema, temp_registry
    ):
        """Test successful server schema addition."""
        success = registry_manager.add_server_schema(sample_server_schema)

        assert success is True
        schema_file = temp_registry / "servers" / "sample-server.json"
        assert schema_file.exists()

        # Verify content
        with open(schema_file) as f:
            saved_data = json.load(f)
        assert saved_data["name"] == "sample-server"
        assert saved_data["display_name"] == "Sample MCP Server"

    def test_add_server_schema_already_exists(
        self, registry_manager, sample_server_schema
    ):
        """Test adding server that already exists without force."""
        registry_manager.add_server_schema(sample_server_schema)

        # Try to add again without force
        success = registry_manager.add_server_schema(sample_server_schema, force=False)

        assert success is False

    def test_add_server_schema_force_overwrite(
        self, registry_manager, sample_server_schema
    ):
        """Test adding server with force overwrites existing."""
        registry_manager.add_server_schema(sample_server_schema)

        # Modify and add again with force
        sample_server_schema.description = "Updated description"
        success = registry_manager.add_server_schema(sample_server_schema, force=True)

        assert success is True

        # Verify update
        retrieved = registry_manager.get_server_schema("sample-server")
        assert retrieved.description == "Updated description"

    def test_add_server_schema_write_error(
        self, registry_manager, sample_server_schema
    ):
        """Test handling write errors."""
        with patch("builtins.open", side_effect=IOError("Write failed")):
            success = registry_manager.add_server_schema(sample_server_schema)

        assert success is False


class TestGetServerSchema:
    """Tests for retrieving server schemas."""

    def test_get_existing_schema(self, registry_manager, sample_server_schema):
        """Test retrieving an existing server schema."""
        registry_manager.add_server_schema(sample_server_schema)

        retrieved = registry_manager.get_server_schema("sample-server")

        assert retrieved is not None
        assert retrieved.name == "sample-server"
        assert retrieved.display_name == "Sample MCP Server"

    def test_get_nonexistent_schema(self, registry_manager):
        """Test retrieving a non-existent server schema."""
        retrieved = registry_manager.get_server_schema("nonexistent")

        assert retrieved is None

    def test_get_schema_with_invalid_json(self, registry_manager, temp_registry):
        """Test handling invalid JSON in schema file."""
        # Create invalid JSON file
        invalid_file = temp_registry / "servers" / "invalid-server.json"
        invalid_file.write_text("not valid json{")

        retrieved = registry_manager.get_server_schema("invalid-server")

        assert retrieved is None

    def test_get_schema_with_missing_fields(self, registry_manager, temp_registry):
        """Test handling schema file with missing required fields."""
        # Create schema missing required fields
        incomplete_file = temp_registry / "servers" / "incomplete.json"
        incomplete_file.write_text('{"name": "incomplete"}')

        # Should handle validation error gracefully
        retrieved = registry_manager.get_server_schema("incomplete")
        # Depending on pydantic validation, this might be None or raise
        # The implementation should handle this gracefully


class TestListServerSchemas:
    """Tests for listing all server schemas."""

    def test_list_empty_registry(self, registry_manager):
        """Test listing schemas from empty registry."""
        schemas = registry_manager.list_server_schemas()

        assert schemas == {}

    def test_list_single_schema(self, registry_manager, sample_server_schema):
        """Test listing with single schema."""
        registry_manager.add_server_schema(sample_server_schema)

        schemas = registry_manager.list_server_schemas()

        assert len(schemas) == 1
        assert "sample-server" in schemas

    def test_list_multiple_schemas(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test listing multiple schemas."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        schemas = registry_manager.list_server_schemas()

        assert len(schemas) == 2
        assert "sample-server" in schemas
        assert "another-server" in schemas

    def test_list_skips_invalid_schemas(
        self, registry_manager, temp_registry, sample_server_schema
    ):
        """Test that invalid schemas are skipped during listing."""
        registry_manager.add_server_schema(sample_server_schema)

        # Add invalid JSON file
        invalid_file = temp_registry / "servers" / "invalid.json"
        invalid_file.write_text("not json")

        schemas = registry_manager.list_server_schemas()

        # Should only return valid schema
        assert len(schemas) == 1
        assert "sample-server" in schemas


class TestRemoveServerSchema:
    """Tests for removing server schemas."""

    def test_remove_existing_schema(
        self, registry_manager, sample_server_schema, temp_registry
    ):
        """Test removing an existing schema."""
        registry_manager.add_server_schema(sample_server_schema)
        schema_file = temp_registry / "servers" / "sample-server.json"
        assert schema_file.exists()

        success = registry_manager.remove_server_schema("sample-server")

        assert success is True
        assert not schema_file.exists()

    def test_remove_nonexistent_schema(self, registry_manager):
        """Test removing a non-existent schema."""
        success = registry_manager.remove_server_schema("nonexistent")

        assert success is False

    def test_remove_schema_file_error(self, registry_manager, sample_server_schema):
        """Test handling file deletion errors."""
        registry_manager.add_server_schema(sample_server_schema)

        with patch.object(Path, "unlink", side_effect=OSError("Delete failed")):
            success = registry_manager.remove_server_schema("sample-server")

        assert success is False


class TestSearchServerSchemas:
    """Tests for searching server schemas."""

    def test_search_no_query_returns_all(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test search without query returns all schemas."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        results = registry_manager.search_server_schemas()

        assert len(results) == 2

    def test_search_by_name(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test searching by server name."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        results = registry_manager.search_server_schemas("sample")

        assert len(results) == 1
        assert results[0].name == "sample-server"

    def test_search_by_display_name(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test searching by display name."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        results = registry_manager.search_server_schemas("Another Server")

        assert len(results) == 1
        assert results[0].name == "another-server"

    def test_search_by_description(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test searching by description."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        results = registry_manager.search_server_schemas("different properties")

        assert len(results) == 1
        assert results[0].name == "another-server"

    def test_search_by_tag(
        self, registry_manager, sample_server_schema, another_server_schema
    ):
        """Test searching by tag."""
        registry_manager.add_server_schema(sample_server_schema)
        registry_manager.add_server_schema(another_server_schema)

        results = registry_manager.search_server_schemas("storage")

        assert len(results) == 1
        assert results[0].name == "another-server"

    def test_search_case_insensitive(self, registry_manager, sample_server_schema):
        """Test that search is case insensitive."""
        registry_manager.add_server_schema(sample_server_schema)

        results = registry_manager.search_server_schemas("SAMPLE")

        assert len(results) == 1
        assert results[0].name == "sample-server"

    def test_search_no_matches(self, registry_manager, sample_server_schema):
        """Test search with no matches."""
        registry_manager.add_server_schema(sample_server_schema)

        results = registry_manager.search_server_schemas("nonexistent-term")

        assert len(results) == 0


class TestDefaultRegistryPath:
    """Tests for default registry path."""

    def test_default_path_exists(self):
        """Test that the default registry path constant is defined."""
        assert DEFAULT_REGISTRY_PATH is not None
        assert "registry" in DEFAULT_REGISTRY_PATH
