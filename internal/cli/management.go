package cli

import (
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

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/camconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/entities"
	"github.com/chat2anyllm/code-agent-manager/internal/fetching"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/repoconfig"
)

// managementCommand returns the prompt/skill/agent/plugin command tree with
// four subcommands modeled after `gh skill`: search, list, update, install.
func (a *App) managementCommand(group, alias string, state *globalState) *cobra.Command {
	kind := groupKind(group)
	aliases := []string{}
	if alias != "" {
		aliases = strings.Split(alias, ",")
	}
	cmd := &cobra.Command{
		Use:     group,
		Aliases: aliases,
		Short:   "Manage " + group + " configurations",
	}
	cmd.AddCommand(entitySearchCommand(kind))
	cmd.AddCommand(entityListCommand(kind))
	cmd.AddCommand(entityUpdateCommand(kind))
	cmd.AddCommand(entityInstallCommand(kind))
	cmd.AddCommand(entityUninstallCommand(kind))
	return cmd
}

func groupKind(group string) entities.Kind {
	switch group {
	case "instruction":
		return entities.KindInstruction
	case "prompt":
		return entities.KindPrompt
	case "skill":
		return entities.KindSkill
	case "agent":
		return entities.KindAgent
	case "plugin":
		return entities.KindPlugin
	}
	return entities.Kind(group)
}

// ============================================================================
// search — 3-tier search: GitHub → skill_repos.json → config.yaml remotes
// ============================================================================

func entitySearchCommand(kind entities.Kind) *cobra.Command {
	var (
		owner string
		limit int
		local bool
	)
	cmd := &cobra.Command{
		Use:   "search <query>",
		Short: "Search for " + string(kind) + "s across GitHub",
		Long: "Search across all public GitHub repositories for " + string(kind) + `s matching a keyword.

Uses the GitHub Code Search API to find ` + defaultManifestName(kind) + ` files whose
name or description matches the query term.

Search results are validated to ensure they follow the skill standard
(valid directory conventions, proper SKILL.md frontmatter with name and
description).

Results are presented in three tiers:
  1. GitHub Code Search (primary discovery)
  2. Configured skill repositories (skill_repos.json)
  3. Remote sources (config.yaml)

Also searches the local store and configured repositories for matches.

Use --owner to scope GitHub results to a specific GitHub user or organization.
Use --local to skip the GitHub search and only search local sources.

Set GITHUB_TOKEN or GH_TOKEN for higher API rate limits.`,
		Example: "  cam " + string(kind) + " search terraform\n" +
			"  cam " + string(kind) + " search code-review\n" +
			"  cam " + string(kind) + " search terraform --owner hashicorp\n" +
			"  cam " + string(kind) + " search terraform --limit 5\n" +
			"  cam " + string(kind) + " search terraform --local",
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			query := strings.ToLower(strings.Join(args, " "))
			out := cmd.OutOrStdout()

			// -----------------------------------------------------------
			// Tier 1: GitHub Code Search (skip with --local).
			// -----------------------------------------------------------
			var ghResults []ghSearchResult
			if !local {
				var err error
				ghResults, err = searchGitHub(kind, strings.Join(args, " "), owner, limit)
				if err != nil {
					fmt.Fprintf(out, "GitHub search: %v\n\n", err)
				}

				// Validate: filter to only valid skills.
				if kind == entities.KindSkill {
					ghResults = filterValidSkillResults(ghResults)
				}

				// Rank by relevance.
				rankGHResults(ghResults, strings.Join(args, " "))
			}

			// -----------------------------------------------------------
			// Tier 2: Local store search.
			// -----------------------------------------------------------
			store := entities.NewStore(kind)
			storeItems, _ := store.All()
			var storeMatches []entities.Entity
			for _, e := range storeItems {
				if matchesQuery(e, query) {
					storeMatches = append(storeMatches, e)
				}
			}

			// -----------------------------------------------------------
			// Tier 3: Configured repos — split into local (skill_repos.json)
			// and remote (config.yaml) sources.
			// -----------------------------------------------------------
			localRepoMatches, remoteRepoMatches := searchConfiguredReposTiered(kind, query)

			// -----------------------------------------------------------
			// Render: show tiers in order.
			// -----------------------------------------------------------
			totalMatches := len(ghResults) + len(storeMatches) + len(localRepoMatches) + len(remoteRepoMatches)
			if totalMatches == 0 {
				fmt.Fprintf(out, "No %ss found matching %q\n", kind, query)
				return nil
			}

			// Tier 1: GitHub results.
			if len(ghResults) > 0 {
				if isInteractive(os.Stdin) {
					fmt.Fprintf(out, "Showing %d %s(s) matching %q\n", len(ghResults), kind, query)
					return promptSearchInstall(ghResults, kind, out)
				}

				fmt.Fprintf(out, "Showing %d %s(s) matching %q\n\n", len(ghResults), kind, query)
				fmt.Fprintf(out, "  %-45s %-40s %-10s\n", strings.ToUpper(string(kind)), "REPOSITORY", "STARS")
				fmt.Fprintf(out, "  %-45s %-40s %-10s\n",
					strings.Repeat("─", 45), strings.Repeat("─", 40),
					strings.Repeat("─", 10))
				for _, r := range ghResults {
					id := r.ID
					if id == "" {
						id = r.Name
					}
					stars := formatStars(r.Stars)
					desc := r.Description
					if len(desc) > 120 {
						desc = desc[:117] + "..."
					}
					fmt.Fprintf(out, "  %-45s %-40s %s\n", id, r.Repo, stars)
					if desc != "" {
						fmt.Fprintf(out, "  %s\n", desc)
					}
				}
				fmt.Fprintf(out, "\nInstall with: cam %s install <repo> --from-github --app <agent>\n", kind)
			}

			// Tier 2: Local store matches.
			if len(storeMatches) > 0 {
				if len(ghResults) > 0 {
					fmt.Fprintln(out)
				}
				fmt.Fprintf(out, "Local %ss matching %q (%d):\n\n", kind, query, len(storeMatches))
				for _, e := range storeMatches {
					desc := e.Description
					if desc == "" {
						desc = "(no description)"
					}
					repo := ""
					if e.Repo != nil {
						repo = fmt.Sprintf("  [%s/%s]", e.Repo.Owner, e.Repo.Name)
					}
					fmt.Fprintf(out, "  %-35s %s%s\n", e.Name, desc, repo)
				}
			}

			// Tier 3a: Configured repos from skill_repos.json.
			if len(localRepoMatches) > 0 {
				if len(ghResults) > 0 || len(storeMatches) > 0 {
					fmt.Fprintln(out)
				}
				sort.Slice(localRepoMatches, func(i, j int) bool {
					return localRepoMatches[i].Key < localRepoMatches[j].Key
				})
				fmt.Fprintf(out, "Configured repos (skill_repos.json) matching %q (%d):\n\n", query, len(localRepoMatches))
				for _, r := range localRepoMatches {
					desc := r.Description
					if desc == "" {
						desc = "(no description)"
					}
					fmt.Fprintf(out, "  %-40s %s/%s@%s  %s\n", r.Key, r.Owner, r.Name, r.Branch, desc)
				}
			}

			// Tier 3b: Remote repos from config.yaml.
			if len(remoteRepoMatches) > 0 {
				if len(ghResults) > 0 || len(storeMatches) > 0 || len(localRepoMatches) > 0 {
					fmt.Fprintln(out)
				}
				sort.Slice(remoteRepoMatches, func(i, j int) bool {
					return remoteRepoMatches[i].Key < remoteRepoMatches[j].Key
				})
				fmt.Fprintf(out, "Remote repos (config.yaml) matching %q (%d):\n\n", query, len(remoteRepoMatches))
				for _, r := range remoteRepoMatches {
					desc := r.Description
					if desc == "" {
						desc = "(no description)"
					}
					fmt.Fprintf(out, "  %-40s %s/%s@%s  %s\n", r.Key, r.Owner, r.Name, r.Branch, desc)
				}
			}

			return nil
		},
	}
	cmd.Flags().StringVar(&owner, "owner", "", "Filter GitHub results to a specific owner/org")
	cmd.Flags().IntVarP(&limit, "limit", "L", 15, "Maximum number of GitHub results")
	cmd.Flags().BoolVar(&local, "local", false, "Only search local store and configured repos (skip GitHub)")
	return cmd
}

type repoSearchResult struct {
	Key         string
	Owner       string
	Name        string
	Branch      string
	Description string
}

// ghSearchResult holds a single GitHub Code Search hit.
type ghSearchResult struct {
	Repo        string
	Name        string // simple skill name (used for install)
	ID          string // scope/name identifier for display (like gh skill search)
	Path        string
	Description string
	Stars       int
}

