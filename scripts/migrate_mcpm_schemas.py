#!/usr/bin/env python3
"""
Migration script to migrate MCP server schemas from mcpm.sh to code-assistant-manager.

This script:
1. Reads all server manifests from mcpm.sh mcp-registry/servers/
2. Transforms them to the enhanced code-assistant-manager schema format
3. Saves them to code-assistant-manager/mcp/registry/servers/
4. Provides backward compatibility for existing simple schemas
"""

import copy
import difflib
import json
import os

# Import from code-assistant-manager
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from tabulate import tabulate

sys.path.insert(0, os.path.dirname(__file__))
from code_assistant_manager.mcp.schema import ServerSchema


class MCPMSchemaMigrator:
    """Migrator for mcpm.sh MCP server schemas to code-assistant-manager format"""

    def __init__(
        self,
        mcpm_path: str,
        code_assistant_manager_path: str,
        ignore_keys: Optional[List[str]] = None,
    ):
        self.mcpm_path = Path(mcpm_path)
        self.code_assistant_manager_path = Path(code_assistant_manager_path)
        self.mcpm_servers_dir = self.mcpm_path / "mcp-registry" / "servers"
        self.code_assistant_manager_servers_dir = (
            self.code_assistant_manager_path
            / "code_assistant_manager"
            / "mcp"
            / "registry"
            / "servers"
        )
        # Keys to ignore when comparing existing vs migrated schemas
        self.ignore_keys = ignore_keys or ["updated_at", "last_modified", "timestamp"]
        # Store detailed differences for reporting
        self.detailed_differences = []

    def migrate_server_schema(self, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a mcpm.sh server schema to code-assistant-manager enhanced format.

        Args:
            server_data: Raw server data from mcpm.sh

        Returns:
            Transformed server data compatible with code-assistant-manager
        """
        # Start with the original data
        migrated = dict(server_data)

        # Ensure repository is in the right format
        if isinstance(migrated.get("repository"), dict):
            # Already in object format, keep as is
            pass
        elif isinstance(migrated.get("repository"), str):
            # Convert string to object format
            migrated["repository"] = {
                "type": "git" if "github.com" in migrated["repository"] else "npm",
                "url": migrated["repository"],
            }

        # Ensure author is in object format if it's a string
        if isinstance(migrated.get("author"), str):
            migrated["author"] = {"name": migrated["author"]}

        # Tools/resources/prompts are already in the enhanced format from mcpm.sh
        # The ServerSchema now supports both formats

        # Set defaults for new fields
        migrated.setdefault("is_official", False)
        migrated.setdefault("is_archived", False)
        migrated.setdefault("docker_url", None)
        migrated.setdefault("homepage", None)

        return migrated

    def validate_migrated_schema(self, server_data: Dict[str, Any]) -> bool:
        """
        Validate that the migrated schema conforms to the code-assistant-manager format.

        Args:
            server_data: Migrated server data

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to create ServerSchema object
            schema = ServerSchema(**server_data)
            return True
        except Exception as e:
            print(f"Validation failed for {server_data.get('name', 'unknown')}: {e}")
            return False

    def _strip_ignored_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of data with ignore_keys removed (recursively)."""

        def _rec_copy(obj):
            if isinstance(obj, dict):
                res = {}
                for k, v in obj.items():
                    if k in self.ignore_keys:
                        continue
                    res[k] = _rec_copy(v)
                return res
            elif isinstance(obj, list):
                return [_rec_copy(x) for x in obj]
            else:
                return obj

        return _rec_copy(data)

    def _collect_detailed_differences(
        self, server_name: str, existing: Dict[str, Any], migrated: Dict[str, Any]
    ) -> None:
        """Collect detailed differences between existing and migrated schemas for reporting."""
        # Compare key fields that are likely to differ
        key_fields = [
            "installations",
            "description",
            "author",
            "license",
            "categories",
            "tags",
            "homepage",
            "repository",
        ]

        for field in key_fields:
            existing_val = existing.get(field)
            migrated_val = migrated.get(field)

            if existing_val != migrated_val:
                # Format the field name for display
                display_field = field.replace("_", " ").title()

                # Create readable representations
                existing_str = self._format_value_for_display(existing_val)
                migrated_str = self._format_value_for_display(migrated_val)

                # Determine change type
                change_type = self._determine_change_type(
                    field, existing_val, migrated_val
                )

                self.detailed_differences.append(
                    {
                        "file": f"📄 {server_name}.json",
                        "aspect": display_field,
                        "upstream": migrated_str,  # migrated is from upstream (mcpm.sh)
                        "local": existing_str,  # existing is from local registry
                        "change_type": change_type,
                    }
                )

        # Special handling for installations (most common difference)
        if "installations" in existing and "installations" in migrated:
            existing_installs = existing["installations"]
            migrated_installs = migrated["installations"]

            existing_keys = set(existing_installs.keys())
            migrated_keys = set(migrated_installs.keys())

            added = migrated_keys - existing_keys  # upstream has, local doesn't
            removed = existing_keys - migrated_keys  # local has, upstream doesn't

            if added:
                for method in added:
                    self.detailed_differences.append(
                        {
                            "file": f"📄 {server_name}.json",
                            "aspect": f"Installation method '{method}'",
                            "upstream": self._format_installation_method(
                                migrated_installs[method]
                            ),  # upstream has it
                            "local": "Not present",  # local doesn't have it
                            "change_type": "Available upstream",
                        }
                    )

            if removed:
                for method in removed:
                    self.detailed_differences.append(
                        {
                            "file": f"📄 {server_name}.json",
                            "aspect": f"Installation method '{method}'",
                            "upstream": "Not present",  # upstream doesn't have it
                            "local": self._format_installation_method(
                                existing_installs[method]
                            ),  # local has it
                            "change_type": "Local addition",
                        }
                    )

    def _format_value_for_display(self, value: Any) -> str:
        """Format a value for display in the differences table."""
        if value is None:
            return "None"
        elif isinstance(value, str):
            return value[:50] + "..." if len(value) > 50 else value
        elif isinstance(value, list):
            return ", ".join(str(item) for item in value[:3]) + (
                f" (+{len(value)-3} more)" if len(value) > 3 else ""
            )
        elif isinstance(value, dict):
            if "name" in value:
                return value["name"]
            elif "url" in value:
                return value["url"]
            else:
                return f"{{{', '.join(value.keys())}}}"
        else:
            return str(value)[:50] + "..." if len(str(value)) > 50 else str(value)

    def _format_installation_method(self, method_data: Dict[str, Any]) -> str:
        """Format installation method data for display."""
        if "command" in method_data and "args" in method_data:
            cmd = method_data["command"]
            args = " ".join(method_data["args"])
            return f"{cmd} {args}"
        elif "type" in method_data:
            return f"{method_data['type']} method"
        else:
            return str(method_data)[:50]

    def _determine_change_type(
        self, field: str, existing_val: Any, migrated_val: Any
    ) -> str:
        """Determine the type of change made."""
        if existing_val is None and migrated_val is not None:
            return "Added in upstream"
        elif existing_val is not None and migrated_val is None:
            return "Removed in upstream"
        elif (
            field == "installations"
            and isinstance(existing_val, dict)
            and isinstance(migrated_val, dict)
        ):
            existing_keys = set(existing_val.keys())
            migrated_keys = set(migrated_val.keys())
            if len(migrated_keys) > len(existing_keys):
                return "Enhanced upstream"  # upstream has more methods
            elif len(existing_keys) > len(migrated_keys):
                return "Enhanced locally"  # local has more methods
            else:
                return "Modified"
        else:
            return "Modified"

    def _pretty_json(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)

    def _print_json_diff(
        self, existing: Dict[str, Any], migrated: Dict[str, Any]
    ) -> None:
        """Print a human-friendly line-based diff between two JSON objects."""
        existing_lines = self._pretty_json(existing).splitlines()
        migrated_lines = self._pretty_json(migrated).splitlines()
        diff = difflib.unified_diff(
            existing_lines,
            migrated_lines,
            fromfile="existing",
            tofile="migrated",
            lineterm="",
        )
        print("\n".join(diff))

    def migrate_all_servers(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all server schemas from mcpm.sh to code-assistant-manager.

        Args:
            dry_run: If True, don't write files, just report what would be done

        Returns:
            Migration summary statistics
        """
        if not self.mcpm_servers_dir.exists():
            raise FileNotFoundError(
                f"mcpm.sh servers directory not found: {self.mcpm_servers_dir}"
            )

        if not self.code_assistant_manager_servers_dir.exists():
            if not dry_run:
                self.code_assistant_manager_servers_dir.mkdir(
                    parents=True, exist_ok=True
                )
            print(
                f"Created code-assistant-manager servers directory: {self.code_assistant_manager_servers_dir}"
            )

        # Get all server files from source
        source_files = list(self.mcpm_servers_dir.glob("*.json"))

        # Get all server files from target for comparison
        target_files = (
            list(self.code_assistant_manager_servers_dir.glob("*.json"))
            if self.code_assistant_manager_servers_dir.exists()
            else []
        )

        print(f"🔍 Analyzing {len(source_files)} MCP servers from mcpm.sh")
        print(f"📁 Found {len(target_files)} servers in local registry")
        print()

        # Progress tracking
        processed_count = 0
        identical_count = 0

        migrated_count = 0
        failed_count = 0
        skipped_count = 0
        different_count = 0

        # Track which target files we've processed (to identify extras)
        processed_target_files = set()

        for server_file in sorted(source_files):
            try:
                # Read mcpm.sh server data
                with open(server_file, "r", encoding="utf-8") as f:
                    server_data = json.load(f)

                server_name = server_data.get("name", server_file.stem)

                # Sanitize server name for filename (handle scoped npm packages)
                filename = self._sanitize_filename(server_name)

                code_assistant_manager_file = (
                    self.code_assistant_manager_servers_dir / f"{filename}.json"
                )
                processed_target_files.add(f"{filename}.json")

                # Migrate the schema
                migrated_data = self.migrate_server_schema(server_data)

                # Validate the migrated schema
                if not self.validate_migrated_schema(migrated_data):
                    print(f"Failed validation for {server_name}")
                    failed_count += 1
                    continue

                # If target exists, compare and prompt for override
                if code_assistant_manager_file.exists():
                    try:
                        with open(
                            code_assistant_manager_file, "r", encoding="utf-8"
                        ) as f:
                            existing_data = json.load(f)
                    except Exception as e:
                        print(
                            f"Warning: couldn't read existing file {code_assistant_manager_file}: {e}"
                        )
                        existing_data = None

                    if existing_data is not None:
                        # Prepare comparison copies with ignored keys removed
                        existing_cmp = self._strip_ignored_keys(existing_data)
                        migrated_cmp = self._strip_ignored_keys(migrated_data)

                        existing_json = json.dumps(
                            existing_cmp, sort_keys=True, ensure_ascii=False
                        )
                        migrated_json = json.dumps(
                            migrated_cmp, sort_keys=True, ensure_ascii=False
                        )

                        if existing_json == migrated_json:
                            # Skip identical files quietly - only count them
                            skipped_count += 1
                            continue
                        else:
                            # Show concise difference notification
                            print(f"🔧 {server_name}: differences detected")
                            different_count += 1

                            # Collect detailed differences for reporting
                            self._collect_detailed_differences(
                                server_name, existing_cmp, migrated_cmp
                            )

                            if dry_run:
                                print(
                                    f"Would overwrite {server_name}: differences detected between source and target"
                                )
                                # In dry run, we still count it as different for summary purposes
                                continue
                            else:
                                # If force flag is set on migrator, auto-overwrite
                                if getattr(self, "force", False):
                                    print(f"Overwriting {server_name} (force enabled)")
                                else:
                                    # Prompt user to override or ignore
                                    print(f"\n--- Differences for {server_name} ---")
                                    self._print_json_diff(existing_cmp, migrated_cmp)
                                    overwrite = typer.confirm(
                                        f"Overwrite target schema for '{server_name}'?",
                                        default=False,
                                    )
                                    if not overwrite:
                                        print(
                                            f"Skipping {server_name}: user chose not to overwrite"
                                        )
                                        skipped_count += 1
                                        continue
                                # else proceed to write/overwrite

                if not dry_run:
                    # Write to code-assistant-manager
                    with open(code_assistant_manager_file, "w", encoding="utf-8") as f:
                        json.dump(migrated_data, f, indent=2, ensure_ascii=False)
                        f.write("\n")  # Add trailing newline

                print(f"✅ Migrated {server_name}")
                migrated_count += 1

            except Exception as e:
                print(f"Error migrating {server_file.name}: {e}")
                failed_count += 1

        # Identify files only in target (destination but not in source)
        target_only_files = []
        for target_file in target_files:
            if target_file.name not in processed_target_files:
                target_only_files.append(target_file.name)
                # Add to detailed differences for files that exist only locally
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        local_data = json.load(f)
                    server_name = local_data.get("name", target_file.stem)
                    self.detailed_differences.append(
                        {
                            "file": f"📄 {server_name}.json",
                            "aspect": "Complete server entry",
                            "upstream": "Not present",
                            "local": f"Full server schema ({len(local_data)} fields)",
                            "change_type": "Local only",
                        }
                    )
                except Exception as e:
                    self.detailed_differences.append(
                        {
                            "file": f"📄 {target_file.name}",
                            "aspect": "Server file",
                            "upstream": "Not present",
                            "local": "Present in local registry",
                            "change_type": "Local only",
                        }
                    )

        return {
            "total_found": len(source_files),
            "migrated": migrated_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "different": different_count
            + len(target_only_files),  # Include target-only files in different count
            "target_only": len(target_only_files),
            "target_only_files": target_only_files,
            "dry_run": dry_run,
        }

    def backup_existing_schemas(self) -> Path:
        """
        Create a backup of existing code-assistant-manager server schemas.

        Returns:
            Path to backup directory
        """
        backup_dir = (
            self.code_assistant_manager_path / "backup" / "servers_pre_migration"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        for server_file in self.code_assistant_manager_servers_dir.glob("*.json"):
            backup_file = backup_dir / server_file.name
            with open(server_file, "r", encoding="utf-8") as src:
                with open(backup_file, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

        print(f"Backed up existing schemas to {backup_dir}")
        return backup_dir

    def _sanitize_filename(self, server_name: str) -> str:
        """
        Sanitize server name to create a valid filename.

        Args:
            server_name: Original server name (may contain @ and /)

        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace @ with empty string and / with hyphen for scoped packages
        # e.g., @scope/package-name becomes scope-package-name
        sanitized = server_name.replace("@", "").replace("/", "-")
        return sanitized


import typer

app = typer.Typer(
    help="Migrate MCP server schemas from mcpm.sh to code-assistant-manager"
)


@app.command()
def main(
    mcpm_path: str = typer.Option(..., help="Path to mcpm.sh repository"),
    code_assistant_manager_path: str = typer.Option(
        ".",
        help="Path to code-assistant-manager repository (default: current directory)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be migrated without making changes"
    ),
    backup: bool = typer.Option(
        False, help="Create backup of existing schemas before migration"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Automatically overwrite differing target schemas without prompting",
    ),
    ignore_keys: Optional[List[str]] = typer.Option(
        None,
        help="Comma-separated list of keys to ignore when comparing schemas (e.g. updated_at,last_modified)",
    ),
):
    """Perform migration of all server schemas from mcpm.sh to code-assistant-manager."""
    # Parse ignore_keys option into list if provided
    parsed_ignore_keys = None
    if ignore_keys:
        if isinstance(ignore_keys, str):
            parsed_ignore_keys = [
                k.strip() for k in ignore_keys.split(",") if k.strip()
            ]
        elif isinstance(ignore_keys, list):
            parsed_ignore_keys = ignore_keys

    # Create migrator with provided ignore_keys
    migrator = MCPMSchemaMigrator(
        mcpm_path, code_assistant_manager_path, ignore_keys=parsed_ignore_keys
    )

    # Backup if requested
    if backup and not dry_run:
        migrator.backup_existing_schemas()

    # Perform migration
    # Pass 'force' into environmental flag by temporarily setting an attribute on migrator
    migrator.force = force
    results = migrator.migrate_all_servers(dry_run=dry_run)

    # Print summary
    typer.echo("\nMigration Summary:")
    typer.echo(f"Total servers found: {results['total_found']}")
    typer.echo(f"Successfully migrated: {results['migrated']}")
    typer.echo(f"Failed: {results['failed']}")
    typer.echo(f"Skipped (already exist): {results['skipped']}")
    if results["dry_run"]:
        typer.echo("This was a dry run - no files were modified")

    # Add detailed difference analysis table
    typer.echo("\n" + "=" * 90)
    typer.echo("🎯 MCP REGISTRY MIGRATION ANALYSIS SUMMARY")
    typer.echo("=" * 90)

    # Create difference categories table
    typer.echo("\n📊 DIFFERENCE CATEGORIES:")
    categories_data = []

    # Category 1: Source files not in destination
    missing_count = results["migrated"] + results["failed"]
    status_icon = "⚠️" if missing_count > 0 else "✅"
    categories_data.append(
        [
            f"{status_icon} Files in source but not in destination",
            str(missing_count),
            (
                f"All {results['total_found']} MCP servers from mcpm.sh have local counterparts"
                if missing_count == 0
                else "Some files need migration"
            ),
        ]
    )

    # Category 2: Destination files not in source (locally added)
    local_icon = "➕" if results["target_only"] > 0 else "✅"
    local_details = (
        f"**{', '.join(results['target_only_files'])}** - Microsoft Learn MCP server"
        if results["target_only"] > 0
        else "No locally added files"
    )
    categories_data.append(
        [
            f"{local_icon} Files in destination but not in source",
            str(results["target_only"]),
            local_details,
        ]
    )

    # Category 3: Existing files that are different
    diff_icon = "🔧" if results["different"] > 0 else "✅"
    diff_details = (
        f"{results['different'] - results['target_only']} modified, {results['target_only']} local-only"
        if results["different"] > results["target_only"]
        else f"{results['different']} total differences"
    )
    categories_data.append(
        [
            f"{diff_icon} Existing files that are different",
            str(results["different"]),
            diff_details,
        ]
    )

    typer.echo(
        tabulate(
            categories_data,
            headers=["Category", "Count", "Details"],
            tablefmt="grid",
            maxcolwidths=[40, 8, 35],
        )
    )
    typer.echo()

    # Registry synchronization status table
    typer.echo("📈 REGISTRY SYNCHRONIZATION STATUS:")
    identical_count = (
        results["total_found"]
        - results["migrated"]
        - results["failed"]
        - (results["different"] - results["target_only"])
    )
    sync_rate = (
        (identical_count / results["total_found"] * 100)
        if results["total_found"] > 0
        else 100
    )

    status_data = [
        ["📊 Total upstream servers", str(results["total_found"]), ""],
        [
            "📊 Total local servers",
            str(results["total_found"] + results["target_only"]),
            "",
        ],
        [
            "🎯 Synchronization rate",
            f"{sync_rate:.1f}%",
            f"({identical_count}/{results['total_found']} servers identical)",
        ],
        [
            "✨ Local enhancements",
            str(
                results["target_only"] + (results["different"] - results["target_only"])
            ),
            f"{results['target_only']} new, {results['different'] - results['target_only']} modified",
        ],
    ]

    typer.echo(
        tabulate(
            status_data,
            headers=["Metric", "Value", "Details"],
            tablefmt="grid",
            maxcolwidths=[25, 15, 40],
        )
    )
    typer.echo()

    # Group and show detailed differences by server
    if results["different"] > 0 and migrator.detailed_differences:
        typer.echo("🔍 DETAILED DIFFERENCES BY SERVER:")

        # Group differences by server
        server_groups = {}
        for diff in migrator.detailed_differences:
            server_name = diff["file"].replace("📄 ", "").replace(".json", "")
            if server_name not in server_groups:
                server_groups[server_name] = []
            server_groups[server_name].append(diff)

        # Display each server group
        for server_name, diffs in server_groups.items():
            typer.echo(f"\n📄 {server_name}.json")
            typer.echo("-" * (len(server_name) + 7))

            # Create table for this server's differences
            server_diff_data = []
            for diff in diffs:
                server_diff_data.append(
                    [
                        diff["aspect"],
                        diff["upstream"],
                        diff["local"],
                        diff["change_type"],
                    ]
                )

            typer.echo(
                tabulate(
                    server_diff_data,
                    headers=[
                        "Aspect",
                        "Upstream (mcpm.sh)",
                        "Local Registry",
                        "Change Type",
                    ],
                    tablefmt="grid",
                    maxcolwidths=[25, 25, 35, 15],
                )
            )

    # Legend
    typer.echo("\n📋 LEGEND:")
    legend_data = [
        ["✅", "Identical to upstream"],
        ["➕", "Locally added servers"],
        ["🔧", "Enhanced/modified servers"],
        ["⚠️", "Missing files (needs attention)"],
    ]

    typer.echo(
        tabulate(
            legend_data,
            headers=["Symbol", "Meaning"],
            tablefmt="simple",
            colalign=("center", "left"),
        )
    )
    typer.echo("\n" + "=" * 90)

    if results["failed"] > 0:
        typer.echo("\nSome migrations failed. Check the output above for details.")
        raise typer.Exit(1)

    typer.echo("\nMigration completed successfully!")


if __name__ == "__main__":
    app()
