package metadata

import (
	"context"
)

// ItemDetail is the full view of a single metadata item: its indexed record
// (decorated with installed-app status) plus the rendered manifest content.
// When the content has been previously fetched and cached in the database, it
// is returned directly without a network call. A caller can force a re-fetch
// via DetailForceRefresh.
type ItemDetail struct {
	Item     Item   `json:"item"`
	Content  string `json:"content"`
	Manifest string `json:"manifest_path"`
}

// Detail returns the full detail view for one item. The content is served from
// the database cache when available; only the first call (or a stale cache)
// triggers a network fetch. Use DetailForceRefresh to bypass the cache.
func (svc *Service) Detail(ctx context.Context, kind, installKey string) (ItemDetail, error) {
	return svc.detailImpl(ctx, kind, installKey, false)
}

// DetailForceRefresh always re-fetches the manifest from the source repository,
// updates the database cache, and returns the fresh content. It also updates the
// description if the upstream manifest has changed.
func (svc *Service) DetailForceRefresh(ctx context.Context, kind, installKey string) (ItemDetail, error) {
	return svc.detailImpl(ctx, kind, installKey, true)
}

func (svc *Service) detailImpl(ctx context.Context, kind, installKey string, force bool) (ItemDetail, error) {
	item, err := svc.store.GetItem(ctx, kind, installKey)
	if err != nil {
		return ItemDetail{}, err
	}
	item.InstalledApps = InstalledAppsFor(item)

	if !force && item.Content != "" {
		return ItemDetail{Item: item, Content: item.Content, Manifest: item.ManifestPath}, nil
	}

	content, manifest := svc.fetchResourceManifest(item)
	cachedAt := timeNow()

	if content != "" {
		description := extractDescription(content, item.Kind)
		if description != "" {
			_ = svc.store.SaveItemContentAndDescription(ctx, kind, installKey, content, cachedAt, manifest, description)
			item.Content = content
			item.ContentCachedAt = cachedAt
			item.ManifestPath = manifest
			item.Description = description
		} else {
			_ = svc.store.SaveContent(ctx, kind, installKey, content, cachedAt, manifest)
			item.Content = content
			item.ContentCachedAt = cachedAt
			item.ManifestPath = manifest
		}
	} else if force {
		_ = svc.store.SaveContent(ctx, kind, installKey, "", cachedAt, "")
		item.Content = ""
		item.ContentCachedAt = cachedAt
		item.ManifestPath = ""
	}

	return ItemDetail{Item: item, Content: content, Manifest: manifest}, nil
}

// extractDescription pulls the first non-empty paragraph from a markdown
// manifest as a human-readable description. Returns "" when nothing useful
// is found.
func extractDescription(content, kind string) string {
	inFrontmatter := false
	for _, line := range splitLines(content) {
		trimmed := trimSpace(line)
		if trimmed == "---" {
			inFrontmatter = !inFrontmatter
			continue
		}
		if inFrontmatter {
			if key, val := parseYAMLField(trimmed); key == "description" && val != "" {
				return val
			}
			continue
		}
		if trimmed == "" || trimmed[0] == '#' {
			continue
		}
		return trimmed
	}
	return ""
}

func splitLines(s string) []string {
	var lines []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			lines = append(lines, s[start:i])
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}

func trimSpace(s string) string {
	start, end := 0, len(s)
	for start < end && (s[start] == ' ' || s[start] == '\t' || s[start] == '\r') {
		start++
	}
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t' || s[end-1] == '\r') {
		end--
	}
	return s[start:end]
}

func parseYAMLField(line string) (string, string) {
	for i, ch := range line {
		if ch == ':' {
			key := trimSpace(line[:i])
			val := trimSpace(line[i+1:])
			if len(val) >= 2 && val[0] == '"' && val[len(val)-1] == '"' {
				val = val[1 : len(val)-1]
			}
			return key, val
		}
	}
	return "", ""
}
