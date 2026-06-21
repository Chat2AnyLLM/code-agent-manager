package metadata

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
	"github.com/chat2anyllm/code-agent-manager/internal/fetching"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/repoconfig"
)

// Service orchestrates metadata operations.
type Service struct {
	store   *Store
	fetcher RepoFetcher
}

// RepoFetcher downloads a repository and returns the local path to its extracted
// root. The fetching package satisfies this via DownloadGitHubZip.
type RepoFetcher interface {
	Fetch(owner, repo, branch, dest string) (root string, err error)
}

// NewService constructs a metadata Service with the default GitHub fetcher.
func NewService(store *Store) *Service {
	return &Service{store: store, fetcher: defaultFetcher{}}
}

// WithFetcher overrides the repository fetcher (used in tests).
func (svc *Service) WithFetcher(f RepoFetcher) *Service {
	svc.fetcher = f
	return svc
}

type defaultFetcher struct{}

func (defaultFetcher) Fetch(owner, repo, branch, dest string) (string, error) {
	// A shorter timeout than the package default so one slow/unreachable repo
	// doesn't tie up a worker for a full minute during a bulk refresh.
	client := fetching.New()
	client.HTTPClient.Timeout = 30 * time.Second
	client.Timeout = 30 * time.Second
	return client.DownloadGitHubZip(owner, repo, branch, dest)
}

// RefreshFromFiles reads *_repos.json files from cfgDir and indexes entries into SQLite.
func (svc *Service) RefreshFromFiles(ctx context.Context, cfgDir string) (RefreshSummary, error) {
	if err := svc.store.Init(ctx); err != nil {
		return RefreshSummary{}, err
	}

	summary := RefreshSummary{}
	files := []struct {
		filename string
		kind     string
	}{
		{"skill_repos.json", "skill"},
		{"agent_repos.json", "agent"},
		{"instruction_repos.json", "instruction"},
		{"plugin_repos.json", "plugin"},
	}

	for _, f := range files {
		path := filepath.Join(cfgDir, f.filename)
		data, err := os.ReadFile(path)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			summary.FailedSources = append(summary.FailedSources, f.filename)
			continue
		}

		var repos map[string]json.RawMessage
		if err := json.Unmarshal(data, &repos); err != nil {
			summary.FailedSources = append(summary.FailedSources, f.filename)
			continue
		}

		summary.SourcesScanned++
		for key, raw := range repos {
			var entry repoEntry
			if err := json.Unmarshal(raw, &entry); err != nil {
				continue
			}
			if entry.Enabled != nil && !*entry.Enabled {
				continue
			}

			item := Item{
				Kind:        f.kind,
				Name:        entryName(entry, key),
				Description: entry.Description,
				RepoOwner:   effectiveOwner(entry),
				RepoName:    effectiveName(entry),
				RepoBranch:  effectiveBranch(entry),
				ItemPath:    entryPath(entry, f.kind),
				InstallKey:  key,
				TargetApps:  strings.Join(defaultTargetApps(f.kind), ","),
			}
			if err := svc.store.UpsertItem(ctx, item); err != nil {
				continue
			}
			summary.ItemsAdded++
		}
	}

	return summary, nil
}

