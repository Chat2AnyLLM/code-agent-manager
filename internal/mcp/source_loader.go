package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/catalogconfig"
	"gopkg.in/yaml.v3"
)

var catalogGitHubAPIBaseURL = "https://api.github.com/repos"
var catalogRawBaseURL = "https://raw.githubusercontent.com"

// SetCatalogSourceTestBases overrides upstream GitHub endpoints for tests.
func SetCatalogSourceTestBases(t *testing.T, apiBase, rawBase string) {
	t.Helper()
	oldAPI, oldRaw := catalogGitHubAPIBaseURL, catalogRawBaseURL
	catalogGitHubAPIBaseURL, catalogRawBaseURL = apiBase, rawBase
	t.Cleanup(func() {
		catalogGitHubAPIBaseURL, catalogRawBaseURL = oldAPI, oldRaw
	})
}

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
	entries := parseMCPMarkdown(string(data), repo, filePath)
	return validateCatalog(entries)
}

func parseMCPStructuredFile(data []byte, lowerPath string) ([]ServerSchema, error) {
	if strings.HasSuffix(lowerPath, ".json") {
		if entries, err := parseCatalogJSON(data); err == nil {
			return entries, nil
		}
		var schema ServerSchema
		if err := json.Unmarshal(data, &schema); err != nil {
			return nil, err
		}
		return validateCatalog([]ServerSchema{schema})
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
	if len(parts) >= 4 {
		if strings.Contains(u.Host, "raw.githubusercontent.com") {
			return catalogconfig.GitHubRepo{Owner: parts[0], Repo: parts[1], Branch: parts[2]}, true
		}
		if parts[len(parts)-1] == "config.yaml" || parts[len(parts)-1] == "config.yml" {
			return catalogconfig.GitHubRepo{Owner: parts[len(parts)-4], Repo: parts[len(parts)-3], Branch: parts[len(parts)-2]}, true
		}
	}
	return catalogconfig.GitHubRepo{}, false
}
