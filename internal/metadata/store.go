package metadata

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
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

// Init creates metadata tables if they do not exist and runs idempotent migrations.
func (s *Store) Init(ctx context.Context) error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err = db.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("metadata: init schema: %w", err)
	}
	if err := s.runMigrations(ctx, db); err != nil {
		return fmt.Errorf("metadata: migrations: %w", err)
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
	contentCachedAt := item.ContentCachedAt
	if contentCachedAt == "" {
		contentCachedAt = now
	}
	_, err = db.ExecContext(ctx, `
		INSERT INTO metadata_items(kind, name, description, source_id, repo_owner, repo_name, repo_branch, item_path, install_key, target_apps, metadata_json, installed, installed_targets, content, content_cached_at, manifest_path, last_seen_at, created_at, updated_at)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(kind, install_key) DO UPDATE SET
			name=excluded.name, description=excluded.description, source_id=excluded.source_id,
			repo_owner=excluded.repo_owner, repo_name=excluded.repo_name, repo_branch=excluded.repo_branch,
			item_path=excluded.item_path, target_apps=excluded.target_apps, metadata_json=excluded.metadata_json,
			content=excluded.content, content_cached_at=excluded.content_cached_at, manifest_path=excluded.manifest_path,
			last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at`,
		item.Kind, item.Name, item.Description, item.SourceID,
		item.RepoOwner, item.RepoName, item.RepoBranch, item.ItemPath,
		item.InstallKey, item.TargetApps, coalesce(item.MetadataJSON, "{}"),
		boolToInt(item.Installed), item.InstalledTargets,
		item.Content, contentCachedAt, item.ManifestPath, now, now, now)
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
		INSERT INTO metadata_items(kind, name, description, source_id, repo_owner, repo_name, repo_branch, item_path, install_key, target_apps, metadata_json, installed, installed_targets, content, content_cached_at, manifest_path, last_seen_at, created_at, updated_at)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(kind, install_key) DO UPDATE SET
			name=excluded.name, description=excluded.description, source_id=excluded.source_id,
			repo_owner=excluded.repo_owner, repo_name=excluded.repo_name, repo_branch=excluded.repo_branch,
			item_path=excluded.item_path, target_apps=excluded.target_apps, metadata_json=excluded.metadata_json,
			content=excluded.content, content_cached_at=excluded.content_cached_at, manifest_path=excluded.manifest_path,
			last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at`)
	if err != nil {
		_ = tx.Rollback()
		return 0, fmt.Errorf("metadata: prepare upsert: %w", err)
	}
	defer stmt.Close()

	now := timeNow()
	written := 0
	for _, item := range items {
		contentCachedAt := item.ContentCachedAt
		if contentCachedAt == "" {
			contentCachedAt = now
		}
		if _, err := stmt.ExecContext(ctx,
			item.Kind, item.Name, item.Description, item.SourceID,
			item.RepoOwner, item.RepoName, item.RepoBranch, item.ItemPath,
			item.InstallKey, item.TargetApps, coalesce(item.MetadataJSON, "{}"),
			boolToInt(item.Installed), item.InstalledTargets,
			item.Content, contentCachedAt, item.ManifestPath, now, now, now); err != nil {
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

// itemColumns is the canonical column list selected from metadata_items.
const itemColumns = `id, kind, name, description, source_id, repo_owner, repo_name, repo_branch,
       item_path, install_key, target_apps, metadata_json, installed, installed_targets,
       content, content_cached_at, manifest_path, last_seen_at, created_at, updated_at`

// canonicalOrder ranks candidate rows that share a name so that the
// ROW_NUMBER()=1 pick is a sensible "source of truth". Lower sorts first:
//
//  1. Non-catalog repos beat awesome-list/catalog repos (repo_name LIKE
//     'awesome-%') — a catalog/awesome-list repo is never the chosen source
//     when a real copy exists.
//  2. Official Anthropic repos beat community repos.
//  3. Shorter in-repo paths beat deeply nested ones.
//  4. repo_owner/repo_name as a stable alphabetical tiebreak.
const canonicalOrder = `CASE WHEN repo_name LIKE 'awesome-%' THEN 1 ELSE 0 END,
				CASE WHEN repo_owner = 'anthropics' THEN 0 ELSE 1 END,
				length(item_path),
				repo_owner, repo_name`

// matchPredicate builds the WHERE clause (without the leading "WHERE") for a
// search, optionally narrowed by kind. Pass the raw kind string ("" = any kind).
func matchPredicate(kind string) string {
	pred := "(name LIKE ? OR description LIKE ? OR repo_owner LIKE ? OR repo_name LIKE ? OR install_key LIKE ?)"
	lead := ""
	if kind != "" {
		lead = "kind = ? AND "
	}
	// A subagent is a markdown file beneath an `agents/` folder. Rows whose
	// in-repo path has no `agents` segment (commands/, docs/, README, …) are
	// not subagents and must never appear on the SubAgents page. This mirrors
	// DiscoverResources' underAgentsFolder at query time, so index entries left
	// by an older binary (before that filter existed) can't leak through.
	if kind == "agent" {
		lead += "((item_path LIKE 'agents/%' OR item_path LIKE '%/agents/%') OR (item_path LIKE '%.md' AND item_path NOT LIKE 'docs/%' AND item_path NOT LIKE 'commands/%' AND item_path NOT IN ('', 'README.md', 'CLAUDE.md', 'AGENTS.md', 'GEMINI.md'))) AND "
	}
	return lead + pred
}

// Search queries the metadata_items table with LIKE matching. Results are
// deduplicated by name (case-insensitive): when the same name exists in
// several repos, only the canonical source is returned (see canonicalOrder).
// Install status is unaffected because InstalledAppsFor detects installs by
// on-disk directory name, independent of repo.
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

	args := []any{pattern, pattern, pattern, pattern, pattern}
	if q.Kind != "" {
		args = append([]any{q.Kind}, args...)
	}
	args = append(args, limit, q.Offset)

	rows, err := db.QueryContext(ctx, `
		WITH ranked AS (
			SELECT `+itemColumns+`,
			       ROW_NUMBER() OVER (PARTITION BY lower(name) ORDER BY `+canonicalOrder+`) AS rn
			FROM metadata_items
			WHERE `+matchPredicate(q.Kind)+`
		)
		SELECT `+itemColumns+` FROM ranked WHERE rn = 1
		ORDER BY name LIMIT ? OFFSET ?`,
		args...)
	if err != nil {
		return nil, fmt.Errorf("metadata: search: %w", err)
	}
	defer rows.Close()
	return scanItems(rows)
}

// Count returns the number of deduplicated names matching the query (ignoring
// limit/offset), so the total matches what Search can display.
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
	args := []any{pattern, pattern, pattern, pattern, pattern}
	if q.Kind != "" {
		args = append([]any{q.Kind}, args...)
	}

	var count int
	err = db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM (
			SELECT DISTINCT lower(name) FROM metadata_items WHERE `+matchPredicate(q.Kind)+`
		)`,
		args...).Scan(&count)
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
		       content, content_cached_at, manifest_path, last_seen_at, created_at, updated_at
		FROM metadata_items WHERE kind = ? AND install_key = ?`, kind, installKey).
		Scan(&it.ID, &it.Kind, &it.Name, &it.Description, &it.SourceID,
			&it.RepoOwner, &it.RepoName, &it.RepoBranch, &it.ItemPath, &it.InstallKey,
			&it.TargetApps, &it.MetadataJSON, &installed, &it.InstalledTargets,
			&it.Content, &it.ContentCachedAt, &it.ManifestPath, &it.LastSeenAt, &it.CreatedAt, &it.UpdatedAt)
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

// MarkUninstalled removes the specified app from the installed targets list.
// If no targets remain, the installed flag is cleared. Uses a transaction to
// prevent race conditions when multiple concurrent uninstalls target the same item.
func (s *Store) MarkUninstalled(ctx context.Context, kind, installKey, app string) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("metadata: mark uninstalled: begin tx: %w", err)
	}
	defer tx.Rollback()
	// Fetch current targets within the transaction.
	var currentTargets string
	err = tx.QueryRowContext(ctx, `
		SELECT installed_targets FROM metadata_items
		WHERE kind = ? AND install_key = ?`, kind, installKey).Scan(&currentTargets)
	if err != nil {
		return fmt.Errorf("metadata: mark uninstalled: %w", err)
	}
	// Remove the app from the comma-separated list.
	newTargets := removeAppFromTargets(currentTargets, app)
	now := timeNow()
	if newTargets == "" {
		_, err = tx.ExecContext(ctx, `
			UPDATE metadata_items SET installed = 0, installed_targets = '', updated_at = ?
			WHERE kind = ? AND install_key = ?`, now, kind, installKey)
	} else {
		_, err = tx.ExecContext(ctx, `
			UPDATE metadata_items SET installed_targets = ?, updated_at = ?
			WHERE kind = ? AND install_key = ?`, newTargets, now, kind, installKey)
	}
	if err != nil {
		return fmt.Errorf("metadata: mark uninstalled: %w", err)
	}
	return tx.Commit()
}

// removeAppFromTargets removes a specific app from a comma-separated target list.
func removeAppFromTargets(targets, app string) string {
	if targets == "" {
		return ""
	}
	parts := strings.Split(targets, ",")
	result := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" && p != app {
			result = append(result, p)
		}
	}
	return strings.Join(result, ",")
}

func scanItems(rows *sql.Rows) ([]Item, error) {
	items := []Item{}
	for rows.Next() {
		var it Item
		var installed int
		if err := rows.Scan(&it.ID, &it.Kind, &it.Name, &it.Description, &it.SourceID,
			&it.RepoOwner, &it.RepoName, &it.RepoBranch, &it.ItemPath, &it.InstallKey,
			&it.TargetApps, &it.MetadataJSON, &installed, &it.InstalledTargets,
			&it.Content, &it.ContentCachedAt, &it.ManifestPath, &it.LastSeenAt, &it.CreatedAt, &it.UpdatedAt); err != nil {
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

// runMigrations applies idempotent data migrations after the schema exists.
func (s *Store) runMigrations(ctx context.Context, db *sql.DB) error {
	if _, err := db.ExecContext(ctx, migrationMetaSQL); err != nil {
		return fmt.Errorf("migration meta: %w", err)
	}
	migrations := []struct {
		id  string
		run func(context.Context, *sql.DB) error
	}{
		{id: "prompt_to_instruction", run: s.migratePromptToInstruction},
		{id: "add_content_cache_columns", run: s.migrateAddContentCacheColumns},
		{id: "add_manifest_path_column", run: s.migrateAddManifestPathColumn},
	}
	for _, migration := range migrations {
		var applied int
		if err := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM migration_meta WHERE id = ?`, migration.id).Scan(&applied); err != nil {
			return fmt.Errorf("migration check %s: %w", migration.id, err)
		}
		if applied > 0 {
			continue
		}
		if err := migration.run(ctx, db); err != nil {
			return fmt.Errorf("migration %s: %w", migration.id, err)
		}
		if _, err := db.ExecContext(ctx, `INSERT INTO migration_meta(id, applied_at) VALUES(?, ?)`, migration.id, timeNow()); err != nil {
			return fmt.Errorf("migration record %s: %w", migration.id, err)
		}
	}
	return nil
}

