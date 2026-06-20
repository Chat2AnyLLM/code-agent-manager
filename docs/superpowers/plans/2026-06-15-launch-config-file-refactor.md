# Launch Config-File Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `internal/tools/launch.go`'s per-tool env-export switch with a data-driven config-file writer so `cam launch <tool>` writes each tool's native config file from `tools.yaml` and then launches the tool with a clean env.

**Architecture:** Add a `config_target` block to nine tool entries in `internal/tools/embed/tools.yaml`. Add `internal/tools/configwriter.go` with `Plan` / `Apply` / `WriteConfig` that read the block, expand placeholders, and write JSON / TOML / YAML via `internal/editorconfig` primitives. Extend `internal/editorconfig` with a YAML backend and array `[+]` / `[key=value]` operators. Delete the per-tool switch in `launch.go`; `cli/launch.go` calls `WriteConfig` before `Run`.

**Tech Stack:** Go 1.26, `gopkg.in/yaml.v3` (already vendored), `github.com/pelletier/go-toml/v2` (already vendored), Cobra (already vendored).

---

## File Structure

**New files:**
- `internal/editorconfig/yaml_tool.go` — YAML backend for the editorconfig registry.
- `internal/editorconfig/yaml_tool_test.go` — tests for the YAML backend.
- `internal/editorconfig/arraypath.go` — `[+]` and `[key=value]` parsing + Set/Unset helpers.
- `internal/editorconfig/arraypath_test.go` — tests for the array operators.
- `internal/tools/configwriter.go` — `Plan`, `Apply`, `WriteConfig`, placeholder expansion.
- `internal/tools/configwriter_test.go` — unit tests for the writer.
- `internal/tools/configwriter_per_tool_test.go` — golden table tests, one sub-test per tool.
- `internal/tools/codex_postwrite.go` — Codex `wire_api` post-hook.
- `internal/tools/codex_postwrite_test.go` — Codex post-hook tests.
- `internal/tools/testdata/<tool>.expected.{json,toml,yaml}` — 9 golden files.

**Modified files:**
- `internal/tools/registry.go` — add `ConfigTarget` struct + yaml tag.
- `internal/tools/embed/tools.yaml` — add `config_target` block to 9 tools; trim their `env.exported` blocks.
- `internal/tools/launch.go` — delete the per-tool `switch tool.Name` block.
- `internal/cli/launch.go` — call `tools.WriteConfig` before `tools.Run`; print plan in `--dry-run`.
- `internal/editorconfig/keypath.go` — wire arraypath into `Parse`/`Set`/`Unset` when a segment contains `[`.
- `internal/cli/cmd_launch_test.go` — extend with config-file assertions, drop env-export assertions.
- `internal/tools/registry_test.go` — assert `ConfigTarget` parsing.

---

## Conventions

- Every commit message uses the form: `<area>: <change>` (e.g. `tools: add config-file writer`).
- Per project CLAUDE.md: never `Co-Authored-By: Claude`. Author is `James Zhu <zhujian0805@gmail.com>` (already the default git user).
- Per project CLAUDE.md: ask the user before any `git commit` / `git push`. Each "commit" step in this plan is a request for approval, not an auto-commit.
- Per project CLAUDE.md: after all code changes, run `rm -rf dist/* && ./install.sh uninstall && ./install.sh && # providers.json is deprecated; no restore step is needed` to reinstall. Tests run independently via `go test ./...` and `find . -name '*_test.go' -path './internal/*'` per CLAUDE.md "find all files and run them one by one".
- TDD throughout: write the failing test first, see it fail, write the minimum code, see it pass, then commit.

---

## Task 1: ConfigTarget struct & YAML parsing

**Files:**
- Modify: `internal/tools/registry.go` (add struct, add field on `Tool`)
- Modify: `internal/tools/registry_test.go` (parse assertion)

- [ ] **Step 1: Write the failing test**

Append to `internal/tools/registry_test.go`:

```go
func TestParseRegistry_LoadsConfigTarget(t *testing.T) {
	data := []byte(`
tools:
  claude-code:
    cli_command: claude
    config_target:
      path: ~/.claude/settings.json
      format: json
      upsert:
        env.ANTHROPIC_BASE_URL: "{endpoint}"
        env.ANTHROPIC_AUTH_TOKEN: "{api_key}"
      remove:
        - env.LEGACY_KEY
`)
	reg, err := parseRegistry(data)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	tool, ok := reg.Get("claude-code")
	if !ok {
		t.Fatal("claude-code missing")
	}
	ct := tool.ConfigTarget
	if ct == nil {
		t.Fatal("ConfigTarget nil")
	}
	if ct.Path != "~/.claude/settings.json" {
		t.Errorf("path = %q, want ~/.claude/settings.json", ct.Path)
	}
	if ct.Format != "json" {
		t.Errorf("format = %q, want json", ct.Format)
	}
	if got := ct.Upsert["env.ANTHROPIC_BASE_URL"]; got != "{endpoint}" {
		t.Errorf("upsert env.ANTHROPIC_BASE_URL = %q, want {endpoint}", got)
	}
	if got := ct.Upsert["env.ANTHROPIC_AUTH_TOKEN"]; got != "{api_key}" {
		t.Errorf("upsert env.ANTHROPIC_AUTH_TOKEN = %q, want {api_key}", got)
	}
	if len(ct.Remove) != 1 || ct.Remove[0] != "env.LEGACY_KEY" {
		t.Errorf("remove = %v, want [env.LEGACY_KEY]", ct.Remove)
	}
}

func TestParseRegistry_NoConfigTarget_NilPointer(t *testing.T) {
	data := []byte(`
tools:
  gemini-cli:
    cli_command: gemini
`)
	reg, err := parseRegistry(data)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	tool, _ := reg.Get("gemini-cli")
	if tool.ConfigTarget != nil {
		t.Errorf("ConfigTarget = %v, want nil", tool.ConfigTarget)
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/tools/ -run TestParseRegistry_LoadsConfigTarget -v`
Expected: FAIL — compile error `tool.ConfigTarget undefined`.

- [ ] **Step 3: Add the struct and field**

Edit `internal/tools/registry.go`. Add after the `CLIParams` struct definition (around line 45):

```go
// ConfigTarget captures the config_target: block for a tool: which file CAM
// writes/updates before launching, what format it is, and the key paths
// (with placeholders) to upsert or remove.
type ConfigTarget struct {
	Path   string            `yaml:"path"`
	Format string            `yaml:"format"`
	Upsert map[string]string `yaml:"upsert"`
	Remove []string          `yaml:"remove"`
}
```

Add to the `Tool` struct (in the field list, after `CLIParameters`):

```go
	ConfigTarget  *ConfigTarget `yaml:"config_target,omitempty"`
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/tools/ -run TestParseRegistry -v`
Expected: PASS for both new tests.

- [ ] **Step 5: Request commit**

Tell the user: "Task 1 complete. Ready to commit? Suggested message: `tools: add ConfigTarget struct to tool registry`. Files: `internal/tools/registry.go`, `internal/tools/registry_test.go`."

Wait for approval before `git commit`.

---

## Task 2: Placeholder expansion (Plan / no-op writer)

**Files:**
- Create: `internal/tools/configwriter.go`
- Create: `internal/tools/configwriter_test.go`

- [ ] **Step 1: Write the failing test**

Create `internal/tools/configwriter_test.go`:

