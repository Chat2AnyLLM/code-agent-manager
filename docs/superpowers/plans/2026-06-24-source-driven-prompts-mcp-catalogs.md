# Source-Driven Prompts and MCP Catalogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CAM load prompts and MCP servers from upstream `config.yaml` `sources:` entries instead of generated `dist/prompts.json` and `dist/servers.json` artifacts.

**Architecture:** Extend the shared catalog config parser to expose source entries, add reusable GitHub source helpers, then replace prompt and MCP YAML handling with source aggregation. Prompts normalize source files into existing `AwesomePrompt` records; MCP normalizes structured local files and only installable Markdown-derived candidates into existing `ServerSchema` records.

**Tech Stack:** Go, YAML (`gopkg.in/yaml.v3`), SQLite-backed existing stores, `net/http`, existing `internal/metadata.RepoBrowser`, existing CLI/desktop service layers.

---

## Scope and file map

This plan intentionally covers both prompts and MCP because they share the same upstream-catalog pattern and shared config/source helper work. Tasks are ordered so each unit is testable independently.

### Files to modify

- `internal/catalogconfig/catalogconfig.go`
  - Add `Sources` parsing while preserving `DataFile` behavior.
- `internal/catalogconfig/catalogconfig_test.go`
  - New test file for parsing `sources:`.
- `internal/catalogconfig/source_helpers.go`
  - New shared helpers for GitHub URL parsing, source-name slugging, raw/blob URL building, and source path checks.
- `internal/catalogconfig/source_helpers_test.go`
  - Tests for shared helpers.
- `internal/prompts/source_loader.go`
  - New prompt source aggregation implementation.
- `internal/prompts/service.go`
  - Replace config-to-dist resolution with source aggregation.
- `internal/prompts/service_test.go`
  - Rewrite dist-based tests to source-based tests; keep explicit direct JSON override tests if still needed for dev/test paths.
- `internal/mcp/source_loader.go`
  - New MCP source aggregation implementation.
- `internal/mcp/catalog_loader.go`
  - Replace remote YAML dist resolution with source aggregation; keep direct local/remote JSON catalog behavior.
- `internal/mcp/mcp_test.go`
  - Rewrite remote config YAML test and add source aggregation tests.
- `README.md`
  - Update wording that says prompts/MCP consume dist artifacts.

### Files to inspect during implementation

- `internal/metadata/repobrowser.go`
  - Existing GitHub tree/file fetch interface.
- `internal/prompts/store.go`
  - Prompt uniqueness and field mapping.
- `internal/mcp/registry.go`
  - `ServerSchema` and `InstallationEntry` fields.
- `internal/mcp/schema.go` or equivalent if present
  - `ServerFromSchema` validation behavior. If no separate file exists, search for `ServerFromSchema`.

---

## Task 1: Extend catalog config parsing

**Files:**
- Modify: `internal/catalogconfig/catalogconfig.go`
- Create: `internal/catalogconfig/catalogconfig_test.go`

- [ ] **Step 1: Write failing tests for source parsing and existing DataFile compatibility**

Create `internal/catalogconfig/catalogconfig_test.go` with:

```go
package catalogconfig

import "testing"

func TestParseReadsSourcesAndOutput(t *testing.T) {
	raw := []byte(`version: "1.0.0"
description: Example catalog
output:
  dir: dist
  formats: [json, csv]
sources:
  - name: Local Prompts
    type: local
    path: prompts/
  - name: Prompts Chat
    type: github
    url: https://github.com/f/prompts.chat
    format: csv
    file_path: prompts.csv
`)

	cfg, err := Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if cfg.Output.Dir != "dist" {
		t.Fatalf("Output.Dir = %q, want dist", cfg.Output.Dir)
	}
	if len(cfg.Output.Formats) != 2 || cfg.Output.Formats[0] != "json" || cfg.Output.Formats[1] != "csv" {
		t.Fatalf("Output.Formats = %#v", cfg.Output.Formats)
	}
	if len(cfg.Sources) != 2 {
		t.Fatalf("Sources len = %d, want 2", len(cfg.Sources))
	}
	first := cfg.Sources[0]
	if first.Name != "Local Prompts" || first.Type != "local" || first.Path != "prompts/" {
		t.Fatalf("first source = %#v", first)
	}
	second := cfg.Sources[1]
	if second.Name != "Prompts Chat" || second.Type != "github" || second.URL != "https://github.com/f/prompts.chat" || second.Format != "csv" || second.FilePath != "prompts.csv" {
		t.Fatalf("second source = %#v", second)
	}
}

func TestDataFileStillUsesOutput(t *testing.T) {
	raw := []byte(`output:
  dir: dist
  formats: [json, csv]
sources:
  - name: Ignored
    type: local
    path: prompts/
`)

	got, err := DataFile("prompts", raw)
	if err != nil {
		t.Fatalf("DataFile: %v", err)
	}
	if got != "dist/prompts.json" {
		t.Fatalf("DataFile = %q, want dist/prompts.json", got)
	}
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
go test ./internal/catalogconfig
```

Expected: FAIL because `Parse`, `OutputConfig`, and `CatalogSource` do not exist or `Config.Sources` does not exist.

- [ ] **Step 3: Implement catalog config source parsing**

Modify `internal/catalogconfig/catalogconfig.go` to this shape, preserving existing behavior:

```go
package catalogconfig

import (
	"fmt"
	"strings"

	"gopkg.in/yaml.v3"
)

// Config is the shared config.yaml shape used by Chat2AnyLLM catalog repos.
type Config struct {
	Output  OutputConfig    `yaml:"output"`
	Sources []CatalogSource `yaml:"sources"`
}

// OutputConfig describes where an upstream catalog build writes generated data.
type OutputConfig struct {
	Dir     string   `yaml:"dir"`
	Formats []string `yaml:"formats"`
}

// CatalogSource describes one upstream source declared in a catalog config.yaml.
type CatalogSource struct {
	Name     string `yaml:"name"`
	Type     string `yaml:"type"`
	Path     string `yaml:"path"`
	URL      string `yaml:"url"`
	Format   string `yaml:"format"`
	FilePath string `yaml:"file_path"`
}

// Parse decodes a catalog config.yaml and preserves unknown fields for forward compatibility.
func Parse(raw []byte) (Config, error) {
	var cfg Config
	if err := yaml.Unmarshal(raw, &cfg); err != nil {
		return Config{}, fmt.Errorf("catalog config: parse: %w", err)
	}
	return cfg, nil
}

// DataFile derives the generated data file path for a config.yaml catalog.
func DataFile(dataName string, raw []byte) (string, error) {
	cfg, err := Parse(raw)
	if err != nil {
		return "", err
	}
	dir := strings.Trim(strings.TrimSpace(cfg.Output.Dir), "/")
	if dir == "" {
		dir = "dist"
	}
	for _, format := range cfg.Output.Formats {
		if strings.EqualFold(strings.TrimSpace(format), "json") {
			return dir + "/" + dataName + ".json", nil
		}
	}
	return "", fmt.Errorf("catalog config: missing json output format")
}
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
go test ./internal/catalogconfig
```

