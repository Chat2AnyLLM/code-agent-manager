package metadata

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestDiscoverSkills(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "skills", "deep-research", "SKILL.md"), "---\nname: deep-research\ndescription: Multi-source research\n---\nbody")
	writeFile(t, filepath.Join(root, "skills", "code-review", "SKILL.md"), "---\nname: code-review\ndescription: Reviews code\n---\nbody")
	writeFile(t, filepath.Join(root, "README.md"), "# repo")

	res := DiscoverResources(root, "", entities.KindSkill)
	if len(res) != 2 {
		t.Fatalf("expected 2 skills, got %d: %+v", len(res), res)
	}
	names := map[string]string{}
	for _, r := range res {
		names[r.Name] = r.Description
	}
	if names["deep-research"] != "Multi-source research" {
		t.Fatalf("deep-research desc = %q", names["deep-research"])
	}
	if names["code-review"] != "Reviews code" {
		t.Fatalf("code-review desc = %q", names["code-review"])
	}
}

func TestDiscoverSkillsRespectsSubPath(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, ".claude", "skills", "x", "SKILL.md"), "---\nname: x\n---\n")
	writeFile(t, filepath.Join(root, "other", "y", "SKILL.md"), "---\nname: y\n---\n")

	res := DiscoverResources(root, ".claude/skills", entities.KindSkill)
	if len(res) != 1 || res[0].Name != "x" {
		t.Fatalf("subPath scan failed: %+v", res)
	}
}

func TestDiscoverAgents(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "agents", "code-reviewer.md"), "---\nname: code-reviewer\ndescription: Reviews PRs\n---\nbody")
	writeFile(t, filepath.Join(root, "agents", "test-runner.md"), "body without frontmatter")
	writeFile(t, filepath.Join(root, "agents", "README.md"), "# agents")

	res := DiscoverResources(root, "agents", entities.KindAgent)
	if len(res) != 2 {
		t.Fatalf("expected 2 agents (README excluded), got %d: %+v", len(res), res)
	}
	byName := map[string]DiscoveredResource{}
	for _, r := range res {
		byName[r.Name] = r
	}
	if byName["code-reviewer"].Description != "Reviews PRs" {
		t.Fatalf("code-reviewer desc = %q", byName["code-reviewer"].Description)
	}
	if _, ok := byName["test-runner"]; !ok {
		t.Fatalf("test-runner (no frontmatter) should still be discovered by filename")
	}
}

func TestDiscoverAgentsRequiresAgentsFolder(t *testing.T) {
	// A loose .md anywhere in the tree is NOT a subagent: only files beneath an
	// `agents/` folder count. This is what stops README/CLAUDE.md/docs/*.md from
	// leaking in as fake agents.
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "CLAUDE.md"), "# project notes")
	writeFile(t, filepath.Join(root, "docs", "best-practices.md"), "# best practices")
	writeFile(t, filepath.Join(root, "agents", "planner.md"), "---\nname: planner\n---\nbody")
	writeFile(t, filepath.Join(root, ".claude", "agents", "reviewer.md"), "---\nname: reviewer\n---\nbody")

	res := DiscoverResources(root, "", entities.KindAgent)
	names := map[string]bool{}
	for _, r := range res {
		names[r.Name] = true
	}
	if len(res) != 2 {
		t.Fatalf("expected 2 agents (only those under agents/), got %d: %+v", len(res), res)
	}
	if !names["planner"] || !names["reviewer"] {
		t.Fatalf("expected planner + reviewer, got %v", names)
	}
	if names["CLAUDE"] || names["best-practices"] {
		t.Fatalf("loose docs must not be agents, got %v", names)
	}
}

func TestDiscoverAgentsNestedUnderAgents(t *testing.T) {
	// Agents organized into category subfolders beneath an `agents/` dir count.
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "agents", "design", "brand-guardian.md"), "---\nname: brand-guardian\n---\n")
	writeFile(t, filepath.Join(root, "agents", "engineering", "backend-architect.md"), "---\nname: backend-architect\n---\n")

	res := DiscoverResources(root, "", entities.KindAgent)
	if len(res) != 2 {
		t.Fatalf("expected 2 nested agents, got %d: %+v", len(res), res)
	}
}

func TestDiscoverAgentDirectlySpecifiedFile(t *testing.T) {
	// A single .md pointed at by subPath is an agent even when it is not under an
	// agents/ folder — the "directly specified" case.
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "docs", "guide.md"), "---\nname: guide\n---\nbody")

	res := DiscoverResources(root, filepath.ToSlash(filepath.Join("docs", "guide.md")), entities.KindAgent)
	if len(res) != 1 || res[0].Name != "guide" {
		t.Fatalf("directly-specified agent not discovered: %+v", res)
	}
}

func TestDiscoverPrompts(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "prompts", "summarize.md"), "---\nname: summarize\ndescription: Summarize text\n---\n")
	writeFile(t, filepath.Join(root, "LICENSE.md"), "MIT")

	res := DiscoverResources(root, "", entities.KindPrompt)
	if len(res) != 1 || res[0].Name != "summarize" {
		t.Fatalf("prompt discovery failed: %+v", res)
	}
}

func TestDiscoverPlugins(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "my-plugin", ".claude-plugin", "plugin.json"), `{"name":"my-plugin","description":"A plugin"}`)
	writeFile(t, filepath.Join(root, "other", "plugin.json"), `{"name":"other","description":"Other plugin"}`)

	res := DiscoverResources(root, "", entities.KindPlugin)
	if len(res) != 2 {
		t.Fatalf("expected 2 plugins, got %d: %+v", len(res), res)
	}
	byName := map[string]string{}
	for _, r := range res {
		byName[r.Name] = r.Description
	}
	if byName["my-plugin"] != "A plugin" {
		t.Fatalf("my-plugin desc = %q", byName["my-plugin"])
	}
}

func TestParseFrontmatter(t *testing.T) {
	name, desc, ok := parseFrontmatter("---\nname: foo\ndescription: bar baz\n---\nbody")
	if !ok || name != "foo" || desc != "bar baz" {
		t.Fatalf("got name=%q desc=%q ok=%v", name, desc, ok)
	}
	if _, _, ok := parseFrontmatter("no frontmatter here"); ok {
		t.Fatal("expected ok=false for content without frontmatter")
	}
}
