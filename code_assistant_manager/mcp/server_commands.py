"""Simplified MCP Server Commands for managing MCP servers across clients"""

import json
from typing import List, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .installation_manager import InstallationManager
from .registry_manager import LocalRegistryManager

console = Console()
app = typer.Typer(
    help="Simplified MCP Server Management Commands", no_args_is_help=True
)
registry_manager = LocalRegistryManager()
installation_manager = InstallationManager()
# Factory to create MCPManager instances. Tests can monkeypatch MCPManagerFactory on this module to inject fakes.
from . import manager as _manager_module  # noqa: E402

MCPManagerFactory = lambda: _manager_module.MCPManager()


@app.command()
def list(
    client: Optional[str] = typer.Option(
        None, "--client", "-c", help="Show only servers installed for this client"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Use interactive mode"
    ),
):
    """List MCP servers. Use --client to show installed servers."""
    if client:
        # Support comma-separated client lists (e.g., "claude,codex") and the special value "all"
        manager = MCPManagerFactory()
        if isinstance(client, str) and client.strip().lower() == "all":
            clients = manager.get_available_tools()
        else:
            clients = [c.strip() for c in client.split(",") if c.strip()]

        # Validate requested clients
        validated_clients = []
        for cn in clients:
            client_obj = manager.get_client(cn)
            if client_obj:
                validated_clients.append((cn, client_obj))
            else:
                console.print(f"[red]Error:[/] Client '{cn}' is not supported.")
        if not validated_clients:
            console.print("[red]Error:[/] No valid clients specified.")
            return

        # List servers for each validated client
        for client_name, client_obj in validated_clients:
            console.print(f"[bold]MCP Servers installed for {client_name}:[/]")
            success = client_obj.list_servers()
            if not success:
                console.print(
                    f"[red]Error:[/] Failed to list servers for '{client_name}'."
                )
        return

    # Show available servers from registry
    schemas = registry_manager.list_server_schemas().values()

    if not schemas:
        console.print("[yellow]No MCP servers found in the local registry.[/]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Display Name", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Categories", style="blue")

    for schema in schemas:
        display_name = schema.display_name or schema.name
        categories = ", ".join(schema.categories) if schema.categories else "None"
        table.add_row(schema.name, display_name, schema.description, categories)

    console.print(table)


@app.command()
def search(query: str = typer.Argument(..., help="Search query to filter servers")):
    """Search for MCP servers by name, description, or tags."""
    schemas = registry_manager.search_server_schemas(query)

    if not schemas:
        console.print(f"[yellow]No MCP servers found matching '{query}'.[/]")
        return

    table = Table(title=f"MCP Servers matching '{query}'")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Display Name", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Categories", style="blue")

    for schema in schemas:
        display_name = schema.display_name or schema.name
        categories = ", ".join(schema.categories) if schema.categories else "None"
        table.add_row(schema.name, display_name, schema.description, categories)

    console.print(table)


# ==================== Show Command Helper Functions ====================


def _display_optional_field(label: str, value: Optional[str]) -> None:
    """Display an optional field if it has a value."""
    if value:
        console.print(f"[bold]{label}:[/] {value}")


def _display_author_info(author: Optional[dict]) -> None:
    """Display author information."""
    if not author:
        return

    author_info = author.get("name", "Unknown")
    if author.get("url"):
        author_info += f" ({author['url']})"
    console.print(f"[bold]Author:[/] {author_info}")


def _display_installation_methods(installations: dict) -> None:
    """Display available installation methods."""
    console.print(f"\n[bold]Installation Methods:[/]")
    for method_name, method in installations.items():
        recommended = " [green](recommended)[/]" if method.recommended else ""
        console.print(f"  • {method_name}: {method.description}{recommended}")
        if method.command:
            args_str = " ".join(method.args) if method.args else ""
            console.print(f"    [dim]{method.command} {args_str}[/]")


def _display_tools(tools: Optional[list]) -> None:
    """Display available tools."""
    if not tools:
        return

    tool_names = []
    for tool in tools:
        if isinstance(tool, dict) and "name" in tool:
            tool_names.append(tool["name"])
        elif isinstance(tool, str):
            tool_names.append(tool)

    if tool_names:
        console.print(f"\n[bold]Available Tools:[/] {', '.join(tool_names)}")


def _display_examples(examples: Optional[list]) -> None:
    """Display usage examples."""
    if not examples:
        return

    console.print(f"\n[bold]Usage Examples:[/]")
    for i, example in enumerate(examples, 1):
        title = example.get("title", f"Example {i}")
        description = example.get("description", "")
        prompt = example.get("prompt", "")

        console.print(f"  [cyan]{title}[/]: {description}")
        if prompt:
            console.print(f'  Try: [italic]"{prompt}"[/]\n')