Expected: PASS.

- [ ] **Step 5: Do not commit yet**

Do not commit until the user explicitly approves commits. Continue to Task 2.

---

## Task 2: Add shared source helpers

**Files:**
- Create: `internal/catalogconfig/source_helpers.go`
- Create: `internal/catalogconfig/source_helpers_test.go`

- [ ] **Step 1: Write failing helper tests**

Create `internal/catalogconfig/source_helpers_test.go`:

```go
package catalogconfig

import "testing"

func TestParseGitHubRepoURL(t *testing.T) {
	cases := []struct {
		name   string
		raw    string
		owner  string
		repo   string
		branch string
		ok     bool
	}{
		{name: "plain", raw: "https://github.com/f/prompts.chat", owner: "f", repo: "prompts.chat", branch: "", ok: true},
		{name: "tree", raw: "https://github.com/owner/repo/tree/dev/prompts", owner: "owner", repo: "repo", branch: "dev", ok: true},
		{name: "git suffix", raw: "https://github.com/owner/repo.git", owner: "owner", repo: "repo", branch: "", ok: true},
		{name: "not github", raw: "https://example.com/owner/repo", ok: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := ParseGitHubRepoURL(tc.raw)
			if ok != tc.ok {
				t.Fatalf("ok = %v, want %v", ok, tc.ok)
			}
			if !ok {
				return
			}
			if got.Owner != tc.owner || got.Repo != tc.repo || got.Branch != tc.branch {
				t.Fatalf("repo = %#v", got)
			}
		})
	}
}

func TestSourceSlug(t *testing.T) {
	if got := SourceSlug("Prompts Chat"); got != "prompts_chat" {
		t.Fatalf("SourceSlug = %q", got)
	}
	if got := SourceSlug(" AI Boost: Awesome Prompts! "); got != "ai_boost_awesome_prompts" {
		t.Fatalf("SourceSlug punctuation = %q", got)
	}
}

func TestBlobURLAndRawURL(t *testing.T) {
	repo := GitHubRepo{Owner: "owner", Repo: "repo", Branch: "dev"}
	if got := repo.RawURL("prompts/a.txt"); got != "https://raw.githubusercontent.com/owner/repo/dev/prompts/a.txt" {
		t.Fatalf("RawURL = %q", got)
	}
	if got := repo.BlobURL("prompts/a.txt"); got != "https://github.com/owner/repo/blob/dev/prompts/a.txt" {
		t.Fatalf("BlobURL = %q", got)
	}
}

func TestCleanSourcePath(t *testing.T) {
	if got := CleanSourcePath("/prompts//"); got != "prompts" {
		t.Fatalf("CleanSourcePath = %q", got)
	}
	if got := CleanSourcePath(""); got != "" {
		t.Fatalf("CleanSourcePath empty = %q", got)
	}
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
go test ./internal/catalogconfig
```

Expected: FAIL because helper symbols do not exist.

- [ ] **Step 3: Implement helpers**

Create `internal/catalogconfig/source_helpers.go`:

```go
package catalogconfig

import (
	"net/url"
	"path"
	"regexp"
	"strings"
)

// GitHubRepo identifies a GitHub repository and optional branch/ref.
type GitHubRepo struct {
	Owner  string
	Repo   string
	Branch string
}

// BranchOrDefault returns the configured branch or main.
func (r GitHubRepo) BranchOrDefault() string {
	if strings.TrimSpace(r.Branch) == "" {
		return "main"
	}
	return r.Branch
}

// RawURL returns the raw.githubusercontent.com URL for a repo-relative file.
func (r GitHubRepo) RawURL(filePath string) string {
	return "https://raw.githubusercontent.com/" + url.PathEscape(r.Owner) + "/" + url.PathEscape(r.Repo) + "/" + url.PathEscape(r.BranchOrDefault()) + "/" + CleanSourcePath(filePath)
}

// BlobURL returns the github.com blob URL for a repo-relative file.
func (r GitHubRepo) BlobURL(filePath string) string {
	return "https://github.com/" + url.PathEscape(r.Owner) + "/" + url.PathEscape(r.Repo) + "/blob/" + url.PathEscape(r.BranchOrDefault()) + "/" + CleanSourcePath(filePath)
}

// ParseGitHubRepoURL extracts owner/repo/ref from a GitHub repository URL.
func ParseGitHubRepoURL(raw string) (GitHubRepo, bool) {
	s := strings.TrimSpace(raw)
	if s == "" {
		return GitHubRepo{}, false
	}
	u, err := url.Parse(s)
	if err != nil || !strings.EqualFold(strings.TrimPrefix(u.Host, "www."), "github.com") {
		return GitHubRepo{}, false
	}
	parts := strings.Split(strings.Trim(strings.TrimSuffix(u.Path, ".git"), "/"), "/")
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return GitHubRepo{}, false
	}
	repo := GitHubRepo{Owner: parts[0], Repo: strings.TrimSuffix(parts[1], ".git")}
	if len(parts) >= 4 && (parts[2] == "tree" || parts[2] == "blob") {
		repo.Branch = parts[3]
	}
	return repo, true
}

var slugNonWord = regexp.MustCompile(`[^a-z0-9]+`)

// SourceSlug converts a source display name into a stable storage key.
func SourceSlug(name string) string {
	s := strings.ToLower(strings.TrimSpace(name))
	s = slugNonWord.ReplaceAllString(s, "_")
	s = strings.Trim(s, "_")
	if s == "" {
		return "unknown_source"
	}
	return s
}

// CleanSourcePath normalizes config source paths to repo-relative slash paths.
func CleanSourcePath(p string) string {
	p = strings.TrimSpace(strings.Trim(p, "/"))
	if p == "" {
		return ""
	}
	return path.Clean(p)
}

// JoinSourcePath joins repo-relative path fragments.
func JoinSourcePath(parts ...string) string {
	cleaned := make([]string, 0, len(parts))
	for _, part := range parts {
		if c := CleanSourcePath(part); c != "" {
			cleaned = append(cleaned, c)
		}
	}
	if len(cleaned) == 0 {
		return ""
	}
	return path.Join(cleaned...)
}
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
go test ./internal/catalogconfig
```

Expected: PASS.

---

## Task 3: Add prompt source aggregation loader tests

**Files:**
- Create: `internal/prompts/source_loader.go`
- Modify: `internal/prompts/service.go`
- Modify: `internal/prompts/service_test.go`

- [ ] **Step 1: Add source-driven prompt tests**