```go
package tools

import (
	"reflect"
	"sort"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func sortPlan(p []PlannedWrite) {
	sort.Slice(p, func(i, j int) bool { return p[i].KeyPath < p[j].KeyPath })
}

func TestPlan_PlaceholderSubstitution(t *testing.T) {
	tool := Tool{
		Name: "claude-code",
		ConfigTarget: &ConfigTarget{
			Path:   "~/.claude/settings.json",
			Format: "json",
			Upsert: map[string]string{
				"env.BASE":     "{endpoint}",
				"env.KEY":      "{api_key}",
				"env.MODEL":    "{selected_model}",
				"env.PROVIDER": "{endpoint_name}",
				"env.SECOND":   "{model_2}",
			},
		},
	}
	ep := providers.Endpoint{Endpoint: "https://example.test"}
	plan, err := Plan(tool, ep, "litellm", "claude-sonnet-4", "sk-abcd1234")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	sortPlan(plan)
	want := []PlannedWrite{
		{KeyPath: "env.BASE", Value: "https://example.test", Op: "upsert"},
		{KeyPath: "env.KEY", Value: "sk-abcd1234", Op: "upsert"},
		{KeyPath: "env.MODEL", Value: "claude-sonnet-4", Op: "upsert"},
		{KeyPath: "env.PROVIDER", Value: "litellm", Op: "upsert"},
		{KeyPath: "env.SECOND", Value: "", Op: "upsert"},
	}
	if !reflect.DeepEqual(plan, want) {
		t.Errorf("plan = %#v\nwant %#v", plan, want)
	}
}

func TestPlan_PlaceholdersInKeyPath(t *testing.T) {
	tool := Tool{
		Name: "openai-codex",
		ConfigTarget: &ConfigTarget{
			Path:   "~/.codex/config.toml",
			Format: "toml",
			Upsert: map[string]string{
				"model_providers.{endpoint_name}.base_url": "{endpoint}",
			},
		},
	}
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	plan, err := Plan(tool, ep, "myprov", "gpt-4o", "sk-x")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	if len(plan) != 1 {
		t.Fatalf("plan len = %d, want 1", len(plan))
	}
	if plan[0].KeyPath != "model_providers.myprov.base_url" {
		t.Errorf("KeyPath = %q, want model_providers.myprov.base_url", plan[0].KeyPath)
	}
	if plan[0].Value != "https://api.test" {
		t.Errorf("Value = %q, want https://api.test", plan[0].Value)
	}
}

func TestPlan_TypeCoercion(t *testing.T) {
	tool := Tool{
		ConfigTarget: &ConfigTarget{
			Path:   "/tmp/x.json",
			Format: "json",
			Upsert: map[string]string{
				"flags.enabled":     "true",
				"flags.disabled":    "false",
				"limits.maxTokens":  "8192",
				"limits.weight":     "1.5",
				"name":              "claude",
			},
		},
	}
	plan, err := Plan(tool, providers.Endpoint{}, "", "", "")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	got := map[string]any{}
	for _, p := range plan {
		got[p.KeyPath] = p.Value
	}
	if got["flags.enabled"] != true {
		t.Errorf("flags.enabled = %v (%T), want true", got["flags.enabled"], got["flags.enabled"])
	}
	if got["flags.disabled"] != false {
		t.Errorf("flags.disabled = %v, want false", got["flags.disabled"])
	}
	if got["limits.maxTokens"] != int64(8192) {
		t.Errorf("limits.maxTokens = %v (%T), want int64(8192)", got["limits.maxTokens"], got["limits.maxTokens"])
	}
	if got["limits.weight"] != 1.5 {
		t.Errorf("limits.weight = %v, want 1.5", got["limits.weight"])
	}
	if got["name"] != "claude" {
		t.Errorf("name = %v, want claude", got["name"])
	}
}

func TestPlan_NoConfigTarget_EmptyPlan(t *testing.T) {
	plan, err := Plan(Tool{Name: "gemini-cli"}, providers.Endpoint{}, "", "", "")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	if len(plan) != 0 {
		t.Errorf("plan = %v, want empty", plan)
	}
}

func TestPlan_OrderingDeterministic(t *testing.T) {
	tool := Tool{
		ConfigTarget: &ConfigTarget{
			Path:   "/tmp/x.json",
			Format: "json",
			Upsert: map[string]string{
				"z": "1", "a": "2", "m": "3", "b": "4",
			},
			Remove: []string{"r2", "r1"},
		},
	}
	p1, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	p2, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if !reflect.DeepEqual(p1, p2) {
		t.Errorf("plans differ across calls:\n  p1=%#v\n  p2=%#v", p1, p2)
	}
	// Verify lex order: a, b, m, r1, r2, z
	wantOrder := []string{"a", "b", "m", "r1", "r2", "z"}
	for i, p := range p1 {
		if p.KeyPath != wantOrder[i] {
			t.Errorf("plan[%d].KeyPath = %q, want %q", i, p.KeyPath, wantOrder[i])
		}
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/tools/ -run TestPlan -v`
Expected: FAIL — `undefined: Plan`, `undefined: PlannedWrite`.

- [ ] **Step 3: Implement `configwriter.go`**

Create `internal/tools/configwriter.go`:

```go
package tools

import (
	"sort"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// PlannedWrite is one upsert/remove that the writer will apply.
type PlannedWrite struct {
	KeyPath string // expanded key path (placeholders substituted)
	Value   any    // string|bool|int64|float64; nil for Remove
	Op      string // "upsert" | "remove"
}

// Plan resolves all placeholders and returns the ordered list of writes
// without touching disk.  Used by --dry-run and Apply alike.
func Plan(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) ([]PlannedWrite, error) {
	if tool.ConfigTarget == nil {
		return nil, nil
	}
	ct := tool.ConfigTarget

	out := make([]PlannedWrite, 0, len(ct.Upsert)+len(ct.Remove))

	// Upserts: lex-sorted by key path.
	keys := make([]string, 0, len(ct.Upsert))
	for k := range ct.Upsert {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, rawKey := range keys {
		key := expandConfigPlaceholders(rawKey, endpoint, endpointName, model, apiKey)
		raw := expandConfigPlaceholders(ct.Upsert[rawKey], endpoint, endpointName, model, apiKey)
		out = append(out, PlannedWrite{KeyPath: key, Value: coerceScalar(raw), Op: "upsert"})
	}

	// Removes: sorted for determinism.
	removes := append([]string(nil), ct.Remove...)
	sort.Strings(removes)
	for _, rawKey := range removes {
		key := expandConfigPlaceholders(rawKey, endpoint, endpointName, model, apiKey)
		out = append(out, PlannedWrite{KeyPath: key, Value: nil, Op: "remove"})
	}
	return out, nil
}

// expandConfigPlaceholders substitutes the five recognised placeholders.  It
// is a superset of expandPlaceholders in launch.go (adds {endpoint_name} and
// {model_2}; model_2 is empty until callers thread a secondary model in).
func expandConfigPlaceholders(raw string, ep providers.Endpoint, endpointName, model, apiKey string) string {
	s := raw
	s = strings.ReplaceAll(s, "{endpoint}", ep.Endpoint)
	s = strings.ReplaceAll(s, "{endpoint_name}", endpointName)
	s = strings.ReplaceAll(s, "{api_key}", apiKey)
	s = strings.ReplaceAll(s, "{selected_model}", model)
	s = strings.ReplaceAll(s, "{model_2}", "")
	return s
}

// coerceScalar promotes a raw string into the most specific Go type that fits.
// Order: bool > int64 > float64 > string.  Reuses editorconfig.ParseScalar
// but widens int to int64 so the marshallers emit `8192`, not the truncated
// platform int width.
func coerceScalar(raw string) any {
	v := editorconfig.ParseScalar(raw)
	if i, ok := v.(int); ok {
		return int64(i)
	}
	return v
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/tools/ -run TestPlan -v`
Expected: PASS for all five `TestPlan*` cases.

- [ ] **Step 5: Request commit**

Tell the user: "Task 2 complete. Ready to commit? Suggested message: `tools: add Plan() + placeholder expansion for config writer`. Files: `internal/tools/configwriter.go`, `internal/tools/configwriter_test.go`."

Wait for approval.

---

## Task 3: editorconfig YAML backend

**Files:**
- Create: `internal/editorconfig/yaml_tool.go`
- Create: `internal/editorconfig/yaml_tool_test.go`

- [ ] **Step 1: Write the failing test**

Create `internal/editorconfig/yaml_tool_test.go`:

