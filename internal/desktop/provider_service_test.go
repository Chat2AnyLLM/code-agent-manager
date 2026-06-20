package desktop

import (
	"errors"
	"path/filepath"
	"testing"
)

func TestProviderServiceLifecycle(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	service := NewProviderService("")

	if _, err := service.Init(); err != nil {
		t.Fatalf("init: %v", err)
	}
	enabled := true
	created, err := service.Add(ProviderInput{
		Name: "local", Endpoint: "http://localhost:4000/v1", APIKeyEnv: "LOCAL_KEY",
		Clients: []string{"claude", "codex"}, Models: []string{"model-a"}, Enabled: &enabled,
		Description: "Local endpoint",
	})
	if err != nil {
		t.Fatalf("add: %v", err)
	}
	if created.Name != "local" || !created.Enabled || len(created.Clients) != 2 {
		t.Fatalf("unexpected created provider: %+v", created)
	}

	list, err := service.List()
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(list) != 1 || list[0].Name != "local" {
		t.Fatalf("unexpected list: %+v", list)
	}

	disabled, err := service.Disable("local")
	if err != nil {
		t.Fatalf("disable: %v", err)
	}
	if disabled.Enabled {
		t.Fatal("expected disabled provider")
	}

	renamed, err := service.Rename("local", "renamed")
	if err != nil {
		t.Fatalf("rename: %v", err)
	}
	if renamed.Name != "renamed" {
		t.Fatalf("expected renamed provider, got %+v", renamed)
	}

	if _, err := service.Remove("renamed"); err != nil {
		t.Fatalf("remove: %v", err)
	}
	list, err = service.List()
	if err != nil {
		t.Fatalf("list after remove: %v", err)
	}
	if len(list) != 0 {
		t.Fatalf("expected empty list, got %+v", list)
	}
}

func TestProviderServiceNotFound(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	t.Setenv("CAM_DB_PATH", dbPath)
	service := NewProviderService("")
	_, _ = service.Init()
	_, err := service.Show("missing")
	var appErr AppError
	if !errors.As(err, &appErr) || appErr.Code != "PROVIDER_NOT_FOUND" {
		t.Fatalf("expected PROVIDER_NOT_FOUND, got %v", err)
	}
}

func TestProviderServiceUsesExplicitSQLitePath(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "custom.db")
	service := NewProviderService(dbPath)

	if _, err := service.Init(); err != nil {
		t.Fatalf("init: %v", err)
	}
	if _, err := service.List(); err != nil {
		t.Fatalf("list: %v", err)
	}
}
