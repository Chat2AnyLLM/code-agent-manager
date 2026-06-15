package entities

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// AgentInfo holds metadata about a supported code agent.
type AgentInfo struct {
	ID          string // short id used as --app value (e.g. "claude")
	DisplayName string // human-readable name (e.g. "Claude Code")
	CLIBinary   string // binary to check on PATH (e.g. "claude")
}

// agentRegistry is the authoritative list of supported code agents,
// matching the cli/cli internal/skills/registry/registry.go.
var agentRegistry = []AgentInfo{
	// Tier 1: major agents
	{ID: "copilot", DisplayName: "GitHub Copilot", CLIBinary: "copilot"},
	{ID: "claude", DisplayName: "Claude Code", CLIBinary: "claude"},
	{ID: "cursor", DisplayName: "Cursor", CLIBinary: "cursor"},
	{ID: "codex", DisplayName: "Codex", CLIBinary: "codex"},
	{ID: "gemini", DisplayName: "Gemini CLI", CLIBinary: "gemini"},
	{ID: "antigravity", DisplayName: "Antigravity", CLIBinary: "antigravity"},

	// Tier 2
	{ID: "adal", DisplayName: "AdaL", CLIBinary: "adal"},
	{ID: "amp", DisplayName: "Amp", CLIBinary: "amp"},
	{ID: "augment", DisplayName: "Augment", CLIBinary: "augment"},
	{ID: "bob", DisplayName: "IBM Bob", CLIBinary: "bob"},
	{ID: "cline", DisplayName: "Cline", CLIBinary: "cline"},
	{ID: "codebuddy", DisplayName: "CodeBuddy", CLIBinary: "codebuddy"},
	{ID: "command-code", DisplayName: "Command Code", CLIBinary: "commandcode"},
	{ID: "continue", DisplayName: "Continue", CLIBinary: "continue"},
	{ID: "cortex", DisplayName: "Cortex Code", CLIBinary: "cortex"},
	{ID: "crush", DisplayName: "Crush", CLIBinary: "crush"},
	{ID: "deepagents", DisplayName: "Deep Agents", CLIBinary: "deepagents"},
	{ID: "droid", DisplayName: "Droid", CLIBinary: "droid"},
	{ID: "firebender", DisplayName: "Firebender", CLIBinary: "firebender"},
	{ID: "goose", DisplayName: "Goose", CLIBinary: "goose"},
	{ID: "iflow-cli", DisplayName: "iFlow CLI", CLIBinary: "iflow"},
	{ID: "junie", DisplayName: "Junie", CLIBinary: "junie"},
	{ID: "kilo", DisplayName: "Kilo Code", CLIBinary: "kilo"},
	{ID: "kimi-cli", DisplayName: "Kimi Code CLI", CLIBinary: "kimi"},
	{ID: "kiro-cli", DisplayName: "Kiro CLI", CLIBinary: "kiro"},
	{ID: "kode", DisplayName: "Kode", CLIBinary: "kode"},
	{ID: "mcpjam", DisplayName: "MCPJam", CLIBinary: "mcpjam"},
	{ID: "mistral-vibe", DisplayName: "Mistral Vibe", CLIBinary: "vibe"},
	{ID: "mux", DisplayName: "Mux", CLIBinary: "mux"},
	{ID: "neovate", DisplayName: "Neovate", CLIBinary: "neovate"},
	{ID: "openclaw", DisplayName: "OpenClaw", CLIBinary: "openclaw"},
	{ID: "opencode", DisplayName: "OpenCode", CLIBinary: "opencode"},
	{ID: "openhands", DisplayName: "OpenHands", CLIBinary: "openhands"},
	{ID: "pi", DisplayName: "Pi", CLIBinary: "pi-code"},
	{ID: "pochi", DisplayName: "Pochi", CLIBinary: "pochi"},
	{ID: "qoder", DisplayName: "Qoder", CLIBinary: "qoder"},
	{ID: "qwen", DisplayName: "Qwen Code", CLIBinary: "qwen"},
	{ID: "replit", DisplayName: "Replit", CLIBinary: "replit"},
	{ID: "roo", DisplayName: "Roo Code", CLIBinary: "roo"},
	{ID: "trae", DisplayName: "Trae", CLIBinary: "trae"},
	{ID: "trae-cn", DisplayName: "Trae CN", CLIBinary: "trae-cn"},
	{ID: "universal", DisplayName: "Universal", CLIBinary: "universal"},
	{ID: "warp", DisplayName: "Warp", CLIBinary: "warp"},
	{ID: "windsurf", DisplayName: "Windsurf", CLIBinary: "windsurf"},
	{ID: "zencoder", DisplayName: "Zencoder", CLIBinary: "zencoder"},
}

