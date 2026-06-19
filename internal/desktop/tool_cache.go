package desktop

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// detectionTTL bounds how long a cached tool-detection result is served
// without re-probing the binary. Each probe spawns a subprocess (`<bin>
// --version`), which is the dominant cost of the Agents page; CLI
// install/version state changes rarely, so even a short TTL makes repeat
// page loads instant while still picking up installs/upgrades within the
// window. Mirrors the model-discovery cache TTL convention in
// internal/providers/models.go.
const detectionTTL = 5 * time.Minute

// detectionEntry is one cached tool-detection result.
type detectionEntry struct {
	Installed  bool      `json:"installed"`
	Version    string    `json:"version"`
	DetectedAt time.Time `json:"detected_at"`
}

// detectionCacheFile is the on-disk shape at cachePath().
type detectionCacheFile struct {
	Tools map[string]detectionEntry `json:"tools"`
}

// detectionCache memoizes tool-detection results. It is held on the
// long-lived sidecar ToolService, so the in-memory map makes repeat
// Agents-page loads free within a process; the on-disk file additionally
// lets a freshly started sidecar serve the last-known results immediately.
type detectionCache struct {
	mu      sync.RWMutex
	loaded  bool // disk has been read into entries
	path    string
	entries map[string]detectionEntry
}

func newDetectionCache() *detectionCache {
	return &detectionCache{
		path:    filepath.Join(pathutil.CacheDir(), "tools", "detection.json"),
		entries: map[string]detectionEntry{},
	}
}

// loadOnce reads the on-disk cache into memory the first time it is called.
// Best-effort: a missing or corrupt file leaves the cache empty so callers
// fall through to a fresh probe.
func (c *detectionCache) loadOnce() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.loaded {
		return
	}
	c.loaded = true
	raw, err := os.ReadFile(c.path)
	if err != nil {
		return
	}
	var file detectionCacheFile
	if err := json.Unmarshal(raw, &file); err != nil {
		return
	}
	for name, entry := range file.Tools {
		c.entries[name] = entry
	}
}

// get returns the cached entry for name and whether it is still fresh
// (within detectionTTL). A stale or missing entry reports fresh=false so the
// caller knows to re-probe.
func (c *detectionCache) get(name string) (detectionEntry, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	entry, ok := c.entries[name]
	if !ok {
		return detectionEntry{}, false
	}
	if entry.DetectedAt.IsZero() || time.Since(entry.DetectedAt) > detectionTTL {
		return entry, false
	}
	return entry, true
}

// put stores a fresh detection result.
func (c *detectionCache) put(name string, installed bool, version string) {
	c.mu.Lock()
	c.entries[name] = detectionEntry{Installed: installed, Version: version, DetectedAt: time.Now()}
	c.mu.Unlock()
}

// persist writes the in-memory entries to disk atomically. Best-effort: a
// write failure only means the next cold start re-probes, which is correct.
func (c *detectionCache) persist() {
	c.mu.RLock()
	file := detectionCacheFile{Tools: make(map[string]detectionEntry, len(c.entries))}
	for name, entry := range c.entries {
		file.Tools[name] = entry
	}
	path := c.path
	c.mu.RUnlock()

	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return
	}
	payload, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return
	}
	tmp := fmt.Sprintf("%s.tmp.%d", path, os.Getpid())
	if err := os.WriteFile(tmp, payload, 0o600); err != nil {
		return
	}
	_ = os.Rename(tmp, path)
}