Append these tests to `internal/prompts/service_test.go`. They intentionally use an HTTP test server by overriding `repoRawBaseURL`, so no live GitHub access is needed.

```go
func TestFetchAwesomePromptsLoadsConfigSources(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			w.Header().Set("Content-Type", "text/yaml")
			_, _ = w.Write([]byte(`sources:
  - name: Local Prompts
    type: local
    path: prompts/
  - name: Prompts Chat
    type: github
    url: https://github.com/f/prompts.chat
    format: csv
    file_path: prompts.csv
`))
		case "/repos/Chat2AnyLLM/awesome-prompts/git/trees/master":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"tree":[{"path":"prompts/local.yaml","type":"blob","size":80}],"truncated":false}`))
		case "/Chat2AnyLLM/awesome-prompts/master/prompts/local.yaml":
			_, _ = w.Write([]byte("slug: local\ntitle: Local Prompt\ndescription: Local description\nprompt: Use local prompt\ntags: [local]\ncategory: local-cat\nauthor: tester\n"))
		case "/f/prompts.chat/main/prompts.csv":
			_, _ = w.Write([]byte("title,prompt,description,category,tags,author\nCSV Prompt,Use csv prompt,CSV description,csv-cat,one;two,csv-author\n"))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	svc.repoRawBaseURL = server.URL
	svc.githubAPIBaseURL = server.URL + "/repos"

	got, err := svc.FetchAwesomePrompts(ctx)
	if err != nil {
		t.Fatalf("FetchAwesomePrompts: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 prompts, got %d: %#v", len(got), got)
	}
	if got[0].Title != "Local Prompt" || got[0].Prompt != "Use local prompt" {
		t.Fatalf("unexpected local prompt: %#v", got[0])
	}
	if got[1].Title != "CSV Prompt" || got[1].Prompt != "Use csv prompt" || got[1].Author != "csv-author" {
		t.Fatalf("unexpected csv prompt: %#v", got[1])
	}
}

func TestFetchAwesomePromptsDoesNotUseDistFallback(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			_, _ = w.Write([]byte("output:\n  dir: dist\n  formats: [json]\nsources: []\n"))
		case "/dist/prompts.json":
			t.Fatalf("dist/prompts.json should not be fetched")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	_, err := svc.FetchAwesomePrompts(ctx)
	if err == nil || !strings.Contains(err.Error(), "no prompts loaded") {
		t.Fatalf("expected no prompts loaded error, got %v", err)
	}
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
go test ./internal/prompts -run "TestFetchAwesomePrompts(LoadsConfigSources|DoesNotUseDistFallback)" -v
```

Expected: FAIL because `githubAPIBaseURL` and source aggregation do not exist, and current code still resolves dist JSON.

---

## Task 4: Implement prompt source aggregation

**Files:**
- Create: `internal/prompts/source_loader.go`
- Modify: `internal/prompts/service.go`

- [ ] **Step 1: Add service fields for testable GitHub source access**

Modify `internal/prompts/service.go` `Service` struct to include:

```go
	githubAPIBaseURL string
```

Modify `NewService()` to set:

```go
		githubAPIBaseURL: "https://api.github.com/repos",
```

Keep existing `repoRawBaseURL`.

- [ ] **Step 2: Replace config-to-dist resolution in FetchAwesomePrompts**

Change `FetchAwesomePrompts` in `internal/prompts/service.go` from remote-dist-with-embedded-fallback to source-driven loading:

```go
func (s *Service) FetchAwesomePrompts(ctx context.Context) ([]AwesomePrompt, error) {
	if strings.TrimSpace(os.Getenv(awesomePromptsURLEnv)) != "" || s.preferSourceURLDirect {
		return s.fetchRemoteAwesomePrompts(ctx)
	}
	return s.fetchConfigSources(ctx)
}
```

This keeps explicit direct JSON override behavior for tests/dev but production default uses config sources.

- [ ] **Step 3: Add prompt source loader implementation**

Create `internal/prompts/source_loader.go` with the following implementation. If compile errors reveal exact struct field names differ, adjust only those names and keep behavior identical.

```go
package prompts

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/catalogconfig"
	"gopkg.in/yaml.v3"
)

type promptTreeResponse struct {
	Tree []struct {
		Path string `json:"path"`
		Type string `json:"type"`
	} `json:"tree"`
}

func (s *Service) fetchConfigSources(ctx context.Context) ([]AwesomePrompt, error) {
	body, err := s.fetchBytes(ctx, s.configURL)
	if err != nil {
		return nil, fmt.Errorf("awesome_prompts: fetch config: %w", err)
	}
	cfg, err := catalogconfig.Parse(body)
	if err != nil {
		return nil, err
	}
	configRepo, ok := repoFromRawConfigURL(s.configURL)
	if !ok {
		configRepo = catalogconfig.GitHubRepo{Owner: "Chat2AnyLLM", Repo: "awesome-prompts", Branch: "master"}
	}
	var out []AwesomePrompt
	for _, source := range cfg.Sources {
		loaded, err := s.loadPromptSource(ctx, configRepo, source)
		if err != nil {
			return nil, err
		}
		out = append(out, loaded...)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("awesome_prompts: no prompts loaded from config sources")
	}
	return out, nil
}

func (s *Service) loadPromptSource(ctx context.Context, configRepo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]AwesomePrompt, error) {
	switch strings.ToLower(strings.TrimSpace(source.Type)) {
	case "local":
		return s.loadPromptDirectory(ctx, configRepo, source, catalogconfig.CleanSourcePath(source.Path))
	case "github":
		repo, ok := catalogconfig.ParseGitHubRepoURL(source.URL)
		if !ok {
			return nil, fmt.Errorf("awesome_prompts: source %q has invalid GitHub URL %q", source.Name, source.URL)
		}
		switch strings.ToLower(strings.TrimSpace(source.Format)) {
		case "csv":
			return s.loadPromptCSV(ctx, repo, source)
		case "md":
			return s.loadPromptMarkdown(ctx, repo, source)
		case "txt":
			return s.loadPromptText(ctx, repo, source)
		default:
			return nil, fmt.Errorf("awesome_prompts: source %q has unsupported format %q", source.Name, source.Format)
		}
	default:
		return nil, fmt.Errorf("awesome_prompts: source %q has unsupported type %q", source.Name, source.Type)
	}
}

