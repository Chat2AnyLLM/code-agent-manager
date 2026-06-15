package tools

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
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
				"flags.enabled":    "true",
				"flags.disabled":   "false",
				"limits.maxTokens": "8192",
				"limits.weight":    "1.5",
				"name":             "claude",
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
	s := string(raw)
	if !strings.Contains(s, "history") {
		t.Errorf("history table lost:\n%s", s)
	}
	if !strings.Contains(s, "https://x") {
		t.Errorf("base_url not set:\n%s", s)
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
