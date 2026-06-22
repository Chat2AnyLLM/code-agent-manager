package desktop

import (
	"os"
	"path/filepath"
	"testing"
)

func TestMCPServiceClientsAndRegistry(t *testing.T) {
	writeMCPServiceTestConfig(t)
	service := NewMCPService()
	clients := service.ListClients()
	if len(clients) == 0 {
		t.Fatal("expected supported clients")
	}

	matches, err := service.SearchRegistry("github")
	if err != nil {
		t.Fatalf("search registry: %v", err)
	}
	if matches == nil {
		t.Fatal("expected non-nil registry result slice")
	}
}

func TestMCPServiceListRegistry(t *testing.T) {
	writeMCPServiceTestConfig(t)
	service := NewMCPService()

	// Empty query lists the whole catalog; each item carries its install type.
	items, err := service.ListRegistry("", "user")
	if err != nil {
		t.Fatalf("list registry: %v", err)
	}
	if len(items) == 0 {
		t.Fatal("expected discovered registry servers")
	}
	var seen bool
	for _, item := range items {
		if item.Name != "" && item.InstallType != "" {
			seen = true
		}
	}
	if !seen {
		t.Fatalf("expected items with name + installType, got %+v", items[:min(3, len(items))])
	}

	// A query narrows the results to matches.
	filtered, err := service.ListRegistry("github", "user")
	if err != nil {
		t.Fatalf("list registry filtered: %v", err)
	}
	if len(filtered) >= len(items) {
		t.Fatalf("expected query to narrow results, got %d (all=%d)", len(filtered), len(items))
	}
	for _, item := range filtered {
		if item.Name == "" {
			t.Fatalf("expected named item, got %+v", item)
		}
	}
}

func TestMCPServiceInstallFromRegistry(t *testing.T) {
	writeMCPServiceTestConfig(t)
	service := NewMCPService()
	// Installing an unknown server fails fast without touching config.
	if _, err := service.InstallFromRegistry("claude", "user", "does-not-exist-mcp"); err == nil {
		t.Fatal("expected error installing unknown server")
	}
}

func writeMCPServiceTestConfig(t *testing.T) {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	cfgDir := filepath.Join(dir, "cfg")
	t.Setenv("CAM_CONFIG_DIR", cfgDir)
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	catalogPath := filepath.Join(cfgDir, "mcp_servers.json")
	catalog := `[
  {
    "name": "github-test-mcp",
    "display_name": "GitHub Test MCP",
    "description": "GitHub test catalog MCP server",
    "repository": {"type": "git", "url": "https://example.com/github-test-mcp"},
    "tags": ["github"],
    "installations": {
      "npm": {"type": "npm", "command": "npx", "args": ["-y", "github-test-mcp"]}
    }
  },
  {
    "name": "memory-test-mcp",
    "display_name": "Memory Test MCP",
    "description": "Memory test catalog MCP server",
    "installations": {
      "npm": {"type": "npm", "command": "npx", "args": ["-y", "memory-test-mcp"]}
    }
  }
]`
	if err := os.WriteFile(catalogPath, []byte(catalog), 0o600); err != nil {
		t.Fatal(err)
	}
	config := "repositories:\n  mcpServers:\n    sources:\n      - type: local\n        path: " + filepath.ToSlash(catalogPath) + "\ncache:\n  enabled: false\n"
	if err := os.WriteFile(filepath.Join(cfgDir, "config.yaml"), []byte(config), 0o600); err != nil {
		t.Fatal(err)
	}
}
