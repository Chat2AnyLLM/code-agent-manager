package metadata

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

var githubBaseURL = "https://api.github.com"
var githubRawBaseURL = "https://raw.githubusercontent.com"

type onlineSkillSearchResult struct {
	Repo        string
	Name        string
	Path        string
	Description string
	Stars       int
}

type ghCodeSearchItem struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	Repository struct {
		FullName        string `json:"full_name"`
		StargazersCount int    `json:"stargazers_count"`
	} `json:"repository"`
}

const onlineSearchPageSize = 100

// RefreshOnlineSkillSearch mirrors the `gh skill search` GitHub Code Search
// behavior and persists matching skill manifests into the metadata cache.
func (svc *Service) RefreshOnlineSkillSearch(ctx context.Context, query string, limit int) (int, error) {
	query = strings.TrimSpace(query)
	if query == "" {
		return 0, nil
	}
	if limit <= 0 {
		limit = 50
	}
	results, err := searchOnlineSkills(ctx, query, limit)
	if err != nil {
		return 0, err
	}
	items := make([]Item, 0, len(results))
	targetApps := strings.Join(defaultTargetApps("skill"), ",")
	for _, result := range results {
		owner, repo, ok := strings.Cut(result.Repo, "/")
		if !ok || owner == "" || repo == "" {
			continue
		}
		itemPath := filepath.ToSlash(filepath.Dir(result.Path))
		items = append(items, Item{
			Kind:        "skill",
			Name:        result.Name,
			Description: result.Description,
			RepoOwner:   owner,
			RepoName:    repo,
			RepoBranch:  "main",
			ItemPath:    itemPath,
			InstallKey:  fmt.Sprintf("%s/%s:%s", owner, repo, result.Name),
			TargetApps:  targetApps,
		})
	}
	return svc.store.UpsertItems(ctx, items)
}

func searchOnlineSkills(ctx context.Context, query string, limit int) ([]onlineSkillSearchResult, error) {
	ownerScope := ""
	pathTerm := strings.ReplaceAll(query, " ", "-")
	queries := []string{
		fmt.Sprintf("filename:SKILL.md path:%s", pathTerm),
		fmt.Sprintf("filename:SKILL.md %s", query),
	}
	if couldBeGHOwner(query) {
		queries = append(queries, fmt.Sprintf("filename:SKILL.md user:%s", query))
	}
	if strings.Contains(query, " ") {
		queries = append(queries, fmt.Sprintf("filename:SKILL.md %s%s", pathTerm, ownerScope))
	}

	client := &http.Client{Timeout: 15 * time.Second}
	authHeader := resolveGitHubAuth()

	type queryResult struct {
		items []ghCodeSearchItem
		err   error
	}
	resultCh := make(chan queryResult, len(queries))
	var wg sync.WaitGroup
	for _, q := range queries {
		wg.Add(1)
		go func(searchQuery string) {
			defer wg.Done()
			items, err := executeGHSearch(ctx, client, searchQuery, limit, authHeader)
			resultCh <- queryResult{items: items, err: err}
		}(q)
	}
	wg.Wait()
	close(resultCh)

	var allItems []ghCodeSearchItem
	for result := range resultCh {
		if result.err != nil {
			return nil, result.err
		}
		allItems = append(allItems, result.items...)
	}

	type key struct{ repo, name string }
	seen := make(map[key]bool)
	results := make([]onlineSkillSearchResult, 0, limit)
	for _, item := range allItems {
		name := filepath.Base(filepath.Dir(item.Path))
		if name == "." || name == "" {
			name = strings.TrimSuffix(item.Name, filepath.Ext(item.Name))
		}
		if !isValidSkillResult(item.Path, name) {
			continue
		}
		k := key{item.Repository.FullName, name}
		if seen[k] {
			continue
		}
		seen[k] = true
		results = append(results, onlineSkillSearchResult{
			Repo:  item.Repository.FullName,
			Name:  name,
			Path:  item.Path,
			Stars: item.Repository.StargazersCount,
		})
	}
	enrichOnlineSkillDescriptions(ctx, client, authHeader, results)
	rankOnlineSkillResults(results, query)
	if len(results) > limit {
		results = results[:limit]
	}
	return results, nil
}