func (s *Store) migratePromptToInstruction(ctx context.Context, db *sql.DB) error {
	for _, table := range []string{"metadata_items", "metadata_sources"} {
		if _, err := db.ExecContext(ctx, `UPDATE `+table+` SET kind = 'instruction' WHERE kind = 'prompt'`); err != nil {
			return fmt.Errorf("migrate %s: %w", table, err)
		}
	}
	return nil
}

func (s *Store) migrateAddContentCacheColumns(ctx context.Context, db *sql.DB) error {
	for _, stmt := range []string{
		`ALTER TABLE metadata_items ADD COLUMN content TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE metadata_items ADD COLUMN content_cached_at TEXT NOT NULL DEFAULT ''`,
	} {
		_, err := db.ExecContext(ctx, stmt)
		if err != nil && !strings.Contains(err.Error(), "duplicate column name") {
			return fmt.Errorf("migrate add content cache columns: %w", err)
		}
	}
	return nil
}

func (s *Store) migrateAddManifestPathColumn(ctx context.Context, db *sql.DB) error {
	_, err := db.ExecContext(ctx, `ALTER TABLE metadata_items ADD COLUMN manifest_path TEXT NOT NULL DEFAULT ''`)
	if err != nil && !strings.Contains(err.Error(), "duplicate column name") {
		return fmt.Errorf("migrate add manifest_path column: %w", err)
	}
	return nil
}

