package appapi

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/appstate"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestProviderAPIInitListShow(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "cam.db")
	api := ProviderAPI{DBPath: dbPath, Env: os.Getenv}
	enabled := true

	result, err := api.Init(context.Background())
	if err != nil {
		t.Fatalf("Init error = %v", err)
	}
	if !result.OK || result.Message == "" || result.Path != dbPath {
		t.Fatalf("Init result = %+v, want ok message and db path", result)
	}
	if _, err := os.Stat(result.Path); err != nil {
		t.Fatalf("db file missing: %v", err)
	}

	_, err = api.Add(context.Background(), ProviderInput{
		Name:            "local",
		Endpoint:        "http://localhost:4000/v1",
		APIKeyEnv:       "LOCAL_KEY",
		SupportedClient: "claude,codex",
		Models:          []string{"m1", "m2"},
		Enabled:         &enabled,
	})
	if err != nil {
		t.Fatalf("Add error = %v", err)
	}

	listed, err := api.List(context.Background())
	if err != nil {
		t.Fatalf("List error = %v", err)
	}
	if len(listed) != 1 || listed[0].Name != "local" || listed[0].Endpoint != "http://localhost:4000/v1" {
		t.Fatalf("List = %+v, want local provider", listed)
	}

	shown, err := api.Show(context.Background(), "local")
	if err != nil {
		t.Fatalf("Show error = %v", err)
	}
	if shown.Name != "local" || len(shown.Models) != 2 || len(shown.Clients) != 2 {
		t.Fatalf("Show = %+v, want local with models and clients", shown)
	}
}

func TestProviderAPIMutations(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	api := ProviderAPI{DBPath: dbPath, Env: os.Getenv}
	enabled := true

	added, err := api.Add(context.Background(), ProviderInput{
		Name:            "alpha",
		Endpoint:        "https://alpha.example",
		APIKeyEnv:       "ALPHA_KEY",
		SupportedClient: "claude,codex",
		Models:          []string{"m1"},
		Enabled:         &enabled,
		Description:     "alpha provider",
	})
	if err != nil {
		t.Fatalf("Add error = %v", err)
	}
	if added.Name != "alpha" || !added.Enabled || len(added.Models) != 1 {
		t.Fatalf("Add = %+v", added)
	}

	endpoint := "https://updated.example"
	description := "updated provider"
	models := providers.ListPatch{Op: providers.ListOpReplace, Items: []string{"m2", "m3"}}
	updated, err := api.Update(context.Background(), "alpha", ProviderPatch{
		Endpoint:    &endpoint,
		Models:      &models,
		Description: &description,
	})
	if err != nil {
		t.Fatalf("Update error = %v", err)
	}
	if updated.Endpoint != endpoint || updated.Description != description || len(updated.Models) != 2 {
		t.Fatalf("Update = %+v", updated)
	}

	disabled, err := api.SetEnabled(context.Background(), "alpha", false)
	if err != nil {
		t.Fatalf("SetEnabled false error = %v", err)
	}
	if disabled.Enabled {
		t.Fatalf("SetEnabled false = %+v", disabled)
	}

	renamed, err := api.Rename(context.Background(), "alpha", "beta")
	if err != nil {
		t.Fatalf("Rename error = %v", err)
	}
	if renamed.Name != "beta" {
		t.Fatalf("Rename = %+v", renamed)
	}
	if _, err := api.Show(context.Background(), "alpha"); err == nil {
		t.Fatal("old provider name should be missing")
	}

	result, err := api.Remove(context.Background(), "beta")
	if err != nil {
		t.Fatalf("Remove error = %v", err)
	}
	if !result.OK {
		t.Fatalf("Remove result = %+v", result)
	}
	listed, err := api.List(context.Background())
	if err != nil {
		t.Fatalf("List after remove error = %v", err)
	}
	if len(listed) != 0 {
		t.Fatalf("List after remove = %+v", listed)
	}
}

func TestProviderAPIResolveModels(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	api := ProviderAPI{DBPath: dbPath, Env: os.Getenv}
	enabled := true
	_, err := api.Add(context.Background(), ProviderInput{
		Name:            "alpha",
		Endpoint:        "https://alpha.example",
		SupportedClient: "claude",
		Models:          []string{"static-a", "static-b"},
		Enabled:         &enabled,
	})
	if err != nil {
		t.Fatalf("Add error = %v", err)
	}
	models, err := api.ResolveModels(context.Background(), "alpha")
	if err != nil {
		t.Fatalf("ResolveModels error = %v", err)
	}
	if len(models) < 2 || models[0] != "static-a" || models[1] != "static-b" {
		t.Fatalf("models = %v", models)
	}
}

func TestProviderAPIDeletesDefaultProvidersJSONForAddAndList(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, ".config", "code-agent-manager"))

	legacyPath := filepath.Join(pathutil.ConfigDir(), "providers.json")
	if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example"}}}`), 0o600); err != nil {
		t.Fatalf("write legacy providers.json: %v", err)
	}

	api := ProviderAPI{DBPath: filepath.Join(t.TempDir(), "cam.db")}
	enabled := true
	if _, err := api.Add(context.Background(), ProviderInput{Name: "alpha", Endpoint: "https://alpha.example", Enabled: &enabled}); err != nil {
		t.Fatalf("Add error = %v", err)
	}
	if _, err := os.Stat(legacyPath); !os.IsNotExist(err) {
		t.Fatalf("expected Add to delete default providers.json, got err=%v", err)
	}

	if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example"}}}`), 0o600); err != nil {
		t.Fatalf("rewrite legacy providers.json: %v", err)
	}
	listed, err := api.List(context.Background())
	if err != nil {
		t.Fatalf("List error = %v", err)
	}
	if len(listed) != 1 || listed[0].Name != "alpha" {
		t.Fatalf("List = %+v", listed)
	}
	if _, err := os.Stat(legacyPath); !os.IsNotExist(err) {
		t.Fatalf("expected List to delete default providers.json, got err=%v", err)
	}
}

