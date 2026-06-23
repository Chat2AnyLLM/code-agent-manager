package desktop

import (
	"os"
	"path/filepath"

	"github.com/chat2anyllm/code-agent-manager/internal/camconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

type ConfigService struct{}

func NewConfigService() *ConfigService { return &ConfigService{} }

func (s *ConfigService) ListFiles() []ConfigFileDTO {
	out := []ConfigFileDTO{{
		App: "cam", Scope: "user", Path: camconfig.DefaultPath(), Format: "yaml",
		Description: "code-agent-manager configuration", Exists: pathutil.Exists(camconfig.DefaultPath()),
	}}
	registry, err := editorconfig.DefaultRegistry()
	if err != nil {
		return out
	}
	for _, name := range registry.Names() {
		tool, ok := registry.Get(name)
		if !ok {
			continue
		}
		for _, path := range tool.UserPaths() {
			out = append(out, ConfigFileDTO{App: name, Scope: "user", Path: path, Format: string(tool.Format()), Description: tool.Description(), Exists: pathutil.Exists(path)})
		}
		if projectPath := tool.ProjectPath(); projectPath != "" {
			out = append(out, ConfigFileDTO{App: name, Scope: "project", Path: projectPath, Format: string(tool.Format()), Description: tool.Description(), Exists: pathutil.Exists(projectPath)})
		}
	}
	return out
}

func (s *ConfigService) Show(app, scope, key string) (map[string]any, error) {
	if app == "" || app == "cam" {
		cfg, err := camconfig.Load("")
		if err != nil {
			return nil, wrapError("CONFIG_LOAD_FAILED", err)
		}
		return map[string]any{"cache": cfg.Cache, "repositories": cfg.Repositories}, nil
	}
	tool, err := editorTool(app)
	if err != nil {
		return nil, err
	}
	data, _, err := tool.Load(editorconfig.Scope(scope))
	if err != nil {
		return nil, wrapError("CONFIG_LOAD_FAILED", err)
	}
	return data, nil
}

func (s *ConfigService) Set(app, scope, key string, value any) (OperationResult, error) {
	tool, err := editorTool(app)
	if err != nil {
		return OperationResult{}, err
	}
	path, err := tool.Set(editorconfig.Scope(scope), key, value)
	if err != nil {
		return OperationResult{}, wrapError("CONFIG_SET_FAILED", err)
	}
	return OperationResult{OK: true, Message: "config value set", Path: path}, nil
}

func (s *ConfigService) Unset(app, scope, key string) (OperationResult, error) {
	tool, err := editorTool(app)
	if err != nil {
		return OperationResult{}, err
	}
	found, path, err := tool.Unset(editorconfig.Scope(scope), key)
	if err != nil {
		return OperationResult{}, wrapError("CONFIG_UNSET_FAILED", err)
	}
	if !found {
		return OperationResult{}, NewError("CONFIG_KEY_NOT_FOUND", "config key not found", map[string]string{"key": key})
	}
	return OperationResult{OK: true, Message: "config value removed", Path: path}, nil
}

func (s *ConfigService) Validate() (OperationResult, error) {
	if _, err := camconfig.Load(""); err != nil {
		return OperationResult{}, wrapError("CONFIG_VALIDATE_FAILED", err)
	}
	return OperationResult{OK: true, Message: "configuration valid", Path: camconfig.DefaultPath()}, nil
}

func (s *ConfigService) ReadFile(path string) (string, error) {
	clean := filepath.Clean(path)
	data, err := os.ReadFile(clean)
	if err != nil {
		return "", wrapError("CONFIG_READ_FAILED", err)
	}
	return string(data), nil
}

func editorTool(app string) (editorconfig.ToolConfig, error) {
	registry, err := editorconfig.DefaultRegistry()
	if err != nil {
		return nil, wrapError("CONFIG_REGISTRY_INIT_FAILED", err)
	}
	tool, ok := registry.Get(app)
	if !ok {
		return nil, NewError("CONFIG_APP_NOT_FOUND", "unsupported config app", map[string]string{"app": app})
	}
	return tool, nil
}
