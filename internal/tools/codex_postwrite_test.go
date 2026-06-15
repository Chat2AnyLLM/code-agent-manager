package tools

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCodexPostHook_GPTSetsWireAPI(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.toml")
	os.WriteFile(path, []byte(`[model_providers.myprov]
name = "myprov"
base_url = "https://x"
`), 0o600)

	if err := applyCodexWireAPI(path, "myprov", "gpt-4o"); err != nil {
		t.Fatalf("hook: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if !strings.Contains(string(raw), `wire_api = 'responses'`) {
		t.Errorf("wire_api not set:\n%s", raw)
	}
}

func TestCodexPostHook_NonGPTUnsetsWireAPI(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.toml")
	os.WriteFile(path, []byte(`[model_providers.myprov]
name = "myprov"
base_url = "https://x"
wire_api = "responses"
`), 0o600)

	if err := applyCodexWireAPI(path, "myprov", "claude-sonnet-4"); err != nil {
		t.Fatalf("hook: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if strings.Contains(string(raw), "wire_api") {
		t.Errorf("wire_api still present:\n%s", raw)
	}
}

func TestCodexPostHook_NoCodexNoop(t *testing.T) {
	tool := Tool{Name: "qwen-code"}
	if err := codexPostWrite(tool, "", "", ""); err != nil {
		t.Errorf("non-codex tool hook errored: %v", err)
	}
}