// AgentDisplayName returns the display name for an agent ID.
func AgentDisplayName(id string) string {
	for _, a := range agentRegistry {
		if a.ID == id {
			return a.DisplayName
		}
	}
	return id
}

// AllAgents returns the full agent registry.
func AllAgents() []AgentInfo {
	return agentRegistry
}

// IsAgentInstalled checks if an agent's CLI binary is on PATH.
func IsAgentInstalled(info AgentInfo) bool {
	_, err := exec.LookPath(info.CLIBinary)
	return err == nil
}

// AppPaths describes where a given app stores a kind of entity on disk.  All
// paths are user-level; project-level support can be added by callers if
// needed (Python only supports user level for skills/agents/plugins).
type AppPaths struct {
	App  string
	Path string
}

// Apps returns the install destinations for an entity kind keyed by app name.
// Paths use `~` (resolved at call time) so tests can swap HOME.
//
// The agent list matches the official gh skill registry (cli/cli
// internal/skills/registry/registry.go) — 45 supported agents.

var promptApps = map[string]string{
	"claude":    "~/.claude/CLAUDE.md",
	"codex":     "~/.codex/AGENTS.md",
	"gemini":    "~/.gemini/GEMINI.md",
	"copilot":   "~/.copilot/COPILOT.md",
	"codebuddy": "~/.codebuddy/CODEBUDDY.md",
	"opencode":  "~/.config/opencode/AGENTS.md",
	"cursor":    "~/.cursor/AGENTS.md",
	"windsurf":  "~/.codeium/windsurf/AGENTS.md",
	"amp":       "~/.config/agents/AGENTS.md",
	"roo":       "~/.roo/AGENTS.md",
}

// skillApps matches the cli/cli registry UserDir for skills — all 45 agents.
var skillApps = map[string]string{
	// Tier 1: major agents
	"claude":       "~/.claude/skills",
	"copilot":      "~/.copilot/skills",
	"cursor":       "~/.cursor/skills",
	"codex":        "~/.codex/skills",
	"gemini":       "~/.gemini/skills",
	"opencode":     "~/.config/opencode/skills",
	"windsurf":     "~/.codeium/windsurf/skills",

	// Tier 2: well-known agents
	"adal":         "~/.adal/skills",
	"amp":          "~/.config/agents/skills",
	"antigravity":  "~/.gemini/antigravity/skills",
	"augment":      "~/.augment/skills",
	"bob":          "~/.bob/skills",
	"cline":        "~/.agents/skills",
	"codebuddy":    "~/.codebuddy/skills",
	"command-code": "~/.commandcode/skills",
	"continue":     "~/.continue/skills",
	"cortex":       "~/.snowflake/cortex/skills",
	"crush":        "~/.config/crush/skills",
	"deepagents":   "~/.deepagents/agent/skills",
	"droid":        "~/.factory/skills",
	"firebender":   "~/.firebender/skills",
	"goose":        "~/.config/goose/skills",
	"iflow-cli":    "~/.iflow/skills",
	"junie":        "~/.junie/skills",
	"kilo":         "~/.kilocode/skills",
	"kimi-cli":     "~/.config/agents/skills",
	"kiro-cli":     "~/.kiro/skills",
	"kode":         "~/.kode/skills",
	"mcpjam":       "~/.mcpjam/skills",
	"mistral-vibe": "~/.vibe/skills",
	"mux":          "~/.mux/skills",
	"neovate":      "~/.neovate/skills",
	"openclaw":     "~/.openclaw/skills",
	"openhands":    "~/.openhands/skills",
	"pi":           "~/.pi/agent/skills",
	"pochi":        "~/.pochi/skills",
	"qoder":        "~/.qoder/skills",
	"qwen":         "~/.qwen/skills",
	"replit":       "~/.config/agents/skills",
	"roo":          "~/.roo/skills",
	"trae":         "~/.trae/skills",
	"trae-cn":      "~/.trae-cn/skills",
	"universal":    "~/.config/agents/skills",
	"warp":         "~/.agents/skills",
	"zencoder":     "~/.zencoder/skills",
}

