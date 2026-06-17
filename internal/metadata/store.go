package metadata

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	_ "modernc.org/sqlite"
)

// Store is the SQLite-backed metadata index.
type Store struct {
	path string
}

// NewStore returns a Store. If path is empty, uses the default cam.db location.
func NewStore(path string) *Store {
	if path == "" {
		if p := os.Getenv("CAM_DB_PATH"); p != "" {
			path = p
		} else {
			path = filepath.Join(pathutil.ConfigDir(), "cam.db")
		}
	}
	return &Store{path: path}
}

// Init creates metadata tables if they do not exist.
func (s *Store) Init(ctx context.Context) error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, schemaSQL)
	if err != nil {
		return fmt.Errorf("metadata: init schema: %w", err)
	}
	return nil
}

// UpsertItem inserts or updates a metadata item by (kind, install_key).
func (s *Store) UpsertItem(ctx context.Context, item Item) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	now := timeNow()
	_, err = db.ExecContext(ctx, `
		INSERT INTO metadata_items(kind, name, description, source_id, repo_owner, repo_name, repo_branch, item_path, install_key, target_apps, metadata_json, installed, installed_targets, last_seen_at, created_at, updated_at)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(kind, install_key) DO UPDATE SET
			name=excluded.name, description=excluded.description, source_id=excluded.source_id,
			repo_owner=excluded.repo_owner, repo_name=excluded.repo_name, repo_branch=excluded.repo_branch,
			item_path=excluded.item_path, target_apps=excluded.target_apps, metadata_json=excluded.metadata_json,
			last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at`,
		item.Kind, item.Name, item.Description, item.SourceID,
		item.RepoOwner, item.RepoName, item.RepoBranch, item.ItemPath,
		item.InstallKey, item.TargetApps, coalesce(item.MetadataJSON, "{}"),
		boolToInt(item.Installed), item.InstalledTargets, now, now, now)
	if err != nil {
		return fmt.Errorf("metadata: upsert item: %w", err)
	}
	return nil
}

