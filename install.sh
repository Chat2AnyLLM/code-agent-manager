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
DESKTOP_ENTRY_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
DESKTOP_ICON_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}/icons/hicolor/256x256/apps
VERSION=${VERSION:-dev}
INSTALL_DESKTOP=0

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

build_desktop() {
    print_header "Building Tauri desktop and Go sidecar"
    mkdir -p dist src-tauri/binaries
    npm --prefix frontend run build
    go build -ldflags "-X main.version=$VERSION" -o src-tauri/binaries/cam-sidecar ./cmd/cam-sidecar
    cp src-tauri/binaries/cam-sidecar dist/cam-sidecar 2>/dev/null || cp src-tauri/binaries/cam-sidecar.exe dist/cam-sidecar.exe
    if command -v cargo >/dev/null 2>&1 && [ -f src-tauri/Cargo.toml ]; then
        cargo tauri build --manifest-path src-tauri/Cargo.toml || print_warning "cargo tauri build failed; sidecar fallback is still available"
    fi
    print_success "Built Go sidecar and attempted Tauri desktop build"
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

install_desktop() {
    print_header "Installing CAM sidecar"
    mkdir -p "$INSTALL_DIR"
    local sidecar_bin=cam-sidecar
    if [ -f dist/cam-sidecar.exe ]; then
        sidecar_bin=cam-sidecar.exe
    fi
    cp "dist/$sidecar_bin" "$INSTALL_DIR/$sidecar_bin"
    chmod 755 "$INSTALL_DIR/$sidecar_bin"
    print_success "Installed $sidecar_bin to $INSTALL_DIR"

    if [ "$(uname -s)" != "Linux" ]; then
        return
    fi

    mkdir -p "$DESKTOP_ENTRY_DIR" "$DESKTOP_ICON_DIR"
    if [ -f build/appicon.png ]; then
        cp build/appicon.png "$DESKTOP_ICON_DIR/cam-desktop.png"
    fi

    cat > "$DESKTOP_ENTRY_DIR/cam-desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Code Agent Manager
Comment=Desktop UI for code-agent-manager
Exec=$INSTALL_DIR/$sidecar_bin
Icon=cam-desktop
Terminal=false
Categories=Development;Utility;
EOF
    chmod 644 "$DESKTOP_ENTRY_DIR/cam-desktop.desktop"
    print_success "Installed sidecar desktop entry to $DESKTOP_ENTRY_DIR"
}

setup_config() {
    print_header "Setting up configuration"
    mkdir -p "$CONFIG_DIR"

    if [ -f code_assistant_manager/config.yaml ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cp code_assistant_manager/config.yaml "$CONFIG_DIR/config.yaml"
        print_success "Created $CONFIG_DIR/config.yaml"
    fi

    if [ -f "$CONFIG_DIR/providers.json" ]; then
        rm -f "$CONFIG_DIR/providers.json"
        print_success "Removed deprecated $CONFIG_DIR/providers.json"
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

    if [ "$INSTALL_DESKTOP" -eq 1 ]; then
        if [ -x "$INSTALL_DIR/cam-sidecar" ]; then
            print_success "cam-sidecar installed at $INSTALL_DIR/cam-sidecar"
            "$INSTALL_DIR/cam-sidecar" --version-json >/dev/null || true
        elif [ -x "$INSTALL_DIR/cam-sidecar.exe" ]; then
            print_success "cam-sidecar.exe installed at $INSTALL_DIR/cam-sidecar.exe"
            "$INSTALL_DIR/cam-sidecar.exe" --version-json >/dev/null || true
        else
            print_error "cam-sidecar not found"
            exit 1
        fi
    fi
}

uninstall_package() {
    print_header "Uninstalling CAM binaries"
    local removed=0
    for binary in cam code-agent-manager cam-desktop cam-sidecar cam-sidecar.exe; do
        if [ -f "$INSTALL_DIR/$binary" ]; then
            rm -f "$INSTALL_DIR/$binary"
            print_success "Removed $INSTALL_DIR/$binary"
            removed=1
        fi
    done
    if [ -f "$DESKTOP_ENTRY_DIR/cam-desktop.desktop" ]; then
        rm -f "$DESKTOP_ENTRY_DIR/cam-desktop.desktop"
        print_success "Removed $DESKTOP_ENTRY_DIR/cam-desktop.desktop"
        removed=1
    fi
    if [ -f "$DESKTOP_ICON_DIR/cam-desktop.png" ]; then
        rm -f "$DESKTOP_ICON_DIR/cam-desktop.png"
        print_success "Removed $DESKTOP_ICON_DIR/cam-desktop.png"
        removed=1
    fi
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

Usage: $0 [METHOD] [--desktop]

Methods:
    install          Build and install Go binaries (default)
    source           Alias for install
    pypi             Compatibility alias for install
    build            Build dist/cam and dist/code-agent-manager only
    verify           Verify installed binaries
    uninstall        Remove installed binaries from INSTALL_DIR
    uninstall-purge  Remove installed binaries and CAM config directory
    help             Show this help

Options:
    --desktop        Also build/install/verify dist/cam-desktop and Linux desktop entry

Environment:
    INSTALL_DIR      Destination directory (default: ~/.local/bin)
    CAM_CONFIG_DIR   Config directory (default: ~/.config/code-agent-manager)
    VERSION          Version embedded into binaries (default: dev)

EOF
}

main() {
    local method=install
    for arg in "$@"; do
        case "$arg" in
            --desktop)
                INSTALL_DESKTOP=1
                ;;
            install|source|pypi|build|verify|uninstall|uninstall-purge|help|--help|-h)
                method="$arg"
                ;;
            *)
                print_error "Unknown argument: $arg"
                show_usage
                exit 1
                ;;
        esac
    done
    print_header "Code Agent Manager Go Installer"

    case "$method" in
        install|source|pypi)
            check_go
            build_binaries
            if [ "$INSTALL_DESKTOP" -eq 1 ]; then
                build_desktop
            fi
            install_binaries
            if [ "$INSTALL_DESKTOP" -eq 1 ]; then
                install_desktop
            fi
            setup_config
            verify_install
            ;;
        build)
            check_go
            build_binaries
            if [ "$INSTALL_DESKTOP" -eq 1 ]; then
                build_desktop
            fi
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