// computeSkillID derives the display identifier from a SKILL.md path,
// matching gh skill search format.  It strips "skills/" prefix and the
// manifest filename, keeping scope/name structure.
//
//	"skills/foo/SKILL.md"           → "foo"
//	"scope/foo/SKILL.md"            → "scope/foo"
//	"prefix/skills/foo/SKILL.md"    → "foo"
//	"foo/SKILL.md"                  → "foo"
func computeSkillID(path string) string {
	path = filepath.ToSlash(path)
	// Remove the manifest filename.
	dir := filepath.Dir(path)
	dir = filepath.ToSlash(dir)

	parts := strings.Split(dir, "/")
	// Remove leading "skills" directory if present.
	for i, p := range parts {
		if p == "skills" {
			parts = parts[i+1:]
			break
		}
	}
	if len(parts) == 0 {
		return ""
	}
	return strings.Join(parts, "/")
}

// formatStars formats a star count for display, like gh skill search:
//
//	0    → ""
//	65   → "★ 65"
//	1500 → "★ 1.5k"
//	40800 → "★ 40.8k"
func formatStars(n int) string {
	if n <= 0 {
		return ""
	}
	if n < 1000 {
		return fmt.Sprintf("★ %d", n)
	}
	k := float64(n) / 1000.0
	if k >= 10 {
		return fmt.Sprintf("★ %.1fk", k)
	}
	return fmt.Sprintf("★ %.1fk", k)
}

// searchGitHub queries the GitHub Code Search API for manifest files matching
// the query, using parallel search strategies mirroring gh skill search:
//
//   - content match: filename:<manifest> <query>
//   - path match: filename:<manifest> path:<hyphenated-query>
//   - owner match: filename:<manifest> user:<query> (when query looks like a GitHub user)
//   - hyphen match: filename:<manifest> <hyphenated-query> (when query has spaces)
func searchGitHub(kind entities.Kind, query, owner string, limit int) ([]ghSearchResult, error) {
	manifest := defaultManifestName(kind)

	ownerScope := ""
	if owner != "" {
		ownerScope = " user:" + owner
	}

	contentQ := fmt.Sprintf("filename:%s %s%s", manifest, query, ownerScope)
	pathTerm := strings.ReplaceAll(query, " ", "-")
	pathQ := fmt.Sprintf("filename:%s path:%s%s", manifest, pathTerm, ownerScope)

	client := &http.Client{Timeout: 15 * time.Second}
	authHeader := resolveGitHubAuth()

	var (
		contentItems []ghCodeSearchItem
		contentErr   error
		pathItems    []ghCodeSearchItem
		pathErr      error
		ownerItems   []ghCodeSearchItem
		hyphenItems  []ghCodeSearchItem
	)

	hasSpaces := strings.Contains(query, " ")

	var wg sync.WaitGroup

	// Path search (parallel).
	wg.Add(1)
	go func() {
		defer wg.Done()
		pathItems, pathErr = executeGHSearch(client, pathQ, limit, authHeader)
	}()

	// Owner search: when no --owner flag and query looks like a GitHub user.
	if owner == "" && couldBeGHOwner(query) {
		ownerQ := fmt.Sprintf("filename:%s user:%s", manifest, query)
		wg.Add(1)
		go func() {
			defer wg.Done()
			ownerItems, _ = executeGHSearch(client, ownerQ, limit, authHeader)
		}()
	}

	// Hyphen search: when query has spaces (e.g. "mcp apps" → "mcp-apps").
	if hasSpaces {
		hyphenQ := fmt.Sprintf("filename:%s %s%s", manifest, pathTerm, ownerScope)
		wg.Add(1)
		go func() {
			defer wg.Done()
			hyphenItems, _ = executeGHSearch(client, hyphenQ, limit, authHeader)
		}()
	}

	// Content search runs on the main goroutine.
	contentItems, contentErr = executeGHSearch(client, contentQ, limit, authHeader)
	wg.Wait()

	if contentErr != nil {
		return nil, contentErr
	}

	// Merge: path > hyphen > owner > content (priority order).
	var allItems []ghCodeSearchItem
	if pathErr == nil {
		allItems = append(allItems, pathItems...)
	}
	if hasSpaces {
		allItems = append(allItems, hyphenItems...)
	}
	allItems = append(allItems, ownerItems...)
	allItems = append(allItems, contentItems...)

	// Deduplicate by (repo, skill-name).
	type key struct{ repo, name string }
	seen := make(map[key]bool)
	var results []ghSearchResult
	for _, item := range allItems {
		skillID := computeSkillID(item.Path)
		skillName := filepath.Base(filepath.Dir(item.Path))
		if skillName == "." || skillName == "" {
			skillName = strings.TrimSuffix(item.Name, filepath.Ext(item.Name))
		}
		if skillID == "" {
			skillID = skillName
		}
		k := key{item.Repository.FullName, skillName}
		if seen[k] {
			continue
		}
		seen[k] = true
		results = append(results, ghSearchResult{
			Repo:  item.Repository.FullName,
			Name:  skillName,
			ID:    skillID,
			Path:  item.Path,
			Stars: item.Repository.StargazersCount,
		})
		if len(results) >= limit*3 { // over-fetch for filtering
			break
		}
	}

	// Fetch descriptions from SKILL.md frontmatter concurrently.
	if authHeader != "" {
		enrichGHDescriptions(client, authHeader, results)
	}

	return results, nil
}

// couldBeGHOwner returns true if s looks like a valid GitHub username/org.
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

type ghCodeSearchItem struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	SHA        string `json:"sha"`
	Repository struct {
		FullName        string `json:"full_name"`
		StargazersCount int    `json:"stargazers_count"`
	} `json:"repository"`
}

const (
	// searchPageSize is the number of raw results to request from the
	// GitHub Search API per call (max allowed by the API).
	searchPageSize = 100
)

func executeGHSearch(client *http.Client, query string, limit int, authHeader string) ([]ghCodeSearchItem, error) {
	// Always request a full page of results from the API, regardless of
	// the display limit.  More raw results → better filtering/ranking.
	perPage := searchPageSize
	if limit > perPage {
		perPage = limit
	}
	apiURL := fmt.Sprintf("https://api.github.com/search/code?q=%s&per_page=%d",
		url.QueryEscape(query), perPage)

	req, err := http.NewRequest("GET", apiURL, nil)
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

	// Distinguish true rate limits from other 403s.
	if resp.StatusCode == 429 {
		return nil, fmt.Errorf("GitHub API rate limit exceeded, set GITHUB_TOKEN for higher limits")
	}
	if resp.StatusCode == 403 {
		// Check rate-limit headers: x-ratelimit-remaining: 0 or retry-after.
		if resp.Header.Get("X-Ratelimit-Remaining") == "0" || resp.Header.Get("Retry-After") != "" {
			return nil, fmt.Errorf("GitHub API rate limit exceeded, set GITHUB_TOKEN for higher limits")
		}
		// Secondary rate limit or other 403 — return empty, not fatal.
		return nil, nil
	}
	if resp.StatusCode == 401 {
		return nil, fmt.Errorf("GitHub API auth failed, set GITHUB_TOKEN or GH_TOKEN")
	}
	if resp.StatusCode != 200 {
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

// enrichGHDescriptions fetches SKILL.md blob content to extract the frontmatter
// description field concurrently with bounded parallelism, and also fetches
// star counts for unique repos (mirroring gh skill search enrichment).
func enrichGHDescriptions(client *http.Client, authHeader string, results []ghSearchResult) {
	const maxWorkers = 10
	sem := make(chan struct{}, maxWorkers)

	// Fetch descriptions concurrently.
	var descWG sync.WaitGroup
	for i := range results {
		parts := strings.SplitN(results[i].Repo, "/", 2)
		if len(parts) != 2 {
			continue
		}
		descWG.Add(1)
		go func(idx int, owner, repo, path string) {
			defer descWG.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			rawURL := fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/main/%s",
				owner, repo, path)
			req, err := http.NewRequest("GET", rawURL, nil)
			if err != nil {
				return
			}
			req.Header.Set("User-Agent", "code-agent-manager")
			if authHeader != "" {
				req.Header.Set("Authorization", authHeader)
			}
			resp, err := client.Do(req)
			if err != nil || resp.StatusCode != 200 {
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
			desc := extractFrontmatterDescription(string(body))
			if desc != "" {
				results[idx].Description = desc
			}
		}(i, parts[0], parts[1], results[i].Path)
	}

	// Fetch star counts for unique repos concurrently.
	type repoKey struct{ owner, name string }
	repoStars := make(map[string]int)
	var starsMu sync.Mutex
	seen := make(map[string]bool)

	var starsWG sync.WaitGroup
	for _, r := range results {
		if seen[r.Repo] {
			continue
		}
		seen[r.Repo] = true
		parts := strings.SplitN(r.Repo, "/", 2)
		if len(parts) != 2 {
			continue
		}
		starsWG.Add(1)
		go func(fullName, owner, repo string) {
			defer starsWG.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s", owner, repo)
			req, err := http.NewRequest("GET", apiURL, nil)
			if err != nil {
				return
			}
			req.Header.Set("Accept", "application/vnd.github.v3+json")
			req.Header.Set("User-Agent", "code-agent-manager")
			if authHeader != "" {
				req.Header.Set("Authorization", authHeader)
			}
			resp, err := client.Do(req)
			if err != nil || resp.StatusCode != 200 {
				if resp != nil {
					resp.Body.Close()
				}
				return
			}
			var info struct {
				StargazersCount int `json:"stargazers_count"`
			}
			if err := json.NewDecoder(resp.Body).Decode(&info); err == nil {
				starsMu.Lock()
				repoStars[fullName] = info.StargazersCount
				starsMu.Unlock()
			}
			resp.Body.Close()
		}(r.Repo, parts[0], parts[1])
	}

	descWG.Wait()
	starsWG.Wait()

	// Apply star counts to results.
	for i := range results {
		if stars, ok := repoStars[results[i].Repo]; ok && stars > 0 {
			results[i].Stars = stars
		}
	}
}

// extractFrontmatterDescription extracts the description from YAML frontmatter.
// Handles the simple case: a line starting with "description:" between --- delimiters.
func extractFrontmatterDescription(content string) string {
	lines := strings.Split(content, "\n")
	inFrontmatter := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "---" {
			if !inFrontmatter {
				inFrontmatter = true
				continue
			}
			break // end of frontmatter
		}
		if !inFrontmatter {
			continue
		}
		if strings.HasPrefix(trimmed, "description:") {
			desc := strings.TrimPrefix(trimmed, "description:")
			desc = strings.TrimSpace(desc)
			// Remove surrounding quotes.
			desc = strings.Trim(desc, `"'`)
			return desc
		}
	}
	return ""
}

// resolveGitHubAuth returns a GitHub API auth header by checking, in order:
//  1. GITHUB_TOKEN env var
//  2. GH_TOKEN env var
//  3. `gh auth token` command output (uses gh CLI's stored credentials)
//
// Returns empty string if no token is found.
func resolveGitHubAuth() string {
	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		return "token " + token
	}
	if token := os.Getenv("GH_TOKEN"); token != "" {
		return "token " + token
	}
	// Fall back to gh CLI's auth system.
	out, err := exec.Command("gh", "auth", "token").Output()
	if err == nil {
		token := strings.TrimSpace(string(out))
		if token != "" {
			return "token " + token
		}
	}
	return ""
}