```go
package editorconfig

import (
	"os"
	"path/filepath"
	"testing"
)

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
}

func TestYAML_LoadEmpty(t *testing.T) {
	tmp := t.TempDir()
	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{filepath.Join(tmp, "missing.yaml")},
	})
	data, _, err := tool.Load(UserScope)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if len(data) != 0 {
		t.Errorf("data = %v, want empty", data)
	}
}

func TestYAML_SetAndUnset_PreservesOther(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.yaml")
	writeFile(t, path, "theme: dark\nclients:\n  existing:\n    api_base: http://old\n")

	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{path},
	})
	if _, err := tool.Set(UserScope, "clients.new.api_base", "http://new"); err != nil {
		t.Fatalf("Set: %v", err)
	}

	data, _, err := tool.Load(UserScope)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if data["theme"] != "dark" {
		t.Errorf("theme lost: %v", data["theme"])
	}
	clients := data["clients"].(map[string]any)
	existing := clients["existing"].(map[string]any)
	if existing["api_base"] != "http://old" {
		t.Errorf("existing.api_base = %v, want http://old", existing["api_base"])
	}
	newC := clients["new"].(map[string]any)
	if newC["api_base"] != "http://new" {
		t.Errorf("new.api_base = %v, want http://new", newC["api_base"])
	}

	found, _, err := tool.Unset(UserScope, "clients.existing.api_base")
	if err != nil {
		t.Fatalf("Unset: %v", err)
	}
	if !found {
		t.Error("Unset returned !found")
	}
	data2, _, _ := tool.Load(UserScope)
	if data2["theme"] != "dark" {
		t.Error("theme lost after unset")
	}
}

func TestYAML_FilePermissions(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "perm.yaml")
	tool := newYAMLToolConfig(spec{
		name: "aichat", format: FormatYAML,
		userPaths: []string{path},
	})
	if _, err := tool.Set(UserScope, "x", "y"); err != nil {
		t.Fatalf("Set: %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Errorf("mode = %o, want 0600", info.Mode().Perm())
	}
}
```

- [ ] **Step 2: Add the `FormatYAML` constant**

Edit `internal/editorconfig/editor.go`. Find:

```go
const (
	FormatJSON Format = "json"
	FormatTOML Format = "toml"
)
```

Replace with:

