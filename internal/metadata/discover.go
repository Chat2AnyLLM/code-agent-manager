package metadata

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

// DiscoveredResource is one resource (skill/agent/instruction/plugin) found inside a
// repository tree, with metadata parsed from its manifest file.
type DiscoveredResource struct {
	Name           string
	Description    string
	RelPath        string // path of the resource directory/file relative to repo root
	ManifestRel    string // path of the manifest file relative to repo root
	InstallKeyName string // optional stable key suffix when catalog rows share a name
	// Source attribution for catalog rows whose name cell links to the real
	// source repo (e.g. awesome-list catalogs that only point at other repos).
	// When set, the indexed item is attributed to this repo instead of the
	// catalog repo so it merges with a direct scan of the source repo.
	SourceOwner  string
	SourceRepo   string
	SourceBranch string
	SourcePath   string
}

// DiscoverResources walks an extracted repository tree rooted at root and
// returns the individual resources of the given kind. subPath optionally
// narrows the scan to a sub-directory (supporting the "a|b" multi-path syntax
// used in repo configs); when empty the whole tree is scanned.
//
// Conventions, matching the existing CLI fetch behavior:
//   - skill:  directories containing a SKILL.md file
//   - agent:  *.md files (each file is one agent), excluding README/LICENSE
//   - instruction: *.md files (each file is one instruction), excluding README/LICENSE
//   - plugin: directories containing a plugin.json or .claude-plugin/plugin.json
func DiscoverResources(root, subPath string, kind entities.Kind) []DiscoveredResource {
	scanRoots := resolveScanRoots(root, subPath)
	var out []DiscoveredResource
	seen := map[string]bool{}

	for _, scanRoot := range scanRoots {
		// A directly-specified single file (e.g. an agentsPath that points at one
		// .md) is the resource itself: walk it as one file, with no folder
		// constraint. This is the "directly specified" subagent case.
		if info, err := os.Stat(scanRoot); err == nil && !info.IsDir() {
			res, ok := resourceFromFile(root, scanRoot, filepath.Base(scanRoot), kind)
			if ok && !seen[res.Name+"|"+res.RelPath] {
				seen[res.Name+"|"+res.RelPath] = true
				out = append(out, res)
			}
			continue
		}
		_ = filepath.WalkDir(scanRoot, func(p string, d os.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if d.IsDir() {
				if shouldSkipDir(d.Name()) {
					return filepath.SkipDir
				}
				return nil
			}
			res, ok := resourceFromFile(root, p, d.Name(), kind)
			if !ok {
				return nil
			}
			// Subagents follow the convention that they live under an `agents/`
			// folder (agents/, .claude/agents/, agents/<category>/…). A loose
			// .md anywhere in the tree (README, CLAUDE.md, docs/*) is not a
			// subagent. Directly-specified single files are handled above.
			if kind == entities.KindAgent && !underAgentsFolder(root, p) {
				return nil
			}
			if seen[res.Name+"|"+res.RelPath] {
				return nil
			}
			seen[res.Name+"|"+res.RelPath] = true
			out = append(out, res)
			return nil
		})
	}
	return out
}

// underAgentsFolder reports whether p (relative to the repo root) is beneath a
// directory named "agents" at any depth, e.g. agents/foo.md,
// .claude/agents/foo.md, or agents/category/foo.md.
func underAgentsFolder(root, p string) bool {
	rel := relPath(root, p)
	for _, seg := range strings.Split(rel, "/") {
		if seg == "agents" {
			return true
		}
	}
	return false
}

func resolveScanRoots(root, subPath string) []string {
	if subPath == "" {
		return []string{root}
	}
	var roots []string
	for _, sp := range strings.Split(subPath, "|") {
		sp = strings.TrimSpace(strings.Trim(sp, "/"))
		if sp == "" {
			roots = append(roots, root)
			continue
		}
		candidate := filepath.Join(root, sp)
		if _, err := os.Stat(candidate); err == nil {
			roots = append(roots, candidate)
		}
	}
	if len(roots) == 0 {
		roots = append(roots, root)
	}
	return roots
}