func matchesQuery(e entities.Entity, query string) bool {
	if strings.Contains(strings.ToLower(e.Name), query) {
		return true
	}
	if strings.Contains(strings.ToLower(e.Description), query) {
		return true
	}
	for _, tag := range e.Tags {
		if strings.Contains(strings.ToLower(tag), query) {
			return true
		}
	}
	if e.Repo != nil {
		repoStr := strings.ToLower(e.Repo.Owner + "/" + e.Repo.Name)
		if strings.Contains(repoStr, query) {
			return true
		}
	}
	return false
}

// filterValidSkillResults filters GitHub search results to only those that
// follow the skill standard: valid path convention + valid skill name.
func filterValidSkillResults(results []ghSearchResult) []ghSearchResult {
	var valid []ghSearchResult
	for _, r := range results {
		if isValidSkillResult(r.Path, r.Name) {
			valid = append(valid, r)
		}
	}
	return valid
}

// rankGHResults sorts GitHub search results by relevance score (highest first).
func rankGHResults(results []ghSearchResult, query string) {
	sort.SliceStable(results, func(i, j int) bool {
		si := relevanceScore(results[i].Name, results[i].Description, results[i].Repo, results[i].Stars, query)
		sj := relevanceScore(results[j].Name, results[j].Description, results[j].Repo, results[j].Stars, query)
		return si > sj
	})
}

// searchConfiguredReposTiered searches configured repos and returns results
// split into two tiers: local (from skill_repos.json) and remote (from config.yaml).
func searchConfiguredReposTiered(kind entities.Kind, query string) (localMatches, remoteMatches []repoSearchResult) {
	// Identify which keys come from local sources vs remote sources.
	localKeys := identifyLocalRepoKeys(kind)

	repos, err := repoconfig.LoadEnabled(kind)
	if err != nil {
		return nil, nil
	}

	for key, r := range repos {
		rOwner := r.EffectiveOwner()
		name := r.EffectiveName()
		if rOwner == "" || name == "" {
			continue
		}
		keyLower := strings.ToLower(key)
		ownerLower := strings.ToLower(rOwner)
		nameLower := strings.ToLower(name)
		descLower := strings.ToLower(r.Description)
		if strings.Contains(keyLower, query) ||
			strings.Contains(ownerLower, query) ||
			strings.Contains(nameLower, query) ||
			strings.Contains(descLower, query) {
			match := repoSearchResult{
				Key:         key,
				Owner:       rOwner,
				Name:        name,
				Branch:      r.EffectiveBranch(),
				Description: r.Description,
			}
			if localKeys[key] {
				localMatches = append(localMatches, match)
			} else {
				remoteMatches = append(remoteMatches, match)
			}
		}
	}
	return localMatches, remoteMatches
}

// identifyLocalRepoKeys returns the set of repo keys that come from local
// sources (skill_repos.json files), as opposed to remote/bundled sources.
func identifyLocalRepoKeys(kind entities.Kind) map[string]bool {
	keys := make(map[string]bool)

	cfg, err := camconfig.Load("")
	if err != nil {
		return keys
	}
	repoKey := string(kind) + "s"
	src, ok := cfg.Repositories[repoKey]
	if !ok {
		return keys
	}
	for _, s := range src.Sources {
		if s.Type != "local" || s.Path == "" {
			continue
		}
		local, err := repoconfig.LoadLocalSource(s.Path)
		if err != nil || local == nil {
			continue
		}
		for k := range local {
			keys[k] = true
		}
	}
	return keys
}

// ============================================================================
// Skill validation — verify results follow the skill standard
// ============================================================================

// skillNamePattern matches the agentskills.io name spec:
// 1-64 chars, lowercase alphanumeric + hyphens, no leading/trailing/consecutive hyphens.
var skillNamePattern = regexp.MustCompile(`^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`)

// safeSkillNamePattern matches names safe for filesystem use.
// Allows letters (any case), numbers, hyphens, underscores, dots.
var safeSkillNamePattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._\- ]*$`)

// isValidSkillName checks whether a skill name matches the filesystem-safe pattern
// (1-64 chars, no slashes, no path traversal).
func isValidSkillName(name string) bool {
	if len(name) == 0 || len(name) > 64 {
		return false
	}
	if strings.Contains(name, "/") || strings.Contains(name, "..") {
		return false
	}
	return safeSkillNamePattern.MatchString(name)
}

// isSpecCompliantName checks if a skill name matches the strict agentskills.io spec:
// lowercase alphanumeric + hyphens, no consecutive hyphens.
func isSpecCompliantName(name string) bool {
	if len(name) == 0 || len(name) > 64 {
		return false
	}
	if strings.Contains(name, "--") {
		return false
	}
	return skillNamePattern.MatchString(name)
}

// isValidSkillPath checks whether a SKILL.md path matches a known skill convention.
// Recognized patterns (mirroring gh skill search / agentskills.io):
//
//	skills/<name>/SKILL.md               → standard flat
//	skills/<scope>/<name>/SKILL.md        → namespaced
//	<prefix>/skills/<name>/SKILL.md       → deeply nested
//	<prefix>/skills/<scope>/<name>/SKILL.md → deeply nested namespaced
//	<name>/SKILL.md                       → root-level
//
// Paths with hidden (dot-prefixed) segments are rejected unless under a known
// agent config directory pattern.
func isValidSkillPath(relPath string) bool {
	relPath = filepath.ToSlash(relPath)
	parts := strings.Split(relPath, "/")
	if len(parts) < 2 {
		return false
	}
	// Must end with SKILL.md.
	if parts[len(parts)-1] != "SKILL.md" {
		return false
	}
	// Reject hidden segments (dot-prefixed).
	for _, p := range parts {
		if strings.HasPrefix(p, ".") {
			return false
		}
	}
	skillName := parts[len(parts)-2]
	if !isValidSkillName(skillName) {
		return false
	}
	// skills/name/SKILL.md (3 parts)
	if len(parts) == 3 && parts[0] == "skills" {
		return true
	}
	// skills/scope/name/SKILL.md (4 parts)
	if len(parts) == 4 && parts[0] == "skills" {
		return true
	}
	// Deeply nested: any/prefix/skills/name/SKILL.md
	for i, part := range parts {
		if part == "skills" && i < len(parts)-2 {
			return true
		}
	}
	// root-level: name/SKILL.md (2 parts, name is not "skills" or "plugins")
	if len(parts) == 2 && skillName != "skills" && skillName != "plugins" {
		return true
	}
	return false
}

// isValidSkillFrontmatter checks that SKILL.md content has valid YAML
// frontmatter with the required "name" and "description" fields.
func isValidSkillFrontmatter(content string) bool {
	lines := strings.Split(content, "\n")
	inFrontmatter := false
	hasName := false
	hasDesc := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "---" {
			if !inFrontmatter {
				inFrontmatter = true
				continue
			}
			break
		}
		if !inFrontmatter {
			continue
		}
		if strings.HasPrefix(trimmed, "name:") {
			val := strings.TrimSpace(strings.TrimPrefix(trimmed, "name:"))
			val = strings.Trim(val, `"'`)
			if val != "" {
				hasName = true
			}
		}
		if strings.HasPrefix(trimmed, "description:") {
			val := strings.TrimSpace(strings.TrimPrefix(trimmed, "description:"))
			val = strings.Trim(val, `"'`)
			if val != "" {
				hasDesc = true
			}
		}
	}
	return hasName && hasDesc
}