func (s *Service) loadPromptDirectory(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource, prefix string) ([]AwesomePrompt, error) {
	paths, err := s.listRepoFiles(ctx, repo, prefix)
	if err != nil {
		return nil, fmt.Errorf("awesome_prompts: list source %q: %w", source.Name, err)
	}
	var out []AwesomePrompt
	for _, p := range paths {
		lower := strings.ToLower(p)
		if !(strings.HasSuffix(lower, ".yaml") || strings.HasSuffix(lower, ".yml") || strings.HasSuffix(lower, ".json") || strings.HasSuffix(lower, ".md") || strings.HasSuffix(lower, ".txt")) {
			continue
		}
		data, err := s.fetchBytes(ctx, rawURLForBase(s.repoRawBaseURL, repo, p))
		if err != nil {
			return nil, fmt.Errorf("awesome_prompts: fetch %s: %w", p, err)
		}
		prompt, ok := promptFromFile(source, repo, p, data)
		if ok {
			out = append(out, prompt)
		}
	}
	return out, nil
}

func (s *Service) loadPromptCSV(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]AwesomePrompt, error) {
	filePath := catalogconfig.CleanSourcePath(source.FilePath)
	data, err := s.fetchBytes(ctx, rawURLForBase(s.repoRawBaseURL, repo, filePath))
	if err != nil {
		return nil, fmt.Errorf("awesome_prompts: fetch csv source %q: %w", source.Name, err)
	}
	reader := csv.NewReader(strings.NewReader(string(data)))
	reader.FieldsPerRecord = -1
	rows, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("awesome_prompts: parse csv source %q: %w", source.Name, err)
	}
	if len(rows) == 0 {
		return nil, nil
	}
	header := map[string]int{}
	for i, h := range rows[0] {
		header[normalizeColumn(h)] = i
	}
	var out []AwesomePrompt
	for idx, row := range rows[1:] {
		content := csvValue(row, header, "prompt", "content", "text")
		if strings.TrimSpace(content) == "" {
			continue
		}
		title := csvValue(row, header, "title", "name")
		if strings.TrimSpace(title) == "" {
			title = fmt.Sprintf("%s %d", source.Name, idx+1)
		}
		slug := slugFromTitle(title)
		out = append(out, AwesomePrompt{
			Slug:        slug,
			Title:       title,
			Description: csvValue(row, header, "description"),
			Prompt:      content,
			Tags:        splitTags(csvValue(row, header, "tags")),
			Category:    csvValue(row, header, "category"),
			Author:      csvValue(row, header, "author"),
			SourceURL:   repo.BlobURL(filePath) + fmt.Sprintf("#row=%d", idx+2),
		})
	}
	return out, nil
}

func (s *Service) loadPromptMarkdown(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]AwesomePrompt, error) {
	filePath := catalogconfig.CleanSourcePath(source.FilePath)
	if filePath != "" {
		data, err := s.fetchBytes(ctx, rawURLForBase(s.repoRawBaseURL, repo, filePath))
		if err != nil {
			return nil, err
		}
		if p, ok := promptFromMarkdown(source, repo, filePath, data); ok {
			return []AwesomePrompt{p}, nil
		}
		return nil, nil
	}
	return s.loadPromptDirectory(ctx, repo, source, "")
}

func (s *Service) loadPromptText(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]AwesomePrompt, error) {
	filePath := catalogconfig.CleanSourcePath(source.FilePath)
	return s.loadPromptDirectory(ctx, repo, source, filePath)
}

func (s *Service) listRepoFiles(ctx context.Context, repo catalogconfig.GitHubRepo, prefix string) ([]string, error) {
	u := strings.TrimRight(s.githubAPIBaseURL, "/") + "/" + url.PathEscape(repo.Owner) + "/" + url.PathEscape(repo.Repo) + "/git/trees/" + url.PathEscape(repo.BranchOrDefault()) + "?recursive=1"
	data, err := s.fetchBytes(ctx, u)
	if err != nil {
		return nil, err
	}
	var parsed promptTreeResponse
	if err := json.Unmarshal(data, &parsed); err != nil {
		return nil, err
	}
	prefix = catalogconfig.CleanSourcePath(prefix)
	if prefix != "" {
		prefix += "/"
	}
	var paths []string
	for _, entry := range parsed.Tree {
		if entry.Type != "blob" {
			continue
		}
		if prefix == "" || strings.HasPrefix(entry.Path, prefix) {
			paths = append(paths, entry.Path)
		}
	}
	return paths, nil
}

func (s *Service) fetchBytes(ctx context.Context, u string) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return nil, fmt.Errorf("%s: %s", resp.Status, strings.TrimSpace(string(body)))
	}
	return io.ReadAll(io.LimitReader(resp.Body, 8<<20))
}

func promptFromFile(source catalogconfig.CatalogSource, repo catalogconfig.GitHubRepo, filePath string, data []byte) (AwesomePrompt, bool) {
	lower := strings.ToLower(filePath)
	switch {
	case strings.HasSuffix(lower, ".yaml") || strings.HasSuffix(lower, ".yml"):
		return promptFromStructured(source, repo, filePath, data, true)
	case strings.HasSuffix(lower, ".json"):
		return promptFromStructured(source, repo, filePath, data, false)
	case strings.HasSuffix(lower, ".md"):
		return promptFromMarkdown(source, repo, filePath, data)
	case strings.HasSuffix(lower, ".txt"):
		content := strings.TrimSpace(string(data))
		if content == "" {
			return AwesomePrompt{}, false
		}
		title := titleFromPath(filePath)
		return AwesomePrompt{Slug: slugFromTitle(title), Title: title, Prompt: content, Category: path.Base(path.Dir(filePath)), SourceURL: repo.BlobURL(filePath)}, true
	}
	return AwesomePrompt{}, false
}

func promptFromStructured(source catalogconfig.CatalogSource, repo catalogconfig.GitHubRepo, filePath string, data []byte, isYAML bool) (AwesomePrompt, bool) {
	var raw map[string]any
	var err error
	if isYAML {
		err = yaml.Unmarshal(data, &raw)
	} else {
		err = json.Unmarshal(data, &raw)
	}
	if err != nil {
		return AwesomePrompt{}, false
	}
	title := stringField(raw, "title", "name")
	if title == "" {
		title = titleFromPath(filePath)
	}
	content := stringField(raw, "prompt", "content", "text")
	if strings.TrimSpace(content) == "" {
		return AwesomePrompt{}, false
	}
	slug := stringField(raw, "slug")
	if slug == "" {
		slug = slugFromTitle(title)
	}
	return AwesomePrompt{Slug: slug, Title: title, Description: stringField(raw, "description"), Prompt: content, Tags: tagsField(raw, "tags"), Category: stringField(raw, "category"), Author: stringField(raw, "author"), SourceURL: repo.BlobURL(filePath)}, true
}

