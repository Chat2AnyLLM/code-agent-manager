package tools

import (
	"reflect"
	"sort"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

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

func TestLoadDefaultIncludesCoreTools(t *testing.T) {
	r, err := LoadDefault()
	if err != nil {
		t.Fatalf("LoadDefault err = %v", err)
	}
	for _, name := range []string{"claude-code", "openai-codex", "gemini-cli", "qwen-code", "codebuddy", "github-copilot", "droid"} {
		if _, ok := r.Get(name); !ok {
			t.Fatalf("Get(%q) returned false", name)
		}
	}
	if len(r.LaunchNames()) == 0 {
		t.Fatal("LaunchNames should not be empty")
	}
}

func TestByCLICommandMapsBinaryToToolKey(t *testing.T) {
	r, err := LoadDefault()
	if err != nil {
		t.Fatal(err)
	}
	tool, ok := r.ByCLICommand("claude")
	if !ok {
		t.Fatal("ByCLICommand(claude) false")
	}
	if tool.Name != "claude-code" {
		t.Fatalf("name = %q, want claude-code", tool.Name)
	}
}

func TestLaunchNamesDeduplicatesAndSorts(t *testing.T) {
	r, err := LoadDefault()
	if err != nil {
		t.Fatal(err)
	}
	names := r.LaunchNames()
	got := append([]string(nil), names...)
	sort.Strings(got)
	if !reflect.DeepEqual(names, got) {
		t.Fatalf("LaunchNames not sorted: %v", names)
	}
	seen := map[string]int{}
	for _, n := range names {
		seen[n]++
	}
	for n, count := range seen {
		if count > 1 {
			t.Fatalf("duplicate launch name %q (%d)", n, count)
		}
	}
}

func TestResolveLaunchEnvSubstitutesPlaceholders(t *testing.T) {
	t.Setenv("OPENAI_KEY", "sk-test")
	ep := providers.Endpoint{Endpoint: "https://api.example.com", APIKeyEnv: "OPENAI_KEY"}
	tool := Tool{
		Name:       "openai-codex",
		CLICommand: "codex",
		Env: Env{
			Exported: map[string]string{
				"BASE_URL":       "{BASE_URL}",
				"OPENAI_API_KEY": "{api_key}",
			},
			Managed: map[string]string{
				"NODE_TLS_REJECT_UNAUTHORIZED": "0",
			},
		},
		CLIParameters: CLIParams{
			Injected: []string{
				"-c model_providers.custom.base_url={BASE_URL}",
				"-c profiles.custom.model={selected_model}",
				"-p custom",
			},
		},
	}
	launch := ResolveLaunchEnv(tool, ep, "openai", "gpt-4o-mini")
	if launch.Env["BASE_URL"] != "https://api.example.com" {
		t.Fatalf("BASE_URL = %q", launch.Env["BASE_URL"])
	}
	if launch.Env["OPENAI_API_KEY"] != "sk-test" {
		t.Fatalf("OPENAI_API_KEY = %q", launch.Env["OPENAI_API_KEY"])
	}
	// Non-local endpoint must NOT have NODE_TLS_REJECT_UNAUTHORIZED=*** applied;
	// see internal/tools/launch.go isLocalEndpoint().
	if v, ok := launch.Env["NODE_TLS_REJECT_UNAUTHORIZED"]; ok {
		t.Fatalf("NODE_TLS_REJECT_UNAUTHORIZED should be stripped for non-local endpoint, got %q", v)
	}
	if len(launch.Inject) != 3 {
		t.Fatalf("inject = %v", launch.Inject)
	}
	if launch.Inject[0] != "-c model_providers.custom.base_url=https://api.example.com" {
		t.Fatalf("inject[0] = %q", launch.Inject[0])
	}
	if launch.Inject[1] != "-c profiles.custom.model=gpt-4o-mini" {
		t.Fatalf("inject[1] = %q", launch.Inject[1])
	}
}

func TestResolveLaunchEnvKeepsTLSDisableForLocalEndpoint(t *testing.T) {
	t.Setenv("OPENAI_KEY", "sk-test")
	tool := Tool{
		Name: "openai-codex",
		Env: Env{
			Managed: map[string]string{
				"NODE_TLS_REJECT_UNAUTHORIZED": "0",
			},
		},
	}
	cases := []struct {
		name     string
		endpoint string
		want     bool // true = TLS-disable should be applied
	}{
		{"localhost", "https://localhost:5000", true},
		{"127.0.0.1", "https://127.0.0.1:5000", true},
		{"ipv6 loopback", "https://[::1]:5000", true},
		{"0.0.0.0", "https://0.0.0.0:5000", true},
		{"empty endpoint", "", true},
		{"public api", "https://api.openai.com", false},
		{"public api with port", "https://api.openai.com:443", false},
		{"private but not loopback", "https://10.0.0.1", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			ep := providers.Endpoint{Endpoint: tc.endpoint, APIKeyEnv: "OPENAI_KEY"}
			launch := ResolveLaunchEnv(tool, ep, "openai", "gpt-4o-mini")
			_, ok := launch.Env["NODE_TLS_REJECT_UNAUTHORIZED"]
			if ok != tc.want {
				t.Fatalf("endpoint=%q: got TLS-disable present=%v, want %v (env=%v)", tc.endpoint, ok, tc.want, launch.Env["NODE_TLS_REJECT_UNAUTHORIZED"])
			}
		})
	}
}

func TestResolveLaunchEnvRemovedVarsAreCleared(t *testing.T) {
	t.Setenv("HTTPS_PROXY", "http://proxy.example.com:8080")
	tool := Tool{
		Name: "droid",
		Env:  Env{Removed: []string{"HTTPS_PROXY"}},
	}
	launch := ResolveLaunchEnv(tool, providers.Endpoint{}, "", "")
	if _, ok := launch.Env["HTTPS_PROXY"]; ok {
		t.Fatalf("HTTPS_PROXY should be removed: %v", launch.Env)
	}
}
