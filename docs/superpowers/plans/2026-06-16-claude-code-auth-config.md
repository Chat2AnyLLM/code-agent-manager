# Claude Code Auth Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent `cam l claude` / `cam l` from writing conflicting Claude Code auth variables that trigger `Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set` warnings.

**Architecture:** Keep the existing generic config writer unchanged. Fix the Claude Code tool definitions so they write API-key mode (`ANTHROPIC_API_KEY`) for Anthropic-compatible endpoints and remove token-mode variables (`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`) when applying the config.

**Tech Stack:** Go CLI, YAML embedded tool registries, Go unit tests.

---

### Task 1: Update Claude Code config target tests

**Files:**
- Modify: `internal/tools/registry_test.go`
- Test: `internal/tools/registry_test.go`

- [ ] **Step 1: Write the failing registry test update**

Update `TestParseRegistry_LoadsConfigTarget` so the inline Claude Code fixture uses `env.ANTHROPIC_API_KEY`, and asserts removal of both token-mode variables:

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
        env.ANTHROPIC_API_KEY: "{api_key}"
      remove:
        - env.ANTHROPIC_AUTH_TOKEN
        - env.CLAUDE_CODE_OAUTH_TOKEN
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
	if got := ct.Upsert["env.ANTHROPIC_API_KEY"]; got != "{api_key}" {
		t.Errorf("upsert env.ANTHROPIC_API_KEY = %q, want {api_key}", got)
	}
	wantRemove := []string{"env.ANTHROPIC_AUTH_TOKEN", "env.CLAUDE_CODE_OAUTH_TOKEN"}
	if !reflect.DeepEqual(ct.Remove, wantRemove) {
		t.Errorf("remove = %v, want %v", ct.Remove, wantRemove)
	}
}
```

- [ ] **Step 2: Run focused test and verify it fails**

Run: `go test ./internal/tools -run TestParseRegistry_LoadsConfigTarget -v`

Expected before implementation: FAIL if the embedded/fixture expectations are not yet aligned.

### Task 2: Change Claude Code embedded tool definitions

**Files:**
- Modify: `internal/tools/embed/tools.yaml`
- Modify: `internal/doctor/embed/tools.yaml`
- Modify: `code_assistant_manager/tools.yaml`
- Test: `internal/tools/registry_test.go`

- [ ] **Step 1: Update Claude Code config target YAML**

For each Claude Code `config_target.upsert` block, replace token-mode writes:

```yaml
        env.ANTHROPIC_AUTH_TOKEN: "{api_key}"
        env.CLAUDE_CODE_OAUTH_TOKEN: "{api_key}"
```

with API-key mode plus cleanup:

```yaml
        env.ANTHROPIC_API_KEY: "{api_key}"
      remove:
        - env.ANTHROPIC_AUTH_TOKEN
        - env.CLAUDE_CODE_OAUTH_TOKEN
```

Keep existing model and traffic variables unchanged.

- [ ] **Step 2: Run focused registry tests**

Run: `go test ./internal/tools -run 'TestParseRegistry_LoadsConfigTarget|TestByCLICommandMapsBinaryToToolKey' -v`

Expected: PASS.

### Task 3: Add config writer regression test for removal

**Files:**
- Modify: `internal/tools/configwriter_test.go`
- Test: `internal/tools/configwriter_test.go`

- [ ] **Step 1: Add regression test**

Add a test that starts with both token-mode variables and `ANTHROPIC_API_KEY`, applies a Claude Code plan, and verifies the token variables are removed while the API key is set:

```go
func TestApply_ClaudeCodeAPIKeyModeRemovesTokenAuth(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "settings.json")
	if err := os.WriteFile(path, []byte(`{"env":{"ANTHROPIC_API_KEY":"old","ANTHROPIC_AUTH_TOKEN":"token","CLAUDE_CODE_OAUTH_TOKEN":"oauth"}}`), 0o600); err != nil {
		t.Fatal(err)
	}
	tool := Tool{ConfigTarget: &ConfigTarget{
		Path:   path,
		Format: "json",
		Upsert: map[string]string{
			"env.ANTHROPIC_API_KEY":  "{api_key}",
			"env.ANTHROPIC_BASE_URL": "{endpoint}",
		},
		Remove: []string{
			"env.ANTHROPIC_AUTH_TOKEN",
			"env.CLAUDE_CODE_OAUTH_TOKEN",
		},
	}}
	plan, err := Plan(tool, providers.Endpoint{Endpoint: "http://localhost:5000"}, "local", "claude-opus-4-8", "new-key")
	if err != nil {
		t.Fatalf("Plan: %v", err)
	}
	if _, err := Apply(tool, plan); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	env := got["env"].(map[string]any)
	if env["ANTHROPIC_API_KEY"] != "new-key" {
		t.Errorf("ANTHROPIC_API_KEY = %v, want new-key", env["ANTHROPIC_API_KEY"])
	}
	if env["ANTHROPIC_BASE_URL"] != "http://localhost:5000" {
		t.Errorf("ANTHROPIC_BASE_URL = %v, want http://localhost:5000", env["ANTHROPIC_BASE_URL"])
	}
	if _, ok := env["ANTHROPIC_AUTH_TOKEN"]; ok {
		t.Errorf("ANTHROPIC_AUTH_TOKEN should be removed: %#v", env)
	}
	if _, ok := env["CLAUDE_CODE_OAUTH_TOKEN"]; ok {
		t.Errorf("CLAUDE_CODE_OAUTH_TOKEN should be removed: %#v", env)
	}
}
```

- [ ] **Step 2: Run focused config writer test**

Run: `go test ./internal/tools -run TestApply_ClaudeCodeAPIKeyModeRemovesTokenAuth -v`

Expected: PASS.

### Task 4: Validate and reinstall

**Files:**
- No code edits.

- [ ] **Step 1: Run focused Go tests**

Run: `go test ./internal/tools -v`

Expected: PASS.

- [ ] **Step 2: Run repository Go tests**

Run: `find . -name '*_test.go' -print`

Then run package tests one by one for packages listed by `go list ./...`, at minimum including changed package `./internal/tools`.

Expected: PASS for run tests.

- [ ] **Step 3: Reinstall per project instructions**

Run:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed
```

Expected: install completes successfully.