func promptFromMarkdown(source catalogconfig.CatalogSource, repo catalogconfig.GitHubRepo, filePath string, data []byte) (AwesomePrompt, bool) {
	content := strings.TrimSpace(string(data))
	if content == "" {
		return AwesomePrompt{}, false
	}
	title := titleFromPath(filePath)
	desc := ""
	if strings.HasPrefix(content, "---\n") {
		parts := strings.SplitN(content[4:], "\n---", 2)
		if len(parts) == 2 {
			var fm map[string]any
			if yaml.Unmarshal([]byte(parts[0]), &fm) == nil {
				if v := stringField(fm, "title", "name"); v != "" {
					title = v
				}
				desc = stringField(fm, "description")
			}
			content = strings.TrimSpace(strings.TrimPrefix(parts[1], "\n"))
		}
	}
	return AwesomePrompt{Slug: slugFromTitle(title), Title: title, Description: desc, Prompt: content, Category: path.Base(path.Dir(filePath)), SourceURL: repo.BlobURL(filePath)}, true
}

func rawURLForBase(base string, repo catalogconfig.GitHubRepo, filePath string) string {
	if strings.TrimRight(base, "/") == "https://raw.githubusercontent.com" {
		return repo.RawURL(filePath)
	}
	return strings.TrimRight(base, "/") + "/" + repo.Owner + "/" + repo.Repo + "/" + repo.BranchOrDefault() + "/" + catalogconfig.CleanSourcePath(filePath)
}

func repoFromRawConfigURL(raw string) (catalogconfig.GitHubRepo, bool) {
	u, err := url.Parse(raw)
	if err != nil {
		return catalogconfig.GitHubRepo{}, false
	}
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	if len(parts) >= 4 && strings.Contains(u.Host, "raw.githubusercontent.com") {
		return catalogconfig.GitHubRepo{Owner: parts[0], Repo: parts[1], Branch: parts[2]}, true
	}
	return catalogconfig.GitHubRepo{}, false
}

func normalizeColumn(s string) string { return strings.ToLower(strings.TrimSpace(s)) }

func csvValue(row []string, header map[string]int, names ...string) string {
	for _, name := range names {
		idx, ok := header[name]
		if ok && idx >= 0 && idx < len(row) {
			return strings.TrimSpace(row[idx])
		}
	}
	return ""
}

