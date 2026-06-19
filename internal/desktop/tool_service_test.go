package desktop

import (
	"testing"
)

func TestToolServiceList(t *testing.T) {
	withTempCacheDir(t)
	tools, err := NewToolService().List()
	if err != nil {
		t.Fatalf("list tools: %v", err)
	}
	if len(tools) == 0 {
		t.Fatal("expected bundled tools")
	}
}

// TestToolServiceListCachesDetection confirms a second List() call reuses the
// cached detection results rather than re-probing every binary. We assert this
// by snapshotting the first result, clearing the registry's binaries out of
// PATH is not feasible here, so instead we verify the cache holds an entry for
// every tool after the first call and that a second call returns matching DTOs.
func TestToolServiceListCachesDetection(t *testing.T) {
	withTempCacheDir(t)
	svc := NewToolService()

	first, err := svc.List()
	if err != nil {
		t.Fatalf("first list: %v", err)
	}
	// Every returned tool should now have a fresh cache entry.
	for _, tool := range first {
		if _, fresh := svc.cache.get(tool.Name); !fresh {
			t.Fatalf("tool %q not cached after List()", tool.Name)
		}
	}

	second, err := svc.List()
	if err != nil {
		t.Fatalf("second list: %v", err)
	}
	if len(first) != len(second) {
		t.Fatalf("len changed: %d -> %d", len(first), len(second))
	}
	for i, tool := range first {
		if tool != second[i] {
			t.Fatalf("tool %d differs after re-list: %+v vs %+v", i, tool, second[i])
		}
	}
}