// SetCatalogCount stores an upstream catalog total for a kind.
func (s *Store) SetCatalogCount(ctx context.Context, kind string, count int, sourceURL string) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, `INSERT INTO metadata_catalog_counts(kind, count, source_url, updated_at) VALUES(?,?,?,?) ON CONFLICT(kind) DO UPDATE SET count=excluded.count, source_url=excluded.source_url, updated_at=excluded.updated_at`, kind, count, sourceURL, timeNow())
	if err != nil {
		return fmt.Errorf("metadata: set catalog count: %w", err)
	}
	return nil
}

// CatalogCount returns the upstream catalog total for a kind when available.
func (s *Store) CatalogCount(ctx context.Context, kind string) (int, bool, error) {
	if err := s.Init(ctx); err != nil {
		return 0, false, err
	}
	db, err := s.open()
	if err != nil {
		return 0, false, err
	}
	defer db.Close()
	var count int
	err = db.QueryRowContext(ctx, `SELECT count FROM metadata_catalog_counts WHERE kind = ?`, kind).Scan(&count)
	if err == sql.ErrNoRows {
		return 0, false, nil
	}
	if err != nil {
		return 0, false, fmt.Errorf("metadata: catalog count: %w", err)
	}
	return count, true, nil
}

// SaveContent persists fetched manifest content and a timestamp for a single
// metadata item. The content is the raw text of the manifest file (SKILL.md,
// AGENT.md, etc.) and cachedAt is an RFC3339 timestamp of when it was fetched.
func (s *Store) SaveContent(ctx context.Context, kind, installKey, content, cachedAt, manifestPath string) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, `
		UPDATE metadata_items SET content = ?, content_cached_at = ?, manifest_path = ?, updated_at = ?
		WHERE kind = ? AND install_key = ?`, content, cachedAt, manifestPath, cachedAt, kind, installKey)
	if err != nil {
		return fmt.Errorf("metadata: save content: %w", err)
	}
	return nil
}

