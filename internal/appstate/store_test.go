package appstate

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestProviderCRUD(t *testing.T) {
	ctx := context.Background()
	store := New(filepath.Join(t.TempDir(), "cam.db"))
	enabled := true

	if err := store.AddProvider(ctx, "alpha", providers.Endpoint{Endpoint: "https://alpha.example", SupportedClient: "claude,codex", Models: []string{"m1"}, Enabled: &enabled}); err != nil {
		t.Fatalf("AddProvider: %v", err)
	}
	file, err := store.ListProviders(ctx)
	if err != nil {
		t.Fatalf("ListProviders: %v", err)
	}
	if len(file.Endpoints) != 1 || file.Endpoints["alpha"].Endpoint != "https://alpha.example" {
		t.Fatalf("providers = %+v", file.Endpoints)
	}

	endpoint := "https://updated.example"
	models := providers.ListPatch{Op: providers.ListOpReplace, Items: []string{"m2", "m3"}}
	if err := store.UpdateProvider(ctx, "alpha", providers.Patch{Endpoint: &endpoint, Models: &models}); err != nil {
		t.Fatalf("UpdateProvider: %v", err)
	}
	file, _ = store.ListProviders(ctx)
	if file.Endpoints["alpha"].Endpoint != endpoint || len(file.Endpoints["alpha"].Models) != 2 {
		t.Fatalf("updated provider = %+v", file.Endpoints["alpha"])
	}

	if err := store.SetProviderEnabled(ctx, "alpha", false); err != nil {
		t.Fatalf("SetProviderEnabled: %v", err)
	}
	file, _ = store.ListProviders(ctx)
	if file.Endpoints["alpha"].IsEnabled() {
		t.Fatal("provider should be disabled")
	}

	if err := store.RenameProvider(ctx, "alpha", "beta"); err != nil {
		t.Fatalf("RenameProvider: %v", err)
	}
	file, _ = store.ListProviders(ctx)
	if _, ok := file.Endpoints["alpha"]; ok {
		t.Fatal("old provider name still exists")
	}
	if _, ok := file.Endpoints["beta"]; !ok {
		t.Fatal("new provider name missing")
	}

	if !store.RemoveProvider(ctx, "beta") {
		t.Fatal("RemoveProvider returned false")
	}
	file, _ = store.ListProviders(ctx)
	if len(file.Endpoints) != 0 {
		t.Fatalf("providers after remove = %+v", file.Endpoints)
	}
}

func TestAppStateKeyValue(t *testing.T) {
	ctx := context.Background()
	store := New(filepath.Join(t.TempDir(), "cam.db"))
	want := map[string]any{"sidebar": "wide"}
	if err := store.SetState(ctx, "ui", want); err != nil {
		t.Fatalf("SetState: %v", err)
	}
	var got map[string]any
	ok, err := store.GetState(ctx, "ui", &got)
	if err != nil {
		t.Fatalf("GetState: %v", err)
	}
	if !ok || got["sidebar"] != "wide" {
		t.Fatalf("state = ok:%v value:%+v", ok, got)
	}
	if _, err := os.Stat(store.Path()); err != nil {
		t.Fatalf("db file missing: %v", err)
	}
}

// TestInitCreatesInstructionTablesWithoutLosingData verifies that opening a
// cam.db created before the instructions feature lands adds the new tables
// while leaving existing providers/app_state rows intact.
func TestInitCreatesInstructionTablesWithoutLosingData(t *testing.T) {
	ctx := context.Background()
	dbPath := filepath.Join(t.TempDir(), "cam.db")
	store := New(dbPath)

	enabled := true
	if err := store.AddProvider(ctx, "alpha", providers.Endpoint{Endpoint: "https://alpha.example", Models: []string{"m1"}, Enabled: &enabled}); err != nil {
		t.Fatalf("AddProvider: %v", err)
	}
	if err := store.SetState(ctx, "ui", map[string]any{"sidebar": "wide"}); err != nil {
		t.Fatalf("SetState: %v", err)
	}

	// Re-init (simulating an upgraded binary opening an existing DB).
	if err := store.Init(ctx); err != nil {
		t.Fatalf("Init: %v", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer db.Close()
	for _, table := range []string{"instructions", "instruction_installs"} {
		var name string
		err := db.QueryRowContext(ctx, `SELECT name FROM sqlite_master WHERE type='table' AND name=?`, table).Scan(&name)
		if err != nil {
			t.Fatalf("table %s missing: %v", table, err)
		}
	}

	file, err := store.ListProviders(ctx)
	if err != nil {
		t.Fatalf("ListProviders: %v", err)
	}
	if _, ok := file.Endpoints["alpha"]; !ok {
		t.Fatalf("provider lost after upgrade: %+v", file.Endpoints)
	}
	var got map[string]any
	ok, err := store.GetState(ctx, "ui", &got)
	if err != nil || !ok || got["sidebar"] != "wide" {
		t.Fatalf("app_state lost after upgrade: ok=%v err=%v value=%+v", ok, err, got)
	}
}

func TestRenameProviderLeavesOnlyNewRow(t *testing.T) {
	ctx := context.Background()
	store := New(filepath.Join(t.TempDir(), "cam.db"))
	enabled := true
	if err := store.AddProvider(ctx, "alpha", providers.Endpoint{Endpoint: "https://alpha.example", Models: []string{"m1"}, Enabled: &enabled}); err != nil {
		t.Fatalf("AddProvider: %v", err)
	}
	if err := store.RenameProvider(ctx, "alpha", "beta"); err != nil {
		t.Fatalf("RenameProvider: %v", err)
	}
	db, err := sql.Open("sqlite", store.Path())
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer db.Close()
	var oldCount, newCount, total int
	if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM providers WHERE name = ?`, "alpha").Scan(&oldCount); err != nil {
		t.Fatalf("count old: %v", err)
	}
	if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM providers WHERE name = ?`, "beta").Scan(&newCount); err != nil {
		t.Fatalf("count new: %v", err)
	}
	if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM providers`).Scan(&total); err != nil {
		t.Fatalf("count total: %v", err)
	}
	if oldCount != 0 || newCount != 1 || total != 1 {
		t.Fatalf("provider rows old=%d new=%d total=%d", oldCount, newCount, total)
	}
}
