package appstate

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	_ "modernc.org/sqlite"
)

// Store is the SQLite-backed app state store.
type Store struct {
	path string
}

// ProviderPatch aliases the provider package patch type for app state updates.
type ProviderPatch = providers.Patch

// DefaultPath returns the canonical SQLite database path.
func DefaultPath() string {
	if path := os.Getenv("CAM_DB_PATH"); path != "" {
		return path
	}
	return filepath.Join(pathutil.ConfigDir(), "cam.db")
}

// New returns a Store using path, or DefaultPath when path is empty.
func New(path string) Store {
	if path == "" {
		path = DefaultPath()
	}
	return Store{path: path}
}

// Path returns the database path.
func (s Store) Path() string { return s.path }

// Init creates the schema if needed.
func (s Store) Init(ctx context.Context) error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, schemaSQL)
	if err != nil {
		return fmt.Errorf("appstate: init schema: %w", err)
	}
	if err := migrate(ctx, db); err != nil {
		return fmt.Errorf("appstate: migrate schema: %w", err)
	}
	return nil
}

// migrate applies idempotent, additive schema changes to databases created by
// older versions. ADD COLUMN on an existing column returns a "duplicate column"
// error which we treat as already-applied.
func migrate(ctx context.Context, db *sql.DB) error {
	for _, stmt := range []string{
		`ALTER TABLE providers ADD COLUMN api_key TEXT NOT NULL DEFAULT ''`,
	} {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			if strings.Contains(err.Error(), "duplicate column name") {
				continue
			}
			return err
		}
	}
	return nil
}

// ImportProvidersJSON is a no-op. Providers were historically migrated from a
// legacy providers.json file into the SQLite store. That migration is complete
// — the SQLite database is the sole source of truth.
func (s Store) ImportProvidersJSON(ctx context.Context, path string) error {
	return nil
}

// ListProviders returns all providers in providers.File shape for compatibility.
func (s Store) ListProviders(ctx context.Context) (providers.File, error) {
	if err := s.Init(ctx); err != nil {
		return providers.File{}, err
	}
	db, err := s.open()
	if err != nil {
		return providers.File{}, err
	}
	defer db.Close()
	rows, err := db.QueryContext(ctx, `SELECT name, endpoint, api_key, api_key_env, supported_client, list_models_cmd, models_json, keep_proxy_config, use_proxy, enabled, description FROM providers ORDER BY name`)
	if err != nil {
		return providers.File{}, fmt.Errorf("appstate: list providers: %w", err)
	}
	defer rows.Close()
	file := providers.File{Common: map[string]any{}, Endpoints: map[string]providers.Endpoint{}}
	for rows.Next() {
		var name, modelsJSON string
		var endpoint providers.Endpoint
		var keepProxy, useProxy bool
		var enabled sql.NullInt64
		if err := rows.Scan(&name, &endpoint.Endpoint, &endpoint.APIKey, &endpoint.APIKeyEnv, &endpoint.SupportedClient, &endpoint.ListModelsCmd, &modelsJSON, &keepProxy, &useProxy, &enabled, &endpoint.Description); err != nil {
			return providers.File{}, fmt.Errorf("appstate: scan provider: %w", err)
		}
		if err := json.Unmarshal([]byte(modelsJSON), &endpoint.Models); err != nil {
			return providers.File{}, fmt.Errorf("appstate: parse models for %s: %w", name, err)
		}
		endpoint.KeepProxyConfig = keepProxy
		endpoint.UseProxy = useProxy
		if enabled.Valid {
			v := enabled.Int64 != 0
			endpoint.Enabled = &v
		}
		file.Endpoints[name] = endpoint
	}
	if err := rows.Err(); err != nil {
		return providers.File{}, fmt.Errorf("appstate: iterate providers: %w", err)
	}
	return file, nil
}

// AddProvider inserts a provider.
func (s Store) AddProvider(ctx context.Context, name string, endpoint providers.Endpoint) error {
	file, err := s.ListProviders(ctx)
	if err != nil {
		return err
	}
	if err := providers.Add(&file, name, endpoint); err != nil {
		return err
	}
	return s.upsertProvider(ctx, name, file.Endpoints[name])
}

// UpdateProvider applies a sparse patch.
func (s Store) UpdateProvider(ctx context.Context, name string, patch ProviderPatch) error {
	file, err := s.ListProviders(ctx)
	if err != nil {
		return err
	}
	if err := providers.Update(&file, name, patch); err != nil {
		return err
	}
	return s.upsertProvider(ctx, name, file.Endpoints[name])
}