```go
const (
	FormatJSON Format = "json"
	FormatTOML Format = "toml"
	FormatYAML Format = "yaml"
)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `go test ./internal/editorconfig/ -run TestYAML -v`
Expected: FAIL — `undefined: newYAMLToolConfig`.

- [ ] **Step 4: Implement `yaml_tool.go`**

Create `internal/editorconfig/yaml_tool.go`:

```go
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
```

- [ ] **Step 5: Wire YAML into DefaultRegistry switch**

Edit `internal/editorconfig/editor.go`. Find the `switch s.format` in `DefaultRegistry`:

```go
switch s.format {
case FormatJSON:
    tool = newJSONToolConfig(s)
case FormatTOML:
    tool = newTOMLToolConfig(s)
default:
    panic(...)
}
```

Replace with:

```go
switch s.format {
case FormatJSON:
    tool = newJSONToolConfig(s)
case FormatTOML:
    tool = newTOMLToolConfig(s)
case FormatYAML:
    tool = newYAMLToolConfig(s)
default:
    panic(fmt.Sprintf("editorconfig: unsupported format %q", s.format))
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `go test ./internal/editorconfig/ -run TestYAML -v`
Expected: PASS for all three `TestYAML_*` cases.

- [ ] **Step 7: Re-run full editorconfig package**

Run: `go test ./internal/editorconfig/ -v`
Expected: all existing tests still PASS.

- [ ] **Step 8: Request commit**

Tell the user: "Task 3 complete. Ready to commit? Suggested message: `editorconfig: add YAML backend for aichat config files`. Files: `internal/editorconfig/yaml_tool.go`, `internal/editorconfig/yaml_tool_test.go`, `internal/editorconfig/editor.go`."

Wait for approval.

---

## Task 4: Array operators (`[+]` and `[key=value]`)

**Files:**
- Create: `internal/editorconfig/arraypath.go`
- Create: `internal/editorconfig/arraypath_test.go`
- Modify: `internal/editorconfig/keypath.go` (route array segments)

- [ ] **Step 1: Write the failing test**

Create `internal/editorconfig/arraypath_test.go`:

```go
package editorconfig

import (
	"reflect"
	"testing"
)

func TestParseSegment_PlainKey(t *testing.T) {
	seg := ParseSegment("plain")
	if seg.Key != "plain" || seg.IsArray {
		t.Errorf("seg = %+v, want plain key", seg)
	}
}

func TestParseSegment_Append(t *testing.T) {
	seg := ParseSegment("models[+]")
	if seg.Key != "models" || !seg.IsArray || !seg.Append || seg.MatchKey != "" {
		t.Errorf("seg = %+v, want array append on 'models'", seg)
	}
}

func TestParseSegment_MatchByKey(t *testing.T) {
	seg := ParseSegment("customModels[displayName=foo/bar]")
	if seg.Key != "customModels" || !seg.IsArray || seg.Append {
		t.Errorf("seg = %+v, want array match", seg)
	}
	if seg.MatchKey != "displayName" || seg.MatchValue != "foo/bar" {
		t.Errorf("match = %s=%s, want displayName=foo/bar", seg.MatchKey, seg.MatchValue)
	}
}

func TestSetArray_AppendCreatesElement(t *testing.T) {
	data := map[string]any{}
	parts := []string{"customModels[+]", "name"}
	SetArray(data, parts, "alpha")
	got := data["customModels"].([]any)
	if len(got) != 1 {
		t.Fatalf("len = %d, want 1", len(got))
	}
	el := got[0].(map[string]any)
	if el["name"] != "alpha" {
		t.Errorf("el.name = %v, want alpha", el["name"])
	}
}

func TestSetArray_MatchUpsertsInPlace(t *testing.T) {
	data := map[string]any{
		"customModels": []any{
			map[string]any{"displayName": "x", "model": "old"},
			map[string]any{"displayName": "y", "model": "keep"},
		},
	}
	parts := []string{"customModels[displayName=x]", "model"}
	SetArray(data, parts, "new")
	got := data["customModels"].([]any)
	if len(got) != 2 {
		t.Fatalf("len = %d, want 2 (no append)", len(got))
	}
	el := got[0].(map[string]any)
	if el["model"] != "new" {
		t.Errorf("first.model = %v, want new", el["model"])
	}
	if got[1].(map[string]any)["model"] != "keep" {
		t.Errorf("second.model = %v, want keep", got[1].(map[string]any)["model"])
	}
}

func TestSetArray_MatchAppendsWhenAbsent(t *testing.T) {
	data := map[string]any{
		"customModels": []any{
			map[string]any{"displayName": "x"},
		},
	}
	parts := []string{"customModels[displayName=y]", "model"}
	SetArray(data, parts, "yval")
	got := data["customModels"].([]any)
	if len(got) != 2 {
		t.Fatalf("len = %d, want 2 (append)", len(got))
	}
	el := got[1].(map[string]any)
	if el["displayName"] != "y" {
		t.Errorf("new.displayName = %v, want y", el["displayName"])
	}
	if el["model"] != "yval" {
		t.Errorf("new.model = %v, want yval", el["model"])
	}
}

func TestSetArray_SameMatchSharesElement(t *testing.T) {
	// Two consecutive Sets with the same match clause must write to one element.
	data := map[string]any{}
	SetArray(data, []string{"customModels[displayName=foo]", "model"}, "m1")
	SetArray(data, []string{"customModels[displayName=foo]", "baseUrl"}, "https://x")
	got := data["customModels"].([]any)
	if len(got) != 1 {
		t.Fatalf("len = %d, want 1 element", len(got))
	}
	el := got[0].(map[string]any)
	if el["model"] != "m1" || el["baseUrl"] != "https://x" || el["displayName"] != "foo" {
		t.Errorf("el = %v", el)
	}
}

func TestParse_DispatchesArraySegments(t *testing.T) {
	// Top-level Parse must still split on dots; bracket content must not
	// confuse the dot splitter.
	parts, err := Parse("customModels[displayName=a.b/c-d].field")
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	want := []string{"customModels[displayName=a.b/c-d]", "field"}
	if !reflect.DeepEqual(parts, want) {
		t.Errorf("parts = %v, want %v", parts, want)
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/editorconfig/ -run "TestParseSegment|TestSetArray|TestParse_DispatchesArraySegments" -v`
Expected: FAIL — `undefined: ParseSegment`, `undefined: SetArray`.

- [ ] **Step 3: Implement `arraypath.go`**

Create `internal/editorconfig/arraypath.go`:

```go
package editorconfig

import (
	"strings"
)

// Segment represents one component of a key path.  Plain keys have IsArray
// false.  Array segments carry either Append (the [+] operator) or a
// MatchKey/MatchValue pair (the [k=v] operator).
type Segment struct {
	Key        string // map key holding the array
	IsArray    bool
	Append     bool   // true for [+]
	MatchKey   string // non-empty for [k=v]
	MatchValue string
}

// ParseSegment classifies one already-split dotted-key segment.
// "plain" -> {Key:"plain"}
// "models[+]" -> {Key:"models", IsArray:true, Append:true}
// "models[k=v]" -> {Key:"models", IsArray:true, MatchKey:"k", MatchValue:"v"}
func ParseSegment(raw string) Segment {
	open := strings.IndexByte(raw, '[')
	close := strings.LastIndexByte(raw, ']')
	if open < 0 || close < 0 || close < open {
		return Segment{Key: raw}
	}
	key := raw[:open]
	body := raw[open+1 : close]
	if body == "+" {
		return Segment{Key: key, IsArray: true, Append: true}
	}
	eq := strings.IndexByte(body, '=')
	if eq < 0 {
		return Segment{Key: raw}
	}
	return Segment{
		Key:        key,
		IsArray:    true,
		MatchKey:   strings.TrimSpace(body[:eq]),
		MatchValue: strings.TrimSpace(body[eq+1:]),
	}
}

// SetArray walks data using parts (which may include array segments) and
// assigns value at the leaf, creating maps and arrays as needed.  It is the
// array-aware companion to Set.
func SetArray(data map[string]any, parts []string, value any) {
	if len(parts) == 0 {
		return
	}
	cursor := any(data)
	for i, raw := range parts {
		seg := ParseSegment(raw)
		isLeaf := i == len(parts)-1
		cursorMap, ok := cursor.(map[string]any)
		if !ok {
			return // can't descend through scalars
		}
		if !seg.IsArray {
			if isLeaf {
				cursorMap[seg.Key] = value
				return
			}
			next, ok := cursorMap[seg.Key].(map[string]any)
			if !ok {
				next = map[string]any{}
				cursorMap[seg.Key] = next
			}
			cursor = next
			continue
		}
		// Array segment.
		arr, _ := cursorMap[seg.Key].([]any)
		var elem map[string]any
		var idx int
		switch {
		case seg.Append:
			elem = map[string]any{}
			arr = append(arr, elem)
			idx = len(arr) - 1
		default: // MatchKey=MatchValue
			idx = -1
			for j, raw := range arr {
				m, ok := raw.(map[string]any)
				if !ok {
					continue
				}
				if asString(m[seg.MatchKey]) == seg.MatchValue {
					idx = j
					elem = m
					break
				}
			}
			if idx < 0 {
				elem = map[string]any{seg.MatchKey: seg.MatchValue}
				arr = append(arr, elem)
				idx = len(arr) - 1
			}
		}
		cursorMap[seg.Key] = arr
		if isLeaf {
			arr[idx] = value
			cursorMap[seg.Key] = arr
			return
		}
		cursor = elem
	}
}

func asString(v any) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
```

- [ ] **Step 4: Extend `Parse` to keep bracket content as one segment**

Edit `internal/editorconfig/keypath.go`. Find the `for` loop body inside `Parse`. Add bracket tracking. The full updated `Parse`:

```go
func Parse(raw string) ([]string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, fmt.Errorf("editorconfig: empty key path")
	}
	var parts []string
	var buf strings.Builder
	var inQuote, inBracket bool
	for i := 0; i < len(raw); i++ {
		ch := raw[i]
		switch {
		case ch == '"' && (i == 0 || raw[i-1] != '\\'):
			inQuote = !inQuote
			buf.WriteByte(ch) // preserve quote so callers see it
		case ch == '[' && !inQuote:
			inBracket = true
			buf.WriteByte(ch)
		case ch == ']' && !inQuote:
			inBracket = false
			buf.WriteByte(ch)
		case ch == '.' && !inQuote && !inBracket:
			if buf.Len() == 0 {
				return nil, fmt.Errorf("editorconfig: empty segment in %q", raw)
			}
			parts = append(parts, buf.String())
			buf.Reset()
		default:
			if ch == '\\' && i+1 < len(raw) && raw[i+1] == '"' {
				buf.WriteByte('"')
				i++
				continue
			}
			buf.WriteByte(ch)
		}
	}
	if inQuote {
		return nil, fmt.Errorf("editorconfig: unterminated quote in %q", raw)
	}
	if inBracket {
		return nil, fmt.Errorf("editorconfig: unterminated bracket in %q", raw)
	}
	if buf.Len() > 0 {
		parts = append(parts, buf.String())
	}
	if len(parts) == 0 {
		return nil, fmt.Errorf("editorconfig: empty key path")
	}
	return parts, nil
}
```

Note: this change also wraps quote chars back into `buf` (the previous code stripped them). Existing tests in `keypath_test.go` may need updating — check next step.

- [ ] **Step 5: Run all editorconfig tests**

Run: `go test ./internal/editorconfig/ -v`
Expected: any test that asserted quoted-segment **stripped** output will FAIL. Fix those tests to expect the quote characters preserved (the consumer code in `toml_tool.go` is what needs to unquote, not `Parse`).

Audit `internal/editorconfig/editorconfig_test.go` for assertions on `Parse` output containing quoted segments. If any assert `["a", "b.c", "d"]` from `a."b.c".d`, update to `["a", "\"b.c\"", "d"]`. Then re-run.

If `toml_tool.go` relies on `Parse` returning unquoted segments, add an unquote helper there (strip leading/trailing `"` from each segment when looking up).

Re-run: `go test ./internal/editorconfig/ -v`
Expected: all PASS.

- [ ] **Step 6: Request commit**

Tell the user: "Task 4 complete. Ready to commit? Suggested message: `editorconfig: support [+] and [key=value] array operators`. Files: `internal/editorconfig/arraypath.go`, `internal/editorconfig/arraypath_test.go`, `internal/editorconfig/keypath.go` (and any test-fixture updates if needed)."

Wait for approval.

---

## Task 5: Apply (write to disk)

**Files:**
- Modify: `internal/tools/configwriter.go` (add `Apply` + `WriteConfig`)
- Modify: `internal/tools/configwriter_test.go` (Apply tests)

- [ ] **Step 1: Write the failing tests**

Append to `internal/tools/configwriter_test.go`:

```go
import (
	"encoding/json"
	"os"
	"path/filepath"
	// ...existing imports
)

func TestApply_JSON_PreservesUnrelatedKeys(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "settings.json")
	if err := os.WriteFile(path, []byte(`{"theme":"dark","env":{"FOO":"bar"}}`), 0o600); err != nil {
		t.Fatal(err)
	}
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "json",
		Upsert: map[string]string{
			"env.ANTHROPIC_BASE_URL": "https://x",
			"env.ANTHROPIC_MODEL":    "claude-sonnet-4",
		},
	}}
	plan, _ := Plan(tool, providers.Endpoint{Endpoint: "https://x"}, "ep", "claude-sonnet-4", "sk")
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["theme"] != "dark" {
		t.Errorf("theme lost: %v", got["theme"])
	}
	env := got["env"].(map[string]any)
	if env["FOO"] != "bar" {
		t.Errorf("env.FOO lost: %v", env["FOO"])
	}
	if env["ANTHROPIC_BASE_URL"] != "https://x" {
		t.Errorf("ANTHROPIC_BASE_URL = %v, want https://x", env["ANTHROPIC_BASE_URL"])
	}
	if env["ANTHROPIC_MODEL"] != "claude-sonnet-4" {
		t.Errorf("ANTHROPIC_MODEL = %v", env["ANTHROPIC_MODEL"])
	}
}

func TestApply_CreatesParentDir(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "nested", "deep", "x.json")
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "json",
		Upsert: map[string]string{"k": "v"},
	}}
	plan, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Errorf("file missing: %v", err)
	}
}

func TestApply_FilePermissions(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "p.json")
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "json",
		Upsert: map[string]string{"k": "v"},
	}}
	plan, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	info, _ := os.Stat(path)
	if info.Mode().Perm() != 0o600 {
		t.Errorf("mode = %o, want 0600", info.Mode().Perm())
	}
}

func TestApply_NoConfigTarget_Noop(t *testing.T) {
	tool := Tool{Name: "gemini-cli"}
	plan, err := Plan(tool, providers.Endpoint{}, "", "", "")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	path, err := Apply(tool, plan)
	if err != nil {
		t.Errorf("Apply: %v", err)
	}
	if path != "" {
		t.Errorf("path = %q, want empty", path)
	}
}

func TestApply_RemoveAbsentKey_NotError(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "x.json")
	os.WriteFile(path, []byte(`{"a":1}`), 0o600)
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "json",
		Remove: []string{"nonexistent.key"},
	}}
	plan, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if _, err := Apply(tool, plan); err != nil {
		t.Errorf("Apply on absent remove: %v", err)
	}
}

func TestApply_TOML_PreservesUnrelatedTables(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.toml")
	os.WriteFile(path, []byte("[history]\nlimit = 100\n"), 0o600)
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "toml",
		Upsert: map[string]string{
			"model_providers.{endpoint_name}.base_url": "{endpoint}",
		},
	}}
	plan, _ := Plan(tool, providers.Endpoint{Endpoint: "https://x"}, "myprov", "", "")
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if !contains(string(raw), "[history]") {
		t.Errorf("history table lost: %s", raw)
	}
	if !contains(string(raw), "https://x") {
		t.Errorf("base_url not set: %s", raw)
	}
}

func TestApply_ArrayUpsertByMatch(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "settings.json")
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path: path, Format: "json",
		Upsert: map[string]string{
			"customModels[displayName=ep/m1].displayName": "ep/m1",
			"customModels[displayName=ep/m1].baseUrl":     "https://x",
		},
	}}
	plan, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	// Second Apply with same match must update in place, not duplicate.
	tool.ConfigTarget.Upsert["customModels[displayName=ep/m1].baseUrl"] = "https://y"
	plan2, _ := Plan(tool, providers.Endpoint{}, "", "", "")
	if _, err := Apply(tool, plan2); err != nil {
		t.Fatalf("Apply 2: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	arr := got["customModels"].([]any)
	if len(arr) != 1 {
		t.Fatalf("len = %d, want 1 (in-place upsert)", len(arr))
	}
	if arr[0].(map[string]any)["baseUrl"] != "https://y" {
		t.Errorf("baseUrl = %v, want https://y", arr[0].(map[string]any)["baseUrl"])
	}
}

func contains(haystack, needle string) bool {
	return len(haystack) >= len(needle) && (haystack == needle || (len(haystack) > 0 && (haystack[:len(needle)] == needle || contains(haystack[1:], needle))))
}
```

(Replace `contains` with `strings.Contains` from the `strings` import if it's already in scope.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `go test ./internal/tools/ -run TestApply -v`
Expected: FAIL — `undefined: Apply`.

- [ ] **Step 3: Implement `Apply` and `WriteConfig`**

Append to `internal/tools/configwriter.go`:

```go
import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	// ...existing imports
	tomlv2 "github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"
)

// Apply writes the planned writes to tool.ConfigTarget.path atomically.
// Returns the written path or "" when tool has no config_target.
func Apply(tool Tool, plan []PlannedWrite) (string, error) {
	if tool.ConfigTarget == nil {
		return "", nil
	}
	ct := tool.ConfigTarget
	path := pathutil.Expand(ct.Path)

	data, err := readConfigFile(path, ct.Format)
	if err != nil {
		return "", err
	}

	for _, p := range plan {
		parts, err := editorconfig.Parse(p.KeyPath)
		if err != nil {
			return "", fmt.Errorf("configwriter: parse key %q: %w", p.KeyPath, err)
		}
		switch p.Op {
		case "upsert":
			if containsArraySegment(parts) {
				editorconfig.SetArray(data, parts, p.Value)
			} else {
				editorconfig.Set(data, parts, p.Value)
			}
		case "remove":
			// Remove on array segments isn't required by any tool today;
			// fall through to map Unset which silently no-ops on miss.
			editorconfig.Unset(data, parts)
		}
	}

	if err := writeConfigFile(path, ct.Format, data); err != nil {
		return "", err
	}
	return path, nil
}

// WriteConfig is Plan + Apply.  Used by cli/launch.go.
func WriteConfig(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) (string, error) {
	plan, err := Plan(tool, endpoint, endpointName, model, apiKey)
	if err != nil {
		return "", err
	}
	return Apply(tool, plan)
}

func containsArraySegment(parts []string) bool {
	for _, p := range parts {
		if seg := editorconfig.ParseSegment(p); seg.IsArray {
			return true
		}
	}
	return false
}

func readConfigFile(path, format string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]any{}, nil
		}
		return nil, fmt.Errorf("configwriter: read %s: %w", path, err)
	}
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	out := map[string]any{}
	switch format {
	case "json":
		if err := json.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	case "toml":
		if err := tomlv2.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	case "yaml":
		if err := yaml.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	default:
		return nil, fmt.Errorf("configwriter: unknown format %q", format)
	}
	return out, nil
}

func writeConfigFile(path, format string, data map[string]any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("configwriter: mkdir %s: %w", filepath.Dir(path), err)
	}
	var encoded []byte
	var err error
	switch format {
	case "json":
		encoded, err = json.MarshalIndent(data, "", "  ")
		if err == nil {
			encoded = append(encoded, '\n')
		}
	case "toml":
		encoded, err = tomlv2.Marshal(data)
	case "yaml":
		encoded, err = yaml.Marshal(data)
	default:
		return fmt.Errorf("configwriter: unknown format %q", format)
	}
	if err != nil {
		return fmt.Errorf("configwriter: marshal %s: %w", path, err)
	}
	if err := os.WriteFile(path, encoded, 0o600); err != nil {
		return fmt.Errorf("configwriter: write %s: %w", path, err)
	}
	return nil
}
```

Also add the `pathutil` import at the top of `configwriter.go`:

```go
import (
	// ...existing
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `go test ./internal/tools/ -run TestApply -v`
Expected: PASS for all `TestApply_*` cases.

- [ ] **Step 5: Run full configwriter test**

Run: `go test ./internal/tools/ -run "TestPlan|TestApply" -v`
Expected: PASS for all.

- [ ] **Step 6: Request commit**

Tell the user: "Task 5 complete. Ready to commit? Suggested message: `tools: implement Apply + WriteConfig for config-file writer`. Files: `internal/tools/configwriter.go`, `internal/tools/configwriter_test.go`."

Wait for approval.

---

## Task 6: Codex `wire_api` post-hook

**Files:**
- Create: `internal/tools/codex_postwrite.go`
- Create: `internal/tools/codex_postwrite_test.go`
- Modify: `internal/tools/configwriter.go` (call hook from `Apply`)

- [ ] **Step 1: Write the failing test**

Create `internal/tools/codex_postwrite_test.go`:

```go
package tools

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCodexPostHook_GPTSetsWireAPI(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.toml")
	os.WriteFile(path, []byte(`[model_providers.myprov]
name = "myprov"
base_url = "https://x"
`), 0o600)

	if err := applyCodexWireAPI(path, "myprov", "gpt-4o"); err != nil {
		t.Fatalf("hook: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if !strings.Contains(string(raw), `wire_api = "responses"`) {
		t.Errorf("wire_api not set:\n%s", raw)
	}
}

func TestCodexPostHook_NonGPTUnsetsWireAPI(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "config.toml")
	os.WriteFile(path, []byte(`[model_providers.myprov]
name = "myprov"
base_url = "https://x"
wire_api = "responses"
`), 0o600)

	if err := applyCodexWireAPI(path, "myprov", "claude-sonnet-4"); err != nil {
		t.Fatalf("hook: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if strings.Contains(string(raw), "wire_api") {
		t.Errorf("wire_api still present:\n%s", raw)
	}
}

func TestCodexPostHook_NoCodexNoop(t *testing.T) {
	tool := Tool{Name: "qwen-code"}
	if err := codexPostWrite(tool, "", "", ""); err != nil {
		t.Errorf("non-codex tool hook errored: %v", err)
	}
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `go test ./internal/tools/ -run TestCodexPostHook -v`
Expected: FAIL — `undefined: applyCodexWireAPI`, `undefined: codexPostWrite`.

- [ ] **Step 3: Implement the hook**

Create `internal/tools/codex_postwrite.go`:

```go
package tools

import (
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// codexPostWrite runs after the generic Apply for the openai-codex tool.
// If the selected model starts with "gpt", it sets
//
//	[model_providers.<endpointName>] wire_api = "responses"
//
// Otherwise it unsets wire_api on that provider.  No-op for other tools.
func codexPostWrite(tool Tool, endpointName, model, configPath string) error {
	if tool.Name != "openai-codex" {
		return nil
	}
	path := configPath
	if path == "" && tool.ConfigTarget != nil {
		path = pathutil.Expand(tool.ConfigTarget.Path)
	}
	if path == "" || endpointName == "" {
		return nil
	}
	return applyCodexWireAPI(path, endpointName, model)
}

func applyCodexWireAPI(path, endpointName, model string) error {
	data, err := readConfigFile(path, "toml")
	if err != nil {
		return err
	}
	keyPath := "model_providers." + quoteSegmentIfNeeded(endpointName) + ".wire_api"
	parts, err := editorconfig.Parse(keyPath)
	if err != nil {
		return err
	}
	if strings.HasPrefix(model, "gpt") {
		editorconfig.Set(data, parts, "responses")
	} else {
		editorconfig.Unset(data, parts)
	}
	return writeConfigFile(path, "toml", data)
}

// quoteSegmentIfNeeded wraps name in TOML quotes when it would not be a
// bare key (e.g. contains a hyphen or slash).
func quoteSegmentIfNeeded(name string) string {
	for _, ch := range name {
		isAlnum := (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_'
		if !isAlnum {
			return `"` + name + `"`
		}
	}
	return name
}
```

- [ ] **Step 4: Wire `codexPostWrite` into `WriteConfig`**

Edit `internal/tools/configwriter.go`. Update `WriteConfig`:

```go
func WriteConfig(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) (string, error) {
	plan, err := Plan(tool, endpoint, endpointName, model, apiKey)
	if err != nil {
		return "", err
	}
	path, err := Apply(tool, plan)
	if err != nil {
		return "", err
	}
	if err := codexPostWrite(tool, endpointName, model, path); err != nil {
		return "", err
	}
	return path, nil
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `go test ./internal/tools/ -run TestCodexPostHook -v`
Expected: PASS for all three cases.

- [ ] **Step 6: Request commit**

Tell the user: "Task 6 complete. Ready to commit? Suggested message: `tools: add codex wire_api post-hook for GPT model branching`. Files: `internal/tools/codex_postwrite.go`, `internal/tools/codex_postwrite_test.go`, `internal/tools/configwriter.go`."

Wait for approval.

---

## Task 7: Update `tools.yaml` — claude-code

**Files:**
- Modify: `internal/tools/embed/tools.yaml`

- [ ] **Step 1: Write the failing per-tool golden test**

Create `internal/tools/configwriter_per_tool_test.go`:

```go
package tools

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestPerTool_ClaudeCode_GoldenJSON(t *testing.T) {
	reg, err := LoadDefault()
	if err != nil {
		t.Fatalf("LoadDefault: %v", err)
	}
	tool, ok := reg.Get("claude-code")
	if !ok || tool.ConfigTarget == nil {
		t.Fatal("claude-code config_target missing")
	}
	tmp := t.TempDir()
	tool.ConfigTarget.Path = filepath.Join(tmp, "settings.json")

	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "litellm", "claude-sonnet-4", "sk-1234"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(tool.ConfigTarget.Path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	env := got["env"].(map[string]any)
	checks := map[string]any{
		"ANTHROPIC_BASE_URL":             "https://api.test",
		"ANTHROPIC_AUTH_TOKEN":           "sk-1234",
		"CLAUDE_CODE_OAUTH_TOKEN":        "sk-1234",
		"ANTHROPIC_MODEL":                "claude-sonnet-4",
		"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4",
		"ANTHROPIC_DEFAULT_HAIKU_MODEL":  "claude-sonnet-4",
		"DISABLE_NON_ESSENTIAL_MODEL_CALLS":         "1",
		"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":  "1",
	}
	for k, want := range checks {
		if env[k] != want {
			t.Errorf("env[%q] = %v, want %v", k, env[k], want)
		}
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/tools/ -run TestPerTool_ClaudeCode_GoldenJSON -v`
Expected: FAIL — `config_target missing`.

- [ ] **Step 3: Edit `tools.yaml` — add claude-code's `config_target`**

Edit `internal/tools/embed/tools.yaml`. Find the `claude-code:` entry. Replace its `env:` block:

```yaml
    env:
      exported:
        ANTHROPIC_BASE_URL: "Populated from selected endpoint.endpoint."
        ANTHROPIC_AUTH_TOKEN: "Resolved API key for the endpoint."
        ... [many lines]
        NODE_TLS_REJECT_UNAUTHORIZED: "0"
```

with:

```yaml
    env:
      managed:
        NODE_TLS_REJECT_UNAUTHORIZED: "0"
    config_target:
      path: ~/.claude/settings.json
      format: json
      upsert:
        env.ANTHROPIC_BASE_URL: "{endpoint}"
        env.ANTHROPIC_AUTH_TOKEN: "{api_key}"
        env.CLAUDE_CODE_OAUTH_TOKEN: "{api_key}"
        env.ANTHROPIC_MODEL: "{selected_model}"
        env.ANTHROPIC_SMALL_FAST_MODEL: "{model_2}"
        env.ANTHROPIC_DEFAULT_SONNET_MODEL: "{selected_model}"
        env.ANTHROPIC_DEFAULT_HAIKU_MODEL: "{selected_model}"
        env.DISABLE_NON_ESSENTIAL_MODEL_CALLS: "1"
        env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/tools/ -run TestPerTool_ClaudeCode_GoldenJSON -v`
Expected: PASS.

- [ ] **Step 5: Request commit**

Tell the user: "Task 7 complete (claude-code wired). Ready to commit? Suggested message: `tools: migrate claude-code env exports to config_target`."

Wait for approval.

---

## Tasks 8–15: Other tools

Each task follows the **exact same shape as Task 7** — write a golden test, edit `tools.yaml`, verify the test passes, request commit. The per-tool content matches the spec §5.4 verbatim. Tests live in `internal/tools/configwriter_per_tool_test.go`.

### Task 8: openai-codex

- [ ] Write golden test `TestPerTool_OpenAICodex_GoldenTOML` that:
  - Loads `LoadDefault()` → `openai-codex`.
  - Calls `WriteConfig(tool, {Endpoint: "https://api.test"}, "myprov", "gpt-4o", "sk-1")`.
  - Reads the TOML file, asserts:
    - `model_providers.myprov.name == "myprov"`
    - `model_providers.myprov.base_url == "https://api.test"`
    - `model_providers.myprov.env_key == "OPENAI_API_KEY"`
    - `model_providers.myprov.wire_api == "responses"` (because model starts with gpt)
    - `profiles.gpt-4o.model == "gpt-4o"`
    - `profiles.gpt-4o.model_provider == "myprov"`
    - `profiles.gpt-4o.model_reasoning_effort == "low"`
- [ ] Run test → FAIL.
- [ ] Edit `tools.yaml` `openai-codex` entry: replace `env:` block with `env: {managed: {NODE_TLS_REJECT_UNAUTHORIZED: "0"}}` and add `config_target` per spec §5.4.
- [ ] Run test → PASS.
- [ ] Also write `TestPerTool_OpenAICodex_NonGPTUnsetsWireAPI` calling with `claude-sonnet-4` and asserting `wire_api` is absent.
- [ ] Request commit: `tools: migrate openai-codex to config_target with wire_api post-hook`.

### Task 9: qwen-code

- [ ] Write golden test `TestPerTool_QwenCode_GoldenJSON` asserting `~/.qwen/settings.json` has `env.OPENAI_BASE_URL`, `env.OPENAI_API_KEY`, `env.OPENAI_MODEL`.
- [ ] Edit `tools.yaml` qwen-code entry per spec §5.4.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate qwen-code to config_target`.

### Task 10: codebuddy

- [ ] Write golden test for `~/.codebuddy.json`: `env.CODEBUDDY_BASE_URL`, `env.CODEBUDDY_API_KEY`.
- [ ] Edit `tools.yaml`.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate codebuddy to config_target`.

### Task 11: iflow

- [ ] Write golden test for `~/.iflow/settings.json`: `env.IFLOW_BASE_URL`, `env.IFLOW_API_KEY`, `env.IFLOW_MODEL_NAME`.
- [ ] Edit `tools.yaml`.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate iflow to config_target`.

### Task 12: aichat (YAML)

- [ ] Write golden test that loads the YAML file and asserts:
  - `clients.myprov.type == "openai-compatible"`
  - `clients.myprov.api_base == "https://api.test"`
  - `clients.myprov.api_key == "sk-1"`
  - `clients.myprov.models[0].name == "model-x"`
- [ ] Edit `tools.yaml` aichat entry per spec §5.4 (uses `clients.{endpoint_name}.models[+].name` syntax).
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate aichat to config_target (YAML)`.

### Task 13: kimi (TOML)

- [ ] Write golden test for `~/.kimi/config.toml`: top-level `provider`, `providers.myprov.{base_url,api_key,model}`.
- [ ] Edit `tools.yaml`.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate kimi to config_target (TOML)`.

### Task 14: droid (array upsert)

- [ ] Write golden test for `~/.factory/settings.json` asserting `customModels[0].{displayName,model,baseUrl,apiKey,provider,maxOutputTokens}`.
- [ ] Also assert: a second `WriteConfig` with the same `(endpointName, model)` does NOT append a second element (test array-by-match upsert).
- [ ] Edit `tools.yaml` droid entry per spec §5.4 with `customModels[displayName={endpoint_name}/{selected_model}].FIELD` syntax.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate droid to config_target (array upsert)`.

### Task 15: neovate

- [ ] Write golden test for `~/.neovate/config.json`: `providers.myprov.{baseURL,apiKey,model}`, `defaultProvider == "myprov"`.
- [ ] Edit `tools.yaml`.
- [ ] Test → PASS.
- [ ] Request commit: `tools: migrate neovate to config_target`.

---

## Task 16: Delete the per-tool switch in `launch.go`

**Files:**
- Modify: `internal/tools/launch.go`

- [ ] **Step 1: Write the failing test**

Append to `internal/tools/launch.go`'s test (create `internal/tools/launch_test.go` if not present):

```go
package tools

import (
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestResolveLaunchEnv_NoEndpointVarsForRefactoredTools(t *testing.T) {
	cases := []struct {
		toolName string
		absent   []string
	}{
		{"claude-code", []string{"ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"}},
		{"openai-codex", []string{"BASE_URL", "OPENAI_API_KEY"}},
		{"qwen-code", []string{"OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"}},
		{"codebuddy", []string{"CODEBUDDY_BASE_URL", "CODEBUDDY_API_KEY"}},
	}
	for _, tc := range cases {
		t.Run(tc.toolName, func(t *testing.T) {
			tool := Tool{Name: tc.toolName}
			ep := providers.Endpoint{Endpoint: "https://x"}
			launch := ResolveLaunchEnv(tool, ep, "ep", "model-x")
			for _, k := range tc.absent {
				if _, ok := launch.Env[k]; ok {
					t.Errorf("%s: env[%q] still set to %q after refactor", tc.toolName, k, launch.Env[k])
				}
			}
		})
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `go test ./internal/tools/ -run TestResolveLaunchEnv_NoEndpointVarsForRefactoredTools -v`
Expected: FAIL — env vars still set by the switch block.

- [ ] **Step 3: Delete the per-tool switch**

Edit `internal/tools/launch.go`. Remove the entire block from line ~51 through ~75 (the `switch tool.Name { case "claude-code": ... case "openai-codex": ... case "qwen-code": ... case "codebuddy": ... }`).

Verify the function now reads (roughly):

```go
func ResolveLaunchEnv(tool Tool, endpoint providers.Endpoint, endpointName, model string) LaunchEnv {
	env := map[string]string{}
	for _, kv := range os.Environ() { /* unchanged */ }
	apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)
	for k, v := range tool.Env.Exported {
		env[k] = expandPlaceholders(v, endpoint, model, apiKey)
	}
	for k, v := range tool.Env.Managed { env[k] = v }
	for _, removed := range tool.Env.Removed { delete(env, removed) }
	inject := make([]string, 0, len(tool.CLIParameters.Injected))
	for _, raw := range tool.CLIParameters.Injected {
		inject = append(inject, expandPlaceholders(raw, endpoint, model, apiKey))
	}
	return LaunchEnv{Tool: tool, Endpoint: endpoint, Model: model, Env: env, Inject: inject}
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `go test ./internal/tools/ -run TestResolveLaunchEnv_NoEndpointVarsForRefactoredTools -v`
Expected: PASS for all four sub-tests.

- [ ] **Step 5: Run all tools tests**

Run: `go test ./internal/tools/ -v`
Expected: all PASS.

- [ ] **Step 6: Request commit**

Tell the user: "Task 16 complete. Ready to commit? Suggested message: `tools: drop per-tool env switch from ResolveLaunchEnv`. Files: `internal/tools/launch.go`, `internal/tools/launch_test.go`."

Wait for approval.

---

## Task 17: `cli/launch.go` calls `WriteConfig`

**Files:**
- Modify: `internal/cli/launch.go`
- Modify: `internal/cli/cmd_launch_test.go`

- [ ] **Step 1: Write the failing tests**

Append to `internal/cli/cmd_launch_test.go`:

```go
import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLaunch_DryRun_PrintsConfigPlan(t *testing.T) {
	// Run `cam launch claude --dry-run` against a temp providers.json and
	// assert the output contains "Config writes (".
	// Use the existing test harness pattern in cmd_launch_test.go.
	out, err := runCLI(t, []string{"launch", "claude", "--dry-run", "--endpoint", "test-ep"}, /*providersJSON*/ minimalProvidersJSON(t))
	if err != nil {
		t.Fatalf("runCLI: %v", err)
	}
	if !strings.Contains(out, "Config writes (") {
		t.Errorf("output missing Config writes section:\n%s", out)
	}
}

func TestLaunch_DryRun_DoesNotTouchDisk(t *testing.T) {
	tmpHome := t.TempDir()
	t.Setenv("HOME", tmpHome)
	target := filepath.Join(tmpHome, ".claude", "settings.json")

	_, err := runCLI(t, []string{"launch", "claude", "--dry-run", "--endpoint", "test-ep"}, minimalProvidersJSON(t))
	if err != nil {
		t.Fatalf("runCLI: %v", err)
	}
	if _, err := os.Stat(target); !os.IsNotExist(err) {
		t.Errorf("dry-run wrote file: %v", err)
	}
}
```

(Adapt `runCLI` and `minimalProvidersJSON` to the existing test helpers in `cmd_launch_test.go`. If those helpers don't exist, build them from the patterns already used in `cmd_doctor_test.go`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `go test ./internal/cli/ -run "TestLaunch_DryRun" -v`
Expected: FAIL — `Config writes (` substring not in output (or test helper undefined).

- [ ] **Step 3: Update `internal/cli/launch.go`**

Find the `RunE` body, lines roughly 29–77. Replace the section starting at:

```go
launch := tools.ResolveLaunchEnv(tool, endpoint, epName, model)
if dryRun {
    printDryRun(cmd.OutOrStdout(), launch, toolArgs)
    return nil
}
code, err := tools.Run(launch, toolArgs)
```

with:

```go
apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)

if dryRun {
    plan, err := tools.Plan(tool, endpoint, epName, model, apiKey)
    if err != nil {
        return err
    }
    printDryRunWithPlan(cmd.OutOrStdout(), tool, endpoint, model, plan, toolArgs)
    return nil
}

if _, err := tools.WriteConfig(tool, endpoint, epName, model, apiKey); err != nil {
    return fmt.Errorf("launch: write %s config: %w", tool.Name, err)
}

launch := tools.ResolveLaunchEnv(tool, endpoint, epName, model)
code, err := tools.Run(launch, toolArgs)
```

Replace the existing `printDryRun` function with `printDryRunWithPlan`:

```go
func printDryRunWithPlan(out io.Writer, tool tools.Tool, ep providers.Endpoint, model string, plan []tools.PlannedWrite, args []string) {
    fmt.Fprintf(out, "Tool: %s\n", tool.LaunchCommand())
    if ep.Endpoint != "" {
        fmt.Fprintf(out, "Endpoint: %s\n", ep.Endpoint)
    }
    if model != "" {
        fmt.Fprintf(out, "Model: %s\n", model)
    }
    if tool.ConfigTarget != nil && len(plan) > 0 {
        fmt.Fprintf(out, "Config writes (%s):\n", tool.ConfigTarget.Path)
        for _, p := range plan {
            v := p.Value
            // Mask anything that looks like a key path containing AUTH/KEY/TOKEN.
            keyU := strings.ToUpper(p.KeyPath)
            if s, ok := v.(string); ok && (strings.Contains(keyU, "AUTH") || strings.Contains(keyU, "KEY") || strings.Contains(keyU, "TOKEN")) {
                v = providers.MaskedAPIKey(s)
            }
            fmt.Fprintf(out, "  %s %s = %q\n", p.Op, p.KeyPath, fmt.Sprintf("%v", v))
        }
    }
    if len(args) > 0 {
        fmt.Fprintf(out, "Args: %s\n", strings.Join(args, " "))
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `go test ./internal/cli/ -run "TestLaunch_DryRun" -v`
Expected: PASS.

- [ ] **Step 5: Run all cli tests**

Run: `go test ./internal/cli/ -v`
Expected: all PASS. If any old `TestLaunch_DryRun` test asserted the absence of a "Config writes" section, update it.

- [ ] **Step 6: Request commit**

Tell the user: "Task 17 complete. Ready to commit? Suggested message: `cli: write tool config files before launching; show plan in --dry-run`. Files: `internal/cli/launch.go`, `internal/cli/cmd_launch_test.go`."

Wait for approval.

---

## Task 18: Update CHANGELOG and run the full test suite

**Files:**
- Modify: `docs/CHANGELOG.md` (or create if absent)

- [ ] **Step 1: Add CHANGELOG entry**

Edit (or create) `docs/CHANGELOG.md`. Add at the top under a new "Unreleased" section:

```markdown
## Unreleased

### Changed

- `cam launch <tool>` now writes each tool's native config file
  (e.g. `~/.codex/config.toml`, `~/.claude/settings.json`,
  `~/.factory/settings.json`) before launching the binary, instead of
  exporting endpoint-derived environment variables into the child
  process.  Affected tools: claude-code, openai-codex, qwen-code,
  codebuddy, iflow, aichat, kimi, droid, neovate.
- The child process no longer receives `ANTHROPIC_BASE_URL`,
  `OPENAI_API_KEY`, `BASE_URL`, `CODEBUDDY_*`, `IFLOW_*`,
  `OPENAI_MODEL`, etc. from CAM.  These values now live in the tool's
  config file.  Wrapper scripts that read those vars from the env
  should switch to reading the config file.

### Added

- `config_target` block in `internal/tools/embed/tools.yaml` declaring
  per-tool config-file paths, formats, and key paths to upsert.
- YAML backend in `internal/editorconfig` (for aichat).
- `[+]` and `[key=value]` array operators in editorconfig key paths
  (for Droid's `customModels` array).
- Codex `wire_api` post-write hook: sets `wire_api = "responses"`
  for GPT models and unsets it otherwise.
```

- [ ] **Step 2: Run the entire Go test suite**

Per CLAUDE.md instruction "find all files with 'find' command and run them all one by one":

Run:
```bash
find . -name '*_test.go' -not -path './vendor/*' -not -path './node_modules/*' -not -path './.serena/*' | while read f; do
  pkg=$(dirname "$f")
  go test -count=1 -v "./$pkg" 2>&1 | tail -50
done
```

Expected: every package's tests PASS.

- [ ] **Step 3: Reinstall per CLAUDE.md**

Run:
```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed
```

Expected: install completes; `cam version` works; `cam launch --dry-run claude` shows the new "Config writes (...)" block.

- [ ] **Step 4: Smoke test live**

Run: `cam launch claude --dry-run --endpoint <some real endpoint name from your providers.json>`

Expected output includes:
- `Tool: claude`
- `Endpoint: ...`
- `Model: ...`
- `Config writes (~/.claude/settings.json):` followed by `upsert env.ANTHROPIC_*` lines with the API key masked.

- [ ] **Step 5: Request final commit**

Tell the user: "Task 18 complete. All tests pass, reinstall succeeded, smoke test confirms config-file output. Ready to commit? Suggested message: `docs: changelog entry for launch config-file refactor`. Files: `docs/CHANGELOG.md`."

Wait for approval.

- [ ] **Step 6: (Optional) Ask if they want to push the branch / open a PR**

Per CLAUDE.md: ask before push. Do not push automatically.

---

## Self-Review Notes

**Spec coverage:** Every section of the spec maps to at least one task:
- §4 architecture → Tasks 1, 2, 5, 16, 17 (files in place)
- §5 schema → Task 1 (struct), Tasks 7–15 (per-tool yaml)
- §5.3 type coercion → Task 2
- §6 writer behavior → Tasks 2, 5, 6
- §7 launch changes → Tasks 16, 17
- §8 tests → covered in every task
- §9 migration / changelog → Task 18

**Placeholder scan:** No "TBD" / "implement later" / generic "add validation" / unreferenced types remain.

**Type consistency:** `PlannedWrite`, `Plan`, `Apply`, `WriteConfig`, `ConfigTarget`, `Tool.ConfigTarget`, `Segment`, `ParseSegment`, `SetArray`, `applyCodexWireAPI`, `codexPostWrite` are all defined where first used and referenced consistently afterward.

**Known sequencing risk:** Task 4 modifies `Parse` in `keypath.go` which is called by the existing JSON/TOML setters. Step 5 of Task 4 explicitly says to audit and update any existing test that depended on the old quote-stripping behavior — that's the only foreseeable breakage point.