func TestProviderAPIReadOperationsDoNotImportProvidersJSON(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, ".config", "code-agent-manager"))
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(home, ".config"))

	legacyPath := filepath.Join(pathutil.ConfigDir(), "providers.json")
	if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example","list_of_models":["legacy-model"]}}}`), 0o600); err != nil {
		t.Fatalf("write legacy providers.json: %v", err)
	}

	dbPath := filepath.Join(t.TempDir(), "cam.db")
	api := ProviderAPI{DBPath: dbPath}
	enabled := true
	if _, err := api.Add(context.Background(), ProviderInput{Name: "alpha", Endpoint: "https://alpha.example", Models: []string{"sqlite-model"}, Enabled: &enabled}); err != nil {
		t.Fatalf("Add error = %v", err)
	}
	if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example","list_of_models":["legacy-model"]}}}`), 0o600); err != nil {
		t.Fatalf("rewrite legacy providers.json: %v", err)
	}

	file, err := api.File(context.Background())
	if err != nil {
		t.Fatalf("File error = %v", err)
	}
	if _, ok := file.Endpoints["legacy"]; ok {
		t.Fatalf("File imported legacy providers.json: %+v", file.Endpoints)
	}
	shown, err := api.Show(context.Background(), "alpha")
	if err != nil {
		t.Fatalf("Show error = %v", err)
	}
	if shown.Name != "alpha" {
		t.Fatalf("Show = %+v", shown)
	}
	models, err := api.ResolveModels(context.Background(), "alpha")
	if err != nil {
		t.Fatalf("ResolveModels error = %v", err)
	}
	if len(models) != 1 || models[0] != "sqlite-model" {
		t.Fatalf("ResolveModels = %v", models)
	}
	if _, err := os.Stat(legacyPath); !os.IsNotExist(err) {
		t.Fatalf("expected read operations to delete default providers.json, got err=%v", err)
	}

	stored, err := appstate.New(dbPath).ListProviders(context.Background())
	if err != nil {
		t.Fatalf("ListProviders error = %v", err)
	}
	if _, ok := stored.Endpoints["legacy"]; ok {
		t.Fatalf("sqlite store imported legacy providers.json: %+v", stored.Endpoints)
	}
}

func boolPtr(v bool) *bool { return &v }

func TestProviderAPIMethodsDeleteDefaultProvidersJSON(t *testing.T) {
	tests := []struct {
		name string
		run  func(context.Context, ProviderAPI) error
	}{
		{name: "Init", run: func(ctx context.Context, api ProviderAPI) error { _, err := api.Init(ctx); return err }},
		{name: "File", run: func(ctx context.Context, api ProviderAPI) error { _, err := api.File(ctx); return err }},
		{name: "Show", run: func(ctx context.Context, api ProviderAPI) error { _, err := api.Show(ctx, "alpha"); return err }},
		{name: "Update", run: func(ctx context.Context, api ProviderAPI) error {
			endpoint := "https://updated.example"
			_, err := api.Update(ctx, "alpha", ProviderPatch{Endpoint: &endpoint})
			return err
		}},
		{name: "Remove", run: func(ctx context.Context, api ProviderAPI) error { _, err := api.Remove(ctx, "alpha"); return err }},
		{name: "SetEnabled", run: func(ctx context.Context, api ProviderAPI) error {
			_, err := api.SetEnabled(ctx, "alpha", false)
			return err
		}},
		{name: "Rename", run: func(ctx context.Context, api ProviderAPI) error {
			_, err := api.Rename(ctx, "alpha", "beta")
			return err
		}},
		{name: "ResolveModels", run: func(ctx context.Context, api ProviderAPI) error {
			_, err := api.ResolveModels(ctx, "alpha")
			return err
		}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			home := t.TempDir()
			t.Setenv("HOME", home)
			t.Setenv("USERPROFILE", home)
			t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, ".config", "code-agent-manager"))
			t.Setenv("XDG_CONFIG_HOME", filepath.Join(home, ".config"))

			legacyPath := filepath.Join(pathutil.ConfigDir(), "providers.json")
			if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
				t.Fatalf("mkdir legacy dir: %v", err)
			}
			if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example"}}}`), 0o600); err != nil {
				t.Fatalf("write legacy providers.json: %v", err)
			}

			api := ProviderAPI{DBPath: filepath.Join(t.TempDir(), "cam.db")}
			enabled := true
			if tc.name != "Init" {
				if _, err := api.Add(context.Background(), ProviderInput{Name: "alpha", Endpoint: "https://alpha.example", Models: []string{"sqlite-model"}, Enabled: &enabled}); err != nil {
					t.Fatalf("seed provider: %v", err)
				}
				if err := os.WriteFile(legacyPath, []byte(`{"endpoints":{"legacy":{"endpoint":"https://legacy.example"}}}`), 0o600); err != nil {
					t.Fatalf("rewrite legacy providers.json: %v", err)
				}
			}

			if err := tc.run(context.Background(), api); err != nil {
				t.Fatalf("%s error = %v", tc.name, err)
			}
			if _, err := os.Stat(legacyPath); !os.IsNotExist(err) {
				t.Fatalf("expected %s to delete providers.json, got err=%v", tc.name, err)
			}
		})
	}
}