// UpsertItems inserts or updates many items in a single transaction, reusing one
// database connection. Used by refresh, which produces hundreds of items: a
// per-item open/close (as UpsertItem does) is dramatically slower. Returns the
// number of rows successfully written.
func (s *Store) UpsertItems(ctx context.Context, items []Item) (int, error) {
	if len(items) == 0 {
		return 0, nil
	}
	if err := s.Init(ctx); err != nil {
		return 0, err
	}
	db, err := s.open()
	if err != nil {
		return 0, err
	}
	defer db.Close()

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("metadata: begin tx: %w", err)
	}
	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO metadata_items(kind, name, description, source_id, repo_owner, repo_name, repo_branch, item_path, install_key, target_apps, metadata_json, installed, installed_targets, last_seen_at, created_at, updated_at)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(kind, install_key) DO UPDATE SET
			name=excluded.name, description=excluded.description, source_id=excluded.source_id,
			repo_owner=excluded.repo_owner, repo_name=excluded.repo_name, repo_branch=excluded.repo_branch,
			item_path=excluded.item_path, target_apps=excluded.target_apps, metadata_json=excluded.metadata_json,
			last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at`)
	if err != nil {
		_ = tx.Rollback()
		return 0, fmt.Errorf("metadata: prepare upsert: %w", err)
	}
	defer stmt.Close()

	now := timeNow()
	written := 0
	for _, item := range items {
		if _, err := stmt.ExecContext(ctx,
			item.Kind, item.Name, item.Description, item.SourceID,
			item.RepoOwner, item.RepoName, item.RepoBranch, item.ItemPath,
			item.InstallKey, item.TargetApps, coalesce(item.MetadataJSON, "{}"),
			boolToInt(item.Installed), item.InstalledTargets, now, now, now); err != nil {
			_ = tx.Rollback()
			return 0, fmt.Errorf("metadata: batch upsert: %w", err)
		}
		written++
	}
	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("metadata: commit upsert: %w", err)
	}
	return written, nil
}

// DeleteStale removes items of a kind whose last_seen_at is older than the given
// timestamp. Used after a refresh to prune resources that no longer exist
// upstream. installed_targets is preserved on surviving rows because the upsert
// no longer overwrites install status.
func (s *Store) DeleteStale(ctx context.Context, kind, before string) (int, error) {
	if err := s.Init(ctx); err != nil {
		return 0, err
	}
	db, err := s.open()
	if err != nil {
		return 0, err
	}
	defer db.Close()
	res, err := db.ExecContext(ctx, `DELETE FROM metadata_items WHERE kind = ? AND last_seen_at < ?`, kind, before)
	if err != nil {
		return 0, fmt.Errorf("metadata: delete stale: %w", err)
	}
	n, _ := res.RowsAffected()
	return int(n), nil
}

// Search queries the metadata_items table with LIKE matching.
func (s *Store) Search(ctx context.Context, q SearchQuery) ([]Item, error) {
	if err := s.Init(ctx); err != nil {
		return nil, err
	}
	db, err := s.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	limit := q.Limit
	if limit <= 0 {
		limit = 100
	}
	pattern := "%" + q.Query + "%"

	var rows *sql.Rows
	if q.Kind != "" {
		rows, err = db.QueryContext(ctx, `
			SELECT id, kind, name, description, source_id, repo_owner, repo_name, repo_branch,
			       item_path, install_key, target_apps, metadata_json, installed, installed_targets,
			       last_seen_at, created_at, updated_at
			FROM metadata_items
			WHERE kind = ? AND (name LIKE ? OR description LIKE ? OR repo_owner LIKE ? OR repo_name LIKE ? OR install_key LIKE ?)
			ORDER BY name LIMIT ? OFFSET ?`,
			q.Kind, pattern, pattern, pattern, pattern, pattern, limit, q.Offset)
	} else {
		rows, err = db.QueryContext(ctx, `
			SELECT id, kind, name, description, source_id, repo_owner, repo_name, repo_branch,
			       item_path, install_key, target_apps, metadata_json, installed, installed_targets,
			       last_seen_at, created_at, updated_at
			FROM metadata_items
			WHERE name LIKE ? OR description LIKE ? OR repo_owner LIKE ? OR repo_name LIKE ? OR install_key LIKE ?
			ORDER BY name LIMIT ? OFFSET ?`,
			pattern, pattern, pattern, pattern, pattern, limit, q.Offset)
	}
	if err != nil {
		return nil, fmt.Errorf("metadata: search: %w", err)
	}
	defer rows.Close()
	return scanItems(rows)
}

// Count returns the number of items matching the query (ignoring limit/offset).
func (s *Store) Count(ctx context.Context, q SearchQuery) (int, error) {
	if err := s.Init(ctx); err != nil {
		return 0, err
	}
	db, err := s.open()
	if err != nil {
		return 0, err
	}
	defer db.Close()

	pattern := "%" + q.Query + "%"
	var count int
	if q.Kind != "" {
		err = db.QueryRowContext(ctx, `
			SELECT COUNT(*) FROM metadata_items
			WHERE kind = ? AND (name LIKE ? OR description LIKE ? OR repo_owner LIKE ? OR repo_name LIKE ? OR install_key LIKE ?)`,
			q.Kind, pattern, pattern, pattern, pattern, pattern).Scan(&count)
	} else {
		err = db.QueryRowContext(ctx, `
			SELECT COUNT(*) FROM metadata_items
			WHERE name LIKE ? OR description LIKE ? OR repo_owner LIKE ? OR repo_name LIKE ? OR install_key LIKE ?`,
			pattern, pattern, pattern, pattern, pattern).Scan(&count)
	}
	if err != nil {
		return 0, fmt.Errorf("metadata: count: %w", err)
	}
	return count, nil
}

// GetItem returns a single item by kind and install_key.
func (s *Store) GetItem(ctx context.Context, kind, installKey string) (Item, error) {
	if err := s.Init(ctx); err != nil {
		return Item{}, err
	}
	db, err := s.open()
	if err != nil {
		return Item{}, err
	}
	defer db.Close()

	var it Item
	var installed int
	err = db.QueryRowContext(ctx, `
		SELECT id, kind, name, description, source_id, repo_owner, repo_name, repo_branch,
		       item_path, install_key, target_apps, metadata_json, installed, installed_targets,
		       last_seen_at, created_at, updated_at
		FROM metadata_items WHERE kind = ? AND install_key = ?`, kind, installKey).
		Scan(&it.ID, &it.Kind, &it.Name, &it.Description, &it.SourceID,
			&it.RepoOwner, &it.RepoName, &it.RepoBranch, &it.ItemPath, &it.InstallKey,
			&it.TargetApps, &it.MetadataJSON, &installed, &it.InstalledTargets,
			&it.LastSeenAt, &it.CreatedAt, &it.UpdatedAt)
	if err != nil {
		return Item{}, fmt.Errorf("metadata: get item: %w", err)
	}
	it.Installed = installed != 0
	return it, nil
}

// MarkInstalled sets the installed flag and records the target app.
func (s *Store) MarkInstalled(ctx context.Context, kind, installKey, targetApp string) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	now := timeNow()
	_, err = db.ExecContext(ctx, `
		UPDATE metadata_items SET installed = 1, installed_targets = ?, updated_at = ?
		WHERE kind = ? AND install_key = ?`, targetApp, now, kind, installKey)
	if err != nil {
		return fmt.Errorf("metadata: mark installed: %w", err)
	}
	return nil
}

func scanItems(rows *sql.Rows) ([]Item, error) {
	items := []Item{}
	for rows.Next() {
		var it Item
		var installed int
		if err := rows.Scan(&it.ID, &it.Kind, &it.Name, &it.Description, &it.SourceID,
			&it.RepoOwner, &it.RepoName, &it.RepoBranch, &it.ItemPath, &it.InstallKey,
			&it.TargetApps, &it.MetadataJSON, &installed, &it.InstalledTargets,
			&it.LastSeenAt, &it.CreatedAt, &it.UpdatedAt); err != nil {
			return nil, fmt.Errorf("metadata: scan item: %w", err)
		}
		it.Installed = installed != 0
		items = append(items, it)
	}
	return items, rows.Err()
}

func (s *Store) open() (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return nil, fmt.Errorf("metadata: mkdir: %w", err)
	}
	db, err := sql.Open("sqlite", s.path)
	if err != nil {
		return nil, fmt.Errorf("metadata: open %s: %w", s.path, err)
	}
	return db, nil
}

func timeNow() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}

func coalesce(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

const schemaSQL = `
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS metadata_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  source_key TEXT NOT NULL,
  owner TEXT NOT NULL DEFAULT '',
  repo TEXT NOT NULL DEFAULT '',
  branch TEXT NOT NULL DEFAULT 'main',
  path TEXT NOT NULL DEFAULT '',
  enabled INTEGER NOT NULL DEFAULT 1,
  source_file TEXT NOT NULL DEFAULT '',
  last_refreshed_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  UNIQUE(kind, source_key)
);

CREATE TABLE IF NOT EXISTS metadata_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  source_id INTEGER NOT NULL DEFAULT 0,
  repo_owner TEXT NOT NULL DEFAULT '',
  repo_name TEXT NOT NULL DEFAULT '',
  repo_branch TEXT NOT NULL DEFAULT 'main',
  item_path TEXT NOT NULL DEFAULT '',
  install_key TEXT NOT NULL DEFAULT '',
  target_apps TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  installed INTEGER NOT NULL DEFAULT 0,
  installed_targets TEXT NOT NULL DEFAULT '',
  last_seen_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  UNIQUE(kind, install_key)
);

CREATE INDEX IF NOT EXISTS idx_metadata_items_name ON metadata_items(name);
CREATE INDEX IF NOT EXISTS idx_metadata_items_kind ON metadata_items(kind);
CREATE INDEX IF NOT EXISTS idx_metadata_items_repo ON metadata_items(repo_owner, repo_name);
`