// RefreshAll downloads every enabled repository for each kind (skill, agent,
// instruction, plugin), discovers the individual resources inside each repo, and
// indexes them into SQLite as cached metadata. Each resource — not each repo —
// becomes one searchable/installable item, so the counts reflect real resources.
//
// Downloads run per-repo and failures are non-fatal: a broken repo is recorded
// in FailedSources and the refresh continues. After indexing a kind, resources
// that were not seen this run are pruned as stale.
//
// Repository downloads (the slow, network-bound phase) run concurrently across a
// bounded worker pool. Only the SQLite writes are serialized, on the calling
// goroutine, which keeps the single DB connection safe and the summary
// deterministic.
func (svc *Service) RefreshAll(ctx context.Context) (RefreshSummary, error) {
	if err := svc.store.Init(ctx); err != nil {
		return RefreshSummary{}, err
	}
	summary := RefreshSummary{}

	kinds := []struct {
		kind       string
		entityKind entities.Kind
	}{
		{"skill", entities.KindSkill},
		{"agent", entities.KindAgent},
		{"instruction", entities.KindInstruction},
		{"plugin", entities.KindPlugin},
	}

	cacheDir := filepath.Join(pathutil.CacheDir(), "metadata-repos")
	startedAt := timeNow()

	for _, k := range kinds {
		repos, err := repoconfig.LoadEnabled(k.entityKind)
		if err != nil {
			summary.FailedSources = append(summary.FailedSources, fmt.Sprintf("%s: %v", k.kind, err))
			continue
		}

		// Build the work list for this kind.
		var jobs []repoJob
		for _, entry := range repos {
			owner := entry.EffectiveOwner()
			repo := entry.EffectiveName()
			if owner == "" || repo == "" {
				continue
			}
			jobs = append(jobs, repoJob{
				owner:       owner,
				repo:        repo,
				branch:      entry.EffectiveBranch(),
				subPath:     entry.SubPath(k.entityKind),
				catalogFile: entry.CatalogFile,
			})
		}
		summary.SourcesScanned += len(jobs)

		// Fan out downloads+discovery; fan in results for serialized DB writes.
		results := svc.fetchAndDiscover(ctx, k.kind, k.entityKind, cacheDir, jobs)
		var batch []Item
		for r := range results {
			if r.err != "" {
				summary.FailedSources = append(summary.FailedSources, r.err)
				continue
			}
			batch = append(batch, r.items...)
		}
		written, err := svc.store.UpsertItems(ctx, batch)
		if err != nil {
			summary.FailedSources = append(summary.FailedSources, fmt.Sprintf("%s: index: %v", k.kind, err))
		}
		summary.ItemsAdded += written

		// Prune resources of this kind that were not seen during this refresh.
		stale, err := svc.store.DeleteStale(ctx, k.kind, startedAt)
		if err == nil {
			summary.ItemsStale += stale
		}
	}

	return summary, nil
}

// repoJob is one repository to download and scan during a refresh.
type repoJob struct {
	owner       string
	repo        string
	branch      string
	subPath     string
	catalogFile string
}

// repoResult is the outcome of processing one repoJob: either a set of indexed
// items or a single error string (non-fatal, recorded in FailedSources).
type repoResult struct {
	items []Item
	err   string
}

// refreshConcurrency bounds simultaneous repository downloads. GitHub archive
// downloads are network-bound, so a modest pool gives a large speedup without
// hammering the host or the remote.
const refreshConcurrency = 8

