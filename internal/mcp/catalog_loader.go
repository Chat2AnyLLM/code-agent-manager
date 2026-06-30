package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/camconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/fetching"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

const mcpCatalogConfigKey = "mcpServers"

// LoadRegistry loads MCP server schemas from configured catalog sources.
func LoadRegistry() (*Registry, error) {
	cfg, err := camconfig.Load("")
	if err != nil {
		return nil, fmt.Errorf("mcp: load catalog config: %w", err)
	}
	if _, ok := cfg.Repositories[mcpCatalogConfigKey]; !ok {
		bundled, err := camconfig.Bundled()
		if err != nil {
			return nil, fmt.Errorf("mcp: load bundled catalog config: %w", err)
		}
		cfg.Repositories[mcpCatalogConfigKey] = bundled.Repositories[mcpCatalogConfigKey]
	}
	return LoadRegistryFromConfig(cfg)
}

// LoadRegistryFromConfig loads MCP server schemas from a parsed CAM config.
func LoadRegistryFromConfig(cfg camconfig.CamConfig) (*Registry, error) {
	merged := map[string]ServerSchema{}
	sources := cfg.Repositories[mcpCatalogConfigKey].Sources
	for _, source := range sources {
		entries, err := loadCatalogSource(source, cfg.Cache)
		if err != nil {
			return nil, err
		}
		for _, entry := range entries {
			if _, exists := merged[entry.Name]; exists {
				continue
			}
			merged[entry.Name] = entry
		}
	}
	registry := &Registry{schemas: merged}
	_ = newCatalogStore("").save(context.Background(), registry.All())
	return registry, nil
}

func registryFromEntries(entries []ServerSchema) *Registry {
	merged := map[string]ServerSchema{}
	for _, entry := range entries {
		if entry.Name != "" {
			merged[entry.Name] = entry
		}
	}
	return &Registry{schemas: merged}
}

func loadCatalogSource(source camconfig.RepoSource, cache camconfig.CacheConfig) ([]ServerSchema, error) {
	switch source.Type {
	case "local":
		if source.Path == "" {
			return nil, nil
		}
		return loadLocalCatalog(source.Path)
	case "remote":
		if source.URL == "" {
			return nil, nil
		}
		return loadRemoteCatalog(source.URL, cache)
	default:
		return nil, fmt.Errorf("mcp: unsupported catalog source type %q", source.Type)
	}
}

func loadLocalCatalog(path string) ([]ServerSchema, error) {
	resolved := pathutil.Expand(path)
	data, err := os.ReadFile(resolved)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("mcp: read local catalog %s: %w", resolved, err)
	}
	entries, err := parseCatalogJSON(data)
	if err != nil {
		return nil, fmt.Errorf("mcp: parse local catalog %s: %w", resolved, err)
	}
	return entries, nil
}

func loadRemoteCatalog(sourceURL string, cache camconfig.CacheConfig) ([]ServerSchema, error) {
	if strings.HasSuffix(strings.ToLower(sourceURL), ".yaml") || strings.HasSuffix(strings.ToLower(sourceURL), ".yml") {
		return loadCatalogConfigSources(context.Background(), sourceURL)
	}
	url := sourceURL
	if cache.Enabled {
		entries, err := loadCatalogFromCache(url, cache)
		if err == nil {
			return entries, nil
		}
	}

	client := fetching.New()
	tmp, err := os.CreateTemp("", "cam-mcp-catalog-*.json")
	if err != nil {
		return nil, fmt.Errorf("mcp: create temp catalog file: %w", err)
	}
	tmpPath := tmp.Name()
	if err := tmp.Close(); err != nil {
		return nil, fmt.Errorf("mcp: close temp catalog file: %w", err)
	}
	defer os.Remove(tmpPath)

	if err := client.FetchFile(url, tmpPath); err != nil {
		return nil, fmt.Errorf("mcp: fetch remote catalog %s: %w", url, err)
	}
	data, err := os.ReadFile(tmpPath)
	if err != nil {
		return nil, fmt.Errorf("mcp: read fetched catalog %s: %w", url, err)
	}
	entries, err := parseCatalogJSON(data)
	if err != nil {
		return nil, fmt.Errorf("mcp: parse remote catalog %s: %w", url, err)
	}
	if cache.Enabled {
		if err := saveCatalogToCache(url, cache, data); err != nil {
			return nil, fmt.Errorf("mcp: save remote catalog cache %s: %w", url, err)
		}
	}
	return entries, nil
}

func parseCatalogJSON(data []byte) ([]ServerSchema, error) {
	var array []ServerSchema
	if err := json.Unmarshal(data, &array); err == nil {
		return validateCatalog(array)
	}

	var object map[string]json.RawMessage
	if err := json.Unmarshal(data, &object); err != nil {
		return nil, fmt.Errorf("decode catalog JSON: %w", err)
	}
	for _, key := range []string{"servers", "items", "data"} {
		if raw, ok := object[key]; ok {
			return parseCatalogJSON(raw)
		}
	}
	return parseCatalogMap(object)
}

func parseCatalogMap(object map[string]json.RawMessage) ([]ServerSchema, error) {
	entries := make([]ServerSchema, 0, len(object))
	for name, raw := range object {
		var schema ServerSchema
		if err := json.Unmarshal(raw, &schema); err != nil {
			return nil, fmt.Errorf("decode catalog record %q: %w", name, err)
		}
		if schema.Name == "" {
			schema.Name = name
		} else if schema.Name != name {
			return nil, fmt.Errorf("catalog record %q conflicts with schema name %q", name, schema.Name)
		}
		entries = append(entries, schema)
	}
	return validateCatalog(entries)
}

func validateCatalog(entries []ServerSchema) ([]ServerSchema, error) {
	for _, entry := range entries {
		if entry.Name == "" {
			return nil, fmt.Errorf("catalog record missing name")
		}
		if entry.Description == "" {
			return nil, fmt.Errorf("catalog record %q missing description", entry.Name)
		}
		if len(entry.Installations) == 0 {
			return nil, fmt.Errorf("catalog record %q missing installations", entry.Name)
		}
	}
	return entries, nil
}

func catalogCacheFilePath(url string, cache camconfig.CacheConfig) string {
	safe := strings.ReplaceAll(url, "https://", "")
	safe = strings.ReplaceAll(safe, "http://", "")
	safe = strings.ReplaceAll(safe, "/", "_")
	safe = strings.ReplaceAll(safe, ":", "_")
	return filepath.Join(cache.Directory, fmt.Sprintf("mcpServers_%s.json", safe))
}

func loadCatalogFromCache(url string, cache camconfig.CacheConfig) ([]ServerSchema, error) {
	path := catalogCacheFilePath(url, cache)
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	if time.Since(info.ModTime()) > time.Duration(cache.TTLSeconds)*time.Second {
		return nil, fmt.Errorf("cache expired")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return parseCatalogJSON(data)
}

func saveCatalogToCache(url string, cache camconfig.CacheConfig, data []byte) error {
	path := catalogCacheFilePath(url, cache)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}
