package catalogconfig

import (
	"net/url"
	"path"
	"regexp"
	"strings"
)

// GitHubRepo identifies a GitHub repository and optional branch/ref.
type GitHubRepo struct {
	Owner  string
	Repo   string
	Branch string
}

// BranchOrDefault returns the configured branch or main.
func (r GitHubRepo) BranchOrDefault() string {
	if strings.TrimSpace(r.Branch) == "" {
		return "main"
	}
	return r.Branch
}

// RawURL returns the raw.githubusercontent.com URL for a repo-relative file.
func (r GitHubRepo) RawURL(filePath string) string {
	return "https://raw.githubusercontent.com/" + url.PathEscape(r.Owner) + "/" + url.PathEscape(r.Repo) + "/" + url.PathEscape(r.BranchOrDefault()) + "/" + CleanSourcePath(filePath)
}

// BlobURL returns the github.com blob URL for a repo-relative file.
func (r GitHubRepo) BlobURL(filePath string) string {
	return "https://github.com/" + url.PathEscape(r.Owner) + "/" + url.PathEscape(r.Repo) + "/blob/" + url.PathEscape(r.BranchOrDefault()) + "/" + CleanSourcePath(filePath)
}

// ParseGitHubRepoURL extracts owner/repo/ref from a GitHub repository URL.
func ParseGitHubRepoURL(raw string) (GitHubRepo, bool) {
	s := strings.TrimSpace(raw)
	if s == "" {
		return GitHubRepo{}, false
	}
	u, err := url.Parse(s)
	if err != nil || !strings.EqualFold(strings.TrimPrefix(u.Host, "www."), "github.com") {
		return GitHubRepo{}, false
	}
	parts := strings.Split(strings.Trim(strings.TrimSuffix(u.Path, ".git"), "/"), "/")
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return GitHubRepo{}, false
	}
	repo := GitHubRepo{Owner: parts[0], Repo: strings.TrimSuffix(parts[1], ".git")}
	if len(parts) >= 4 && (parts[2] == "tree" || parts[2] == "blob") {
		repo.Branch = parts[3]
	}
	return repo, true
}

var slugNonWord = regexp.MustCompile(`[^a-z0-9]+`)

// SourceSlug converts a source display name into a stable storage key.
func SourceSlug(name string) string {
	s := strings.ToLower(strings.TrimSpace(name))
	s = slugNonWord.ReplaceAllString(s, "_")
	s = strings.Trim(s, "_")
	if s == "" {
		return "unknown_source"
	}
	return s
}

// CleanSourcePath normalizes config source paths to repo-relative slash paths.
func CleanSourcePath(p string) string {
	p = strings.TrimSpace(strings.Trim(p, "/"))
	if p == "" {
		return ""
	}
	return path.Clean(p)
}

// JoinSourcePath joins repo-relative path fragments.
func JoinSourcePath(parts ...string) string {
	cleaned := make([]string, 0, len(parts))
	for _, part := range parts {
		if c := CleanSourcePath(part); c != "" {
			cleaned = append(cleaned, c)
		}
	}
	if len(cleaned) == 0 {
		return ""
	}
	return path.Join(cleaned...)
}