// agentApps — only agents that are known to support subagent directories.
var agentApps = map[string]string{
	"claude":    "~/.claude/agents",
	"codex":     "~/.codex/agents",
	"gemini":    "~/.gemini/agents",
	"copilot":   "~/.copilot/agents",
	"cursor":    "~/.cursor/agents",
	"codebuddy": "~/.codebuddy/agents",
	"opencode":  "~/.config/opencode/agents",
	"droid":     "~/.factory/agents",
	"windsurf":  "~/.codeium/windsurf/agents",
	"roo":       "~/.roo/agents",
}

// pluginApps — only agents that support plugin directories.
var pluginApps = map[string]string{
	"claude":    "~/.claude/plugins",
	"codex":     "~/.codex/plugins",
	"gemini":    "~/.gemini/plugins",
	"copilot":   "~/.copilot/plugins",
	"cursor":    "~/.cursor/plugins",
	"codebuddy": "~/.codebuddy/plugins",
	"opencode":  "~/.config/opencode/plugins",
	"droid":     "~/.factory/plugins",
}

// AppPathsFor returns the destinations for a Kind keyed by app name.
func AppPathsFor(kind Kind) map[string]string {
	switch kind {
	case KindPrompt:
		return promptApps
	case KindSkill:
		return skillApps
	case KindAgent:
		return agentApps
	case KindPlugin:
		return pluginApps
	}
	return nil
}

// SupportedApps returns the supported app names for the kind, sorted.
func SupportedApps(kind Kind) []string {
	apps := AppPathsFor(kind)
	out := make([]string, 0, len(apps))
	for a := range apps {
		out = append(out, a)
	}
	sortStrings(out)
	return out
}

// InstalledApps returns only the apps whose CLI binary is found on PATH.
func InstalledApps(kind Kind) []string {
	apps := AppPathsFor(kind)
	var out []string
	for _, info := range agentRegistry {
		if _, ok := apps[info.ID]; !ok {
			continue // this agent doesn't support this kind
		}
		if IsAgentInstalled(info) {
			out = append(out, info.ID)
		}
	}
	return out
}

// InstallToApp writes the entity's content to the resolved location for app.
// For prompts: writes Content as a single file.  For skills/agents/plugins:
// creates a directory named entity.Name containing a SKILL.md/AGENT.md/manifest.json
// — minimal but matches the Python tree shape.
func InstallToApp(entity Entity, kind Kind, app string) (string, error) {
	apps := AppPathsFor(kind)
	dest, ok := apps[app]
	if !ok {
		return "", fmt.Errorf("entities: app %s does not support %s", app, kind)
	}
	resolved := pathutil.Expand(dest)
	if err := os.MkdirAll(filepath.Dir(resolved), 0o755); err != nil {
		return "", err
	}
	switch kind {
	case KindPrompt:
		return resolved, writeFile(resolved, []byte(entity.Content), 0o600)
	default:
		dir := filepath.Join(resolved, entity.Name)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return "", err
		}
		switch kind {
		case KindSkill:
			path := filepath.Join(dir, "SKILL.md")
			return dir, writeFile(path, []byte(entity.Content), 0o600)
		case KindAgent:
			path := filepath.Join(dir, "AGENT.md")
			return dir, writeFile(path, []byte(entity.Content), 0o600)
		case KindPlugin:
			path := filepath.Join(dir, "manifest.json")
			content := entity.Content
			if strings.TrimSpace(content) == "" {
				content = "{}\n"
			}
			return dir, writeFile(path, []byte(content), 0o600)
		}
	}
	return resolved, nil
}

// UninstallFromApp removes the entity's installation for app and reports
// whether anything was removed.
func UninstallFromApp(entityName string, kind Kind, app string) (string, bool, error) {
	apps := AppPathsFor(kind)
	dest, ok := apps[app]
	if !ok {
		return "", false, fmt.Errorf("entities: app %s does not support %s", app, kind)
	}
	resolved := pathutil.Expand(dest)
	switch kind {
	case KindPrompt:
		if !pathutil.Exists(resolved) {
			return resolved, false, nil
		}
		// Prompts are app-wide files; removing the file is opt-in only when
		// the file matches the entity's content marker.  We don't truncate
		// arbitrary user data — instead report "found" if the file exists.
		return resolved, false, nil
	default:
		dir := filepath.Join(resolved, entityName)
		if !pathutil.Exists(dir) {
			return dir, false, nil
		}
		if err := os.RemoveAll(dir); err != nil {
			return dir, false, err
		}
		return dir, true, nil
	}
}

func writeFile(path string, data []byte, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, mode)
}

func sortStrings(s []string) {
	for i := 1; i < len(s); i++ {
		for j := i; j > 0 && s[j-1] > s[j]; j-- {
			s[j-1], s[j] = s[j], s[j-1]
		}
	}
}