// fetchAndDiscover downloads and scans jobs concurrently, returning a channel of
// results. Each job downloads its repo zip, discovers the individual resources,
// and emits them as Items. The DB is never touched here — callers serialize the
// upserts — so the workers need no locking.
func (svc *Service) fetchAndDiscover(ctx context.Context, kind string, entityKind entities.Kind, cacheDir string, jobs []repoJob) <-chan repoResult {
	out := make(chan repoResult)
	if len(jobs) == 0 {
		close(out)
		return out
	}

	workers := min(refreshConcurrency, len(jobs))

	jobCh := make(chan repoJob)
	go func() {
		defer close(jobCh)
		for _, j := range jobs {
			select {
			case <-ctx.Done():
				return
			case jobCh <- j:
			}
		}
	}()

	var wg sync.WaitGroup
	wg.Add(workers)
	targetApps := strings.Join(defaultTargetApps(kind), ",")
	for range workers {
		go func() {
			defer wg.Done()
			for job := range jobCh {
				dest := filepath.Join(cacheDir, kind, job.owner+"-"+job.repo)
				_ = os.RemoveAll(dest)
				root, err := svc.fetcher.Fetch(job.owner, job.repo, job.branch, dest)
				if err != nil {
					out <- repoResult{err: fmt.Sprintf("%s/%s: %v", job.owner, job.repo, err)}
					_ = os.RemoveAll(dest)
					continue
				}

				resources := DiscoverResources(root, job.subPath, entityKind)
				if job.catalogFile != "" {
					if catalogResources := DiscoverCatalogResources(root, job.catalogFile, entityKind); len(catalogResources) > 0 {
						resources = catalogResources
					}
				} else if len(resources) == 0 {
					if catalogFile := inferCatalogFile(root, entityKind); catalogFile != "" {
						resources = DiscoverCatalogResources(root, catalogFile, entityKind)
					}
				}
				items := make([]Item, 0, len(resources))
				cachedAt := timeNow()
				for _, res := range resources {
					owner, repo, branch, itemPath := job.owner, job.repo, job.branch, res.RelPath
					if res.SourceOwner != "" && res.SourceRepo != "" {
						owner, repo = res.SourceOwner, res.SourceRepo
						if res.SourceBranch != "" {
							branch = res.SourceBranch
						}
						if res.SourcePath != "" {
							itemPath = res.SourcePath
						}
					}
					content := ""
					if res.ManifestRel != "" {
						manifestPath := filepath.Join(root, filepath.FromSlash(res.ManifestRel))
						if data, err := os.ReadFile(manifestPath); err == nil {
							content = string(data)
						}
					}
					items = append(items, Item{
						Kind:           kind,
						Name:           res.Name,
						Description:    res.Description,
						RepoOwner:      owner,
						RepoName:       repo,
						RepoBranch:     branch,
						ItemPath:       itemPath,
						InstallKey:     fmt.Sprintf("%s/%s:%s", owner, repo, res.Name),
						TargetApps:     targetApps,
						Content:        content,
						ContentCachedAt: cachedAt,
						ManifestPath:   res.ManifestRel,
					})
				}
				out <- repoResult{items: items}
				_ = os.RemoveAll(dest)
			}
		}()
	}

	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}

// Install installs an item from the metadata index into one target app. The
// resource content is fetched from its source repository at install time so the
// installed file carries the real manifest, not an empty placeholder.
func (svc *Service) Install(ctx context.Context, kind, installKey, targetApp string) error {
	return svc.InstallToTargets(ctx, kind, installKey, []string{targetApp})
}

// InstallInstructionToTargets installs an instruction item into multiple target
// agents at the given install level. User-level installs use the app-specific
// instruction file path; project-level installs require projectDir. Install
// status is recorded per successful target.
func (svc *Service) InstallInstructionToTargets(ctx context.Context, installKey string, targetApps []string, level entities.InstallLevel, projectDir string) error {
	if len(targetApps) == 0 {
		return fmt.Errorf("metadata: no target agents specified")
	}
	item, err := svc.store.GetItem(ctx, "instruction", installKey)
	if err != nil {
		return fmt.Errorf("metadata: item not found: %w", err)
	}
	content := svc.fetchResourceContent(item)
	entity := entities.Entity{
		Kind:        entities.KindInstruction,
		Name:        item.Name,
		Description: item.Description,
		Content:     content,
		Repo: &entities.RepoRef{
			Owner:  item.RepoOwner,
			Name:   item.RepoName,
			Branch: item.RepoBranch,
			Path:   item.ItemPath,
		},
	}
	var installed []string
	var lastErr error
	for _, app := range targetApps {
		if _, err := entities.InstallInstruction(entity, app, level, projectDir); err != nil {
			lastErr = fmt.Errorf("metadata: install instruction to %s: %w", app, err)
			continue
		}
		installed = append(installed, app)
	}
	if len(installed) == 0 {
		return lastErr
	}
	if err := svc.store.MarkInstalled(ctx, "instruction", installKey, strings.Join(installed, ",")); err != nil {
		return err
	}
	return lastErr
}

