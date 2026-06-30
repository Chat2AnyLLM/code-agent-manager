package mcp

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	_ "modernc.org/sqlite"
)

type catalogStore struct {
	path string
}

func newCatalogStore(path string) catalogStore {
	if path == "" {
		if env := os.Getenv("CAM_DB_PATH"); env != "" {
			path = env
		} else {
			path = filepath.Join(pathutil.ConfigDir(), "cam.db")
		}
	}
	return catalogStore{path: path}
}

func (s catalogStore) save(ctx context.Context, entries []ServerSchema) error {
	if len(entries) == 0 {
		return nil
	}
	db, err := s.open(ctx)
	if err != nil {
		return err
	}
	defer db.Close()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("mcp: begin catalog tx: %w", err)
	}
	stmt, err := tx.PrepareContext(ctx, `INSERT INTO mcp_catalog_items(name, schema_json, updated_at) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET schema_json=excluded.schema_json, updated_at=excluded.updated_at`)
	if err != nil {
		_ = tx.Rollback()
		return fmt.Errorf("mcp: prepare catalog upsert: %w", err)
	}
	defer stmt.Close()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	for _, entry := range entries {
		raw, err := json.Marshal(entry)
		if err != nil {
			_ = tx.Rollback()
			return fmt.Errorf("mcp: marshal catalog item %s: %w", entry.Name, err)
		}
		if _, err := stmt.ExecContext(ctx, entry.Name, string(raw), now); err != nil {
			_ = tx.Rollback()
			return fmt.Errorf("mcp: upsert catalog item %s: %w", entry.Name, err)
		}
	}
	return tx.Commit()
}

func (s catalogStore) load(ctx context.Context) ([]ServerSchema, error) {
	db, err := s.open(ctx)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.QueryContext(ctx, `SELECT schema_json FROM mcp_catalog_items ORDER BY name`)
	if err != nil {
		return nil, fmt.Errorf("mcp: query catalog items: %w", err)
	}
	defer rows.Close()
	var entries []ServerSchema
	for rows.Next() {
		var raw string
		if err := rows.Scan(&raw); err != nil {
			return nil, fmt.Errorf("mcp: scan catalog item: %w", err)
		}
		var entry ServerSchema
		if err := json.Unmarshal([]byte(raw), &entry); err != nil {
			return nil, fmt.Errorf("mcp: decode catalog item: %w", err)
		}
		entries = append(entries, entry)
	}
	return entries, rows.Err()
}

func (s catalogStore) open(ctx context.Context) (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return nil, fmt.Errorf("mcp: mkdir catalog db: %w", err)
	}
	db, err := sql.Open("sqlite", s.path)
	if err != nil {
		return nil, fmt.Errorf("mcp: open catalog db: %w", err)
	}
	if _, err := db.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS mcp_catalog_items (
		name TEXT PRIMARY KEY,
		schema_json TEXT NOT NULL,
		updated_at TEXT NOT NULL
	)`); err != nil {
		db.Close()
		return nil, fmt.Errorf("mcp: init catalog db: %w", err)
	}
	return db, nil
}
