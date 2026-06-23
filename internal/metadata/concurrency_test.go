package metadata

import (
	"context"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"
)

// concurrentBrowser records the maximum number of in-flight ListTree calls so
// we can assert metadata refresh actually runs in parallel, and serves a
// deterministic one-skill tree so results are checkable. This is the metadata
// pipeline's hot path — RefreshAll talks to a RepoBrowser, never a fetcher,
// since the pipeline switched to ListTree/FetchFile.
type concurrentBrowser struct {
	inFlight atomic.Int32
	maxSeen  atomic.Int32
	calls    atomic.Int32
}

func (c *concurrentBrowser) ListTree(_ context.Context, _, repo, _ string) (TreeListing, error) {
	c.calls.Add(1)
	cur := c.inFlight.Add(1)
	for {
		prev := c.maxSeen.Load()
		if cur <= prev || c.maxSeen.CompareAndSwap(prev, cur) {
			break
		}
	}
	// Hold the slot briefly so concurrent workers reliably overlap.
	time.Sleep(5 * time.Millisecond)
	defer c.inFlight.Add(-1)
	return TreeListing{
		Entries: []TreeEntry{
			{Path: "skills/" + repo + "-skill/SKILL.md", Size: 64},
		},
	}, nil
}

func (c *concurrentBrowser) FetchFile(_ context.Context, _, repo, _, _ string) ([]byte, error) {
	return []byte("---\nname: " + repo + "-skill\ndescription: x\n---\n"), nil
}

func TestRefreshAllRunsConcurrently(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("CAM_CACHE_DIR", filepath.Join(dir, "cache"))
	s := NewStore(filepath.Join(dir, "cam.db"))

	cb := &concurrentBrowser{}
	svc := NewService(s).WithBrowser(cb)

	summary, err := svc.RefreshAll(ctx)
	if err != nil {
		t.Fatalf("RefreshAll: %v", err)
	}
	if summary.ItemsAdded == 0 {
		t.Fatal("expected items added")
	}
	if cb.calls.Load() == 0 {
		t.Fatal("browser was never called")
	}
	// With many bundled repos and an 8-worker pool, at least 2 ListTree calls
	// must have overlapped. (If the machine is extremely slow this could be
	// flaky; the barrier in ListTree makes overlap reliable.)
	if cb.maxSeen.Load() < 2 {
		t.Fatalf("expected concurrent ListTree calls, max in-flight was %d", cb.maxSeen.Load())
	}
}
