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
