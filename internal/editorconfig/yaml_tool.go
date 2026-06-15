package editorconfig

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"gopkg.in/yaml.v3"
)

// yamlToolConfig implements ToolConfig backed by a YAML file.  Mirrors
// jsonToolConfig in structure and atomicity guarantees.
type yamlToolConfig struct {
	spec spec
}

func newYAMLToolConfig(s spec) *yamlToolConfig {
	return &yamlToolConfig{spec: s}
}

func (c *yamlToolConfig) Name() string        { return c.spec.name }
func (c *yamlToolConfig) Description() string { return c.spec.description }
func (c *yamlToolConfig) Format() Format      { return FormatYAML }

func (c *yamlToolConfig) UserPaths() []string {
	return c.spec.resolveUserPaths()
}

func (c *yamlToolConfig) ProjectPath() string {
	if c.spec.projectPath == "" {
		return ""
	}
	wd, _ := os.Getwd()
	return filepath.Join(wd, c.spec.projectPath)
}

func (c *yamlToolConfig) PathFor(scope Scope) string {
	switch scope {
	case UserScope:
		paths := c.UserPaths()
		for _, p := range paths {
			if pathutil.Exists(p) {
				return p
			}
		}
		if len(paths) > 0 {
			return paths[0]
		}
	case ProjectScope:
		return c.ProjectPath()
	}
	return ""
}

func (c *yamlToolConfig) Load(scope Scope) (map[string]any, string, error) {
	path := c.PathFor(scope)
	if path == "" {
		return nil, "", fmt.Errorf("editorconfig: %s scope %s unsupported", c.spec.name, scope)
	}
	return loadYAML(path)
}

func loadYAML(path string) (map[string]any, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]any{}, path, nil
		}
		return nil, path, fmt.Errorf("editorconfig: read %s: %w", path, err)
	}
	if len(data) == 0 {
		return map[string]any{}, path, nil
	}
	out := map[string]any{}
	if err := yaml.Unmarshal(data, &out); err != nil {
		return nil, path, fmt.Errorf("editorconfig: parse %s: %w", path, err)
	}
	return out, path, nil
}

func (c *yamlToolConfig) LoadAll() map[string]ScopedConfig {
	all := map[string]ScopedConfig{}
	for _, scope := range []Scope{UserScope, ProjectScope} {
		path := c.PathFor(scope)
		if path == "" {
			continue
		}
		data, _, err := loadYAML(path)
		if err != nil {
			continue
		}
		all[string(scope)] = ScopedConfig{Data: data, Path: path}
	}
	return all
}

func (c *yamlToolConfig) Set(scope Scope, keyPath string, value any) (string, error) {
	parts, err := Parse(keyPath)
	if err != nil {
		return "", err
	}
	path := c.PathFor(scope)
	if path == "" {
		return "", fmt.Errorf("editorconfig: %s scope %s unsupported", c.spec.name, scope)
	}
	data, _, err := loadYAML(path)
	if err != nil {
		return "", err
	}
	Set(data, parts, value)
	if err := writeYAML(path, data); err != nil {
		return "", err
	}
	return path, nil
}

func (c *yamlToolConfig) Unset(scope Scope, keyPath string) (bool, string, error) {
	parts, err := Parse(keyPath)
	if err != nil {
		return false, "", err
	}
	path := c.PathFor(scope)
	if path == "" {
		return false, "", fmt.Errorf("editorconfig: %s scope %s unsupported", c.spec.name, scope)
	}
	data, _, err := loadYAML(path)
	if err != nil {
		return false, "", err
	}
	found := Unset(data, parts)
	if !found {
		return false, path, nil
	}
	if err := writeYAML(path, data); err != nil {
		return false, "", err
	}
	return true, path, nil
}

func writeYAML(path string, data map[string]any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("editorconfig: mkdir %s: %w", filepath.Dir(path), err)
	}
	encoded, err := yaml.Marshal(data)
	if err != nil {
		return fmt.Errorf("editorconfig: marshal %s: %w", path, err)
	}
	if err := os.WriteFile(path, encoded, 0o600); err != nil {
		return fmt.Errorf("editorconfig: write %s: %w", path, err)
	}
	return nil
}