func stringField(raw map[string]any, names ...string) string {
	for _, name := range names {
		if v, ok := raw[name]; ok {
			if s, ok := v.(string); ok {
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}

func tagsField(raw map[string]any, name string) []string {
	v, ok := raw[name]
	if !ok {
		return nil
	}
	switch t := v.(type) {
	case []string:
		return t
	case []any:
		out := []string{}
		for _, item := range t {
			if s, ok := item.(string); ok && strings.TrimSpace(s) != "" {
				out = append(out, strings.TrimSpace(s))
			}
		}
		return out
	case string:
		return splitTags(t)
	}
	return nil
}

func splitTags(s string) []string {
	fields := strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == ';' || r == '|' })
	out := []string{}
	for _, f := range fields {
		if trimmed := strings.TrimSpace(f); trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

func titleFromPath(filePath string) string {
	base := path.Base(filePath)
	base = strings.TrimSuffix(base, path.Ext(base))
	base = strings.ReplaceAll(base, "_", " ")
	base = strings.ReplaceAll(base, "-", " ")
	return strings.TrimSpace(base)
}

func slugFromTitle(title string) string { return catalogconfig.SourceSlug(title) }
```

- [ ] **Step 4: Confirm `AwesomePrompt` supports `SourceURL`**

Inspect `internal/prompts/service.go` around `AwesomePrompt`. If it does not have `SourceURL`, add:

```go
	SourceURL string `json:"source_url,omitempty"`
```

If it already exists, do nothing.

- [ ] **Step 5: Run focused prompt tests**

Run:

```powershell
go test ./internal/prompts -run "TestFetchAwesomePrompts(LoadsConfigSources|DoesNotUseDistFallback)|TestSyncAll" -v
```

Expected: Existing dist-based tests may fail until updated in Task 5; the two new source-driven tests should pass after compile fixes.

---

## Task 5: Update prompt tests for no dist fallback

**Files:**
- Modify: `internal/prompts/service_test.go`

- [ ] **Step 1: Replace dist-based config test expectation**

Replace `TestSyncAllUsesAwesomePromptsConfigYaml` with this source-driven version:

```go
func TestSyncAllUsesAwesomePromptsConfigYaml(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			w.Header().Set("Content-Type", "text/yaml")
			_, _ = w.Write([]byte(`sources:
  - name: Local Prompts
    type: local
    path: prompts/
`))
		case "/repos/Chat2AnyLLM/awesome-prompts/git/trees/master":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"tree":[{"path":"prompts/configured.yaml","type":"blob","size":100}],"truncated":false}`))
		case "/Chat2AnyLLM/awesome-prompts/master/prompts/configured.yaml":
			_, _ = w.Write([]byte("slug: configured\ntitle: Configured Prompt\ndescription: Configured description\nprompt: Use configured source\ntags: [configured]\ncategory: repo-config\nauthor: tester\n"))
		case "/dist/prompts.json":
			t.Fatalf("dist/prompts.json should not be fetched")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	svc := NewService()
	svc.configURL = server.URL + "/config.yaml"
	svc.repoRawBaseURL = server.URL
	svc.githubAPIBaseURL = server.URL + "/repos"

	n, err := svc.SyncAll(ctx)
	if err != nil {
		t.Fatalf("SyncAll: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 prompt synced, got %d", n)
	}
	stored, err := svc.store.ListPrompts(ctx, "local_prompts", "")
	if err != nil {
		t.Fatalf("ListPrompts: %v", err)
	}
	if len(stored) != 1 || stored[0].Title != "Configured Prompt" {
		t.Fatalf("expected configured prompt, got %+v", stored)
	}
}
```

- [ ] **Step 2: Replace embedded fallback test**

Replace `TestSyncAll_storesAwesomePrompts_whenRemoteUnavailable` with:

```go
func TestSyncAllReturnsErrorWhenConfigUnavailable(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("CAM_CONFIG_DIR", dir)
	ctx := context.Background()
	svc := NewService()
	svc.configURL = "http://127.0.0.1:1/config.yaml"

	_, err := svc.SyncAll(ctx)
	if err == nil {
		t.Fatal("expected config fetch error")
	}
}
```

- [ ] **Step 3: Keep explicit direct JSON override tests**

Do not remove `TestSyncAllUsesExplicitAwesomePromptsURLOverride` or `TestSyncAll_mapsRemoteAwesomePromptsFields` if they pass with `preferSourceURLDirect = true`. They preserve explicit dev/test direct JSON behavior, not production dist fallback.

- [ ] **Step 4: Run prompt tests**

Run:

```powershell
go test ./internal/prompts -v
```

Expected: PASS.

---

## Task 6: Add MCP source aggregation tests

**Files:**
- Create: `internal/mcp/source_loader.go`
- Modify: `internal/mcp/catalog_loader.go`
- Modify: `internal/mcp/mcp_test.go`

- [ ] **Step 1: Replace remote config YAML dist test**

Replace `TestLoadRegistry_loadsRemoteConfigYamlCatalog` in `internal/mcp/mcp_test.go` with:

```go
func TestLoadRegistry_loadsRemoteConfigYamlSources(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			w.Header().Set("Content-Type", "text/yaml")
			_, _ = w.Write([]byte(`sources:
  - name: Local Servers
    type: local
    path: servers/
`))
		case "/repos/Chat2AnyLLM/awesome-mcp-servers/git/trees/main":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"tree":[{"path":"servers/config-mcp.json","type":"blob","size":100}],"truncated":false}`))
		case "/Chat2AnyLLM/awesome-mcp-servers/main/servers/config-mcp.json":
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(testSchema("config-mcp", "Loaded from config yaml sources"))
		case "/dist/servers.json":
			t.Fatalf("dist/servers.json should not be fetched")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	cfg := camconfig.CamConfig{
		Repositories: map[string]camconfig.RepoSources{
			"mcpServers": {Sources: []camconfig.RepoSource{{Type: "remote", URL: server.URL + "/config.yaml"}}},
		},
		Cache: camconfig.CacheConfig{Enabled: false},
	}

	registry, err := mcp.LoadRegistryFromConfig(cfg)
	if err != nil {
		t.Fatalf("LoadRegistryFromConfig err = %v", err)
	}
	if _, ok := registry.Get("config-mcp"); !ok {
		t.Fatal("expected config-mcp from config.yaml sources")
	}
}
```

- [ ] **Step 2: Add Markdown installable/skip test**

Append this test to `internal/mcp/mcp_test.go`:

```go
func TestLoadRegistry_loadsInstallableMarkdownEntriesOnly(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/config.yaml":
			_, _ = w.Write([]byte(`sources:
  - name: External Markdown
    type: github
    url: https://github.com/example/awesome-mcp
    format: md
    file_path: README.md
`))
		case "/example/awesome-mcp/main/README.md":
			_, _ = w.Write([]byte(`| Name | Description | Install |
| --- | --- | --- |
| Installable MCP | Has command | npx -y installable-mcp |
| Link Only MCP | No command | https://github.com/example/link-only |
`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	cfg := camconfig.CamConfig{
		Repositories: map[string]camconfig.RepoSources{
			"mcpServers": {Sources: []camconfig.RepoSource{{Type: "remote", URL: server.URL + "/config.yaml"}}},
		},
		Cache: camconfig.CacheConfig{Enabled: false},
	}
	mcp.SetCatalogSourceTestBases(t, server.URL+"/repos", server.URL)

	registry, err := mcp.LoadRegistryFromConfig(cfg)
	if err != nil {
		t.Fatalf("LoadRegistryFromConfig err = %v", err)
	}
	if _, ok := registry.Get("installable-mcp"); !ok {
		t.Fatal("expected installable markdown MCP")
	}
	if _, ok := registry.Get("link-only-mcp"); ok {
		t.Fatal("did not expect non-installable markdown MCP")
	}
}
```

This test requires a package-level test hook `SetCatalogSourceTestBases` in Task 7.

- [ ] **Step 3: Run MCP tests and verify they fail**

Run:

```powershell
go test ./internal/mcp -run "TestLoadRegistry_loadsRemoteConfigYamlSources|TestLoadRegistry_loadsInstallableMarkdownEntriesOnly" -v
```

Expected: FAIL because MCP source aggregation and test hook do not exist.

---

## Task 7: Implement MCP source aggregation

**Files:**
- Create: `internal/mcp/source_loader.go`
- Modify: `internal/mcp/catalog_loader.go`

- [ ] **Step 1: Add testable source base variables**

Create `internal/mcp/source_loader.go` with package-level variables and test hook first:

```go
package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"regexp"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/catalogconfig"
	"gopkg.in/yaml.v3"
)

var catalogGitHubAPIBaseURL = "https://api.github.com/repos"
var catalogRawBaseURL = "https://raw.githubusercontent.com"

func SetCatalogSourceTestBases(t *testing.T, apiBase, rawBase string) {
	t.Helper()
	oldAPI, oldRaw := catalogGitHubAPIBaseURL, catalogRawBaseURL
	catalogGitHubAPIBaseURL, catalogRawBaseURL = apiBase, rawBase
	t.Cleanup(func() {
		catalogGitHubAPIBaseURL, catalogRawBaseURL = oldAPI, oldRaw
	})
}
```

- [ ] **Step 2: Add MCP source loader implementation below the variables**

Append to `internal/mcp/source_loader.go`:

```go
type mcpTreeResponse struct {
	Tree []struct {
		Path string `json:"path"`
		Type string `json:"type"`
	} `json:"tree"`
}

func loadCatalogConfigSources(ctx context.Context, configURL string) ([]ServerSchema, error) {
	data, err := fetchCatalogBytes(ctx, configURL)
	if err != nil {
		return nil, fmt.Errorf("mcp: fetch catalog config %s: %w", configURL, err)
	}
	cfg, err := catalogconfig.Parse(data)
	if err != nil {
		return nil, fmt.Errorf("mcp: parse catalog config %s: %w", configURL, err)
	}
	configRepo, ok := repoFromMCPRawConfigURL(configURL)
	if !ok {
		configRepo = catalogconfig.GitHubRepo{Owner: "Chat2AnyLLM", Repo: "awesome-mcp-servers", Branch: "main"}
	}
	var out []ServerSchema
	for _, source := range cfg.Sources {
		loaded, err := loadMCPSource(ctx, configRepo, source)
		if err != nil {
			return nil, err
		}
		out = append(out, loaded...)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("mcp: no installable servers loaded from catalog config %s", configURL)
	}
	return out, nil
}

func loadMCPSource(ctx context.Context, configRepo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]ServerSchema, error) {
	switch strings.ToLower(strings.TrimSpace(source.Type)) {
	case "local":
		return loadMCPLocalSource(ctx, configRepo, source)
	case "github":
		if strings.ToLower(strings.TrimSpace(source.Format)) != "md" {
			return nil, fmt.Errorf("mcp: source %q has unsupported format %q", source.Name, source.Format)
		}
		repo, ok := catalogconfig.ParseGitHubRepoURL(source.URL)
		if !ok {
			return nil, fmt.Errorf("mcp: source %q has invalid GitHub URL %q", source.Name, source.URL)
		}
		return loadMCPMarkdownSource(ctx, repo, source)
	default:
		return nil, fmt.Errorf("mcp: source %q has unsupported type %q", source.Name, source.Type)
	}
}

