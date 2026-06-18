package desktop

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLaunchServiceDryRun(t *testing.T) {
	path := filepath.Join(t.TempDir(), "providers.json")
	providerService := NewProviderService(path)
	_, _ = providerService.Init()
	enabled := true
	_, err := providerService.Add(ProviderInput{
		Name: "local", Endpoint: "http://localhost:4000/v1", Clients: []string{"claude"}, Models: []string{"demo-model"}, Enabled: &enabled,
	})
	if err != nil {
		t.Fatalf("add provider: %v", err)
	}

	launch := NewLaunchService(path)
	providers, err := launch.ListProvidersForTool("claude")
	if err != nil {
		t.Fatalf("providers for tool: %v", err)
	}
	if len(providers) != 1 {
		t.Fatalf("expected one provider, got %+v", providers)
	}

	plan, err := launch.DryRun("claude", "local", "demo-model", []string{"--help"})
	if err != nil {
		t.Fatalf("dry run: %v", err)
	}
	if plan.Provider.Name != "local" || plan.Model != "demo-model" || plan.Command == "" {
		t.Fatalf("unexpected launch plan: %+v", plan)
	}
}

// ApplyConfig writes the provider's config into the agent's native config file
// without launching — the cc-switch "switch" operation. HOME is isolated so
// the write lands in a temp dir and never touches the developer's real config.
func TestLaunchServiceApplyConfig(t *testing.T) {
	t.Setenv("HOME", t.TempDir())

	path := filepath.Join(t.TempDir(), "providers.json")
	providerService := NewProviderService(path)
	_, _ = providerService.Init()
	enabled := true
	_, err := providerService.Add(ProviderInput{
		Name: "local", Endpoint: "http://localhost:4000/v1", Clients: []string{"claude"}, Models: []string{"demo-model"}, Enabled: &enabled,
	})
	if err != nil {
		t.Fatalf("add provider: %v", err)
	}

	launch := NewLaunchService(path)
	result, err := launch.ApplyConfig("claude", "local", "demo-model")
	if err != nil {
		t.Fatalf("apply config: %v", err)
	}
	if result.Provider.Name != "local" || result.Model != "demo-model" {
		t.Fatalf("unexpected apply result: %+v", result)
	}
	// claude has a config_target (~/.claude/settings.json), so a path and at
	// least one planned write are expected.
	if result.ConfigPath == "" {
		t.Fatalf("expected a config path for claude, got empty")
	}
	if len(result.Writes) == 0 {
		t.Fatalf("expected planned writes, got none")
	}
	data, err := os.ReadFile(result.ConfigPath)
	if err != nil {
		t.Fatalf("read written config: %v", err)
	}
	body := string(data)
	for _, want := range []string{"ANTHROPIC_BASE_URL", "http://localhost:4000/v1", "demo-model"} {
		if !strings.Contains(body, want) {
			t.Errorf("written config missing %q\n%s", want, body)
		}
	}
}

// A provider with a literal API key writes that key into the agent's config so
// the agent can authenticate without relying on a process env var being set —
// the scenario that left ~/.claude/settings.json with an empty token.
func TestLaunchServiceApplyConfigWritesStoredAPIKey(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	t.Setenv("USERPROFILE", t.TempDir())

	path := filepath.Join(t.TempDir(), "providers.json")
	providerService := NewProviderService(path)
	_, _ = providerService.Init()
	enabled := true
	if _, err := providerService.Add(ProviderInput{
		Name: "local", Endpoint: "http://localhost:4000/v1", APIKey: "sk-stored-key",
		Clients: []string{"claude"}, Models: []string{"demo-model"}, Enabled: &enabled,
	}); err != nil {
		t.Fatalf("add provider: %v", err)
	}

	launch := NewLaunchService(path)
	result, err := launch.ApplyConfig("claude", "local", "demo-model")
	if err != nil {
		t.Fatalf("apply config: %v", err)
	}
	data, err := os.ReadFile(result.ConfigPath)
	if err != nil {
		t.Fatalf("read written config: %v", err)
	}
	if !strings.Contains(string(data), "sk-stored-key") {
		t.Fatalf("expected stored API key in config, got:\n%s", data)
	}
}

// When a provider has no API key (no literal key, env var unset), applying must
// NOT write an empty ANTHROPIC_API_KEY that would wipe an existing token.
func TestLaunchServiceApplyConfigSkipsEmptyAPIKey(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	t.Setenv("USERPROFILE", t.TempDir())

	path := filepath.Join(t.TempDir(), "providers.json")
	providerService := NewProviderService(path)
	_, _ = providerService.Init()
	enabled := true
	if _, err := providerService.Add(ProviderInput{
		Name: "local", Endpoint: "http://localhost:4000/v1",
		Clients: []string{"claude"}, Models: []string{"demo-model"}, Enabled: &enabled,
	}); err != nil {
		t.Fatalf("add provider: %v", err)
	}

	launch := NewLaunchService(path)
	result, err := launch.ApplyConfig("claude", "local", "demo-model")
	if err != nil {
		t.Fatalf("apply config: %v", err)
	}
	data, err := os.ReadFile(result.ConfigPath)
	if err != nil {
		t.Fatalf("read written config: %v", err)
	}
	if strings.Contains(string(data), "ANTHROPIC_API_KEY") {
		t.Fatalf("expected no ANTHROPIC_API_KEY when key is empty, got:\n%s", data)
	}
}
