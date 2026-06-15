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