// InstallToTargets installs an item into multiple target agents in one call.
// It downloads the source repo once, reads the resource content, then writes it
// to each target. Install status is recorded per successful target.
func (svc *Service) InstallToTargets(ctx context.Context, kind, installKey string, targetApps []string) error {
	if len(targetApps) == 0 {
		return fmt.Errorf("metadata: no target agents specified")
	}
	item, err := svc.store.GetItem(ctx, kind, installKey)
	if err != nil {
		return fmt.Errorf("metadata: item not found: %w", err)
	}

	entityKind := entities.Kind(item.Kind)
	content := svc.fetchResourceContent(item)
	extraFiles := svc.fetchResourceExtraFiles(item)

	entity := entities.Entity{
		Kind:        entityKind,
		Name:        item.Name,
		Description: item.Description,
		Content:     content,
		ExtraFiles:  extraFiles,
		Repo: &entities.RepoRef{
			Owner:  item.RepoOwner,
			Name:   item.RepoName,
			Branch: item.RepoBranch,
			Path:   item.ItemPath,
		},
	}

	var installed []string
	var lastErr error
	for _, app := range targetApps {
		if _, err := entities.InstallToApp(entity, entityKind, app); err != nil {
			lastErr = fmt.Errorf("metadata: install to %s: %w", app, err)
			continue
		}
		installed = append(installed, app)
	}
	if len(installed) == 0 {
		return lastErr
	}
	if err := svc.store.MarkInstalled(ctx, kind, installKey, strings.Join(installed, ",")); err != nil {
		return err
	}
	return lastErr
}

// UninstallFromTargets removes an entity from the specified apps and updates
// the metadata store's installed status.
func (svc *Service) UninstallFromTargets(ctx context.Context, kind, installKey string, targetApps []string) error {
	if len(targetApps) == 0 {
		return fmt.Errorf("metadata: no target agents specified")
	}
	item, err := svc.store.GetItem(ctx, kind, installKey)
	if err != nil {
		return fmt.Errorf("metadata: item not found: %w", err)
	}

	entityKind := entities.Kind(item.Kind)
	entityName := item.Name

	var removed []string
	var lastErr error
	for _, app := range targetApps {
		if _, _, err := entities.UninstallFromApp(entityName, entityKind, app); err != nil {
			lastErr = fmt.Errorf("metadata: uninstall from %s: %w", app, err)
			continue
		}
		removed = append(removed, app)
	}
	if len(removed) == 0 {
		return lastErr
	}
	for _, app := range removed {
		if err := svc.store.MarkUninstalled(ctx, kind, installKey, app); err != nil {
			lastErr = err
		}
	}
	return lastErr
}

// fetchResourceContent downloads the resource's source repo and reads its
// manifest content. Failures return an empty string so install still creates the
// directory structure; the directory presence is what installed-status detection
// keys on. ItemPath points at the resource directory (skills/plugins) or the
// manifest file itself (agents/instructions) relative to the repo root.
func (svc *Service) fetchResourceContent(item Item) string {
	content, _ := svc.fetchResourceManifest(item)
	return content
}

// fetchResourceExtraFiles downloads the resource's source repo and reads all
// files in the resource directory (excluding the manifest file itself). Returns
// a map of relative path → content for extra files like references/.
func (svc *Service) fetchResourceExtraFiles(item Item) map[string]string {
	if item.RepoOwner == "" || item.RepoName == "" || item.ItemPath == "" {
		return nil
	}
	// Only skills and agents have extra files
	if item.Kind != "skill" && item.Kind != "agent" {
		return nil
	}

	dest := filepath.Join(pathutil.CacheDir(), "metadata-install-extra", item.RepoOwner+"-"+item.RepoName+"-"+item.Name)
	_ = os.RemoveAll(dest)
	defer os.RemoveAll(dest)

	root, err := svc.fetcher.Fetch(item.RepoOwner, item.RepoName, item.RepoBranch, dest)
	if err != nil {
		return nil
	}

	target := filepath.Join(root, filepath.FromSlash(item.ItemPath))
	info, err := os.Stat(target)
	if err != nil || !info.IsDir() {
		return nil
	}

	manifestName := defaultManifest(item.Kind)
	extraFiles := make(map[string]string)

	err = filepath.Walk(target, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // skip errors
		}
		if info.IsDir() {
			return nil
		}
		// Skip the manifest file itself
		if info.Name() == manifestName {
			return nil
		}
		// Read the file content
		data, err := os.ReadFile(path)
		if err != nil {
			return nil // skip unreadable files
		}
		// Compute relative path from the skill directory
		relPath, err := filepath.Rel(target, path)
		if err != nil {
			return nil
		}
		// Use forward slashes for consistency
		relPath = filepath.ToSlash(relPath)
		extraFiles[relPath] = string(data)
		return nil
	})

	if err != nil || len(extraFiles) == 0 {
		return nil
	}
	return extraFiles
}

