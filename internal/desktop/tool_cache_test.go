package desktop

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// withTempCacheDir points the detection cache at an isolated temp directory
// for the test and restores the original value on cleanup.
func withTempCacheDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	previous := os.Getenv("CAM_CACHE_DIR")
	os.Setenv("CAM_CACHE_DIR", dir)
	t.Cleanup(func() { os.Setenv("CAM_CACHE_DIR", previous) })
	return dir
}

func TestDetectionCacheGetMissing(t *testing.T) {
	cache := newDetectionCache()
	cache.loadOnce()

	if _, fresh := cache.get("does-not-exist"); fresh {
		t.Fatal("missing entry should not be fresh")
	}
}

func TestDetectionCachePutThenGetFresh(t *testing.T) {
	cache := newDetectionCache()
	cache.loadOnce()

	cache.put("claude-code", true, "1.2.3")
	entry, fresh := cache.get("claude-code")
	if !fresh {
		t.Fatal("just-cached entry should be fresh")
	}
	if !entry.Installed || entry.Version != "1.2.3" {
		t.Fatalf("entry = %+v, want {Installed:true Version:1.2.3}", entry)
	}
}

func TestDetectionCacheStaleAfterTTL(t *testing.T) {
	cache := newDetectionCache()
	cache.loadOnce()
	cache.put("gemini-cli", true, "9.9.9")

	// Backdate the entry past detectionTTL so it reads as stale.
	cache.mu.Lock()
	e := cache.entries["gemini-cli"]
	e.DetectedAt = time.Now().Add(-detectionTTL - time.Second)
	cache.entries["gemini-cli"] = e
	cache.mu.Unlock()

	if _, fresh := cache.get("gemini-cli"); fresh {
		t.Fatal("backdated entry should be stale")
	}
}

func TestDetectionCachePersistLoadRoundTrip(t *testing.T) {
	withTempCacheDir(t)
	cache := newDetectionCache()
	cache.loadOnce()

	cache.put("claude-code", true, "1.2.3")
	cache.put("gemini-cli", false, "")
	cache.persist()

	// A fresh cache over the same on-disk file should see both entries.
	loaded := newDetectionCache()
	loaded.loadOnce()
	if _, fresh := loaded.get("claude-code"); !fresh {
		t.Fatal("claude-code should load from disk fresh")
	}
	if _, fresh := loaded.get("gemini-cli"); !fresh {
		t.Fatal("gemini-cli should load from disk fresh")
	}
}

func TestDetectionCacheWritesToToolsSubdir(t *testing.T) {
	dir := withTempCacheDir(t)
	cache := newDetectionCache()
	cache.loadOnce()
	cache.put("claude-code", true, "1.0.0")
	cache.persist()

	path := filepath.Join(dir, "tools", "detection.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read cache file: %v", err)
	}
	var file detectionCacheFile
	if err := json.Unmarshal(raw, &file); err != nil {
		t.Fatalf("unmarshal cache file: %v", err)
	}
	if entry, ok := file.Tools["claude-code"]; !ok || entry.Version != "1.0.0" {
		t.Fatalf("cache file = %+v, want claude-code 1.0.0", file.Tools)
	}
}

func TestDetectionCacheLoadMissingFileIsNoOp(t *testing.T) {
	withTempCacheDir(t)
	cache := newDetectionCache()
	cache.loadOnce() // no file exists yet
	if _, fresh := cache.get("anything"); fresh {
		t.Fatal("empty cache should report nothing fresh")
	}
}

func TestDetectionCacheLoadCorruptFileIsNoOp(t *testing.T) {
	dir := withTempCacheDir(t)
	if err := os.MkdirAll(filepath.Join(dir, "tools"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "tools", "detection.json"), []byte("{not json"), 0o600); err != nil {
		t.Fatal(err)
	}
	cache := newDetectionCache()
	cache.loadOnce() // corrupt file must not panic or pollute
	if _, fresh := cache.get("anything"); fresh {
		t.Fatal("corrupt cache file should leave nothing fresh")
	}
}
