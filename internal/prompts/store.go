package prompts

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	_ "github.com/mattn/go-sqlite3"
)

// Prompt represents a single prompt from any source.
type Prompt struct {
	ID          int64     `json:"id"`
	Source      string    `json:"source"`       // "claude", "prompts_chat", "promptingguide"
	SourceURL   string    `json:"source_url"`   // original URL
	Category    string    `json:"category"`     // e.g. "coding", "writing", "analysis"
	Title       string    `json:"title"`        // display name
	Description string    `json:"description"`  // short description
	Content     string    `json:"content"`      // the prompt text
	Author      string    `json:"author"`       // original author if known
	Tags        string    `json:"tags"`         // comma-separated tags
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// Store manages the prompts SQLite database.
type Store struct {
	dir string
}

// NewStore creates a new prompts store.
func NewStore() *Store {
	return &Store{dir: pathutil.ConfigDir()}
}

func (s *Store) dbPath() string {
	return fmt.Sprintf("%s/prompts.db", s.dir)
}

func (s *Store) open() (*sql.DB, error) {
	return sql.Open("sqlite3", s.dbPath()+"?_journal_mode=WAL")
}

// Init creates the database and tables if they don't exist.
func (s *Store) Init(ctx context.Context) error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()

	schema := `
	CREATE TABLE IF NOT EXISTS prompts (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		source TEXT NOT NULL,
		source_url TEXT NOT NULL DEFAULT '',
		category TEXT NOT NULL DEFAULT '',
		title TEXT NOT NULL,
		description TEXT NOT NULL DEFAULT '',
		content TEXT NOT NULL,
		author TEXT NOT NULL DEFAULT '',
		tags TEXT NOT NULL DEFAULT '',
		created_at TEXT NOT NULL DEFAULT '',
		updated_at TEXT NOT NULL DEFAULT ''
	);
	CREATE INDEX IF NOT EXISTS idx_prompts_source ON prompts(source);
	CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category);
	CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_source_url ON prompts(source, source_url);
	`
	_, err = db.ExecContext(ctx, schema)
	return err
}

// UpsertPrompt inserts or updates a prompt based on (source, source_url).
func (s *Store) UpsertPrompt(ctx context.Context, p *Prompt) error {
	if err := s.Init(ctx); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()

	now := time.Now().UTC().Format(time.RFC3339)
	_, err = db.ExecContext(ctx, `
		INSERT INTO prompts (source, source_url, category, title, description, content, author, tags, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(source, source_url) DO UPDATE SET
			category = excluded.category,
			title = excluded.title,
			description = excluded.description,
			content = excluded.content,
			author = excluded.author,
			tags = excluded.tags,
			updated_at = excluded.updated_at
	`, p.Source, p.SourceURL, p.Category, p.Title, p.Description, p.Content, p.Author, p.Tags, now, now)
	return err
}

// ListPrompts returns all prompts, optionally filtered by source or category.
func (s *Store) ListPrompts(ctx context.Context, source, category string) ([]Prompt, error) {
	if err := s.Init(ctx); err != nil {
		return nil, err
	}
	db, err := s.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	query := `SELECT id, source, source_url, category, title, description, content, author, tags, created_at, updated_at FROM prompts WHERE 1=1`
	args := []any{}
	if source != "" {
		query += ` AND source = ?`
		args = append(args, source)
	}
	if category != "" {
		query += ` AND category = ?`
		args = append(args, category)
	}
	query += ` ORDER BY source, category, title`

	rows, err := db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var prompts []Prompt
	for rows.Next() {
		var p Prompt
		if err := rows.Scan(&p.ID, &p.Source, &p.SourceURL, &p.Category, &p.Title, &p.Description, &p.Content, &p.Author, &p.Tags, &p.CreatedAt, &p.UpdatedAt); err != nil {
			return nil, err
		}
		prompts = append(prompts, p)
	}
	return prompts, rows.Err()
}

// SearchPrompts searches prompts by title, description, or content.
func (s *Store) SearchPrompts(ctx context.Context, q string) ([]Prompt, error) {
	if err := s.Init(ctx); err != nil {
		return nil, err
	}
	db, err := s.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	like := "%" + q + "%"
	rows, err := db.QueryContext(ctx, `
		SELECT id, source, source_url, category, title, description, content, author, tags, created_at, updated_at
		FROM prompts
		WHERE title LIKE ? OR description LIKE ? OR content LIKE ? OR tags LIKE ?
		ORDER BY source, category, title
	`, like, like, like, like)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var prompts []Prompt
	for rows.Next() {
		var p Prompt
		if err := rows.Scan(&p.ID, &p.Source, &p.SourceURL, &p.Category, &p.Title, &p.Description, &p.Content, &p.Author, &p.Tags, &p.CreatedAt, &p.UpdatedAt); err != nil {
			return nil, err
		}
		prompts = append(prompts, p)
	}
	return prompts, rows.Err()
}

// CountPrompts returns the total number of prompts, optionally filtered.
func (s *Store) CountPrompts(ctx context.Context, source, category string) (int, error) {
	if err := s.Init(ctx); err != nil {
		return 0, err
	}
	db, err := s.open()
	if err != nil {
		return 0, err
	}
	defer db.Close()

	query := `SELECT COUNT(*) FROM prompts WHERE 1=1`
	args := []any{}
	if source != "" {
		query += ` AND source = ?`
		args = append(args, source)
	}
	if category != "" {
		query += ` AND category = ?`
		args = append(args, category)
	}

	var count int
	err = db.QueryRowContext(ctx, query, args...).Scan(&count)
	return count, err
}