// RemoveProvider deletes a provider.
func (s Store) RemoveProvider(ctx context.Context, name string) bool {
	file, err := s.ListProviders(ctx)
	if err != nil {
		return false
	}
	if !providers.Remove(&file, name) {
		return false
	}
	db, err := s.open()
	if err != nil {
		return false
	}
	defer db.Close()
	result, err := db.ExecContext(ctx, `DELETE FROM providers WHERE name = ?`, name)
	if err != nil {
		return false
	}
	rows, _ := result.RowsAffected()
	return rows > 0
}

// RenameProvider renames a provider.
func (s Store) RenameProvider(ctx context.Context, oldName, newName string) error {
	file, err := s.ListProviders(ctx)
	if err != nil {
		return err
	}
	if err := providers.Rename(&file, oldName, newName); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.ExecContext(ctx, `DELETE FROM providers WHERE name = ?`, oldName); err != nil {
		return fmt.Errorf("appstate: delete old provider name: %w", err)
	}
	return s.upsertProvider(ctx, newName, file.Endpoints[newName])
}

// SetProviderEnabled toggles enabled state.
func (s Store) SetProviderEnabled(ctx context.Context, name string, enabled bool) error {
	file, err := s.ListProviders(ctx)
	if err != nil {
		return err
	}
	if err := providers.SetEnabled(&file, name, enabled); err != nil {
		return err
	}
	return s.upsertProvider(ctx, name, file.Endpoints[name])
}

// SetState stores arbitrary future app state as JSON.
func (s Store) SetState(ctx context.Context, key string, value any) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("appstate: marshal state: %w", err)
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, `INSERT INTO app_state(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at`, key, string(data), time.Now().UTC().Format(time.RFC3339Nano))
	if err != nil {
		return fmt.Errorf("appstate: set state: %w", err)
	}
	return nil
}

// GetState loads arbitrary future app state from JSON.
func (s Store) GetState(ctx context.Context, key string, value any) (bool, error) {
	if err := s.Init(ctx); err != nil {
		return false, err
	}
	db, err := s.open()
	if err != nil {
		return false, err
	}
	defer db.Close()
	var raw string
	err = db.QueryRowContext(ctx, `SELECT value_json FROM app_state WHERE key = ?`, key).Scan(&raw)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("appstate: get state: %w", err)
	}
	if err := json.Unmarshal([]byte(raw), value); err != nil {
		return false, fmt.Errorf("appstate: parse state: %w", err)
	}
	return true, nil
}

func (s Store) upsertProvider(ctx context.Context, name string, endpoint providers.Endpoint) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	models, err := json.Marshal(endpoint.Models)
	if err != nil {
		return fmt.Errorf("appstate: marshal models: %w", err)
	}
	var enabled any
	if endpoint.Enabled != nil {
		if *endpoint.Enabled {
			enabled = 1
		} else {
			enabled = 0
		}
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, `INSERT INTO providers(name, endpoint, api_key, api_key_env, supported_client, list_models_cmd, models_json, keep_proxy_config, use_proxy, enabled, description, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET endpoint = excluded.endpoint, api_key = excluded.api_key, api_key_env = excluded.api_key_env, supported_client = excluded.supported_client, list_models_cmd = excluded.list_models_cmd, models_json = excluded.models_json, keep_proxy_config = excluded.keep_proxy_config, use_proxy = excluded.use_proxy, enabled = excluded.enabled, description = excluded.description, updated_at = excluded.updated_at`, name, endpoint.Endpoint, endpoint.APIKey, endpoint.APIKeyEnv, endpoint.SupportedClient, endpoint.ListModelsCmd, string(models), endpoint.KeepProxyConfig, endpoint.UseProxy, enabled, endpoint.Description, time.Now().UTC().Format(time.RFC3339Nano))
	if err != nil {
		return fmt.Errorf("appstate: upsert provider %s: %w", name, err)
	}
	return nil
}

func (s Store) open() (*sql.DB, error) {
	if s.path == "" {
		s.path = DefaultPath()
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return nil, fmt.Errorf("appstate: mkdir db dir: %w", err)
	}
	db, err := sql.Open("sqlite", s.path)
	if err != nil {
		return nil, fmt.Errorf("appstate: open %s: %w", s.path, err)
	}
	return db, nil
}

const schemaSQL = `
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS providers (
  name TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL,
  api_key TEXT NOT NULL DEFAULT '',
  api_key_env TEXT NOT NULL DEFAULT '',
  supported_client TEXT NOT NULL DEFAULT '',
  list_models_cmd TEXT NOT NULL DEFAULT '',
  models_json TEXT NOT NULL DEFAULT '[]',
  keep_proxy_config INTEGER NOT NULL DEFAULT 0,
  use_proxy INTEGER NOT NULL DEFAULT 0,
  enabled INTEGER,
  description TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_state (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
`
