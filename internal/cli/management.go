package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
	"github.com/chat2anyllm/code-agent-manager/internal/fetching"
	"github.com/chat2anyllm/code-agent-manager/internal/repoconfig"
)

// managementCommand returns the prompt/skill/agent/plugin command tree with
// four subcommands modeled after `gh skill`: search, list, update, install.
func (a *App) managementCommand(group, alias string, state *globalState) *cobra.Command {
	kind := groupKind(group)
	cmd := &cobra.Command{
		Use:     group,
		Aliases: []string{alias},
		Short:   "Manage " + group + " configurations",
	}
	cmd.AddCommand(entitySearchCommand(kind))
	cmd.AddCommand(entityListCommand(kind))
	cmd.AddCommand(entityUpdateCommand(kind))
	cmd.AddCommand(entityInstallCommand(kind))
	return cmd
}

func groupKind(group string) entities.Kind {
	switch group {
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
// search — search GitHub + local store + configured repos
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

			// 1. GitHub Code Search (default, skip with --local).
			var ghResults []ghSearchResult
			if !local {
				var err error
				ghResults, err = searchGitHub(kind, strings.Join(args, " "), owner, limit)
				if err != nil {
					fmt.Fprintf(out, "GitHub search: %v\n\n", err)
				}
			}

			// 2. Search local store.
			store := entities.NewStore(kind)
			storeItems, _ := store.All()
			var storeMatches []entities.Entity
			for _, e := range storeItems {
				if matchesQuery(e, query) {
					storeMatches = append(storeMatches, e)
				}
			}

			// 3. Search configured repos.
			repos, err := repoconfig.LoadEnabled(kind)
			if err != nil {
				repos = nil
			}
			var repoMatches []repoSearchResult
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
					repoMatches = append(repoMatches, repoSearchResult{
						Key:         key,
						Owner:       rOwner,
						Name:        name,
						Branch:      r.EffectiveBranch(),
						Description: r.Description,
					})
				}
			}

			totalMatches := len(ghResults) + len(storeMatches) + len(repoMatches)
			if totalMatches == 0 {
				fmt.Fprintf(out, "No %ss found matching %q\n", kind, query)
				return nil
			}

			// Show GitHub results first (primary output, like gh skill search).
			if len(ghResults) > 0 {
				// Interactive: go straight to multi-select picker (skip table to avoid duplicate display).
				if isInteractive() {
					fmt.Fprintf(out, "Showing %d %s(s) matching %q\n", len(ghResults), kind, query)
					return promptSearchInstall(ghResults, kind, out)
				}

				// Non-interactive: print table matching `gh skill search` format.
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

			if len(repoMatches) > 0 {
				if len(ghResults) > 0 || len(storeMatches) > 0 {
					fmt.Fprintln(out)
				}
				sort.Slice(repoMatches, func(i, j int) bool {
					return repoMatches[i].Key < repoMatches[j].Key
				})
				fmt.Fprintf(out, "Configured repos matching %q (%d):\n\n", query, len(repoMatches))
				for _, r := range repoMatches {
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
// the query, similar to how `gh skill search` works.
func searchGitHub(kind entities.Kind, query, owner string, limit int) ([]ghSearchResult, error) {
	manifest := defaultManifestName(kind)

	// Build search queries: content match + path match (like gh skill search).
	contentQ := fmt.Sprintf("filename:%s %s", manifest, query)
	pathTerm := strings.ReplaceAll(query, " ", "-")
	pathQ := fmt.Sprintf("filename:%s path:%s", manifest, pathTerm)
	if owner != "" {
		contentQ += " user:" + owner
		pathQ += " user:" + owner
	}

	client := &http.Client{Timeout: 15 * time.Second}
	authHeader := resolveGitHubAuth()

	// Run content and path searches.
	contentItems, err := executeGHSearch(client, contentQ, limit, authHeader)
	if err != nil {
		return nil, err
	}
	pathItems, _ := executeGHSearch(client, pathQ, limit, authHeader)

	// Merge: path results first, then content results.
	var allItems []ghCodeSearchItem
	allItems = append(allItems, pathItems...)
	allItems = append(allItems, contentItems...)

	// Deduplicate by (repo, skill-name).
	type key struct{ repo, name string }
	seen := make(map[key]bool)
	var results []ghSearchResult
	for _, item := range allItems {
		// Compute scope/name identifier from path, matching gh skill search format.
		// e.g. "skills/hybrid-cloud-architect/SKILL.md" → "hybrid-cloud-architect"
		// e.g. "antigravity-awesome-skills/hybrid-cloud-architect/SKILL.md"
		//   → "antigravity-awesome-skills/hybrid-cloud-architect"
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
		if len(results) >= limit {
			break
		}
	}

	// Fetch descriptions from SKILL.md frontmatter concurrently.
	if authHeader != "" {
		enrichGHDescriptions(client, authHeader, results)
	}

	return results, nil
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

func executeGHSearch(client *http.Client, query string, limit int, authHeader string) ([]ghCodeSearchItem, error) {
	apiURL := fmt.Sprintf("https://api.github.com/search/code?q=%s&per_page=%d",
		url.QueryEscape(query), limit)

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

	if resp.StatusCode == 403 || resp.StatusCode == 429 {
		return nil, fmt.Errorf("GitHub API rate limit exceeded, set GITHUB_TOKEN for higher limits")
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
// description field, similar to how gh skill search enriches results.
func enrichGHDescriptions(client *http.Client, authHeader string, results []ghSearchResult) {
	for i := range results {
		parts := strings.SplitN(results[i].Repo, "/", 2)
		if len(parts) != 2 {
			continue
		}
		// Fetch the raw file content.
		rawURL := fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/main/%s",
			parts[0], parts[1], results[i].Path)
		req, err := http.NewRequest("GET", rawURL, nil)
		if err != nil {
			continue
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
			continue
		}
		body, err := io.ReadAll(io.LimitReader(resp.Body, 4096))
		resp.Body.Close()
		if err != nil {
			continue
		}
		// Extract description from frontmatter: look for "description:" line.
		desc := extractFrontmatterDescription(string(body))
		if desc != "" {
			results[i].Description = desc
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
				case entities.KindPrompt:
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
		home, _ = os.UserHomeDir()
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
       cam ` + string(kind) + ` install owner/repo --app claude --from-github

  3. From a local directory (--from-local):
     Discover and install items from a local directory.
       cam ` + string(kind) + ` install ./my-skills --app claude --from-local

Supported agents: ` + strings.Join(entities.SupportedApps(kind), ", ") + `.

Use --all to install every discovered item.
Use --force to overwrite existing installations.`,
		Example: "  # Install from local store\n" +
			"  cam " + string(kind) + " install my-skill --app claude\n" +
			"  cam " + string(kind) + " install --all --app claude\n\n" +
			"  # Install from GitHub repository\n" +
			"  cam " + string(kind) + " install anthropics/skills --app claude --from-github\n\n" +
			"  # Install from local directory\n" +
			"  cam " + string(kind) + " install ./my-skills-dir --app claude --from-local\n" +
			"  cam " + string(kind) + " install ~/repos/skills my-skill --app claude --from-local\n" +
			"  cam " + string(kind) + " install ~/repos/skills --app claude --from-local --all",
		Args: cobra.MaximumNArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()

			if app == "" {
				return fmt.Errorf("--app is required (one of: %s)", strings.Join(entities.SupportedApps(kind), ", "))
			}

			if fromLocal && fromGH {
				return fmt.Errorf("--from-local and --from-github cannot be used together")
			}

			if fromLocal {
				if len(args) == 0 {
					return fmt.Errorf("--from-local requires a directory path argument")
				}
				skillName := ""
				if len(args) >= 2 {
					skillName = args[1]
				}
				return installFromLocal(kind, args[0], skillName, app, all, force, out)
			}

			if fromGH {
				if len(args) == 0 {
					return fmt.Errorf("--from-github requires an owner/repo argument")
				}
				skillName := ""
				if len(args) >= 2 {
					skillName = args[1]
				}
				return installFromGitHub(kind, args[0], skillName, app, all, force, out)
			}

			// Default: install from local store.
			store := entities.NewStore(kind)

			if all {
				if len(args) > 0 {
					return fmt.Errorf("cannot use --all with a name argument")
				}
				return installAllFromStore(store, kind, app, force, out)
			}

			if len(args) == 0 {
				return fmt.Errorf("NAME is required (or use --all, --from-local, or --from-github)")
			}

			return installOneFromStore(store, kind, app, args[0], force, out)
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

func installFromLocal(kind entities.Kind, dirPath, skillName, app string, all, force bool, out io.Writer) error {
	// Resolve ~ and relative paths.
	if strings.HasPrefix(dirPath, "~/") {
		if home, err := os.UserHomeDir(); err == nil {
			dirPath = filepath.Join(home, dirPath[2:])
		}
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

	// Filter to a specific skill if requested.
	items, err = selectItems(items, skillName, all, kind, absPath)
	if err != nil {
		return err
	}

	installed := 0
	for _, item := range items {
		if !force && isAlreadyInstalled(item.name, kind, app) {
			fmt.Fprintf(out, "  Skipping %s (already installed, use --force)\n", item.name)
			continue
		}
		e := entities.Entity{
			Name:    item.name,
			Content: item.content,
			Path:    item.path,
		}
		dest, err := entities.InstallToApp(e, kind, app)
		if err != nil {
			fmt.Fprintf(out, "  Error installing %s: %v\n", item.name, err)
			continue
		}
		fmt.Fprintf(out, "  Installed %s to %s (from %s)\n", item.name, dest, app)
		installed++
	}
	fmt.Fprintf(out, "\nInstalled %d %s(s) from %s to %s\n", installed, kind, absPath, app)
	return nil
}

// --- install from GitHub ---------------------------------------------------

func installFromGitHub(kind entities.Kind, repoArg, skillName, app string, all, force bool, out io.Writer) error {
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

	source := fmt.Sprintf("%s/%s", ghOwner, ghRepo)
	items, err = selectItems(items, skillName, all, kind, source)
	if err != nil {
		return err
	}

	installed := 0
	for _, item := range items {
		if !force && isAlreadyInstalled(item.name, kind, app) {
			fmt.Fprintf(out, "  Skipping %s (already installed, use --force)\n", item.name)
			continue
		}
		e := entities.Entity{
			Name:    item.name,
			Content: item.content,
			Path:    item.path,
			Repo:    &entities.RepoRef{Owner: ghOwner, Name: ghRepo, Branch: ghBranch},
		}
		destPath, err := entities.InstallToApp(e, kind, app)
		if err != nil {
			fmt.Fprintf(out, "  Error installing %s: %v\n", item.name, err)
			continue
		}
		// Also save to local store for future reference.
		store := entities.NewStore(kind)
		_ = store.Put(e)
		fmt.Fprintf(out, "  Installed %s to %s (from %s/%s)\n", item.name, destPath, ghOwner, ghRepo)
		installed++
	}
	fmt.Fprintf(out, "\nInstalled %d %s(s) from %s/%s to %s\n", installed, kind, ghOwner, ghRepo, app)
	return nil
}

// --- shared discovery & selection ------------------------------------------

type discoveredItem struct {
	name    string
	content string
	path    string
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
		items = append(items, discoveredItem{name: name, content: string(data), path: p})
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
func selectItems(items []discoveredItem, skillName string, all bool, kind entities.Kind, source string) ([]discoveredItem, error) {
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
	if isInteractive() {
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
		label := item.name
		if desc != "" {
			if len(desc) > 80 {
				desc = desc[:77] + "..."
			}
			label = fmt.Sprintf("%-30s %s", item.name, desc)
		}
		msItems[i] = multiSelectItem{
			label:       label,
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

	// Pick target app.
	supportedApps := entities.SupportedApps(kind)
	appItems := make([]multiSelectItem, len(supportedApps))
	for i, app := range supportedApps {
		appItems[i] = multiSelectItem{label: app}
	}
	appModel := newSingleSelectModel("Select target agent:", supportedApps)
	p := tea.NewProgram(appModel)
	final, err := p.Run()
	if err != nil {
		return err
	}
	appResult := final.(singleSelectModel)
	if appResult.aborted || appResult.selected == "" {
		return nil
	}
	app := appResult.selected

	// Install each selected skill from GitHub.
	for _, r := range toInstall {
		fmt.Fprintf(out, "\nInstalling %s from %s...\n", r.Name, r.Repo)
		err := installFromGitHub(kind, r.Repo, r.Name, app, true, false, out)
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
func isInteractive() bool {
	fi, err := os.Stdin.Stat()
	if err != nil {
		return false
	}
	return fi.Mode()&os.ModeCharDevice != 0
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
	case entities.KindPrompt:
		_, err := os.Stat(resolved)
		return err == nil
	default:
		_, err := os.Stat(filepath.Join(resolved, name))
		return err == nil
	}
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
