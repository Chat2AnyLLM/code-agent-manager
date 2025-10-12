"""Local MCP Server Registry Manager

Manages local storage and retrieval of MCP server schemas.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from .schema import ServerSchema

logger = logging.getLogger(__name__)

# Default registry path
DEFAULT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "registry")


class LocalRegistryManager:
    """Manages local MCP server registry operations"""

    def __init__(self, registry_path: str = DEFAULT_REGISTRY_PATH):
        self.registry_path = Path(registry_path)
        self.servers_path = self.registry_path / "servers"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure all registry directories exist"""
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.servers_path.mkdir(parents=True, exist_ok=True)

    def add_server_schema(
        self, server_schema: ServerSchema, force: bool = False
    ) -> bool:
        """Add a server schema to the local registry.

        Args:
            server_schema: The server schema to add
            force: Whether to overwrite existing server schema

        Returns:
            bool: Success or failure
        """
        schema_file = self.servers_path / f"{server_schema.name}.json"

        if schema_file.exists() and not force:
            logger.warning(f"Server schema '{server_schema.name}' already exists")
            return False

        try:
            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(server_schema.model_dump(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving server schema {server_schema.name}: {e}")
            return False

    def get_server_schema(self, server_name: str) -> Optional[ServerSchema]:
        """Get a server schema by name.

        Args:
            server_name: Name of the server

        Returns:
            ServerSchema or None if not found
        """
        schema_file = self.servers_path / f"{server_name}.json"

        if not schema_file.exists():
            return None

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            return ServerSchema(**schema_data)
        except Exception as e:
            logger.error(f"Error loading server schema {server_name}: {e}")
            return None

    def list_server_schemas(self) -> Dict[str, ServerSchema]:
        """Get all server schemas in the local registry.

        Returns:
            Dict mapping server names to schemas
        """
        schemas = {}
        for schema_file in self.servers_path.glob("*.json"):
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_data = json.load(f)
                server_schema = ServerSchema(**schema_data)
                schemas[server_schema.name] = server_schema
            except Exception as e:
                logger.error(f"Error loading server schema from {schema_file}: {e}")
                continue
        return schemas

    def remove_server_schema(self, server_name: str) -> bool:
        """Remove a server schema from the local registry.

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        schema_file = self.servers_path / f"{server_name}.json"

        if not schema_file.exists():
            logger.warning(f"Server schema '{server_name}' not found")
            return False

        try:
            schema_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error removing server schema {server_name}: {e}")
            return False

    def search_server_schemas(self, query: Optional[str] = None) -> List[ServerSchema]:
        """Search for server schemas in the local registry.

        Args:
            query: Optional search query

        Returns:
            List of matching server schemas
        """
        all_schemas = list(self.list_server_schemas().values())

        if not query:
            return all_schemas

        query = query.lower()
        results = []

        for schema in all_schemas:
            # Check standard fields
            if (
                query in schema.name.lower()
                or (schema.display_name and query in schema.display_name.lower())
                or query in schema.description.lower()
            ):
                results.append(schema)
                continue

            # Check in tags
            if any(query in tag.lower() for tag in schema.tags):
                results.append(schema)
                continue

            # Check in categories
            if any(query in cat.lower() for cat in schema.categories):
                results.append(schema)
                continue

        return results
