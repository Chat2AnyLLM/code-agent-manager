#!/usr/bin/env bash

# Code Assistant Manager Installation Script
# This script provides automated installation based on INSTALL.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check Python version
check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Python version: $PYTHON_VERSION"

    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
        print_success "Python version is compatible"
    else
        print_error "Python 3.8+ required"
        exit 1
    fi
}

# Check pip
check_pip() {
    if ! python3 -m pip --version >/dev/null 2>&1; then
        print_error "pip is not available"
        exit 1
    fi
    print_success "pip is available"
}

# Install from PyPI
install_pypi() {
    print_header "Installing from PyPI"
    print_info "Installing code-assistant-manager..."
    # Prefer a local wheel if available (useful for development/test environments)
    if ls dist/*.whl >/dev/null 2>&1; then
        WHEEL=$(ls dist/*.whl | head -n1)
        print_info "Found local wheel: $WHEEL -- installing (force reinstall, no deps)"
        # Force reinstall the wheel into the active environment but skip dependency
        # resolution so we can explicitly install requirements from the public index.
        if python3 -m pip install --force-reinstall --no-deps "$WHEEL"; then
            print_info "Installing runtime dependencies from requirements.txt via PyPI"
            if python3 -m pip install --index-url https://pypi.org/simple -r requirements.txt; then
                print_success "Installed from local wheel and installed dependencies"
                return 0
            else
                print_warning "Failed to install dependencies from PyPI"
                return 1
            fi
        else
            print_warning "Failed to install local wheel"
            return 1
        fi
    fi

    # Try installing from the public PyPI index explicitly. This avoids
    # using a configured internal index (which may not contain the package)
    # and yields a clearer error if the package isn't published.
    # If no local wheel, attempt to build a local wheel and install it.
    if build_and_install_local; then
        return 0
    fi

    if python3 -m pip install --index-url https://pypi.org/simple code-assistant-manager; then
        print_success "Installed from PyPI"
        return 0
    else
        print_warning "PyPI install failed; will attempt source install"
        return 1
    fi
}

# Build a wheel locally and install it from dist/
build_and_install_local() {
    print_header "Building local wheel"
    print_info "Ensuring build tools are available..."
    # Upgrade pip and ensure build tools are present
    python3 -m pip install --upgrade pip setuptools wheel build || {
        print_warning "Failed to install build tools"
        return 1
    }

    print_info "Cleaning previous build artifacts..."
    rm -rf build dist *.egg-info || true

    print_info "Running build..."
            if python3 -m build; then
        if ls dist/*.whl >/dev/null 2>&1; then
            WHEEL=$(ls dist/*.whl | head -n1)
            print_info "Built wheel: $WHEEL -- installing (no deps)"
            # Install wheel without deps, then install runtime deps explicitly
            if python3 -m pip install --force-reinstall --no-deps "$WHEEL"; then
                print_info "Installing runtime dependencies from requirements.txt via PyPI"
                if python3 -m pip install --index-url https://pypi.org/simple -r requirements.txt; then
                    print_success "Installed from built wheel and installed dependencies"
                    return 0
                else
                    print_warning "Failed to install dependencies from PyPI after build"
                    return 1
                fi
            else
                print_warning "Failed to install built wheel"
                return 1
            fi
        else
            print_warning "Build completed but no wheel found in dist/"
            return 1
        fi
    else
        print_warning "Local build failed"
        return 1
    fi
}

# Install from source
install_source() {
    print_header "Installing from source"
    local temp_dir=$(mktemp -d)
    print_info "Cloning repository..."

    if git clone https://github.com/Chat2AnyLLM/code-assistant-manager.git "$temp_dir" 2>/dev/null; then
        cd "$temp_dir"
        print_info "Installing in development mode..."
        python3 -m pip install -e .
        print_success "Installed from source"
        cd - >/dev/null
        rm -rf "$temp_dir"
    else
        print_error "Failed to clone repository"
        exit 1
    fi
}

# Setup configuration
setup_config() {
    print_header "Setting up configuration"

    mkdir -p ~/.config/code-assistant-manager

    # Try to find config files from local dir or installed package
    local pkg_dir=""
    if [ -d "code_assistant_manager" ]; then
        pkg_dir="code_assistant_manager"
    else
        # Try to find from installed package
        pkg_dir=$(python3 -c "import code_assistant_manager; import os; print(os.path.dirname(code_assistant_manager.__file__))" 2>/dev/null || echo "")
    fi

    # Copy config.yaml (multi-source repository configuration)
    if [ -n "$pkg_dir" ] && [ -f "$pkg_dir/config.yaml" ]; then
        if [ ! -f ~/.config/code-assistant-manager/config.yaml ]; then
            cp "$pkg_dir/config.yaml" ~/.config/code-assistant-manager/config.yaml
            print_success "Created config.yaml (multi-source repo configuration)"
            print_info "  You can edit ~/.config/code-assistant-manager/config.yaml to customize sources"
        else
            print_info "config.yaml already exists, skipping"
        fi
    fi

    if [ -n "$pkg_dir" ] && [ -f "$pkg_dir/providers.json" ]; then
        cp "$pkg_dir/providers.json" ~/.config/code-assistant-manager/providers.json
        print_success "Created providers.json"
    fi

    # Initialize skill_repos.json with built-in repos
    if [ -n "$pkg_dir" ] && [ -f "$pkg_dir/skill_repos.json" ]; then
        if [ ! -f ~/.config/code-assistant-manager/skill_repos.json ]; then
            cp "$pkg_dir/skill_repos.json" ~/.config/code-assistant-manager/skill_repos.json
            print_success "Created skill_repos.json with default repositories"
        else
            print_info "skill_repos.json already exists, skipping"
        fi
    fi

    if [ ! -f ~/.env ]; then
        touch ~/.env
        chmod 600 ~/.env
        print_success "Created .env file"
        cat > ~/.env << 'EOL'
# Add your API keys here
# GITHUB_TOKEN=ghu_your_github_token_here
# API_KEY_CLAUDE=sk-ant-your_claude_key_here
# API_KEY_OPENAI=sk-your_openai_key_here
EOL
    fi
}

# Verify installation
verify_install() {
    print_header "Verifying installation"

    if command -v code-assistant-manager >/dev/null 2>&1; then
        print_success "code-assistant-manager command found"
        VERSION=$(code-assistant-manager --version 2>/dev/null || echo "unknown")
        print_info "Version: $VERSION"
    else
        print_warning "code-assistant-manager not found in PATH"
        print_info "You may need to restart your shell or add Python bin to PATH"
    fi

    if command -v cam >/dev/null 2>&1; then
        print_success "cam command found"
    else
        print_warning "cam not found in PATH"
    fi
}

# Uninstall the package from the active Python environment
uninstall_package() {
    print_header "Uninstalling code-assistant-manager"
    if python3 -m pip show code-assistant-manager >/dev/null 2>&1; then
        python3 -m pip uninstall -y code-assistant-manager
        print_success "Uninstalled code-assistant-manager"
    else
        print_warning "code-assistant-manager is not installed in this environment"
    fi
}

# Purge user configuration
purge_config() {
    print_header "Purging user configuration"
    if [ -d "$HOME/.config/code-assistant-manager" ]; then
        rm -rf "$HOME/.config/code-assistant-manager"
        print_success "Removed ~/.config/code-assistant-manager"
    else
        print_warning "No user config directory found"
    fi

    if [ -f "$HOME/.env" ]; then
        rm -f "$HOME/.env"
        print_success "Removed ~/.env"
    else
        print_warning "No ~/.env file found"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Code Assistant Manager Installer

Usage: $0 [METHOD]

Methods:
    pypi      Install from PyPI (default)
    source    Install from GitHub source
    uninstall  Uninstall package from current Python environment
    uninstall-purge  Uninstall package and remove user config (~/.config and ~/.env)
    verify    Only verify current installation

Examples:
    $0              # Install from PyPI
    $0 source       # Install from source
    $0 verify       # Check current installation

EOF
}

# Main logic
main() {
    print_header "Code Assistant Manager Installer"

    METHOD=${1:-pypi}

    case $METHOD in
        pypi)
            check_python
            check_pip
            install_pypi
            setup_config
            verify_install
            ;;
        source)
            check_python
            check_pip
            install_source
            setup_config
            verify_install
            ;;
        verify)
            check_python
            check_pip
            verify_install
            ;;
        uninstall)
            check_python
            check_pip
            uninstall_package
            ;;
        uninstall-purge)
            check_python
            check_pip
            uninstall_package
            purge_config
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown method: $METHOD"
            show_usage
            exit 1
            ;;
    esac

    if [ "$METHOD" != "verify" ]; then
        print_success "Installation completed!"
        echo ""
        print_info "Next steps:"
        echo "1. Add API keys to ~/.env"
        echo "2. Run 'code-assistant-manager doctor' to verify setup"
        echo "3. Try 'code-assistant-manager --help' to see commands"
        echo ""
        print_info "For detailed documentation, see:"
        echo "  INSTALL.md - Installation guide"
        echo "  README.md  - Project overview"
    fi
}

main "$@"
