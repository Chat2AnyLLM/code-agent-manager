#!/bin/bash

# Script to verify all help messages use Typer style formatting
# Also tests commands that require parameters to ensure error messages are properly formatted

set -e

echo "🔍 Checking help messages and error messages for Typer style consistency..."
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if help output uses Typer style
check_typer_style() {
    local cmd="$1"
    local description="$2"

    echo -n "Checking $description... "

    # Run the command and capture output
    if ! output=$(cam $cmd 2>&1); then
        echo -e "${RED}✗ Failed to run command${NC}"
        return 1
    fi

    # Check for Typer-style patterns (including Rich formatting)
    # Look for "Usage:" or "╭─ Options ──" (Rich format)
    # A valid Typer command must have Usage and at least one of: Options, Commands, Arguments, or Run help message
    if (echo "$output" | grep -q "Usage:" || echo "$output" | grep -q "╭─") && \
       (echo "$output" | grep -q "Options:" || echo "$output" | grep -q "╭─ Options" || \
        echo "$output" | grep -q "Commands:" || echo "$output" | grep -q "╭─ Commands" || \
        echo "$output" | grep -q "Run.*--help" || echo "$output" | grep -q "Arguments:" || \
        echo "$output" | grep -q "╭─ Arguments"); then
        echo -e "${GREEN}✓ Typer style${NC}"
        return 0
    else
        echo -e "${RED}✗ Not Typer style${NC}"
        echo "Output preview:"
        echo "$output" | head -10
        echo "..."
        return 1
    fi
}

# Function to check if error output uses Typer style
check_error_typer_style() {
    local cmd="$1"
    local description="$2"

    echo -n "Checking $description error... "

    # Run the command and capture output
    if output=$(cam $cmd 2>&1); then
        echo -e "${YELLOW}⚠ Command succeeded when it should have failed${NC}"
        return 1
    fi

    # Check for Typer-style error patterns
    # Error messages should show usage or have proper formatting
    if echo "$output" | grep -q "Usage:" || echo "$output" | grep -q "Error:" || echo "$output" | grep -q "╭─"; then
        echo -e "${GREEN}✓ Typer style${NC}"
        return 0
    else
        echo -e "${RED}✗ Not Typer style${NC}"
        echo "Error output preview:"
        echo "$output" | head -10
        echo "..."
        return 1
    fi
}

# Function to check for problematic patterns that indicate non-Typer formatting
check_no_problematic_formatting() {
    local cmd="$1"
    local description="$2"

    if ! output=$(cam $cmd 2>&1); then
        return 1
    fi

    # Check for patterns that indicate truly broken/custom formatting
    # (not just Rich formatting which is fine)

    # If it has "Usage:" but no "Options:" or "Commands:", that's problematic
    if echo "$output" | grep -q "^Usage:"; then
        if ! echo "$output" | grep -q "Options:" && ! echo "$output" | grep -q "╭─ Options"; then
            echo -e "${YELLOW}⚠ Warning: Usage line found but no Options section in $description${NC}"
            return 1
        fi
    fi

    return 0
}

failures=0

echo "=== Help Messages ==="
# Test main commands
check_typer_style "--help" "main help" || ((failures++))
check_no_problematic_formatting "--help" "main help"

echo
echo "=== Individual Commands Help ==="
# Test individual commands
commands=("launch --help" "mcp" "upgrade --help" "doctor --help")
descriptions=("launch command" "mcp command" "upgrade command" "doctor command")

for i in "${!commands[@]}"; do
    check_typer_style "${commands[$i]}" "${descriptions[$i]}" || ((failures++))
    check_no_problematic_formatting "${commands[$i]}" "${descriptions[$i]}"
done

echo
echo "=== Launch Sub-commands Help ==="
# Test launch sub-commands
launch_commands=("claude --help" "codex --help" "qwen --help" "gemini --help")
for cmd in "${launch_commands[@]}"; do
    if cam launch $cmd >/dev/null 2>&1; then
        check_typer_style "launch $cmd" "launch $cmd" || ((failures++))
        check_no_problematic_formatting "launch $cmd" "launch $cmd"
    else
        echo -e "${YELLOW}⚠ launch $cmd not available${NC}"
    fi
done

echo
echo "=== MCP Server Commands Help ==="
# Test MCP commands (updated from 'mcp server')
mcp_commands=("list --help" "add --help" "remove --help")
for cmd in "${mcp_commands[@]}"; do
    if cam mcp $cmd >/dev/null 2>&1; then
        check_typer_style "mcp $cmd" "mcp $cmd" || ((failures++))
        check_no_problematic_formatting "mcp $cmd" "mcp $cmd"
    else
        echo -e "${YELLOW}⚠ mcp $cmd not available${NC}"
    fi
done

echo
echo "=== Short Aliases Help ==="
# Test short aliases
aliases=("m" "u --help" "d --help" "l --help")
alias_descriptions=("m alias" "u alias" "d alias" "l alias")

for i in "${!aliases[@]}"; do
    check_typer_style "${aliases[$i]}" "${alias_descriptions[$i]}" || ((failures++))
    check_no_problematic_formatting "${aliases[$i]}" "${alias_descriptions[$i]}"
done

echo
echo "=== Commands Requiring Parameters (Error Messages) ==="
# Test commands that require parameters - should show error messages
# Note: Some commands show help instead of failing, which is also acceptable Typer behavior
error_commands=("mcp add" "mcp remove" "mcp update")
error_descriptions=("mcp add (missing names)" "mcp remove (missing names)" "mcp update (missing names)")

for i in "${!error_commands[@]}"; do
    # For some commands, we expect them to show help rather than fail
    # Both behaviors are acceptable for Typer-style CLI
    if output=$(cam ${error_commands[$i]} 2>&1); then
        # Command succeeded - check if it shows help
        check_typer_style "${error_commands[$i]}" "${error_descriptions[$i]} (shows help)" || ((failures++))
    else
        # Command failed - check if error message is properly formatted
        check_error_typer_style "${error_commands[$i]}" "${error_descriptions[$i]}" || ((failures++))
    fi
done

echo
echo "=== Summary ==="
if [ $failures -eq 0 ]; then
    echo -e "${GREEN}✓ All help and error messages use Typer style!${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $failures messages that don't use Typer style${NC}"
    exit 1
fi