# ==================== Show Command ====================


@app.command()
def show(
    server_name: str,
    schema: bool = typer.Option(
        False, "--schema", help="Show raw JSON schema instead of formatted info"
    ),
):
    """Show detailed information about a specific MCP server."""
    server_schema = registry_manager.get_server_schema(server_name)

    if not server_schema:
        console.print(
            f"[red]Error:[/] Server '{server_name}' not found in the local registry."
        )
        return

    if schema:
        console.print(json.dumps(server_schema.model_dump(), indent=2))
        return

    # Header
    display_name = server_schema.display_name or server_schema.name
    console.print(f"\n[bold]{display_name}[/] ([cyan]{server_schema.name}[/])")
    console.print(f"[dim]{server_schema.description}[/]\n")

    # Optional metadata fields
    _display_optional_field("Repository", server_schema.repository)
    _display_optional_field("License", server_schema.license)
    _display_author_info(server_schema.author)

    # Installation methods
    _display_installation_methods(server_schema.installations)

    # Categories and tags
    if server_schema.categories:
        console.print(f"\n[bold]Categories:[/] {', '.join(server_schema.categories)}")
    if server_schema.tags:
        console.print(f"[bold]Tags:[/] {', '.join(server_schema.tags)}")

    # Tools and examples
    _display_tools(server_schema.tools)
    _display_examples(server_schema.examples)


@app.command()
def add(
    server_names: str = typer.Argument(
        ..., help="Server names to install (comma-separated)"
    ),
    client: str = typer.Option(
        "claude", "--client", "-c", help="Client to install to (claude, codex, all)"
    ),
    method: Optional[str] = typer.Option(
        None, "--method", "-m", help="Installation method to use"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force installation if server already exists"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Use interactive mode for server selection"
    ),
    scope: str = typer.Option(
        "user", "--scope", "-s", help="Configuration scope (user or project)"
    ),
):
    """Add MCP servers to a client."""
    if interactive:
        server_names_list = _interactive_server_selection("add")
        if not server_names_list:
            return
    else:
        server_names_list = [name.strip() for name in server_names.split(",")]

    # Use factory so tests can patch MCPManagerFactory
    manager = MCPManagerFactory()
    # Support comma-separated client lists (e.g., "claude,codex") and the special value "all"
    if isinstance(client, str) and client.strip().lower() == "all":
        clients = manager.get_available_tools()
    else:
        clients = [c.strip() for c in client.split(",") if c.strip()]
    # Validate requested clients
    validated_clients = []
    for cn in clients:
        if manager.get_client(cn):
            validated_clients.append(cn)
        else:
            console.print(f"[red]Error:[/] Client '{cn}' is not supported.")
    if not validated_clients:
        console.print("[red]Error:[/] No valid clients specified.")
        return
    clients = validated_clients

    for server_name in server_names_list:
        # Validate server exists
        schema = registry_manager.get_server_schema(server_name)
        if not schema:
            console.print(
                f"[red]Error:[/] Server '{server_name}' not found in the local registry."
            )
            continue

        for client_name in clients:
            console.print(
                f"Installing '{server_name}' to {client_name} (scope: {scope})..."
            )
            success = installation_manager.install_server(
                server_name=server_name,
                client_name=client_name,
                installation_method=method,
                force=force,
                scope=scope,
            )

            if success:
                console.print(
                    f"[green]✓[/] Successfully installed '{server_name}' to {client_name}"
                )
            else:
                console.print(
                    f"[red]✗[/] Failed to install '{server_name}' to {client_name}"
                )


@app.command()
def remove(
    server_names: str = typer.Argument(
        ..., help="Server names to remove (comma-separated)"
    ),
    client: str = typer.Option(
        "claude", "--client", "-c", help="Client to remove from (claude, codex, all)"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Use interactive mode for server selection"
    ),
    scope: str = typer.Option(
        "user", "--scope", "-s", help="Configuration scope (user or project)"
    ),
):
    """Remove MCP servers from a client."""
    if interactive:
        server_names_list = _interactive_server_selection("remove", client)
        if not server_names_list:
            return
    else:
        server_names_list = [name.strip() for name in server_names.split(",")]

    # Use factory so tests can patch MCPManagerFactory
    manager = MCPManagerFactory()
    # Support comma-separated client lists (e.g., "claude,codex") and the special value "all"
    if isinstance(client, str) and client.strip().lower() == "all":
        clients = manager.get_available_tools()
    else:
        clients = [c.strip() for c in client.split(",") if c.strip()]
    # Validate requested clients
    validated_clients = []
    for cn in clients:
        if manager.get_client(cn):
            validated_clients.append(cn)
        else:
            console.print(f"[red]Error:[/] Client '{cn}' is not supported.")
    if not validated_clients:
        console.print("[red]Error:[/] No valid clients specified.")
        return
    clients = validated_clients

    from .manager import MCPManager

    manager = MCPManager()

    for server_name in server_names_list:
        for client_name in clients:
            client_obj = manager.get_client(client_name)
            if not client_obj:
                console.print(
                    f"[red]Error:[/] Client '{client_name}' is not supported."
                )
                continue

            console.print(
                f"Removing '{server_name}' from {client_name} (scope: {scope})..."
            )
            success = client_obj.remove_server(server_name, scope)

            if success:
                console.print(
                    f"[green]✓[/] Successfully removed '{server_name}' from {client_name}"
                )
            else:
                console.print(
                    f"[red]✗[/] Failed to remove '{server_name}' from {client_name}"
                )