func loadMCPLocalSource(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]ServerSchema, error) {
	prefix := catalogconfig.CleanSourcePath(source.Path)
	paths, err := listMCPRepoFiles(ctx, repo, prefix)
	if err != nil {
		return nil, fmt.Errorf("mcp: list source %q: %w", source.Name, err)
	}
	var out []ServerSchema
	for _, p := range paths {
		lower := strings.ToLower(p)
		if !(strings.HasSuffix(lower, ".json") || strings.HasSuffix(lower, ".yaml") || strings.HasSuffix(lower, ".yml")) {
			continue
		}
		data, err := fetchCatalogBytes(ctx, rawMCPURL(repo, p))
		if err != nil {
			return nil, fmt.Errorf("mcp: fetch local server %s: %w", p, err)
		}
		entries, err := parseMCPStructuredFile(data, lower)
		if err != nil {
			return nil, fmt.Errorf("mcp: parse local server %s: %w", p, err)
		}
		out = append(out, entries...)
	}
	return validateCatalog(out)
}

func loadMCPMarkdownSource(ctx context.Context, repo catalogconfig.GitHubRepo, source catalogconfig.CatalogSource) ([]ServerSchema, error) {
	filePath := catalogconfig.CleanSourcePath(source.FilePath)
	if filePath == "" {
		filePath = "README.md"
	}
	data, err := fetchCatalogBytes(ctx, rawMCPURL(repo, filePath))
	if err != nil {
		return nil, fmt.Errorf("mcp: fetch markdown source %q: %w", source.Name, err)
	}
	return parseMCPMarkdown(string(data), repo, filePath), nil
}

func parseMCPStructuredFile(data []byte, lowerPath string) ([]ServerSchema, error) {
	if strings.HasSuffix(lowerPath, ".json") {
		return parseCatalogJSON(data)
	}
	var schema ServerSchema
	if err := yaml.Unmarshal(data, &schema); err == nil && schema.Name != "" {
		return []ServerSchema{schema}, nil
	}
	var wrapped struct {
		Servers []ServerSchema `yaml:"servers"`
	}
	if err := yaml.Unmarshal(data, &wrapped); err != nil {
		return nil, err
	}
	return wrapped.Servers, nil
}

var commandRe = regexp.MustCompile(`(?i)(npx\s+(?:-y\s+)?[a-z0-9@._/-]+|uvx\s+[a-z0-9@._/-]+|docker\s+run\s+[^|` + "`" + `]+|python\s+-m\s+[a-z0-9@._/-]+)`)

func parseMCPMarkdown(content string, repo catalogconfig.GitHubRepo, filePath string) []ServerSchema {
	lines := strings.Split(strings.ReplaceAll(content, "\r\n", "\n"), "\n")
	var out []ServerSchema
	for i := 0; i < len(lines)-2; i++ {
		if !strings.Contains(lines[i], "|") || !strings.Contains(lines[i+1], "---") {
			continue
		}
		header := splitMarkdownRow(lines[i])
		nameIdx, descIdx, installIdx := markdownColumnIndexes(header)
		if nameIdx < 0 || installIdx < 0 {
			continue
		}
		for j := i + 2; j < len(lines); j++ {
			line := strings.TrimSpace(lines[j])
			if line == "" || !strings.Contains(line, "|") {
				break
			}
			cells := splitMarkdownRow(line)
			if nameIdx >= len(cells) || installIdx >= len(cells) {
				continue
			}
			name := cleanMarkdownCell(cells[nameIdx])
			desc := ""
			if descIdx >= 0 && descIdx < len(cells) {
				desc = cleanMarkdownCell(cells[descIdx])
			}
			install := cleanMarkdownCell(cells[installIdx])
			if schema, ok := schemaFromMarkdownInstall(name, desc, install, repo.BlobURL(filePath)); ok {
				out = append(out, schema)
			}
		}
	}
	return out
}

func markdownColumnIndexes(header []string) (nameIdx, descIdx, installIdx int) {
	nameIdx, descIdx, installIdx = -1, -1, -1
	for i, h := range header {
		clean := strings.ToLower(cleanMarkdownCell(h))
		switch {
		case nameIdx == -1 && (clean == "name" || strings.Contains(clean, "server")):
			nameIdx = i
		case descIdx == -1 && strings.Contains(clean, "description"):
			descIdx = i
		case installIdx == -1 && (strings.Contains(clean, "install") || strings.Contains(clean, "command")):
			installIdx = i
		}
	}
	if nameIdx == -1 && len(header) > 0 {
		nameIdx = 0
	}
	return nameIdx, descIdx, installIdx
}

func schemaFromMarkdownInstall(name, desc, install, sourceURL string) (ServerSchema, bool) {
	name = strings.TrimSpace(name)
	if name == "" || strings.EqualFold(name, "name") {
		return ServerSchema{}, false
	}
	match := commandRe.FindString(install)
	if match == "" {
		return ServerSchema{}, false
	}
	fields := strings.Fields(match)
	if len(fields) < 2 {
		return ServerSchema{}, false
	}
	key := catalogconfig.SourceSlug(name)
	entry := InstallationEntry{Type: "custom", Command: fields[0], Args: fields[1:]}
	if fields[0] == "npx" {
		entry.Type = "npm"
	} else if fields[0] == "uvx" {
		entry.Type = "uvx"
	} else if fields[0] == "docker" {
		entry.Type = "docker"
	} else if fields[0] == "python" {
		entry.Type = "python"
	}
	if desc == "" {
		desc = "MCP server from markdown catalog"
	}
	return ServerSchema{
		Name:        key,
		DisplayName: name,
		Description: desc,
		Homepage:    sourceURL,
		Installations: map[string]InstallationEntry{
			entry.Type: entry,
		},
	}, true
}

func splitMarkdownRow(line string) []string {
	line = strings.TrimSpace(strings.Trim(line, "|"))
	parts := strings.Split(line, "|")
	for i := range parts {
		parts[i] = strings.TrimSpace(parts[i])
	}
	return parts
}

var markdownLinkRe = regexp.MustCompile(`\[([^\]]+)\]\(([^)]*)\)`)
var markdownCodeRe = regexp.MustCompile("`([^`]*)`")

func cleanMarkdownCell(cell string) string {
	cell = markdownLinkRe.ReplaceAllString(cell, "$1")
	cell = markdownCodeRe.ReplaceAllString(cell, "$1")
	cell = strings.ReplaceAll(cell, "<br>", " ")
	cell = strings.ReplaceAll(cell, "<br/>", " ")
	cell = strings.ReplaceAll(cell, "<br />", " ")
	return strings.Join(strings.Fields(strings.Trim(cell, " *_")), " ")
}

