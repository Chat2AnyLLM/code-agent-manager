"""MCP Manager class for orchestrating MCP operations across all tools."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from .base import MCPBase, print_squared_frame


class MCPManager(MCPBase):
    """Manager class for handling MCP operations across all tools."""

    def __init__(self):
        super().__init__()
        self.clients = self._initialize_clients()

    def _initialize_clients(
        self,
    ) -> Dict[str, "MCPClient"]:  # Forward reference to avoid circular import
        """Initialize client instances for all supported tools."""
        # Import here to avoid circular import
        from .clients import (
            ClaudeMCPClient,
            CodeBuddyMCPClient,
            CodexMCPClient,
            CopilotMCPClient,
            CrushMCPClient,
            ContinueMCPClient,
            CursorAgentMCPClient,
            DroidMCPClient,
            GeminiMCPClient,
            IflowMCPClient,
            NeovateMCPClient,
            OpenCodeMCPClient,
            QoderCLIMCPClient,
            QwenMCPClient,
            ZedMCPClient,
        )

        return {
            "claude": ClaudeMCPClient(),
            "codex": CodexMCPClient(),
            "gemini": GeminiMCPClient(),
            "qwen": QwenMCPClient(),
            "copilot": CopilotMCPClient(),
            "codebuddy": CodeBuddyMCPClient(),
            "droid": DroidMCPClient(),
            "iflow": IflowMCPClient(),
            "zed": ZedMCPClient(),
            "qodercli": QoderCLIMCPClient(),
            "neovate": NeovateMCPClient(),
            "crush": CrushMCPClient(),
            "cursor-agent": CursorAgentMCPClient(),
            "opencode": OpenCodeMCPClient(),
            "continue": ContinueMCPClient(),
        }

    def get_client(self, tool_name: str):
        """Get the MCP client for a specific tool."""
        return self.clients.get(tool_name.lower())

    def add_server(self, tool_name: str, server_name: str, scope: str = "user") -> bool:
        """Add a specific MCP server for a tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.add_server(server_name, scope)

    def remove_server(self, tool_name: str, server_name: str) -> bool:
        """Remove a specific MCP server for a tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.remove_server(server_name)

    def list_servers(self, tool_name: str) -> bool:
        """List MCP servers for a specific tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.list_servers()

    def add_all_servers_for_tool(self, tool_name: str, scope: str = "user") -> bool:
        """Add all MCP servers for a specific tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.add_all_servers(scope)

    def remove_all_servers_for_tool(self, tool_name: str) -> bool:
        """Remove all MCP servers for a specific tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.remove_all_servers()

    def refresh_servers_for_tool(self, tool_name: str) -> bool:
        """Refresh all MCP servers for a specific tool."""
        client = self.get_client(tool_name)
        if not client:
            print(f"Error: No MCP client found for tool '{tool_name}'")
            return False
        return client.refresh_servers()

    def add_all_servers(self, scope: str = "user") -> bool:
        """Add MCP servers for all configured tools."""
        available_tools = self.get_available_tools()
        print_squared_frame(
            "MCP SERVERS", "Installing configured MCP servers for all tools..."
        )

        # Early return if no tools are available
        if not available_tools:
            print_squared_frame(
                "MCP SERVERS - COMPLETE",
                "No tools configured for MCP server installation",
            )
            return True

        # Process tools in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=len(available_tools)) as executor:
            # Submit all tool tasks
            future_to_tool = {
                executor.submit(
                    self.add_all_servers_for_tool, tool_name, scope
                ): tool_name
                for tool_name in available_tools
            }

            # Collect results
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    result = future.result()
                    results[tool_name] = result
                except Exception as e:
                    results[tool_name] = f"Error: {e}"

        # Display grouped results with framing
        success_status = True
        status_lines = []
        for tool_name in available_tools:
            if tool_name in results:
                result = results[tool_name]
                if isinstance(result, bool) and result:
                    status_lines.append(
                        f"  {tool_name.upper()}: ✓ Successfully installed"
                    )
                elif isinstance(result, bool) and not result:
                    status_lines.append(f"  {tool_name.upper()}: ✗ Failed to install")
                    success_status = False
                else:
                    status_lines.append(f"  {tool_name.upper()}: ✗ {result}")
                    success_status = False

        if success_status:
            content = (
                "Overall Status: ✓ Successfully installed MCP servers for all tools\n"
                + "\n".join(status_lines)
            )
            print_squared_frame("MCP SERVERS - INSTALLATION COMPLETE", content)
            return True
        else:
            content = (
                "Overall Status: ✗ Failed to install MCP servers for one or more tools\n"
                + "\n".join(status_lines)
            )
            print_squared_frame("MCP SERVERS - INSTALLATION FAILED", content)
            return False

    def remove_all_servers(self) -> bool:
        """Remove MCP servers for all configured tools."""
        available_tools = self.get_available_tools()
        print_squared_frame(
            "MCP SERVERS", "Removing configured MCP servers for all tools..."
        )

        # Early return if no tools are available
        if not available_tools:
            print_squared_frame(
                "MCP SERVERS - COMPLETE", "No tools configured for MCP server removal"
            )
            return True

        # Process tools in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=len(available_tools)) as executor:
            # Submit all tool tasks
            future_to_tool = {
                executor.submit(self.remove_all_servers_for_tool, tool_name): tool_name
                for tool_name in available_tools
            }

            # Collect results
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    result = future.result()
                    results[tool_name] = result
                except Exception as e:
                    results[tool_name] = f"Error: {e}"

        # Display grouped results with framing
        success_status = True
        status_lines = []
        for tool_name in available_tools:
            if tool_name in results:
                result = results[tool_name]
                if isinstance(result, bool) and result:
                    status_lines.append(
                        f"  {tool_name.upper()}: ✓ Successfully removed"
                    )
                elif isinstance(result, bool) and not result:
                    status_lines.append(f"  {tool_name.upper()}: ✗ Failed to remove")
                    success_status = False
                else:
                    status_lines.append(f"  {tool_name.upper()}: ✗ {result}")
                    success_status = False

        if success_status:
            content = (
                "Overall Status: ✓ Successfully removed MCP servers for all tools\n"
                + "\n".join(status_lines)
            )
            print_squared_frame("MCP SERVERS - REMOVAL COMPLETE", content)
            return True
        else:
            content = (
                "Overall Status: ✗ Failed to remove MCP servers for one or more tools\n"
                + "\n".join(status_lines)
            )
            print_squared_frame("MCP SERVERS - REMOVAL FAILED", content)
            return False

    def refresh_all_servers(self) -> bool:
        """Refresh MCP servers for all configured tools."""
        available_tools = self.get_available_tools()
        print_squared_frame(
            "MCP SERVERS", "Refreshing configured MCP servers for all tools..."
        )

        # Process tools sequentially for refresh (not parallel to avoid conflicts)
        results = {}
        for tool_name in available_tools:
            print(f"\n{'='*60}")
            print(f"Refreshing servers for {tool_name.upper()}")
            print(f"{'='*60}")

            success = self.refresh_servers_for_tool(tool_name)
            results[tool_name] = success

        # Display grouped results
        success_status = True
        status_lines = []
        success_count = 0

        for tool_name in available_tools:
            if tool_name in results:
                success = results[tool_name]
                if success:
                    status_lines.append(
                        f"  {tool_name.upper()}: ✅ Successfully refreshed"
                    )
                    success_count += 1
                else:
                    status_lines.append(f"  {tool_name.upper()}: ❌ Failed to refresh")
                    success_status = False

        summary = "\n".join(status_lines)
        if success_status:
            content = f"Overall Status: ✅ Successfully refreshed MCP servers for all {len(available_tools)} tools\n\n{summary}"
            print_squared_frame("MCP SERVERS - REFRESH COMPLETE", content)
            return True
        else:
            content = f"Overall Status: ⚠️  Refreshed {success_count}/{len(available_tools)} tools successfully\n\n{summary}"
            print_squared_frame("MCP SERVERS - REFRESH PARTIAL", content)
            return success_count > 0

    def list_all_servers(self) -> bool:
        """List MCP servers for all configured tools in parallel with squared frames."""
        available_tools = self.get_available_tools()
        print_squared_frame(
            "MCP SERVERS", "Listing configured MCP servers for all tools..."
        )

        # Early return if no tools are available
        if not available_tools:
            print_squared_frame(
                "MCP SERVERS - COMPLETE", "No tools configured for MCP server listing"
            )
            return True

        # Process tools in parallel by calling client.list_servers()
        success_status = True

        def _list_for_tool(tool_name):
            """Helper to list servers for a tool."""
            client = self.get_client(tool_name)
            if not client:
                print_squared_frame(
                    f"{tool_name.upper()} MCP SERVERS",
                    f"Error: No MCP client found for tool '{tool_name}'",
                )
                return False

            try:
                return client.list_servers()
            except Exception as e:
                print_squared_frame(
                    f"{tool_name.upper()} MCP SERVERS",
                    f"Error listing servers for {tool_name}: {e}",
                )
                return False

        with ThreadPoolExecutor(max_workers=len(available_tools)) as executor:
            # Submit all tool tasks
            future_to_tool = {
                executor.submit(_list_for_tool, tool_name): tool_name
                for tool_name in available_tools
            }

            # Collect results
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    success = future.result()
                    if not success:
                        success_status = False
                except Exception as e:
                    print_squared_frame(
                        f"{tool_name.upper()} MCP SERVERS", f"Error: {e}"
                    )
                    success_status = False

        if success_status:
            print_squared_frame(
                "MCP SERVERS",
                "✓ Overall Status: Successfully listed MCP servers for all tools",
            )
            return True
        else:
            print_squared_frame(
                "MCP SERVERS",
                "✗ Overall Status: Failed to list MCP servers for one or more tools",
            )
            return False
