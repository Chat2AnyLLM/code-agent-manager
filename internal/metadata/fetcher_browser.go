package metadata

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// fetcherBackedBrowser adapts a RepoFetcher (the legacy clone-zip download)
// into a RepoBrowser by extracting once per repo into a temp dir, indexing the
// resulting tree, and serving ListTree/FetchFile from the filesystem.
//
// This is *only* used in tests: production code wires NewHTTPRepoBrowser
// directly. WithFetcher transparently wraps the supplied fetcher in this
// adapter so existing fakeFetcher-based tests keep working without rewrites
// while the metadata pipeline now goes through RepoBrowser exclusively.
type fetcherBackedBrowser struct {
	inner RepoFetcher
	mu    sync.Mutex
	cache map[string]string // owner/repo@branch → extracted root path
}

func newFetcherBackedBrowser(inner RepoFetcher) *fetcherBackedBrowser {
	return &fetcherBackedBrowser{
		inner: inner,
		cache: map[string]string{},
	}
}

func (f *fetcherBackedBrowser) ensure(owner, repo, branch string) (string, error) {
	key := owner + "/" + repo + "@" + branch
	f.mu.Lock()
	defer f.mu.Unlock()
	if root, ok := f.cache[key]; ok {
		return root, nil
	}
	dest, err := os.MkdirTemp("", "cam-fetcher-browser-")
	if err != nil {
		return "", err
	}
	root, err := f.inner.Fetch(owner, repo, branch, dest)
	if err != nil {
		_ = os.RemoveAll(dest)
		return "", err
	}
	f.cache[key] = root
	return root, nil
}

func (f *fetcherBackedBrowser) ListTree(ctx context.Context, owner, repo, branch string) (TreeListing, error) {
	root, err := f.ensure(owner, repo, branch)
	if err != nil {
		return TreeListing{}, err
	}
	var entries []TreeEntry
	err = filepath.Walk(root, func(p string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return nil
		}
		if info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(root, p)
		if err != nil {
			return nil
		}
		rel = filepath.ToSlash(rel)
		// Hide synthetic helpers if any test ever leaves them in /tmp; skip
		// dotfiles at the repo root the same way GitHub trees do.
		if strings.HasPrefix(rel, ".") {
			return nil
		}
		entries = append(entries, TreeEntry{Path: rel, Size: info.Size()})
		return nil
	})
	if err != nil {
		return TreeListing{}, err
	}
	return TreeListing{Entries: entries}, nil
}

func (f *fetcherBackedBrowser) FetchFile(ctx context.Context, owner, repo, branch, path string) ([]byte, error) {
	root, err := f.ensure(owner, repo, branch)
	if err != nil {
		return nil, err
	}
	abs := filepath.Join(root, filepath.FromSlash(path))
	data, err := os.ReadFile(abs)
	if os.IsNotExist(err) {
		return nil, ErrFileNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("fetcher-browser: %s/%s@%s/%s: %w", owner, repo, branch, path, err)
	}
	return data, nil
}