@app.command()
def update(
    server_names: str = typer.Argument(
        ..., help="Server names to update (comma-separated)"
    ),
    client: str = typer.Option(
        "claude", "--client", "-c", help="Client to update in (claude, codex, all)"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Use interactive mode for server selection"
    ),
    scope: str = typer.Option(
        "user", "--scope", "-s", help="Configuration scope (user or project)"
    ),
):
    """Update/reinstall MCP servers for a client."""
    if interactive:
        server_names_list = _interactive_server_selection("update", client)
        if not server_names_list:
            return
    else:
        server_names_list = [name.strip() for name in server_names.split(",")]

    # Use factory so tests can patch MCPManagerFactory
    manager = MCPManagerFactory()
    # Support comma-separated client lists (e.g., "claude,codex") and the special value "all"
    if isinstance(client, str) and client.strip().lower() == "all":
        clients = manager.get_available_tools()
    else:
        clients = [c.strip() for c in client.split(",") if c.strip()]
    # Validate requested clients
    validated_clients = []
    for cn in clients:
        if manager.get_client(cn):
            validated_clients.append(cn)
        else:
            console.print(f"[red]Error:[/] Client '{cn}' is not supported.")
    if not validated_clients:
        console.print("[red]Error:[/] No valid clients specified.")
        return
    clients = validated_clients

    from .manager import MCPManager

    manager = MCPManager()

    for server_name in server_names_list:
        # Validate server exists
        schema = registry_manager.get_server_schema(server_name)
        if not schema:
            console.print(
                f"[red]Error:[/] Server '{server_name}' not found in the local registry."
            )
            continue

        for client_name in clients:
            client_obj = manager.get_client(client_name)
            if not client_obj:
                console.print(
                    f"[red]Error:[/] Client '{client_name}' is not supported."
                )
                continue

            console.print(
                f"Updating '{server_name}' for {client_name} (scope: {scope})..."
            )

            # Remove first
            remove_success = client_obj.remove_server(server_name, scope)
            if remove_success:
                console.print(f"  [dim]✓[/] Removed existing '{server_name}'")
            else:
                console.print(
                    f"  [dim]⚠[/] Could not remove '{server_name}' (might not have been installed)"
                )

            # Install again
            install_success = installation_manager.install_server(
                server_name=server_name, client_name=client_name, scope=scope
            )
            if install_success:
                console.print(
                    f"[green]✓[/] Successfully updated '{server_name}' for {client_name}"
                )
            else:
                console.print(
                    f"[red]✗[/] Failed to update '{server_name}' for {client_name}"
                )


def _interactive_server_selection(
    action: str, client: Optional[str] = None
) -> List[str]:
    """Interactive server selection for add/remove/update operations."""
    schemas = registry_manager.list_server_schemas()

    if not schemas:
        console.print("[yellow]No MCP servers found in the local registry.[/]")
        return []

    console.print(f"[bold]Select servers to {action}:[/]")

    # Show available servers
    for i, (name, schema) in enumerate(schemas.items(), 1):
        display_name = schema.display_name or schema.name
        console.print(f"  {i}. {display_name} ([cyan]{name}[/]) - {schema.description}")

    # Get user selection
    while True:
        selection = Prompt.ask("Enter server numbers (comma-separated) or 'all'")

        if selection.lower() == "all":
            return list(schemas.keys())

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_servers = []
            for idx in indices:
                if 0 <= idx < len(schemas):
                    selected_servers.append(list(schemas.keys())[idx])
                else:
                    console.print(f"[red]Invalid selection: {idx + 1}[/]")
                    selected_servers = []
                    break
            if selected_servers:
                return selected_servers
        except ValueError:
            console.print(
                "[red]Invalid input. Please enter numbers separated by commas or 'all'[/]"
            )


if __name__ == "__main__":
    app()
