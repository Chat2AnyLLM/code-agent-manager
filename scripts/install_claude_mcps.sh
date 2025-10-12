#!/bin/bash

# Script to easily install MCP servers for specified clients
# Usage: ./install_claude_mcps.sh [-c clients] [mcp_names...]
# If no MCP names are provided, installs all available MCPs
# If no clients are specified, defaults to 'claude'

set -e

# Default MCP servers
DEFAULT_MCPS=(
    "microsoft-learn"
    "memory"
    "context7"
    "sequential-thinking"
    "serena"
    "terraform"
    "deepwiki"
    "awslabs.aws-documentation-mcp-server"
    "wikipedia-mcp"
    "aws-knowledge-mcp-server"
)

# Default client
DEFAULT_CLIENT="claude"

# Function to display usage
usage() {
    echo "Usage: $0 [-c clients] [mcp_names...]"
    echo ""
    echo "Install MCP servers for specified clients. If no MCP names are provided, installs all available:"
    echo "  ${DEFAULT_MCPS[*]}"
    echo ""
    echo "Options:"
    echo "  -c, --clients CLIENTS    Comma-separated list of clients (e.g., 'claude' or 'claude,codex')"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Install all MCPs for claude client"
    echo "  $0 -c claude,codex                   # Install all MCPs for claude and codex clients"
    echo "  $0 microsoft-learn memory            # Install specific MCPs for claude client"
    echo "  $0 -c claude,codex microsoft-learn   # Install specific MCP for claude and codex clients"
}

# Parse command line arguments
CLIENTS="$DEFAULT_CLIENT"
MCP_NAMES=""

# Check if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clients)
            CLIENTS="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            # Remaining arguments are MCP names
            MCP_NAMES="$*"
            break
            ;;
    esac
done

# If no MCP names provided, use all default MCPs
if [ -z "$MCP_NAMES" ]; then
    MCP_NAMES=$(IFS=,; echo "${DEFAULT_MCPS[*]}")
fi

echo "Installing MCP servers for clients: $CLIENTS"
echo "MCP servers: $MCP_NAMES"

# Execute the cam command
cam mcp server add "$MCP_NAMES" -c "$CLIENTS"

echo "Installation complete!"