// fetchResourceManifest downloads the resource's source repo and reads its
// manifest, returning both the content and the manifest path relative to the
// repo root (e.g. "skills/foo/SKILL.md"). The relative path lets callers show
// users where the content came from. Failures return empty strings so callers
// degrade gracefully: install still creates the directory structure, and the
// detail view still renders the indexed metadata without the manifest body.
func (svc *Service) fetchResourceManifest(item Item) (content, manifestRel string) {
	if item.RepoOwner == "" || item.RepoName == "" || item.ItemPath == "" {
		return "", ""
	}
	dest := filepath.Join(pathutil.CacheDir(), "metadata-install", item.RepoOwner+"-"+item.RepoName)
	_ = os.RemoveAll(dest)
	defer os.RemoveAll(dest)

	root, err := svc.fetcher.Fetch(item.RepoOwner, item.RepoName, item.RepoBranch, dest)
	if err != nil {
		return "", ""
	}

	target := filepath.Join(root, filepath.FromSlash(item.ItemPath))
	info, err := os.Stat(target)
	if err != nil {
		return "", ""
	}
	manifest := target
	if info.IsDir() {
		manifest = filepath.Join(target, defaultManifest(item.Kind))
	}
	data, err := os.ReadFile(manifest)
	if err != nil {
		return "", ""
	}
	return string(data), relPath(root, manifest)
}

func defaultManifest(kind string) string {
	switch kind {
	case "skill":
		return "SKILL.md"
	case "agent":
		return "AGENT.md"
	case "instruction":
		return "INSTRUCTION.md"
	case "plugin":
		return "plugin.json"
	}
	return "README.md"
}

// AvailableTargets returns the list of code agent IDs that support the given
// kind, sorted. Used by the UI to populate the install-target picker.
func AvailableTargets(kind string) []string {
	return entities.SupportedApps(entities.Kind(kind))
}

// RefreshItem re-fetches a single item's manifest content from its source
// repository, updates the description if it has changed, and saves the content
// to the database cache. Returns the refreshed detail view.
func (svc *Service) RefreshItem(ctx context.Context, kind, installKey string) (ItemDetail, error) {
	if err := svc.store.Init(ctx); err != nil {
		return ItemDetail{}, err
	}
	return svc.DetailForceRefresh(ctx, kind, installKey)
}

// SearchPaged runs a paginated search and decorates each item with the list of
// code agents it is currently installed to.
func (svc *Service) SearchPaged(ctx context.Context, q SearchQuery) (SearchResponse, error) {
	items, err := svc.store.Search(ctx, q)
	if err != nil {
		return SearchResponse{}, err
	}
	total, err := svc.store.Count(ctx, q)
	if err != nil {
		return SearchResponse{}, err
	}
	if q.Kind == "skill" && strings.TrimSpace(q.Query) != "" && total == 0 {
		limit := q.Limit
		if limit <= 0 {
			limit = 100
		}
		if _, err := svc.RefreshOnlineSkillSearch(ctx, q.Query, limit); err != nil {
			return SearchResponse{}, err
		}
		items, err = svc.store.Search(ctx, q)
		if err != nil {
			return SearchResponse{}, err
		}
		total, err = svc.store.Count(ctx, q)
		if err != nil {
			return SearchResponse{}, err
		}
	}
	for i := range items {
		items[i].InstalledApps = InstalledAppsFor(items[i])
	}
	limit := q.Limit
	if limit <= 0 {
		limit = 100
	}
	return SearchResponse{Items: items, Total: total, Limit: limit, Offset: q.Offset}, nil
}

