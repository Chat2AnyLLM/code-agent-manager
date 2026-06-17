ifeq ($(OS),Windows_NT)
SHELL := pwsh.exe
.SHELLFLAGS := -NoProfile -Command
EXE := .exe
INSTALL_DIR ?= $(USERPROFILE)/.local/bin
CONFIG_DIR ?= $(USERPROFILE)/.config/code-agent-manager
TAURI_CLI ?= ./frontend/node_modules/.bin/tauri.cmd
CARGO_ENV := $$env:CARGO_HTTP_CHECK_REVOKE='false';
SIDECAR_TARGET ?= src-tauri/binaries/cam-sidecar-x86_64-pc-windows-msvc.exe
else
SHELL := /bin/sh
.SHELLFLAGS := -c
EXE :=
INSTALL_DIR ?= $(HOME)/.local/bin
CONFIG_DIR ?= $(HOME)/.config/code-agent-manager
TAURI_CLI ?= ./frontend/node_modules/.bin/tauri
CARGO_ENV := CARGO_HTTP_CHECK_REVOKE=false
SIDECAR_TARGET ?= src-tauri/binaries/cam-sidecar
endif

.PHONY: help install clean test test-race build build-cli build-sidecar node-deps stop-desktop frontend app dev start sidecar desktop-build fmt fmt-check vet check release

VERSION ?= dev
GOFLAGS ?=
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173
SIDECAR_HOST ?= 127.0.0.1
SIDECAR_PORT ?= 0
TAURI_MANIFEST ?= src-tauri/Cargo.toml
TAURI_CONFIG ?= src-tauri/tauri.conf.json

help:
	@echo "Available commands:"
	@echo "  make start         - Start the full Tauri desktop app (same as make app)"
	@echo "  make app           - Start the Tauri desktop app (alias: make dev)"
	@echo "  make frontend      - Start browser-only Vite frontend at $(FRONTEND_HOST):$(FRONTEND_PORT)"
	@echo "  make sidecar       - Start Go sidecar API at $(SIDECAR_HOST):$(SIDECAR_PORT)"
	@echo "  make desktop-build - Build frontend, Go sidecar, and cargo-check Tauri shell"
	@echo "  make build         - Build Go CLI binaries and sidecar into dist/"
	@echo "  make install       - Build and install cam/code-agent-manager"
	@echo "  make test          - Run Go test suite"
	@echo "  make test-race     - Run Go tests with race detector"
	@echo "  make fmt           - Format Go code"
	@echo "  make vet           - Run go vet"
	@echo "  make check         - Run fmt check, vet, tests, frontend tests, and sidecar build"
	@echo "  make clean         - Remove build artifacts"

install: build-cli
ifeq ($(OS),Windows_NT)
	pwsh.exe -NoProfile -Command "New-Item -ItemType Directory -Force '$(INSTALL_DIR)', '$(CONFIG_DIR)' | Out-Null"
	pwsh.exe -NoProfile -Command "Copy-Item 'dist/cam$(EXE)' '$(INSTALL_DIR)/cam$(EXE)' -Force"
	pwsh.exe -NoProfile -Command "Copy-Item 'dist/code-agent-manager$(EXE)' '$(INSTALL_DIR)/code-agent-manager$(EXE)' -Force"
	pwsh.exe -NoProfile -Command "if (Test-Path 'providers.json') { if (-not (Test-Path '$(CONFIG_DIR)/providers.json')) { Copy-Item 'providers.json' '$(CONFIG_DIR)/providers.json' -Force } } elseif (Test-Path 'providers.json.example') { if (-not (Test-Path '$(CONFIG_DIR)/providers.json')) { Copy-Item 'providers.json.example' '$(CONFIG_DIR)/providers.json' -Force } }"
	pwsh.exe -NoProfile -Command "if (Test-Path 'code_assistant_manager/config.yaml') { if (-not (Test-Path '$(CONFIG_DIR)/config.yaml')) { Copy-Item 'code_assistant_manager/config.yaml' '$(CONFIG_DIR)/config.yaml' -Force } }"
	pwsh.exe -NoProfile -Command "if (-not (Test-Path '$(USERPROFILE)/.env')) { New-Item -ItemType File -Force '$(USERPROFILE)/.env' | Out-Null }"
	@echo "Installed cam and code-agent-manager to $(INSTALL_DIR)"
else
	VERSION=$(VERSION) ./install.sh install
endif

clean:
ifeq ($(OS),Windows_NT)
	Remove-Item -Recurse -Force dist, frontend/dist, src-tauri/target, src-tauri/binaries -ErrorAction SilentlyContinue
	Get-ChildItem -Recurse -Filter *.test -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
	Get-ChildItem -Recurse -Filter coverage.out -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
else
	rm -rf dist/ frontend/dist/ src-tauri/target/ src-tauri/binaries/
	find . -type f -name "*.test" -delete
	find . -type f -name "coverage.out" -delete
endif

build: build-cli build-sidecar

node-deps:
	npm --prefix frontend install

build-cli:
ifeq ($(OS),Windows_NT)
	New-Item -ItemType Directory -Force dist | Out-Null
else
	mkdir -p dist
endif
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o dist/cam$(EXE) ./cmd/cam
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o dist/code-agent-manager$(EXE) ./cmd/code-agent-manager

stop-desktop:
ifeq ($(OS),Windows_NT)
	$$processes = Get-Process cam-sidecar, cam-desktop -ErrorAction SilentlyContinue; if ($$processes) { $$processes | Stop-Process -Force -ErrorAction SilentlyContinue }; exit 0
else
	-pkill -f cam-sidecar || true
	-pkill -f cam-desktop || true
endif

build-sidecar: stop-desktop
ifeq ($(OS),Windows_NT)
	New-Item -ItemType Directory -Force dist, src-tauri/binaries | Out-Null
else
	mkdir -p dist src-tauri/binaries
endif
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o dist/cam-sidecar$(EXE) ./cmd/cam-sidecar
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o $(SIDECAR_TARGET) ./cmd/cam-sidecar

frontend:
	npm --prefix frontend run dev -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT) --strictPort

sidecar:
	go run ./cmd/cam-sidecar --host $(SIDECAR_HOST) --port $(SIDECAR_PORT)

app dev start: node-deps build-sidecar
	$(CARGO_ENV) $(TAURI_CLI) dev --config $(TAURI_CONFIG)

desktop-build: build-sidecar
	npm --prefix frontend run build
	$(CARGO_ENV) cargo check --manifest-path $(TAURI_MANIFEST)

test:
	go test $(GOFLAGS) ./...

test-race:
	go test $(GOFLAGS) -race ./...

fmt:
	gofmt -s -w cmd internal

fmt-check:
ifeq ($(OS),Windows_NT)
	$$files = gofmt -s -l cmd internal; if ($$files) { $$files; exit 1 }
else
	@test -z "$$(gofmt -s -l cmd internal)" || (gofmt -s -l cmd internal && exit 1)
endif

vet:
	go vet ./...

check: fmt-check vet test build-sidecar
	npm --prefix frontend test -- --run
	npm --prefix frontend run build
	$(CARGO_ENV) cargo check --manifest-path $(TAURI_MANIFEST)
	@echo "All checks passed!"

release: clean check build
	@echo "Release build completed successfully!"
ifeq ($(OS),Windows_NT)
	Get-ChildItem dist
else
	ls -lh dist/
endif
