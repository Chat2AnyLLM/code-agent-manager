package camconfig_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/camconfig"
)

func TestLoadFallsBackToBundledWhenMissing(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(t.TempDir(), "missing"))

	got, err := camconfig.Load("")
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	if len(got.Repositories) == 0 {
		t.Fatal("bundled config should expose repository sources")
	}
	for _, key := range []string{"skills", "agents", "plugins", "prompts", "mcpServers"} {
		if _, ok := got.Repositories[key]; !ok {
			t.Fatalf("bundled config missing repository key %q", key)
		}
	}
	promptSources := got.Repositories["prompts"].Sources
	if len(promptSources) != 2 {
		t.Fatalf("prompts source count = %d, want 2", len(promptSources))
	}
	if promptSources[1].URL != "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-prompts/master/config.yaml" {
		t.Fatalf("prompts remote URL = %q", promptSources[1].URL)
	}
	mcpSources := got.Repositories["mcpServers"].Sources
	if len(mcpSources) != 2 {
		t.Fatalf("mcpServers source count = %d, want 2", len(mcpSources))
	}
	if mcpSources[1].URL != "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-mcp-servers/main/config.yaml" {
		t.Fatalf("mcpServers remote URL = %q", mcpSources[1].URL)
	}
	if !got.Cache.Enabled {
		t.Fatal("bundled cache should default to enabled")
	}
}

func TestLoadParsesUserFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	content := strings.TrimSpace(`
cache:
  enabled: false
  directory: ~/.cache/custom
  ttl_seconds: 600
repositories:
  skills:
    sources:
      - type: local
        path: ~/.config/code-agent-manager/skill_repos.json
  plugins:
    sources:
      - type: remote
        url: https://example.com/plugin_repos.json
`)
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("HOME", "/home/test")

	got, err := camconfig.Load(path)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	if got.Cache.Enabled {
		t.Fatal("Cache.Enabled = true, want false")
	}
	if got.Cache.Directory != "/home/test/.cache/custom" {
		t.Fatalf("Cache.Directory = %q, want expanded path", got.Cache.Directory)
	}
	if got.Cache.TTLSeconds != 600 {
		t.Fatalf("Cache.TTLSeconds = %d, want 600", got.Cache.TTLSeconds)
	}
	if got.Repositories["skills"].Sources[0].Type != "local" {
		t.Fatalf("skills source type = %q", got.Repositories["skills"].Sources[0].Type)
	}
	if got.Repositories["plugins"].Sources[0].URL != "https://example.com/plugin_repos.json" {
		t.Fatalf("plugins source url = %q", got.Repositories["plugins"].Sources[0].URL)
	}
}

func TestLoadNormalizesPromptAndMCPConfigSources(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	content := strings.TrimSpace(`
repositories:
  prompts:
    sources:
      - type: local
        path: ~/.config/code-agent-manager/prompt_repos.json
  mcpServers:
    sources:
      - type: remote
        url: https://raw.githubusercontent.com/Chat2AnyLLM/awesome-mcp-servers/main/dist/servers.json
cache:
  enabled: false
`)
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}

	got, err := camconfig.Load(path)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	promptSources := got.Repositories["prompts"].Sources
	if promptSources[len(promptSources)-1].URL != "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-prompts/master/config.yaml" {
		t.Fatalf("prompts sources = %+v", promptSources)
	}
	mcpSources := got.Repositories["mcpServers"].Sources
	if len(mcpSources) != 1 || mcpSources[0].URL != "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-mcp-servers/main/config.yaml" {
		t.Fatalf("mcpServers sources = %+v", mcpSources)
	}
}

func TestLoadReturnsErrorOnMalformedYAML(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	if err := os.WriteFile(path, []byte(":\n  - not valid"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := camconfig.Load(path); err == nil {
		t.Fatal("expected error on malformed YAML")
	}
}

func TestBundledExpandsCacheDirectory(t *testing.T) {
	t.Setenv("HOME", "/home/test")
	cfg, err := camconfig.Bundled()
	if err != nil {
		t.Fatalf("Bundled err = %v", err)
	}
	if cfg.Cache.Directory == "" {
		t.Fatal("bundled cache directory should not be empty")
	}
	if strings.HasPrefix(cfg.Cache.Directory, "~/") {
		t.Fatalf("Cache.Directory not expanded: %q", cfg.Cache.Directory)
	}
}
