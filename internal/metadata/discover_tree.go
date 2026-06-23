package metadata

import (
	"context"
	"errors"
	"path"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

// DiscoverFromTree builds a list of discovered resources from a remote
// repository tree, without touching the filesystem. paths is the recursive
// list of blob paths returned by RepoBrowser.ListTree (one entry per file,
// repo-relative, forward slashes). subPath optionally narrows the scan to a
// sub-directory and supports the same "a|b" multi-path syntax repoconfig uses.
//
// Manifest contents (name/description) are *not* fetched here. Callers may
// optionally hydrate name/description by calling HydrateResourceMetadata
// afterwards — but that's per-resource HTTP and a metadata refresh of ~700
// repos × ~50 resources each would be ~35k extra requests, so the default is
// "leave name as the dir/file basename and description blank".
func DiscoverFromTree(paths []string, subPath string, kind entities.Kind) []DiscoveredResource {
	scanPrefixes := resolveScanPrefixes(subPath)
	seen := map[string]bool{}
	var out []DiscoveredResource

	for _, p := range paths {
		if !underScanPrefix(p, scanPrefixes) {
			continue
		}
		if pathHasSkippedSegment(p) {
			continue
		}
		base := path.Base(p)
		res, ok := resourceFromTreePath(p, base, kind)
		if !ok {
			continue
		}
		if kind == entities.KindAgent && !pathUnderAgentsFolder(p) {
			continue
		}
		key := res.Name + "|" + res.RelPath
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, res)
	}
	return out
}

// HydrateResourceMetadata optionally fetches the manifest for each resource via
// the browser and fills in name/description from frontmatter. It is OK for the
// fetch to fail on individual resources — those keep their fallback names. The
// returned slice is the same length as input with metadata enriched in place.
//
// This is opt-in because for ~36k items it would burn ~36k HTTP calls. The
// metadata index works without it; callers that want richer first-page text
// (e.g. UI search) can run it for visible items only.
func HydrateResourceMetadata(ctx context.Context, browser RepoBrowser, owner, repo, branch string, resources []DiscoveredResource, kind entities.Kind) []DiscoveredResource {
	if browser == nil || len(resources) == 0 {
		return resources
	}
	for i, res := range resources {
		if res.ManifestRel == "" {
			continue
		}
		data, err := browser.FetchFile(ctx, owner, repo, branch, res.ManifestRel)
		if err != nil {
			if errors.Is(err, ErrFileNotFound) {
				continue
			}
			continue
		}
		switch kind {
		case entities.KindPlugin:
			if name := jsonStringField(string(data), "name"); name != "" {
				resources[i].Name = name
			}
			if desc := jsonStringField(string(data), "description"); desc != "" {
				resources[i].Description = desc
			}
		default:
			if fmName, fmDesc, ok := parseFrontmatter(string(data)); ok {
				if fmName != "" {
					resources[i].Name = fmName
				}
				if fmDesc != "" {
					resources[i].Description = fmDesc
				}
			}
		}
	}
	return resources
}

func resolveScanPrefixes(subPath string) []string {
	if subPath == "" {
		return nil // nil = scan everything
	}
	var prefixes []string
	for _, sp := range strings.Split(subPath, "|") {
		sp = strings.TrimSpace(strings.Trim(sp, "/"))
		if sp == "" {
			return nil // an empty entry means "scan all"
		}
		prefixes = append(prefixes, sp+"/")
	}
	return prefixes
}

// underScanPrefix reports whether p falls under one of the configured scan
// prefixes. nil prefixes means "everything". An exact match on the prefix
// (single-file subPath) also counts.
func underScanPrefix(p string, prefixes []string) bool {
	if prefixes == nil {
		return true
	}
	for _, pre := range prefixes {
		if strings.HasPrefix(p, pre) {
			return true
		}
		if p+"/" == pre || p == strings.TrimSuffix(pre, "/") {
			return true
		}
	}
	return false
}

// pathHasSkippedSegment mirrors shouldSkipDir on the filesystem-based scanner:
// a tree entry buried under .git/, node_modules/, dist/, etc. is noise.
func pathHasSkippedSegment(p string) bool {
	for _, seg := range strings.Split(p, "/") {
		if shouldSkipDir(seg) {
			return true
		}
	}
	return false
}

func pathUnderAgentsFolder(p string) bool {
	for _, seg := range strings.Split(p, "/") {
		if seg == "agents" {
			return true
		}
	}
	return false
}

// resourceFromTreePath is the path-only equivalent of resourceFromFile. It
// derives the resource record from the path alone — name defaults to the
// dir/file basename — so a refresh never has to read file bytes off disk.
func resourceFromTreePath(p, base string, kind entities.Kind) (DiscoveredResource, bool) {
	switch kind {
	case entities.KindSkill:
		if !strings.EqualFold(base, "SKILL.md") {
			return DiscoveredResource{}, false
		}
		dir := path.Dir(p)
		return DiscoveredResource{
			Name:        path.Base(dir),
			RelPath:     dir,
			ManifestRel: p,
		}, true

	case entities.KindPlugin:
		if !strings.EqualFold(base, "plugin.json") {
			return DiscoveredResource{}, false
		}
		dir := path.Dir(p)
		if strings.EqualFold(path.Base(dir), ".claude-plugin") {
			dir = path.Dir(dir)
		}
		return DiscoveredResource{
			Name:        path.Base(dir),
			RelPath:     dir,
			ManifestRel: p,
		}, true

	case entities.KindAgent, entities.KindPrompt, entities.KindInstruction:
		if !strings.HasSuffix(strings.ToLower(base), ".md") {
			return DiscoveredResource{}, false
		}
		if isDocFile(base) {
			return DiscoveredResource{}, false
		}
		name := strings.TrimSuffix(base, ".md")
		// Cope with mixed-case .MD too.
		if idx := strings.LastIndex(base, "."); idx > 0 {
			name = base[:idx]
		}
		return DiscoveredResource{
			Name:        name,
			RelPath:     p,
			ManifestRel: p,
		}, true
	}
	return DiscoveredResource{}, false
}
