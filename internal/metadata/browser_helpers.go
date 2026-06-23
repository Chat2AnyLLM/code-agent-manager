package metadata

import (
	"context"
	"path"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

// contextWithTimeout wraps context.WithTimeout against a fresh background ctx.
// Detail/install paths don't have a request context handy and we don't want a
// stalled GitHub call to hang forever.
func contextWithTimeout(d time.Duration) (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), d)
}

// pathJoinClean joins ItemPath and a suffix using forward slashes, stripping
// any trailing slash on the base. ItemPath is forward-slash, repo-relative.
func pathJoinClean(base, suffix string) string {
	base = strings.TrimSuffix(strings.TrimSpace(base), "/")
	suffix = strings.TrimPrefix(strings.TrimSpace(suffix), "/")
	if base == "" {
		return suffix
	}
	if suffix == "" {
		return base
	}
	return base + "/" + suffix
}

// inferCatalogFromPaths replicates inferCatalogFile() against a path list
// (no filesystem). When a catalog file like FULL-SKILLS.md is present in the
// tree, return its path so the caller can fetch and parse it.
func inferCatalogFromPaths(paths []string, kind entities.Kind) string {
	candidates := catalogCandidates(kind)
	pathSet := make(map[string]struct{}, len(paths))
	for _, p := range paths {
		pathSet[p] = struct{}{}
	}
	for _, candidate := range candidates {
		if _, ok := pathSet[candidate]; ok {
			return candidate
		}
	}
	return ""
}

// discoverCatalogFromTree fetches one catalog file via the browser and parses
// it the same way DiscoverCatalogResources does. Mirrors the legacy filesystem
// path so callers can pick the catalog branch transparently.
func (svc *Service) discoverCatalogFromTree(ctx context.Context, job repoJob, kind entities.Kind) []DiscoveredResource {
	catalogFile := strings.TrimSpace(strings.Trim(job.catalogFile, "/"))
	if catalogFile == "" {
		return nil
	}
	data, err := svc.browser.FetchFile(ctx, job.owner, job.repo, job.branch, catalogFile)
	if err != nil {
		return nil
	}
	return parseCatalogMarkdown(string(data), path.Clean(catalogFile), kind)
}