// InstalledAppsFor returns the code agent IDs where the item is installed on disk.
// An item is considered installed to an app when a directory named after the item
// exists under that app's install path for its kind.
func InstalledAppsFor(item Item) []string {
	kind := entities.Kind(item.Kind)
	apps := entities.AppPathsFor(kind)
	if apps == nil {
		return nil
	}
	name := installDirName(item)
	if name == "" {
		return nil
	}
	var installed []string
	for app, dest := range apps {
		// Expand ~ before joining so the home prefix survives on Windows
		// (filepath.Join would otherwise flip ~/ to ~\ and break Expand).
		resolved := filepath.Join(pathutil.Expand(dest), name)
		if info, err := os.Stat(resolved); err == nil && info.IsDir() {
			installed = append(installed, app)
		}
	}
	return installed
}

// installDirName is the on-disk directory name used when the item is installed.
// It prefers the item Name (matching entities.InstallToApp) and falls back to the
// repo name portion of the install key.
func installDirName(item Item) string {
	if item.Name != "" {
		return item.Name
	}
	parts := strings.Split(item.InstallKey, ":")
	key := parts[0]
	if slash := strings.LastIndex(key, "/"); slash >= 0 {
		return key[slash+1:]
	}
	return key
}

// repoEntry mirrors the JSON shape used in *_repos.json files.
type repoEntry struct {
	Owner       string `json:"owner,omitempty"`
	Name        string `json:"name,omitempty"`
	Branch      string `json:"branch,omitempty"`
	Enabled     *bool  `json:"enabled,omitempty"`
	SkillsPath  string `json:"skillsPath,omitempty"`
	AgentsPath  string `json:"agentsPath,omitempty"`
	PluginPath  string `json:"pluginPath,omitempty"`
	CatalogFile string `json:"catalogFile,omitempty"`
	Description string `json:"description,omitempty"`
	RepoOwner   string `json:"repoOwner,omitempty"`
	RepoName    string `json:"repoName,omitempty"`
	RepoBranch  string `json:"repoBranch,omitempty"`
}

func effectiveOwner(e repoEntry) string {
	if e.RepoOwner != "" {
		return e.RepoOwner
	}
	return e.Owner
}

func effectiveName(e repoEntry) string {
	if e.RepoName != "" {
		return e.RepoName
	}
	return e.Name
}

func effectiveBranch(e repoEntry) string {
	if e.RepoBranch != "" {
		return e.RepoBranch
	}
	if e.Branch != "" {
		return e.Branch
	}
	return "main"
}

func entryName(e repoEntry, key string) string {
	if e.Name != "" {
		return e.Name
	}
	parts := strings.Split(key, "/")
	if len(parts) > 1 {
		return parts[len(parts)-1]
	}
	return key
}

func entryPath(e repoEntry, kind string) string {
	switch kind {
	case "skill":
		return e.SkillsPath
	case "agent":
		return e.AgentsPath
	case "instruction":
		return e.AgentsPath
	case "plugin":
		return e.PluginPath
	}
	return ""
}

func defaultTargetApps(kind string) []string {
	switch kind {
	case "skill":
		return []string{"claude", "codex", "gemini", "copilot"}
	case "agent":
		return []string{"claude", "codex", "gemini", "copilot"}
	case "instruction":
		return []string{"claude", "codex", "gemini", "copilot", "codebuddy", "opencode", "cursor", "windsurf", "amp", "roo"}
	case "plugin":
		return []string{"claude", "codebuddy"}
	}
	return []string{"claude"}
}