// SaveItemContentAndDescription updates the content, content_cached_at,
// manifest_path, and description for a single metadata item. Used by per-item
// refresh to persist both the fresh manifest and any upstream description changes.
func (s *Store) SaveItemContentAndDescription(ctx context.Context, kind, installKey, content, cachedAt, manifestPath, description string) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.ExecContext(ctx, `
		UPDATE metadata_items SET content = ?, content_cached_at = ?, manifest_path = ?, description = ?, updated_at = ?
		WHERE kind = ? AND install_key = ?`, content, cachedAt, manifestPath, description, cachedAt, kind, installKey)
	if err != nil {
		return fmt.Errorf("metadata: save content and description: %w", err)
	}
	return nil
}

const migrationMetaSQL = `
CREATE TABLE IF NOT EXISTS migration_meta (
  id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT ''
);
`

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
  content TEXT NOT NULL DEFAULT '',
  content_cached_at TEXT NOT NULL DEFAULT '',
  manifest_path TEXT NOT NULL DEFAULT '',
  last_seen_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  UNIQUE(kind, install_key)
);

CREATE TABLE IF NOT EXISTS metadata_catalog_counts (
  kind TEXT PRIMARY KEY,
  count INTEGER NOT NULL,
  source_url TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_metadata_items_name ON metadata_items(name);
CREATE INDEX IF NOT EXISTS idx_metadata_items_kind ON metadata_items(kind);
CREATE INDEX IF NOT EXISTS idx_metadata_items_repo ON metadata_items(repo_owner, repo_name);
`