// isValidSkillResult checks whether a GitHub search result is a valid skill:
// valid path convention + valid skill name.
func isValidSkillResult(path, skillName string) bool {
	if !isValidSkillName(skillName) {
		return false
	}
	if path != "" && !isValidSkillPath(path) {
		return false
	}
	return true
}

// ============================================================================
// Relevance scoring — rank results by multi-signal score (mirroring gh skill search)
// ============================================================================

// relevanceScore computes a numeric ranking score for a search result.
// Higher scores rank first. Signals (in priority order):
//   - Exact skill name match (3000 points)
//   - Partial skill name match (1000 points)
//   - Description contains query (100 points)
//   - Repository stars (sqrt bonus, ~2400 for 6k stars)
func relevanceScore(name, description, repo string, stars int, query string) int {
	term := strings.ToLower(query)
	termHyphen := strings.ReplaceAll(term, " ", "-")
	score := 0

	nameLower := strings.ToLower(name)
	if nameLower == term || nameLower == termHyphen {
		score += 3_000
	} else if strings.Contains(nameLower, term) || strings.Contains(nameLower, termHyphen) {
		score += 1_000
	}

	if strings.Contains(strings.ToLower(description), term) {
		score += 100
	}

	if stars > 0 {
		score += int(math.Sqrt(float64(stars)) * 30)
	}

	return score
}

// ============================================================================
// list — show what's installed across code agents
// ============================================================================

func entityListCommand(kind entities.Kind) *cobra.Command {
	var (
		showRepos bool
		appFilter string
	)
	cmd := &cobra.Command{
		Use:     "list",
		Aliases: []string{"ls"},
		Short:   "List installed " + string(kind) + "s across code agents",
		Long: "List " + string(kind) + `s installed across all supported code agents.

Scans the installation directories of all supported agents (claude, codex,
gemini, copilot, cursor, and many more) and reports what is installed.

Use --app to filter to a specific agent.
Use --repos to also display configured repository sources.`,
		Example: "  cam " + string(kind) + " list\n" +
			"  cam " + string(kind) + " list --app claude\n" +
			"  cam " + string(kind) + " list --repos",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()

			apps := entities.AppPathsFor(kind)
			if apps == nil {
				fmt.Fprintf(out, "No app paths configured for %ss\n", kind)
				return nil
			}

			appsToScan := apps
			if appFilter != "" {
				if dest, ok := apps[appFilter]; ok {
					appsToScan = map[string]string{appFilter: dest}
				} else {
					return fmt.Errorf("unknown app %q (supported: %s)",
						appFilter, strings.Join(entities.SupportedApps(kind), ", "))
				}
			}

			type installedEntry struct {
				name string
				app  string
				path string
			}
			var installed []installedEntry
			anyFound := false

			sortedApps := make([]string, 0, len(appsToScan))
			for app := range appsToScan {
				sortedApps = append(sortedApps, app)
			}
			sort.Strings(sortedApps)

			// Track Claude-specific plugin listing separately.
			claudeHandled := false
			claudePluginTotal := 0

			for _, app := range sortedApps {
				dest := appsToScan[app]
				resolved := expandPath(dest)

				// For plugins, use Claude-specific metadata-based listing
				// when installed_plugins.json exists (matches `claude plugin list`).
				if kind == entities.KindPlugin && isClaudePluginApp(app, dest) {
					pCount, _ := listClaudePlugins(out, resolved)
					if pCount > 0 {
						anyFound = true
						claudePluginTotal += pCount
					}
					claudeHandled = true
					continue
				}

				switch kind {
				case entities.KindPrompt, entities.KindInstruction:
					if _, err := os.Stat(resolved); err == nil {
						installed = append(installed, installedEntry{
							name: filepath.Base(resolved),
							app:  app,
							path: resolved,
						})
						anyFound = true
					}
				default:
					entries, err := os.ReadDir(resolved)
					if err != nil {
						continue
					}
					for _, e := range entries {
						if !e.IsDir() {
							continue
						}
						installed = append(installed, installedEntry{
							name: e.Name(),
							app:  app,
							path: filepath.Join(resolved, e.Name()),
						})
						anyFound = true
					}
				}
			}

			if !anyFound {
				fmt.Fprintf(out, "No %ss installed across agents\n", kind)
			} else {
				grouped := make(map[string][]installedEntry)
				for _, entry := range installed {
					grouped[entry.app] = append(grouped[entry.app], entry)
				}
				total := claudePluginTotal
				for _, app := range sortedApps {
					items := grouped[app]
					if len(items) == 0 {
						continue
					}
					total += len(items)
					dest := appsToScan[app]
					resolved := expandPath(dest)
					fmt.Fprintf(out, "%s (%s) — %d %s(s):\n",
						app, resolved, len(items), kind)
					for _, item := range items {
						fmt.Fprintf(out, "  %s\n", item.name)
					}
					fmt.Fprintln(out)
				}
				agentCount := len(grouped)
				if claudeHandled {
					agentCount++
				}
				fmt.Fprintf(out, "\nTotal: %d %s(s) across %d agent(s)\n", total, kind, agentCount)
			}

			if showRepos {
				fmt.Fprintln(out)
				repos, err := repoconfig.LoadAll(kind)
				if err != nil {
					fmt.Fprintf(out, "Could not load repos: %v\n", err)
				} else if len(repos) == 0 {
					fmt.Fprintf(out, "No %s repositories configured\n", kind)
				} else {
					fmt.Fprintf(out, "Configured repositories (%d):\n\n", len(repos))
					sortedKeys := make([]string, 0, len(repos))
					for k := range repos {
						sortedKeys = append(sortedKeys, k)
					}
					sort.Strings(sortedKeys)
					for _, key := range sortedKeys {
						r := repos[key]
						enabled := "enabled"
						if !r.IsEnabled() {
							enabled = "disabled"
						}
						fmt.Fprintf(out, "  %-45s %s/%s@%s  [%s]\n",
							key, r.EffectiveOwner(), r.EffectiveName(), r.EffectiveBranch(), enabled)
					}
				}
			}

			return nil
		},
	}
	cmd.Flags().BoolVar(&showRepos, "repos", false, "Also show configured repository sources")
	cmd.Flags().StringVarP(&appFilter, "app", "a", "", "Filter by target agent (e.g. claude, codex, gemini)")
	return cmd
}

func expandPath(path string) string {
	home := os.Getenv("HOME")
	if home == "" {
		home = pathutil.Home()
	}
	return os.ExpandEnv(strings.ReplaceAll(path, "~", home))
}

// ============================================================================
// update — fetch/update from configured repositories
// ============================================================================

func entityUpdateCommand(kind entities.Kind) *cobra.Command {
	var (
		owner  string
		repo   string
		branch string
		path   string
		all    bool
		force  bool
		dryRun bool
	)
	cmd := &cobra.Command{
		Use:   "update",
		Short: "Fetch/update " + string(kind) + "s from configured repositories",
		Long: "Fetch " + string(kind) + `s from GitHub repositories and update the local store.

By default, fetches from all configured repositories (bundled defaults,
local repo configs, and remote sources from config.yaml).

Use --owner/--repo to fetch from a single specific repository instead.
Use --all to update without prompting (non-interactive mode).
Use --force to re-download even if already up to date.
Use --dry-run to check for updates without modifying files.`,
		Example: "  cam " + string(kind) + " update\n" +
			"  cam " + string(kind) + " update --owner anthropics --repo skills\n" +
			"  cam " + string(kind) + " update --all\n" +
			"  cam " + string(kind) + " update --dry-run",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()

			if dryRun {
				fmt.Fprintf(out, "[dry-run] Checking %s repositories...\n\n", kind)
			}

			if owner != "" && repo != "" {
				if dryRun {
					fmt.Fprintf(out, "[dry-run] Would fetch from %s/%s@%s\n", owner, repo, branch)
					return nil
				}
				return fetchSingleRepo(kind, owner, repo, branch, path, out)
			}

			if dryRun {
				return dryRunAllRepos(kind, out)
			}

			return fetchAllRepos(cmd, kind, out)
		},
	}
	cmd.Flags().StringVarP(&owner, "owner", "o", "", "GitHub owner (for single-repo fetch)")
	cmd.Flags().StringVarP(&repo, "repo", "r", "", "GitHub repo (for single-repo fetch)")
	cmd.Flags().StringVarP(&branch, "branch", "b", "main", "Branch")
	cmd.Flags().StringVarP(&path, "path", "p", "", "Sub-directory within the repo")
	cmd.Flags().BoolVar(&all, "all", false, "Update all without prompting")
	cmd.Flags().BoolVar(&force, "force", false, "Re-download even if already up to date")
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Report available updates without modifying files")
	return cmd
}

