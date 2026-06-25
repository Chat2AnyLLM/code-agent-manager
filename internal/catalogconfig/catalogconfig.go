package catalogconfig

import (
	"fmt"
	"strings"

	"gopkg.in/yaml.v3"
)

// Config is the shared config.yaml shape used by Chat2AnyLLM catalog repos.
type Config struct {
	Output  OutputConfig    `yaml:"output"`
	Sources []CatalogSource `yaml:"sources"`
}

// OutputConfig describes where an upstream catalog build writes generated data.
type OutputConfig struct {
	Dir     string   `yaml:"dir"`
	Formats []string `yaml:"formats"`
}

// CatalogSource describes one upstream source declared in a catalog config.yaml.
type CatalogSource struct {
	Name     string `yaml:"name"`
	Type     string `yaml:"type"`
	Path     string `yaml:"path"`
	URL      string `yaml:"url"`
	Format   string `yaml:"format"`
	FilePath string `yaml:"file_path"`
}

// Parse decodes a catalog config.yaml and preserves unknown fields for forward compatibility.
func Parse(raw []byte) (Config, error) {
	var cfg Config
	if err := yaml.Unmarshal(raw, &cfg); err != nil {
		return Config{}, fmt.Errorf("catalog config: parse: %w", err)
	}
	return cfg, nil
}

// DataFile derives the generated data file path for a config.yaml catalog.
func DataFile(dataName string, raw []byte) (string, error) {
	cfg, err := Parse(raw)
	if err != nil {
		return "", err
	}
	dir := strings.Trim(strings.TrimSpace(cfg.Output.Dir), "/")
	if dir == "" {
		dir = "dist"
	}
	for _, format := range cfg.Output.Formats {
		if strings.EqualFold(strings.TrimSpace(format), "json") {
			return dir + "/" + dataName + ".json", nil
		}
	}
	return "", fmt.Errorf("catalog config: missing json output format")
}