func resourceFromFile(root, p, base string, kind entities.Kind) (DiscoveredResource, bool) {
	switch kind {
	case entities.KindSkill:
		if !strings.EqualFold(base, "SKILL.md") {
			return DiscoveredResource{}, false
		}
		dir := filepath.Dir(p)
		name, desc := parseManifest(p, filepath.Base(dir))
		return DiscoveredResource{
			Name:        name,
			Description: desc,
			RelPath:     relPath(root, dir),
			ManifestRel: relPath(root, p),
		}, true

	case entities.KindPlugin:
		if !strings.EqualFold(base, "plugin.json") {
			return DiscoveredResource{}, false
		}
		dir := filepath.Dir(p)
		// .claude-plugin/plugin.json → the plugin is the parent of that dir.
		if strings.EqualFold(filepath.Base(dir), ".claude-plugin") {
			dir = filepath.Dir(dir)
		}
		name, desc := parsePluginJSON(p, filepath.Base(dir))
		return DiscoveredResource{
			Name:        name,
			Description: desc,
			RelPath:     relPath(root, dir),
			ManifestRel: relPath(root, p),
		}, true

	case entities.KindAgent, entities.KindPrompt, entities.KindInstruction:
		if !strings.HasSuffix(strings.ToLower(base), ".md") {
			return DiscoveredResource{}, false
		}
		if isDocFile(base) {
			return DiscoveredResource{}, false
		}
		name := strings.TrimSuffix(base, filepath.Ext(base))
		parsedName, desc := parseManifest(p, name)
		return DiscoveredResource{
			Name:        parsedName,
			Description: desc,
			RelPath:     relPath(root, p),
			ManifestRel: relPath(root, p),
		}, true
	}
	return DiscoveredResource{}, false
}

func relPath(root, p string) string {
	rel, err := filepath.Rel(root, p)
	if err != nil {
		return p
	}
	return filepath.ToSlash(rel)
}

func shouldSkipDir(name string) bool {
	switch name {
	case ".git", "node_modules", ".github", "backups", "dist", "build", "vendor":
		return true
	}
	return false
}

func isDocFile(base string) bool {
	lower := strings.ToLower(strings.TrimSuffix(base, filepath.Ext(base)))
	switch lower {
	case "readme", "license", "licence", "contributing", "changelog", "code_of_conduct", "security":
		return true
	}
	return false
}

// parseManifest reads a markdown manifest and extracts name/description from
// YAML frontmatter when present, falling back to the provided default name and
// the first non-empty heading/paragraph for the description.
func parseManifest(path, fallbackName string) (name, description string) {
	name = fallbackName
	data, err := os.ReadFile(path)
	if err != nil {
		return name, ""
	}
	fmName, fmDesc, ok := parseFrontmatter(string(data))
	if ok {
		if fmName != "" {
			name = fmName
		}
		description = fmDesc
	}
	return name, description
}

// parseFrontmatter extracts name and description from a leading YAML
// frontmatter block delimited by "---" lines. It is intentionally minimal:
// only flat "key: value" pairs are supported, which covers SKILL.md/AGENT.md.
func parseFrontmatter(content string) (name, description string, ok bool) {
	content = strings.ReplaceAll(content, "\r\n", "\n")
	if !strings.HasPrefix(content, "---\n") {
		return "", "", false
	}
	end := strings.Index(content[4:], "\n---")
	if end < 0 {
		return "", "", false
	}
	block := content[4 : 4+end]
	for _, line := range strings.Split(block, "\n") {
		key, value, found := strings.Cut(line, ":")
		if !found {
			continue
		}
		key = strings.TrimSpace(strings.ToLower(key))
		value = strings.TrimSpace(value)
		value = strings.Trim(value, "\"'")
		switch key {
		case "name":
			name = value
		case "description":
			description = value
		}
	}
	return name, description, true
}

// parsePluginJSON extracts name/description from a plugin.json manifest.
func parsePluginJSON(path, fallbackName string) (name, description string) {
	name = fallbackName
	data, err := os.ReadFile(path)
	if err != nil {
		return name, ""
	}
	// Minimal extraction avoiding a struct: reuse the frontmatter-free JSON.
	if n := jsonStringField(string(data), "name"); n != "" {
		name = n
	}
	description = jsonStringField(string(data), "description")
	return name, description
}

// jsonStringField does a tiny, dependency-free extraction of a top-level string
// field from a JSON object. Good enough for plugin.json name/description.
func jsonStringField(content, field string) string {
	needle := "\"" + field + "\""
	idx := strings.Index(content, needle)
	if idx < 0 {
		return ""
	}
	rest := content[idx+len(needle):]
	colon := strings.Index(rest, ":")
	if colon < 0 {
		return ""
	}
	rest = rest[colon+1:]
	q1 := strings.Index(rest, "\"")
	if q1 < 0 {
		return ""
	}
	rest = rest[q1+1:]
	q2 := strings.Index(rest, "\"")
	if q2 < 0 {
		return ""
	}
	return rest[:q2]
}