func dryRunAllRepos(kind entities.Kind, out io.Writer) error {
	repos, err := repoconfig.LoadEnabled(kind)
	if err != nil {
		return err
	}
	if len(repos) == 0 {
		fmt.Fprintf(out, "[dry-run] No enabled %s repositories configured\n", kind)
		return nil
	}
	fmt.Fprintf(out, "[dry-run] Would fetch from %d repositories:\n\n", len(repos))
	for key, r := range repos {
		rOwner := r.EffectiveOwner()
		name := r.EffectiveName()
		if rOwner == "" || name == "" {
			continue
		}
		fmt.Fprintf(out, "  %s/%s@%s  (%s)\n", rOwner, name, r.EffectiveBranch(), key)
	}
	return nil
}

func fetchAllRepos(cmd *cobra.Command, kind entities.Kind, out io.Writer) error {
	repos, err := repoconfig.LoadEnabled(kind)
	if err != nil {
		return err
	}
	if len(repos) == 0 {
		fmt.Fprintf(out, "No enabled %s repositories configured\n", kind)
		return nil
	}

	totalAdded := 0
	for key, r := range repos {
		rOwner := r.EffectiveOwner()
		name := r.EffectiveName()
		branch := r.EffectiveBranch()
		subPath := r.SubPath(kind)

		if rOwner == "" || name == "" {
			fmt.Fprintf(out, "  Skipping %s: missing owner or repo name\n", key)
			continue
		}

		fmt.Fprintf(out, "  Fetching from %s/%s@%s ...\n", rOwner, name, branch)
		added, err := fetchSingleRepoCount(kind, rOwner, name, branch, subPath)
		if err != nil {
			fmt.Fprintf(out, "    Error: %v\n", err)
			continue
		}
		fmt.Fprintf(out, "    Found %d %s(s)\n", added, kind)
		totalAdded += added
	}

	fmt.Fprintf(out, "\nTotal: fetched %d %s(s) from %d repos\n", totalAdded, kind, len(repos))
	return nil
}

func fetchSingleRepo(kind entities.Kind, owner, repo, branch, path string, out io.Writer) error {
	added, err := fetchSingleRepoCount(kind, owner, repo, branch, path)
	if err != nil {
		return err
	}
	fmt.Fprintf(out, "Fetched %d %ss from %s/%s\n", added, kind, owner, repo)
	return nil
}

func fetchSingleRepoCount(kind entities.Kind, owner, repo, branch, path string) (int, error) {
	client := fetching.New()
	dest := filepath.Join(os.TempDir(), fmt.Sprintf("cam-fetch-%s-%s", owner, repo))
	_ = os.RemoveAll(dest)
	root, err := client.DownloadGitHubZip(owner, repo, branch, dest)
	if err != nil {
		return 0, err
	}
	scanRoot := root
	if path != "" {
		paths := strings.Split(path, "|")
		if len(paths) == 1 {
			scanRoot = filepath.Join(root, path)
		} else {
			scanRoot = root
		}
	}
	store := entities.NewStore(kind)
	added := 0
	fileTarget := defaultManifestName(kind)
	err = filepath.WalkDir(scanRoot, func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		if filepath.Base(p) != fileTarget {
			return nil
		}
		data, err := os.ReadFile(p)
		if err != nil {
			return err
		}
		name := filepath.Base(filepath.Dir(p))
		entity := entities.Entity{
			Name:    name,
			Content: string(data),
			Path:    p,
			Repo:    &entities.RepoRef{Owner: owner, Name: repo, Branch: branch, Path: path},
		}
		if err := store.Put(entity); err != nil {
			return err
		}
		added++
		return nil
	})
	if err != nil {
		return added, err
	}
	return added, nil
}

func defaultManifestName(kind entities.Kind) string {
	switch kind {
	case entities.KindSkill:
		return "SKILL.md"
	case entities.KindAgent:
		return "AGENT.md"
	case entities.KindPlugin:
		return "plugin.json"
	}
	return "README.md"
}

// ============================================================================
// install — install into a code agent (from store, GitHub, or local directory)
// ============================================================================

func entityInstallCommand(kind entities.Kind) *cobra.Command {
	var (
		app       string
		all       bool
		force     bool
		fromLocal bool
		fromGH    bool
	)
	cmd := &cobra.Command{
		Use:   "install [NAME | OWNER/REPO | PATH]",
		Short: "Install " + string(kind) + "(s) into a code agent",
		Long: "Install " + string(kind) + `(s) into a target code agent.

Three install modes:

  1. From local store (default):
     Install an item previously fetched via 'update'.
       cam ` + string(kind) + ` install my-skill --app claude

  2. From a GitHub repository (--from-github):
     Download and install directly from a GitHub repo.
       cam ` + string(kind) + ` install owner/repo --from-github

  3. From a local directory (--from-local):
     Discover and install items from a local directory.
       cam ` + string(kind) + ` install ./my-skills --from-local

When --app is omitted in an interactive terminal, you will be prompted
to select a target agent.

Supported agents: ` + strings.Join(entities.SupportedApps(kind), ", ") + `.

Use --all to install every discovered item.
Use --force to overwrite existing installations.`,
		Example: "  # Install from local store\n" +
			"  cam " + string(kind) + " install my-skill --app claude\n" +
			"  cam " + string(kind) + " install --all --app claude\n\n" +
			"  # Install from GitHub repository\n" +
			"  cam " + string(kind) + " install anthropics/skills --from-github\n\n" +
			"  # Install from local directory (prompts for target agent)\n" +
			"  cam " + string(kind) + " install ./my-skills-dir --from-local\n" +
			"  cam " + string(kind) + " install ~/repos/skills my-skill --from-local\n" +
			"  cam " + string(kind) + " install ~/repos/skills --from-local --all",
		Args: cobra.MaximumNArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()

			if fromLocal && fromGH {
				return fmt.Errorf("--from-local and --from-github cannot be used together")
			}

			// resolveApps returns the target agent(s). When --app is given,
			// returns that single app. Otherwise prompts interactively
			// with multi-select so the user can install to several agents.
			resolveApps := func() ([]string, error) {
				if app != "" {
					return []string{app}, nil
				}
				if !isInteractive(cmd.InOrStdin()) {
					return nil, fmt.Errorf("--app is required (one of: %s)", strings.Join(entities.SupportedApps(kind), ", "))
				}
				return promptSelectApp(kind)
			}

			if fromLocal {
				if len(args) == 0 {
					return fmt.Errorf("--from-local requires a directory path argument")
				}
				skillName := ""
				if len(args) >= 2 {
					skillName = args[1]
				}
				return installFromLocal(kind, args[0], skillName, all, force, out, resolveApps, cmd.InOrStdin())
			}

			if fromGH {
				if len(args) == 0 {
					return fmt.Errorf("--from-github requires an owner/repo argument")
				}
				skillName := ""
				if len(args) >= 2 {
					skillName = args[1]
				}
				return installFromGitHub(kind, args[0], skillName, all, force, out, resolveApps, cmd.InOrStdin())
			}

			// Default: install from local store.
			store := entities.NewStore(kind)

			if all {
				if len(args) > 0 {
					return fmt.Errorf("cannot use --all with a name argument")
				}
				apps, err := resolveApps()
				if err != nil {
					return err
				}
				for _, a := range apps {
					if err := installAllFromStore(store, kind, a, force, out); err != nil {
						return err
					}
				}
				return nil
			}

			if len(args) == 0 {
				return fmt.Errorf("NAME is required (or use --all, --from-local, or --from-github)")
			}

			apps, err := resolveApps()
			if err != nil {
				return err
			}
			for _, a := range apps {
				if err := installOneFromStore(store, kind, a, args[0], force, out); err != nil {
					return err
				}
			}
			return nil
		},
	}
	cmd.Flags().StringVarP(&app, "app", "a", "", "Target agent (e.g. claude, codex, gemini)")
	cmd.Flags().BoolVar(&all, "all", false, "Install all discovered items")
	cmd.Flags().BoolVarP(&force, "force", "f", false, "Overwrite existing installations")
	cmd.Flags().BoolVar(&fromLocal, "from-local", false, "Install from a local directory path")
	cmd.Flags().BoolVar(&fromGH, "from-github", false, "Install from a GitHub repository (owner/repo)")
	return cmd
}

