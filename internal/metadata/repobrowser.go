package metadata

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// RepoBrowser is the metadata-only alternative to RepoFetcher. Instead of
// cloning an entire repository archive, it lists the repository tree via the
// GitHub Trees API and fetches individual files via raw.githubusercontent.com.
// One bulk refresh of ~700 repos transfers a few MB instead of hundreds of MB,
// and the heaviest single-repo case (24k SKILL.md) stays inside a single HTTP
// response instead of expanding to gigabytes on disk.
type RepoBrowser interface {
	// ListTree returns every blob path in the repo at branch, plus a Truncated
	// flag set when GitHub capped the response (the API caps at ~100k entries).
	// The error is non-nil only for transport/auth/HTTP failures; an empty repo
	// is a successful zero-entry result.
	ListTree(ctx context.Context, owner, repo, branch string) (TreeListing, error)

	// FetchFile downloads one file by repo-relative path and returns its bytes.
	// Missing files surface as ErrFileNotFound so callers can degrade gracefully
	// (a SKILL.md that does not exist on the upstream branch is not a crash).
	FetchFile(ctx context.Context, owner, repo, branch, path string) ([]byte, error)
}

// TreeListing is the result of one Tree API call.
type TreeListing struct {
	Entries   []TreeEntry
	Truncated bool
}

// TreeEntry is one blob in the repository tree. Only blobs are surfaced;
// sub-tree and commit entries are filtered out so callers can scan paths
// without checking types.
type TreeEntry struct {
	Path string
	Size int64
}

// ErrFileNotFound is returned by FetchFile when the requested path does not
// exist in the repository tree. Callers use this to distinguish "missing
// resource" (degrade gracefully) from "network error" (record as failure).
var ErrFileNotFound = fmt.Errorf("repobrowser: file not found")

// NewHTTPRepoBrowser returns a browser that talks to GitHub directly. It reads
// GITHUB_TOKEN from the environment when present so authenticated calls get
// the 5000-req/h budget; without a token the 60-req/h anonymous budget is
// usually still enough for a small index but rate-limit errors will surface.
func NewHTTPRepoBrowser() RepoBrowser {
	return &httpRepoBrowser{
		client: &http.Client{Timeout: 30 * time.Second},
		token:  strings.TrimSpace(os.Getenv("GITHUB_TOKEN")),
	}
}

type httpRepoBrowser struct {
	client *http.Client
	token  string
}

type ghTreeResponse struct {
	Tree []struct {
		Path string `json:"path"`
		Type string `json:"type"`
		Size int64  `json:"size"`
	} `json:"tree"`
	Truncated bool `json:"truncated"`
}

func (b *httpRepoBrowser) ListTree(ctx context.Context, owner, repo, branch string) (TreeListing, error) {
	if branch == "" {
		branch = "main"
	}
	u := fmt.Sprintf("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1",
		url.PathEscape(owner), url.PathEscape(repo), url.PathEscape(branch))

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return TreeListing{}, err
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	if b.token != "" {
		req.Header.Set("Authorization", "Bearer "+b.token)
	}
	resp, err := b.client.Do(req)
	if err != nil {
		return TreeListing{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return TreeListing{}, fmt.Errorf("repobrowser: tree not found %s/%s@%s", owner, repo, branch)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return TreeListing{}, fmt.Errorf("repobrowser: tree %s/%s@%s: %s: %s", owner, repo, branch, resp.Status, strings.TrimSpace(string(body)))
	}
	var parsed ghTreeResponse
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		return TreeListing{}, err
	}
	entries := make([]TreeEntry, 0, len(parsed.Tree))
	for _, t := range parsed.Tree {
		if t.Type != "blob" {
			continue
		}
		entries = append(entries, TreeEntry{Path: t.Path, Size: t.Size})
	}
	return TreeListing{Entries: entries, Truncated: parsed.Truncated}, nil
}

func (b *httpRepoBrowser) FetchFile(ctx context.Context, owner, repo, branch, path string) ([]byte, error) {
	if branch == "" {
		branch = "main"
	}
	u := fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/%s/%s",
		url.PathEscape(owner), url.PathEscape(repo), url.PathEscape(branch), path)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	if b.token != "" {
		req.Header.Set("Authorization", "Bearer "+b.token)
	}
	resp, err := b.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return nil, ErrFileNotFound
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return nil, fmt.Errorf("repobrowser: raw %s/%s@%s/%s: %s: %s", owner, repo, branch, path, resp.Status, strings.TrimSpace(string(body)))
	}
	// Cap reads at 8 MB so a hostile-but-public file can't blow up the process.
	data, err := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if err != nil {
		return nil, err
	}
	return data, nil
}
