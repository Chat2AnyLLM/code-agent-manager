package editorconfig

import (
	"os"
	"path/filepath"
	"testing"
)

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
}

func TestYAML_LoadEmpty(t *testing.T) {
	tmp := t.TempDir()
	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{filepath.Join(tmp, "missing.yaml")},
	})
	data, _, err := tool.Load(UserScope)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if len(data) != 0 {
		t.Errorf("data = %v, want empty", data)
	}
}

func TestYAML_SetAndUnset_PreservesOther(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.yaml")
	writeFile(t, path, "theme: dark\nclients:\n  existing:\n    api_base: http://old\n")

	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{path},
	})
	if _, err := tool.Set(UserScope, "clients.new.api_base", "http://new"); err != nil {
		t.Fatalf("Set: %v", err)
	}

	data, _, err := tool.Load(UserScope)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if data["theme"] != "dark" {
		t.Errorf("theme lost: %v", data["theme"])
	}
	clients := data["clients"].(map[string]any)
	existing := clients["existing"].(map[string]any)
	if existing["api_base"] != "http://old" {
		t.Errorf("existing.api_base = %v, want http://old", existing["api_base"])
	}
	newC := clients["new"].(map[string]any)
	if newC["api_base"] != "http://new" {
		t.Errorf("new.api_base = %v, want http://new", newC["api_base"])
	}

	found, _, err := tool.Unset(UserScope, "clients.existing.api_base")
	if err != nil {
		t.Fatalf("Unset: %v", err)
	}
	if !found {
		t.Error("Unset returned !found")
	}
	data2, _, _ := tool.Load(UserScope)
	if data2["theme"] != "dark" {
		t.Error("theme lost after unset")
	}
}

func TestYAML_FilePermissions(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "perm.yaml")
	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{path},
	})
	if _, err := tool.Set(UserScope, "x", "y"); err != nil {
		t.Fatalf("Set: %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Errorf("mode = %o, want 0600", info.Mode().Perm())
	}
}