// --- install from store ----------------------------------------------------

func installOneFromStore(store *entities.Store, kind entities.Kind, app, name string, force bool, out io.Writer) error {
	e, err := store.Get(name)
	if err != nil {
		return err
	}
	if !force && isAlreadyInstalled(e.Name, kind, app) {
		fmt.Fprintf(out, "%s already installed for %s (use --force to overwrite)\n", e.Name, app)
		return nil
	}
	dest, err := entities.InstallToApp(e, kind, app)
	if err != nil {
		return err
	}
	fmt.Fprintf(out, "Installed %s to %s (%s)\n", e.Name, dest, app)
	return nil
}

func installAllFromStore(store *entities.Store, kind entities.Kind, app string, force bool, out io.Writer) error {
	items, err := store.All()
	if err != nil {
		return err
	}
	if len(items) == 0 {
		fmt.Fprintf(out, "No %ss in local store to install\n", kind)
		return nil
	}
	installed := 0
	skipped := 0
	for _, e := range items {
		if !force && isAlreadyInstalled(e.Name, kind, app) {
			skipped++
			continue
		}
		dest, err := entities.InstallToApp(e, kind, app)
		if err != nil {
			fmt.Fprintf(out, "  Error installing %s: %v\n", e.Name, err)
			continue
		}
		fmt.Fprintf(out, "  Installed %s to %s\n", e.Name, dest)
		installed++
	}
	msg := fmt.Sprintf("\nInstalled %d %s(s) to %s", installed, kind, app)
	if skipped > 0 {
		msg += fmt.Sprintf(" (skipped %d already installed)", skipped)
	}
	fmt.Fprintln(out, msg)
	return nil
}

// --- install from local directory ------------------------------------------

func installFromLocal(kind entities.Kind, dirPath, skillName string, all, force bool, out io.Writer, resolveApps func() ([]string, error), stdin io.Reader) error {
	// Resolve ~ and relative paths.
	if strings.HasPrefix(dirPath, "~/") {
		dirPath = filepath.Join(pathutil.Home(), dirPath[2:])
	}
	absPath, err := filepath.Abs(dirPath)
	if err != nil {
		return fmt.Errorf("could not resolve path: %w", err)
	}
	info, err := os.Stat(absPath)
	if err != nil {
		return fmt.Errorf("could not access directory: %w", err)
	}
	if !info.IsDir() {
		return fmt.Errorf("%s is not a directory", absPath)
	}

	// Discover entities in the directory.
	items := discoverEntities(kind, absPath)
	if len(items) == 0 {
		fmt.Fprintf(out, "No %ss found in %s\n", kind, absPath)
		return nil
	}

	// Let user pick skills first.
	items, err = selectItems(items, skillName, all, kind, absPath, stdin)
	if err != nil {
		return err
	}

	// Now resolve the target agent(s) (prompt if needed).
	apps, err := resolveApps()
	if err != nil {
		return err
	}

	for _, app := range apps {
		fmt.Fprintf(out, "\n%s:\n", app)
		installed := 0
		for _, item := range items {
			if !force && isAlreadyInstalled(item.name, kind, app) {
				if isInteractive(stdin) && confirmOverwrite(item.name, kind, app) {
					// user said yes — fall through to install
				} else {
					fmt.Fprintf(out, "  Skipping %s (already installed)\n", item.name)
					continue
				}
			}
			e := entities.Entity{
				Name:       item.name,
				Content:    item.content,
				Path:       item.path,
				ExtraFiles: item.extraFiles,
			}
			dest, err := entities.InstallToApp(e, kind, app)
			if err != nil {
				fmt.Fprintf(out, "  Error installing %s: %v\n", item.name, err)
				continue
			}
			fmt.Fprintf(out, "  Installed %s to %s\n", item.name, dest)
			installed++
		}
		fmt.Fprintf(out, "  %d %s(s) installed to %s\n", installed, kind, app)
	}
	return nil
}

// --- install from GitHub ---------------------------------------------------

func installFromGitHub(kind entities.Kind, repoArg, skillName string, all, force bool, out io.Writer, resolveApps func() ([]string, error), stdin io.Reader) error {
	// Parse owner/repo, optional @branch.
	ghOwner, ghRepo, ghBranch := parseRepoArg(repoArg)
	if ghOwner == "" || ghRepo == "" {
		return fmt.Errorf("invalid repository %q: expected owner/repo or owner/repo@branch", repoArg)
	}

	fmt.Fprintf(out, "Fetching from %s/%s@%s ...\n", ghOwner, ghRepo, ghBranch)

	client := fetching.New()
	dest := filepath.Join(os.TempDir(), fmt.Sprintf("cam-install-%s-%s", ghOwner, ghRepo))
	_ = os.RemoveAll(dest)
	root, err := client.DownloadGitHubZip(ghOwner, ghRepo, ghBranch, dest)
	if err != nil {
		return fmt.Errorf("failed to download repository: %w", err)
	}

	items := discoverEntities(kind, root)
	if len(items) == 0 {
		fmt.Fprintf(out, "No %ss found in %s/%s\n", kind, ghOwner, ghRepo)
		return nil
	}

	// Let user pick skills first.
	source := fmt.Sprintf("%s/%s", ghOwner, ghRepo)
	items, err = selectItems(items, skillName, all, kind, source, stdin)
	if err != nil {
		return err
	}

	// Now resolve the target agent(s) (prompt if needed).
	apps, err := resolveApps()
	if err != nil {
		return err
	}

	for _, app := range apps {
		fmt.Fprintf(out, "\n%s:\n", app)
		installed := 0
		for _, item := range items {
			if !force && isAlreadyInstalled(item.name, kind, app) {
				if isInteractive(stdin) && confirmOverwrite(item.name, kind, app) {
					// user said yes — fall through to install
				} else {
					fmt.Fprintf(out, "  Skipping %s (already installed)\n", item.name)
					continue
				}
			}
			e := entities.Entity{
				Name:       item.name,
				Content:    item.content,
				Path:       item.path,
				ExtraFiles: item.extraFiles,
				Repo:       &entities.RepoRef{Owner: ghOwner, Name: ghRepo, Branch: ghBranch},
			}
			destPath, err := entities.InstallToApp(e, kind, app)
			if err != nil {
				fmt.Fprintf(out, "  Error installing %s: %v\n", item.name, err)
				continue
			}
			// Also save to local store for future reference.
			store := entities.NewStore(kind)
			_ = store.Put(e)
			fmt.Fprintf(out, "  Installed %s to %s\n", item.name, destPath)
			installed++
		}
		fmt.Fprintf(out, "  %d %s(s) installed to %s\n", installed, kind, app)
	}
	return nil
}

// --- shared discovery & selection ------------------------------------------

type discoveredItem struct {
	name       string
	content    string
	path       string
	extraFiles map[string]string // relpath → content for additional files
}

// discoverEntities walks a directory and finds entities using the same
// conventions as `gh skill install --from-local`:
//
//  1. skills/*/SKILL.md            → standard flat layout
//  2. skills/{scope}/*/SKILL.md    → namespaced layout
//  3. {prefix}/skills/*/SKILL.md   → deeply nested skills/ dir
//  4. */SKILL.md                   → root-level skills (fallback)
//
// Hidden directories (dot-prefixed like .claude/, .github/) are skipped.
// Duplicates (same name) are deduplicated — first discovered wins.
// For skills and agents, all files in the directory (excluding the manifest)
// are read as extra files.
func discoverEntities(kind entities.Kind, root string) []discoveredItem {
	fileTarget := defaultManifestName(kind)
	seen := make(map[string]bool)
	var items []discoveredItem

	_ = filepath.WalkDir(root, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}

		// Skip hidden directories (dot-prefixed).
		if d.IsDir() && strings.HasPrefix(d.Name(), ".") {
			return filepath.SkipDir
		}
		if d.IsDir() {
			return nil
		}

		if filepath.Base(p) != fileTarget {
			return nil
		}

		// Get path relative to root for convention matching.
		relPath, relErr := filepath.Rel(root, p)
		if relErr != nil {
			return nil
		}
		relPath = filepath.ToSlash(relPath)

		// Check if path matches a known skill convention.
		if !matchesSkillConvention(relPath) {
			return nil
		}

		name := filepath.Base(filepath.Dir(p))
		if seen[name] {
			return nil // deduplicate
		}
		seen[name] = true

		data, readErr := os.ReadFile(p)
		if readErr != nil {
			return nil
		}

		// Read extra files in the skill directory (excluding the manifest)
		extraFiles := make(map[string]string)
		skillDir := filepath.Dir(p)
		if kind == entities.KindSkill || kind == entities.KindAgent {
			entries, err := os.ReadDir(skillDir)
			if err == nil {
				for _, entry := range entries {
					if entry.IsDir() {
						// Recursively read files in subdirectories
						subDir := filepath.Join(skillDir, entry.Name())
						_ = filepath.WalkDir(subDir, func(subPath string, subEntry os.DirEntry, subErr error) error {
							if subErr != nil || subEntry.IsDir() {
								return nil
							}
							// Skip hidden files
							if strings.HasPrefix(subEntry.Name(), ".") {
								return nil
							}
							subData, readErr := os.ReadFile(subPath)
							if readErr != nil {
								return nil
							}
							subRelPath, relErr := filepath.Rel(skillDir, subPath)
							if relErr != nil {
								return nil
							}
							subRelPath = filepath.ToSlash(subRelPath)
							extraFiles[subRelPath] = string(subData)
							return nil
						})
					} else {
						// Skip the manifest file itself and hidden files
						if entry.Name() == fileTarget || strings.HasPrefix(entry.Name(), ".") {
							continue
						}
						filePath := filepath.Join(skillDir, entry.Name())
						fileData, readErr := os.ReadFile(filePath)
						if readErr != nil {
							continue
						}
						fileRelPath := entry.Name()
						extraFiles[fileRelPath] = string(fileData)
					}
				}
			}
		}

		if len(extraFiles) == 0 {
			extraFiles = nil
		}
		items = append(items, discoveredItem{name: name, content: string(data), path: p, extraFiles: extraFiles})
		return nil
	})
	return items
}