func listMCPRepoFiles(ctx context.Context, repo catalogconfig.GitHubRepo, prefix string) ([]string, error) {
	u := strings.TrimRight(catalogGitHubAPIBaseURL, "/") + "/" + url.PathEscape(repo.Owner) + "/" + url.PathEscape(repo.Repo) + "/git/trees/" + url.PathEscape(repo.BranchOrDefault()) + "?recursive=1"
	data, err := fetchCatalogBytes(ctx, u)
	if err != nil {
		return nil, err
	}
	var parsed mcpTreeResponse
	if err := json.Unmarshal(data, &parsed); err != nil {
		return nil, err
	}
	prefix = catalogconfig.CleanSourcePath(prefix)
	if prefix != "" {
		prefix += "/"
	}
	var paths []string
	for _, entry := range parsed.Tree {
		if entry.Type == "blob" && (prefix == "" || strings.HasPrefix(entry.Path, prefix)) {
			paths = append(paths, entry.Path)
		}
	}
	return paths, nil
}

func fetchCatalogBytes(ctx context.Context, u string) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return nil, fmt.Errorf("%s: %s", resp.Status, strings.TrimSpace(string(body)))
	}
	return io.ReadAll(io.LimitReader(resp.Body, 8<<20))
}

func rawMCPURL(repo catalogconfig.GitHubRepo, filePath string) string {
	if strings.TrimRight(catalogRawBaseURL, "/") == "https://raw.githubusercontent.com" {
		return repo.RawURL(filePath)
	}
	return strings.TrimRight(catalogRawBaseURL, "/") + "/" + repo.Owner + "/" + repo.Repo + "/" + repo.BranchOrDefault() + "/" + catalogconfig.CleanSourcePath(filePath)
}

func repoFromMCPRawConfigURL(raw string) (catalogconfig.GitHubRepo, bool) {
	u, err := url.Parse(raw)
	if err != nil {
		return catalogconfig.GitHubRepo{}, false
	}
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	if len(parts) >= 4 && strings.Contains(u.Host, "raw.githubusercontent.com") {
		return catalogconfig.GitHubRepo{Owner: parts[0], Repo: parts[1], Branch: parts[2]}, true
	}
	return catalogconfig.GitHubRepo{}, false
}

func _keepPathImportUsed() { _ = path.Clean }
```

If `path` is unused after implementation, remove the import and `_keepPathImportUsed`.

- [ ] **Step 3: Modify remote YAML handling in `catalog_loader.go`**

In `internal/mcp/catalog_loader.go`, replace the YAML branch in `loadRemoteCatalog`:

```go
	url := sourceURL
	if strings.HasSuffix(strings.ToLower(sourceURL), ".yaml") || strings.HasSuffix(strings.ToLower(sourceURL), ".yml") {
		resolved, err := resolveCatalogConfigURL(sourceURL, "servers", cache)
		if err != nil {
			return nil, err
		}
		url = resolved
	}
```

with:

```go
	if strings.HasSuffix(strings.ToLower(sourceURL), ".yaml") || strings.HasSuffix(strings.ToLower(sourceURL), ".yml") {
		return loadCatalogConfigSources(context.Background(), sourceURL)
	}
	url := sourceURL
```

Leave direct remote JSON loading and caching behavior unchanged. `resolveCatalogConfigURL` may remain unused for now; remove it only if Go reports unused functions are allowed but unused imports are not. Remove imports only if they become unused.

- [ ] **Step 4: Run MCP focused tests**

Run:

```powershell
go test ./internal/mcp -run "TestLoadRegistry_loadsRemoteConfigYamlSources|TestLoadRegistry_loadsInstallableMarkdownEntriesOnly|TestLoadRegistry_keepsLocalEntryWhenRemoteDuplicatesName" -v
```

Expected: PASS after compile fixes.

---

## Task 8: Fix compile issues and update docs wording

**Files:**
- Modify: `internal/prompts/source_loader.go`
- Modify: `internal/prompts/service.go`
- Modify: `internal/mcp/source_loader.go`
- Modify: `internal/mcp/catalog_loader.go`
- Modify: `README.md`

- [ ] **Step 1: Run package tests to expose compile issues**

Run:

```powershell
go test ./internal/catalogconfig ./internal/prompts ./internal/mcp ./internal/desktop
```

Expected before fixes: possible compile errors around imports, `AwesomePrompt` fields, or helper naming. Fix only compile/runtime issues, not unrelated code.

- [ ] **Step 2: Update README source wording**

In `README.md`, replace the MCP line around the config section that says MCP defaults to a remote dist artifact with wording like:

```markdown
- Prompt and MCP catalog sources default to their upstream `config.yaml` files; CAM reads the `sources:` entries and fetches the configured upstream files directly instead of consuming generated `dist/*.json` artifacts.
```

Also update the key feature wording if it says the MCP catalog is bundled/generated. Keep wording concise.

- [ ] **Step 3: Run focused package tests again**

Run:

```powershell
go test ./internal/catalogconfig ./internal/prompts ./internal/mcp ./internal/desktop
```

Expected: PASS.

---

## Task 9: Full verification according to project instructions

**Files:**
- No source edits unless tests expose defects.

- [ ] **Step 1: Run all Go tests one package at a time**

Project instructions say to find all tests and run them one by one. For Go packages, run:

```powershell
go list ./...
```

Then for each returned package, run:

```powershell
go test <package>
```

Expected: PASS for all packages. If a package fails for an unrelated existing issue, capture exact output and report it.

- [ ] **Step 2: Run frontend tests if frontend code or API DTO behavior changed**

If the implementation changed frontend DTO assumptions or UI-visible data, run:

```powershell
npm --prefix frontend test
```

Expected: PASS. If no frontend code changed and backend DTOs remain stable, note that frontend tests were skipped because no frontend code changed.

- [ ] **Step 3: Run reinstall commands required by project instructions after code changes**

Use Bash syntax for the project reinstall commands:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
```

Expected: install completes successfully. If it fails due to environment prerequisites, capture exact output.

- [ ] **Step 4: Check git diff**

Run:

```powershell
git diff --stat
git diff -- internal/catalogconfig internal/prompts internal/mcp README.md docs/superpowers
```

Expected: Diff only contains planned changes.

- [ ] **Step 5: Do not commit without approval**

The project and global instructions say to ask approval before commits and never add `Co-Authored-By`. Stop and report status. If the user asks to commit later, use James Zhu as author/committer and do not include co-author lines.

---

## Self-review checklist

- Spec coverage:
  - Shared `sources:` parser: Task 1.
  - GitHub/source helpers: Task 2.
  - Prompt source loading for local/csv/md/txt: Tasks 3-5.
  - MCP source loading for local structured files and installable markdown: Tasks 6-7.
  - No dist fallback: Tasks 3, 5, 6, 7.
  - Docs and tests: Tasks 8-9.
- Placeholder scan: no TBD/TODO placeholders are present.
- Type consistency: `catalogconfig.CatalogSource`, `catalogconfig.GitHubRepo`, `SourceSlug`, `CleanSourcePath`, and source loader function names are defined before use.