func executeGHSearch(ctx context.Context, client *http.Client, query string, limit int, authHeader string) ([]ghCodeSearchItem, error) {
	perPage := onlineSearchPageSize
	if limit > perPage {
		perPage = limit
	}
	apiURL := fmt.Sprintf("%s/search/code?q=%s&per_page=%d", strings.TrimRight(githubBaseURL, "/"), url.QueryEscape(query), perPage)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "code-agent-manager")
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("GitHub API request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusTooManyRequests {
		return nil, fmt.Errorf("GitHub API rate limit exceeded, set GITHUB_TOKEN for higher limits")
	}
	if resp.StatusCode == http.StatusForbidden {
		if resp.Header.Get("X-Ratelimit-Remaining") == "0" || resp.Header.Get("Retry-After") != "" {
			return nil, fmt.Errorf("GitHub API rate limit exceeded, set GITHUB_TOKEN for higher limits")
		}
		return nil, nil
	}
	if resp.StatusCode == http.StatusUnauthorized {
		return nil, fmt.Errorf("GitHub API auth failed, set GITHUB_TOKEN or GH_TOKEN")
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("GitHub API returned HTTP %d", resp.StatusCode)
	}
	var result struct {
		Items []ghCodeSearchItem `json:"items"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to parse GitHub response: %w", err)
	}
	return result.Items, nil
}

func enrichOnlineSkillDescriptions(ctx context.Context, client *http.Client, authHeader string, results []onlineSkillSearchResult) {
	const maxWorkers = 10
	sem := make(chan struct{}, maxWorkers)
	var wg sync.WaitGroup
	for i := range results {
		owner, repo, ok := strings.Cut(results[i].Repo, "/")
		if !ok {
			continue
		}
		wg.Add(1)
		go func(idx int, owner, repo, path string) {
			defer wg.Done()
			select {
			case sem <- struct{}{}:
				defer func() { <-sem }()
			case <-ctx.Done():
				return
			}
			rawURL := fmt.Sprintf("%s/%s/%s/main/%s", strings.TrimRight(githubRawBaseURL, "/"), owner, repo, path)
			req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
			if err != nil {
				return
			}
			req.Header.Set("User-Agent", "code-agent-manager")
			if authHeader != "" {
				req.Header.Set("Authorization", authHeader)
			}
			resp, err := client.Do(req)
			if err != nil || resp.StatusCode != http.StatusOK {
				if resp != nil {
					resp.Body.Close()
				}
				return
			}
			body, err := io.ReadAll(io.LimitReader(resp.Body, 4096))
			resp.Body.Close()
			if err != nil {
				return
			}
			_, desc, ok := parseFrontmatter(string(body))
			if ok && desc != "" {
				results[idx].Description = desc
			}
		}(i, owner, repo, results[i].Path)
	}
	wg.Wait()
}

func resolveGitHubAuth() string {
	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		return "token " + token
	}
	if token := os.Getenv("GH_TOKEN"); token != "" {
		return "token " + token
	}
	out, err := exec.Command("gh", "auth", "token").Output()
	if err == nil {
		if token := strings.TrimSpace(string(out)); token != "" {
			return "token " + token
		}
	}
	return ""
}

func couldBeGHOwner(s string) bool {
	if len(s) == 0 || len(s) > 39 {
		return false
	}
	for i, c := range s {
		switch {
		case c >= 'a' && c <= 'z', c >= 'A' && c <= 'Z', c >= '0' && c <= '9':
			continue
		case c == '-':
			if i == 0 || i == len(s)-1 {
				return false
			}
		default:
			return false
		}
	}
	return true
}

var safeSkillNamePattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._\- ]*$`)

func isValidSkillName(name string) bool {
	if len(name) == 0 || len(name) > 64 {
		return false
	}
	if strings.Contains(name, "/") || strings.Contains(name, "..") {
		return false
	}
	return safeSkillNamePattern.MatchString(name)
}

func isValidSkillPath(relPath string) bool {
	relPath = filepath.ToSlash(relPath)
	parts := strings.Split(relPath, "/")
	if len(parts) < 2 || parts[len(parts)-1] != "SKILL.md" {
		return false
	}
	for _, p := range parts {
		if strings.HasPrefix(p, ".") {
			return false
		}
	}
	skillName := parts[len(parts)-2]
	if !isValidSkillName(skillName) {
		return false
	}
	if len(parts) == 3 && parts[0] == "skills" {
		return true
	}
	if len(parts) == 4 && parts[0] == "skills" {
		return true
	}
	for i, part := range parts {
		if part == "skills" && i < len(parts)-2 {
			return true
		}
	}
	return len(parts) == 2 && skillName != "skills" && skillName != "plugins"
}

func isValidSkillResult(path, skillName string) bool {
	return isValidSkillName(skillName) && (path == "" || isValidSkillPath(path))
}

func rankOnlineSkillResults(results []onlineSkillSearchResult, query string) {
	sort.SliceStable(results, func(i, j int) bool {
		si := onlineSkillRelevanceScore(results[i], query)
		sj := onlineSkillRelevanceScore(results[j], query)
		return si > sj
	})
}

func onlineSkillRelevanceScore(result onlineSkillSearchResult, query string) int {
	term := strings.ToLower(query)
	termHyphen := strings.ReplaceAll(term, " ", "-")
	nameLower := strings.ToLower(result.Name)
	score := 0
	if nameLower == term || nameLower == termHyphen {
		score += 3000
	} else if strings.Contains(nameLower, term) || strings.Contains(nameLower, termHyphen) {
		score += 1000
	}
	if strings.Contains(strings.ToLower(result.Description), term) {
		score += 100
	}
	if result.Stars > 0 {
		score += int(math.Sqrt(float64(result.Stars)) * 30)
	}
	return score
}
