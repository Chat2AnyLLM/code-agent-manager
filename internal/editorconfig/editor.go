// Package editorconfig manages per-editor configuration files for the CLI's
// `cam config show / set / unset` commands.
//
// Each supported editor implements the ToolConfig interface backed either by a
// JSON file (most editors) or a TOML file (codex only).  The Registry holds
// the canonical list of supported editors and their on-disk locations.
package editorconfig

import (
	"fmt"
	"path/filepath"
	"sort"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// Scope identifies whether a config operation targets the user's home
// directory or a project-local file.
type Scope string

const (
	UserScope    Scope = "user"
	ProjectScope Scope = "project"
)

// Format describes the on-disk format of the underlying config file.
type Format string

const (
	FormatJSON Format = "json"
	FormatTOML Format = "toml"
	FormatYAML Format = "yaml"
)

// ScopedConfig represents the contents of a config file at a particular scope.
type ScopedConfig struct {
	Data map[string]any
	Path string
}

// ToolConfig is the interface every editor implements.
type ToolConfig interface {
	Name() string
	Description() string
	Format() Format
	PathFor(Scope) string
	UserPaths() []string
	ProjectPath() string
	Load(Scope) (data map[string]any, path string, err error)
	LoadAll() map[string]ScopedConfig
	Set(scope Scope, keyPath string, value any) (savedPath string, err error)
	Unset(scope Scope, keyPath string) (found bool, savedPath string, err error)
}

// spec is the static metadata for one editor.  pathFn is called late so
// pathutil.Home() honours t.Setenv in tests.
type spec struct {
	name        string
	description string
	format      Format
	userPaths   []string
	projectPath string
}

func (s spec) resolveUserPaths() []string {
	resolved := make([]string, 0, len(s.userPaths))
	for _, p := range s.userPaths {
		resolved = append(resolved, pathutil.Expand(p))
	}
	return resolved
}

func (s spec) resolveProjectPath() string {
	if s.projectPath == "" {
		return ""
	}
	if filepath.IsAbs(s.projectPath) {
		return s.projectPath
	}
	return s.projectPath
}

// defaultSpecs lists the editors CAM knows about.  Order matters only for
// list output; the registry keys by Name.
var defaultSpecs = []spec{
	{
		name: "claude", description: "Claude Code Editor", format: FormatJSON,
		userPaths:   []string{"~/.claude.json", "~/.claude/settings.json", "~/.claude/settings.local.json"},
		projectPath: ".claude/settings.json",
	},
	{
		name: "cursor-agent", description: "Cursor AI Code Editor", format: FormatJSON,
		userPaths:   []string{"~/.cursor/settings.json", "~/.cursor/mcp.json"},
		projectPath: ".cursor/settings.json",
	},
	{
		name: "gemini", description: "Google Gemini CLI", format: FormatJSON,
		userPaths:   []string{"~/.gemini/settings.json"},
		projectPath: ".gemini/settings.json",
	},
	{
		name: "copilot", description: "GitHub Copilot CLI", format: FormatJSON,
		userPaths: []string{"~/.copilot/mcp-config.json", "~/.copilot/mcp.json"},
	},
	{
		name: "codex", description: "OpenAI Codex CLI", format: FormatTOML,
		userPaths: []string{"~/.codex/config.toml"},
	},
	{
		name: "qwen", description: "Qwen Code CLI", format: FormatJSON,
		userPaths: []string{"~/.qwen/settings.json"},
	},
	{
		name: "codebuddy", description: "Tencent CodeBuddy CLI", format: FormatJSON,
		userPaths:   []string{"~/.codebuddy.json"},
		projectPath: ".codebuddy/mcp.json",
	},
	{
		name: "crush", description: "Charmland Crush CLI", format: FormatJSON,
		userPaths: []string{"~/.config/crush/crush.json"},
	},
	{
		name: "droid", description: "Factory.ai Droid CLI", format: FormatJSON,
		userPaths: []string{"~/.factory/mcp.json", "~/.factory/settings.json"},
	},
	{
		name: "iflow", description: "iFlow CLI", format: FormatJSON,
		userPaths: []string{"~/.iflow/settings.json", "~/.iflow/config.json"},
	},
	{
		name: "neovate", description: "Neovate Code CLI", format: FormatJSON,
		userPaths: []string{"~/.neovate/config.json"},
	},
	{
		name: "qodercli", description: "Qoder CLI", format: FormatJSON,
		userPaths: []string{"~/.qodercli/config.json"},
	},
	{
		name: "zed", description: "Zed Editor", format: FormatJSON,
		userPaths: []string{"~/.config/zed/settings.json"},
	},
}

// Registry maps editor names to their ToolConfig instances.
type Registry struct {
	tools map[string]ToolConfig
	order []string
}

// DefaultRegistry builds a Registry containing every supported editor.
func DefaultRegistry() *Registry {
	r := &Registry{tools: map[string]ToolConfig{}}
	for _, s := range defaultSpecs {
		var tool ToolConfig
		switch s.format {
		case FormatJSON:
			tool = newJSONToolConfig(s)
		case FormatTOML:
			tool = newTOMLToolConfig(s)
		default:
			panic(fmt.Sprintf("editorconfig: unsupported format %q", s.format))
		}
		r.tools[s.name] = tool
		r.order = append(r.order, s.name)
	}
	return r
}

// Get returns the ToolConfig for name, or false when unknown.
func (r *Registry) Get(name string) (ToolConfig, bool) {
	tool, ok := r.tools[name]
	return tool, ok
}

// Names returns the registered editor names in alphabetical order.
func (r *Registry) Names() []string {
	names := append([]string(nil), r.order...)
	sort.Strings(names)
	return names
}