// matchesSkillConvention checks whether a relative SKILL.md path matches
// any recognized skill directory convention, mirroring `gh skill install`
// discovery logic. Paths with hidden (dot-prefixed) segments are rejected.
func matchesSkillConvention(relPath string) bool {
	parts := strings.Split(relPath, "/")

	// Reject any path with a hidden segment.
	for _, part := range parts {
		if strings.HasPrefix(part, ".") {
			return false
		}
	}

	// The file itself must be the manifest (SKILL.md, AGENT.md, etc.)
	// and the parent dir is the skill name.
	if len(parts) < 2 {
		return false
	}

	// skills/name/SKILL.md → standard flat (3 parts)
	if len(parts) == 3 && parts[0] == "skills" {
		return true
	}

	// skills/scope/name/SKILL.md → namespaced (4 parts)
	if len(parts) == 4 && parts[0] == "skills" {
		return true
	}

	// {prefix}/skills/name/SKILL.md → deeply nested skills/ dir
	for i, part := range parts {
		if part == "skills" && i < len(parts)-2 {
			return true
		}
	}

	// name/SKILL.md → root-level (2 parts, name is parent dir)
	if len(parts) == 2 {
		return true
	}

	return false
}

// selectItems filters discovered items based on user intent:
//   - skillName given → find that specific item
//   - --all flag → return everything
//   - single item → return it directly
//   - interactive TTY → run multi-select picker
//   - non-interactive → list what was found and error
func selectItems(items []discoveredItem, skillName string, all bool, kind entities.Kind, source string, stdin io.Reader) ([]discoveredItem, error) {
	if skillName != "" {
		for _, item := range items {
			if item.name == skillName {
				return []discoveredItem{item}, nil
			}
		}
		return nil, fmt.Errorf("%s %q not found in %s", kind, skillName, source)
	}

	if all || len(items) == 1 {
		return items, nil
	}

	// Interactive: run multi-select picker.
	if isInteractive(stdin) {
		return interactiveSelectItems(items, kind, source)
	}

	// Non-interactive: list and ask user to specify.
	fmt.Fprintf(os.Stderr, "Found %d %s(s) in %s:\n\n", len(items), kind, source)
	for _, item := range items {
		desc := extractFrontmatterDescription(item.content)
		if desc != "" {
			if len(desc) > 80 {
				desc = desc[:77] + "..."
			}
			fmt.Fprintf(os.Stderr, "  %-35s %s\n", item.name, desc)
		} else {
			fmt.Fprintf(os.Stderr, "  %s\n", item.name)
		}
	}
	fmt.Fprintf(os.Stderr, "\nSpecify a name to install one, or use --all to install all:\n")
	fmt.Fprintf(os.Stderr, "  cam %s install <source> <name> --from-local --app <agent>\n", kind)
	fmt.Fprintf(os.Stderr, "  cam %s install <source> --from-local --all --app <agent>\n", kind)
	return nil, fmt.Errorf("specify a %s name or use --all", kind)
}

// interactiveSelectItems runs a bubbletea multi-select picker.
func interactiveSelectItems(items []discoveredItem, kind entities.Kind, source string) ([]discoveredItem, error) {
	msItems := make([]multiSelectItem, len(items))
	for i, item := range items {
		desc := extractFrontmatterDescription(item.content)
		if len(desc) > 120 {
			desc = desc[:117] + "..."
		}
		msItems[i] = multiSelectItem{
			label:       item.name,
			description: desc,
		}
	}

	title := fmt.Sprintf("Select %s(s) to install from %s:", kind, source)
	selected, err := runMultiSelect(title, msItems)
	if err != nil {
		return nil, err
	}
	if len(selected) == 0 {
		return nil, fmt.Errorf("no %ss selected", kind)
	}

	// Map selected labels back to items (label starts with the name).
	nameSet := make(map[string]bool)
	for _, label := range selected {
		// Extract the name from "name    description" format.
		name := strings.Fields(label)[0]
		nameSet[name] = true
	}

	var result []discoveredItem
	for _, item := range items {
		if nameSet[item.name] {
			result = append(result, item)
		}
	}
	return result, nil
}

// promptSearchInstall shows an interactive multi-select picker over GitHub
// search results, then asks for a target app, and installs the selected
// skills — matching the `gh skill search` interactive flow.
func promptSearchInstall(results []ghSearchResult, kind entities.Kind, out io.Writer) error {
	// Build multi-select items matching gh skill search / cli/cli format:
	//   > [ ]  scope/name  owner/repo  ★ stars
	//          Full description text
	msItems := make([]multiSelectItem, len(results))
	for i, r := range results {
		id := r.ID
		if id == "" {
			id = r.Name
		}
		stars := formatStars(r.Stars)
		label := fmt.Sprintf("%-40s %-35s", id, r.Repo)
		if stars != "" {
			label += "  " + stars
		}
		msItems[i] = multiSelectItem{
			label:       label,
			description: r.Description,
		}
	}

	selected, err := runMultiSelect("Select skills to install:", msItems)
	if err != nil {
		return err
	}
	if len(selected) == 0 {
		return nil
	}

	// Map selected labels back to results (label starts with the skill ID).
	var toInstall []ghSearchResult
	for _, label := range selected {
		id := strings.TrimSpace(strings.Fields(label)[0])
		for _, r := range results {
			rid := r.ID
			if rid == "" {
				rid = r.Name
			}
			if rid == id {
				toInstall = append(toInstall, r)
				break
			}
		}
	}
	if len(toInstall) == 0 {
		return nil
	}

	// Pick target agent(s) — multi-select.
	apps, err := promptSelectApp(kind)
	if err != nil {
		return err
	}
	if len(apps) == 0 {
		return nil
	}
	appsFn := func() ([]string, error) { return apps, nil }

	// Install each selected skill from GitHub.
	for _, r := range toInstall {
		fmt.Fprintf(out, "\nInstalling %s from %s...\n", r.Name, r.Repo)
		err := installFromGitHub(kind, r.Repo, r.Name, true, false, out, appsFn, os.Stdin)
		if err != nil {
			fmt.Fprintf(out, "  Error: %v\n", err)
		}
	}
	return nil
}

// singleSelectModel is a bubbletea model for picking exactly one item.
type singleSelectModel struct {
	title    string
	items    []string
	cursor   int
	selected string
	aborted  bool
}

func newSingleSelectModel(title string, items []string) singleSelectModel {
	return singleSelectModel{title: title, items: items}
}

func (m singleSelectModel) Init() tea.Cmd { return nil }

func (m singleSelectModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}
	switch key.String() {
	case "ctrl+c", "q", "esc":
		m.aborted = true
		return m, tea.Quit
	case "up", "k":
		if m.cursor > 0 {
			m.cursor--
		}
	case "down", "j":
		if m.cursor < len(m.items)-1 {
			m.cursor++
		}
	case "enter":
		m.selected = m.items[m.cursor]
		return m, tea.Quit
	}
	return m, nil
}

func (m singleSelectModel) View() string {
	var b strings.Builder
	b.WriteString(m.title)
	b.WriteString("\n\n")
	for i, item := range m.items {
		cursor := " "
		if i == m.cursor {
			cursor = ">"
		}
		fmt.Fprintf(&b, "%s %s\n", cursor, item)
	}
	b.WriteString("\n↑/↓=move · enter=select · q=quit\n")
	return b.String()
}

