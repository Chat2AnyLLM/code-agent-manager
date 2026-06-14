#!/usr/bin/env bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_header() { echo -e "${BLUE}=== $1 ===${NC}"; }

INSTALL_DIR=${INSTALL_DIR:-"$HOME/.local/bin"}
CONFIG_DIR=${CAM_CONFIG_DIR:-"$HOME/.config/code-agent-manager"}
VERSION=${VERSION:-dev}

check_go() {
    if ! command -v go >/dev/null 2>&1; then
        print_error "Go is not installed"
        print_info "Install Go 1.26+ and rerun ./install.sh"
        exit 1
    fi
    print_info "$(go version)"
}

build_binaries() {
    print_header "Building Go binaries"
    mkdir -p dist
    go build -ldflags "-X main.version=$VERSION" -o dist/cam ./cmd/cam
    go build -ldflags "-X main.version=$VERSION" -o dist/code-agent-manager ./cmd/code-agent-manager
    print_success "Built dist/cam and dist/code-agent-manager"
}

install_binaries() {
    print_header "Installing CAM"
    mkdir -p "$INSTALL_DIR"
    cp dist/cam "$INSTALL_DIR/cam"
    cp dist/code-agent-manager "$INSTALL_DIR/code-agent-manager"
    chmod 755 "$INSTALL_DIR/cam" "$INSTALL_DIR/code-agent-manager"
    print_success "Installed cam and code-agent-manager to $INSTALL_DIR"

    case ":$PATH:" in
        *":$INSTALL_DIR:"*) ;;
        *) print_warning "$INSTALL_DIR is not in PATH" ;;
    esac
}

setup_config() {
    print_header "Setting up configuration"
    mkdir -p "$CONFIG_DIR"

    if [ -f providers.json ]; then
        if [ ! -f "$CONFIG_DIR/providers.json" ]; then
            cp providers.json "$CONFIG_DIR/providers.json"
            print_success "Created $CONFIG_DIR/providers.json"
        else
            print_info "providers.json already exists, skipping"
        fi
    elif [ -f providers.json.example ] && [ ! -f "$CONFIG_DIR/providers.json" ]; then
        cp providers.json.example "$CONFIG_DIR/providers.json"
        print_success "Created $CONFIG_DIR/providers.json from providers.json.example"
    fi

    if [ -f code_assistant_manager/config.yaml ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cp code_assistant_manager/config.yaml "$CONFIG_DIR/config.yaml"
        print_success "Created $CONFIG_DIR/config.yaml"
    fi

    if [ ! -f "$HOME/.env" ]; then
        touch "$HOME/.env"
        chmod 600 "$HOME/.env"
        print_success "Created $HOME/.env"
    fi
}

verify_install() {
    print_header "Verifying installation"
    if [ -x "$INSTALL_DIR/cam" ]; then
        print_success "cam installed at $INSTALL_DIR/cam"
        "$INSTALL_DIR/cam" --version || true
    elif command -v cam >/dev/null 2>&1; then
        print_success "cam command found: $(command -v cam)"
        cam --version || true
    else
        print_error "cam not found"
        exit 1
    fi

    if [ -x "$INSTALL_DIR/code-agent-manager" ]; then
        print_success "code-agent-manager installed at $INSTALL_DIR/code-agent-manager"
        "$INSTALL_DIR/code-agent-manager" --version || true
    elif command -v code-agent-manager >/dev/null 2>&1; then
        print_success "code-agent-manager command found: $(command -v code-agent-manager)"
    else
        print_error "code-agent-manager not found"
        exit 1
    fi
}

uninstall_package() {
    print_header "Uninstalling CAM binaries"
    local removed=0
    for binary in cam code-agent-manager; do
        if [ -f "$INSTALL_DIR/$binary" ]; then
            rm -f "$INSTALL_DIR/$binary"
            print_success "Removed $INSTALL_DIR/$binary"
            removed=1
        fi
    done
    if [ "$removed" -eq 0 ]; then
        print_warning "No CAM binaries found in $INSTALL_DIR"
    fi
}

purge_config() {
    print_header "Purging user configuration"
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        print_success "Removed $CONFIG_DIR"
    else
        print_warning "No config directory found at $CONFIG_DIR"
    fi
}

show_usage() {
    cat <<EOF
Code Agent Manager Installer

Usage: $0 [METHOD]

Methods:
    install          Build and install Go binaries (default)
    source           Alias for install
    pypi             Compatibility alias for install
    build            Build dist/cam and dist/code-agent-manager only
    verify           Verify installed binaries
    uninstall        Remove installed binaries from INSTALL_DIR
    uninstall-purge  Remove installed binaries and CAM config directory
    help             Show this help

Environment:
    INSTALL_DIR      Destination directory (default: ~/.local/bin)
    CAM_CONFIG_DIR   Config directory (default: ~/.config/code-agent-manager)
    VERSION          Version embedded into binaries (default: dev)

EOF
}

main() {
    local method=${1:-install}
    print_header "Code Agent Manager Go Installer"

    case "$method" in
        install|source|pypi)
            check_go
            build_binaries
            install_binaries
            setup_config
            verify_install
            ;;
        build)
            check_go
            build_binaries
            ;;
        verify)
            verify_install
            ;;
        uninstall)
            uninstall_package
            ;;
        uninstall-purge)
            uninstall_package
            purge_config
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown method: $method"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
