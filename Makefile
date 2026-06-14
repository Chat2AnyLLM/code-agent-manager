.PHONY: help install clean test test-race build release fmt vet check

VERSION ?= dev
GOFLAGS ?=

help:
	@echo "Available commands:"
	@echo "  make build    - Build Go binaries into dist/"
	@echo "  make install  - Build and install cam/code-agent-manager"
	@echo "  make test     - Run Go test suite"
	@echo "  make test-race - Run Go tests with race detector"
	@echo "  make fmt      - Format Go code"
	@echo "  make vet      - Run go vet"
	@echo "  make check    - Run fmt check, vet, tests, and install smoke test"
	@echo "  make clean    - Remove build artifacts"

install:
	VERSION=$(VERSION) ./install.sh install

clean:
	rm -rf dist/
	find . -type f -name "*.test" -delete
	find . -type f -name "coverage.out" -delete

build:
	mkdir -p dist
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o dist/cam ./cmd/cam
	go build $(GOFLAGS) -ldflags "-X main.version=$(VERSION)" -o dist/code-agent-manager ./cmd/code-agent-manager

test:
	go test $(GOFLAGS) ./...

test-race:
	go test $(GOFLAGS) -race ./...

fmt:
	gofmt -s -w cmd internal

fmt-check:
	@test -z "$$(gofmt -s -l cmd internal)" || (gofmt -s -l cmd internal && exit 1)

vet:
	go vet ./...

check: fmt-check vet test
	bash tests/verify_go_cli_install.sh
	@echo "All checks passed!"

release: clean check build
	@echo "Release build completed successfully!"
	@ls -lh dist/