// isInteractive returns true if stdin is a TTY (interactive terminal).
func isInteractive(stdin io.Reader) bool {
	file, ok := stdin.(*os.File)
	if !ok {
		return false
	}
	fi, err := file.Stat()
	if err != nil {
		return false
	}
	return fi.Mode()&os.ModeCharDevice != 0
}

// confirmOverwrite asks the user whether to overwrite an already-installed
// entity.  Returns true if the user confirms.  Only called in interactive mode.
func confirmOverwrite(name string, kind entities.Kind, app string) bool {
	items := []string{"Yes — overwrite", "No — skip"}
	title := fmt.Sprintf("%s %q is already installed in %s. Overwrite?", kind, name, app)
	model := newSingleSelectModel(title, items)
	p := tea.NewProgram(model)
	final, err := p.Run()
	if err != nil {
		return false
	}
	result := final.(singleSelectModel)
	return !result.aborted && strings.HasPrefix(result.selected, "Yes")
}

// promptSelectApp runs a multi-select picker for target code agents.
// Shows only installed agents (binary found on PATH), matching
// the gh skill interactive picker format with display names.
func promptSelectApp(kind entities.Kind) ([]string, error) {
	apps := entities.AppPathsFor(kind)
	allAgents := entities.AllAgents()

	var items []multiSelectItem
	for _, info := range allAgents {
		if _, ok := apps[info.ID]; !ok {
			continue // agent doesn't support this kind
		}
		if !entities.IsAgentInstalled(info) {
			continue // not installed on this system
		}
		items = append(items, multiSelectItem{
			label: info.DisplayName,
		})
	}

	if len(items) == 0 {
		return nil, fmt.Errorf("no code agents found on PATH (install one or use --app)")
	}

	selected, err := runMultiSelect("Select target agent(s):", items)
	if err != nil {
		supported := entities.SupportedApps(kind)
		return nil, fmt.Errorf("--app is required (one of: %s)", strings.Join(supported, ", "))
	}
	if len(selected) == 0 {
		return nil, fmt.Errorf("no agent selected")
	}

	// Map display names back to IDs.
	var ids []string
	for _, displayName := range selected {
		for _, info := range allAgents {
			if info.DisplayName == displayName {
				ids = append(ids, info.ID)
				break
			}
		}
	}
	return ids, nil
}

// parseRepoArg splits "owner/repo" or "owner/repo@branch" into components.
func parseRepoArg(arg string) (owner, repo, branch string) {
	branch = "main"
	// Handle @branch suffix.
	if idx := strings.LastIndex(arg, "@"); idx > 0 {
		branch = arg[idx+1:]
		arg = arg[:idx]
	}
	parts := strings.SplitN(arg, "/", 2)
	if len(parts) != 2 {
		return "", "", ""
	}
	return parts[0], parts[1], branch
}

// isAlreadyInstalled checks whether the named entity is already installed for the given app.
func isAlreadyInstalled(name string, kind entities.Kind, app string) bool {
	apps := entities.AppPathsFor(kind)
	dest, ok := apps[app]
	if !ok {
		return false
	}
	resolved := expandPath(dest)
	switch kind {
	case entities.KindPrompt, entities.KindInstruction:
		_, err := os.Stat(resolved)
		return err == nil
	default:
		_, err := os.Stat(filepath.Join(resolved, name))
		return err == nil
	}
}

// ============================================================================
// uninstall — remove from code agent(s)
// ============================================================================

func entityUninstallCommand(kind entities.Kind) *cobra.Command {
	var (
		app string
		all bool
	)
	cmd := &cobra.Command{
		Use:     "uninstall [NAME...]",
		Aliases: []string{"rm", "remove"},
		Short:   "Uninstall " + string(kind) + "(s) from a code agent",
		Long: "Remove installed " + string(kind) + `(s) from a target code agent.

When --app is omitted in an interactive terminal, you will be prompted
to select target agent(s).

Supported agents: ` + strings.Join(entities.SupportedApps(kind), ", ") + `.

Use --all to uninstall every installed item from the selected agent(s).`,
		Example: "  cam " + string(kind) + " uninstall my-skill --app claude\n" +
			"  cam " + string(kind) + " uninstall --all --app claude\n" +
			"  cam " + string(kind) + " uninstall skill-a skill-b",
		Args: cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()

			// Resolve target app(s).
			var apps []string
			if app != "" {
				apps = []string{app}
			} else if isInteractive(cmd.InOrStdin()) {
				picked, err := promptSelectApp(kind)
				if err != nil {
					return err
				}
				apps = picked
			} else {
				return fmt.Errorf("--app is required (one of: %s)", strings.Join(entities.SupportedApps(kind), ", "))
			}

			if !all && len(args) == 0 {
				// Interactive: list what's installed and let user pick.
				if isInteractive(cmd.InOrStdin()) {
					return interactiveUninstall(kind, apps, out)
				}
				return fmt.Errorf("NAME is required (or use --all)")
			}

			for _, a := range apps {
				if all {
					uninstallAllFromApp(kind, a, out)
				} else {
					for _, name := range args {
						uninstallOneFromApp(kind, a, name, out)
					}
				}
			}
			return nil
		},
	}
	cmd.Flags().StringVarP(&app, "app", "a", "", "Target agent (e.g. claude, codex, gemini)")
	cmd.Flags().BoolVar(&all, "all", false, "Uninstall all installed items")
	return cmd
}

func uninstallOneFromApp(kind entities.Kind, app, name string, out io.Writer) {
	path, removed, err := entities.UninstallFromApp(name, kind, app)
	if err != nil {
		fmt.Fprintf(out, "  Error removing %s from %s: %v\n", name, app, err)
		return
	}
	if !removed {
		fmt.Fprintf(out, "  %s not found in %s (%s)\n", name, app, path)
		return
	}
	fmt.Fprintf(out, "  Removed %s from %s\n", name, app)
}

func uninstallAllFromApp(kind entities.Kind, app string, out io.Writer) {
	appPaths := entities.AppPathsFor(kind)
	dest, ok := appPaths[app]
	if !ok {
		fmt.Fprintf(out, "  %s does not support %ss\n", app, kind)
		return
	}
	resolved := expandPath(dest)

	if kind == entities.KindPrompt || kind == entities.KindInstruction {
		// Prompts are single files — don't remove the user's CLAUDE.md etc.
		fmt.Fprintf(out, "  Skipping %s — prompt files are not bulk-removable\n", app)
		return
	}

	entries, err := os.ReadDir(resolved)
	if err != nil {
		fmt.Fprintf(out, "  No %ss installed in %s\n", kind, app)
		return
	}

	removed := 0
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		target := filepath.Join(resolved, e.Name())
		if err := os.RemoveAll(target); err != nil {
			fmt.Fprintf(out, "  Error removing %s: %v\n", e.Name(), err)
			continue
		}
		fmt.Fprintf(out, "  Removed %s from %s\n", e.Name(), app)
		removed++
	}
	fmt.Fprintf(out, "\nRemoved %d %s(s) from %s\n", removed, kind, app)
}

// interactiveUninstall lists installed items and lets the user pick which to remove.
func interactiveUninstall(kind entities.Kind, apps []string, out io.Writer) error {
	for _, app := range apps {
		appPaths := entities.AppPathsFor(kind)
		dest, ok := appPaths[app]
		if !ok {
			continue
		}
		resolved := expandPath(dest)

		if kind == entities.KindPrompt || kind == entities.KindInstruction {
			fmt.Fprintf(out, "  %s — prompt uninstall not supported interactively\n", app)
			continue
		}

		entries, err := os.ReadDir(resolved)
		if err != nil {
			continue
		}
		var items []multiSelectItem
		for _, e := range entries {
			if !e.IsDir() {
				continue
			}
			items = append(items, multiSelectItem{label: e.Name()})
		}
		if len(items) == 0 {
			fmt.Fprintf(out, "No %ss installed in %s\n", kind, app)
			continue
		}

		title := fmt.Sprintf("Select %s(s) to uninstall from %s:", kind, app)
		selected, err := runMultiSelect(title, items)
		if err != nil {
			return err
		}
		for _, name := range selected {
			uninstallOneFromApp(kind, app, name, out)
		}
	}
	return nil
}

func readStdinIfPiped(in io.Reader) (string, error) {
	if file, ok := in.(*os.File); ok {
		info, err := file.Stat()
		if err != nil {
			return "", nil
		}
		if info.Mode()&os.ModeCharDevice != 0 {
			return "", nil
		}
		data, err := io.ReadAll(file)
		if err != nil {
			return "", err
		}
		return string(data), nil
	}
	data, err := io.ReadAll(in)
	if err != nil {
		return "", err
	}
	return string(data), nil
}
