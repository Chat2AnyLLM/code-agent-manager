package cli

import (
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// driveProvWiz feeds key events into the provider wizard model, same pattern
// as the launch wizard's drive helper.
func driveProvWiz(t *testing.T, m providerWizardModel, keys ...string) providerWizardModel {
	t.Helper()
	for _, k := range keys {
		next, _ := m.Update(keyEvent(k))
		m = next.(providerWizardModel)
	}
	return m
}

// typeKeys returns key event strings for each character in s.
func typeKeys(s string) []string {
	keys := make([]string, len(s))
	for i, ch := range s {
		keys[i] = string(ch)
	}
	return keys
}

func TestProviderWizard_AddFullFlow(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	if m.phase != wizPhaseName {
		t.Fatalf("expected phase Name, got %v", m.phase)
	}
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected phase Endpoint, got %v", m.phase)
	}
	keys = append(typeKeys("https://api.example.com"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseAPIKeyEnv {
		t.Fatalf("expected phase APIKeyEnv, got %v", m.phase)
	}
	keys = append(typeKeys("MY_KEY"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseClients {
		t.Fatalf("expected phase Clients, got %v", m.phase)
	}
	keys = append(typeKeys("claude,aider"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseModels {
		t.Fatalf("expected phase Models, got %v", m.phase)
	}
	keys = append(typeKeys("gpt-4o"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseListModelsCmd {
		t.Fatalf("expected phase ListModelsCmd, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter")

	if m.phase != wizPhaseDescription {
		t.Fatalf("expected phase Description, got %v", m.phase)
	}
	keys = append(typeKeys("My API"), "enter")
	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseUseProxy {
		t.Fatalf("expected phase UseProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter")

	if m.phase != wizPhaseKeepProxy {
		t.Fatalf("expected phase KeepProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter")

	if m.phase != wizPhaseEnabled {
		t.Fatalf("expected phase Enabled, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter")

	if m.phase != wizPhaseDone {
		t.Fatalf("expected Done, got %v", m.phase)
	}
	if m.aborted {
		t.Fatal("should not be aborted")
	}

	name, ep := m.result()
	if name != "myapi" {
		t.Fatalf("name = %q, want myapi", name)
	}
	if ep.Endpoint != "https://api.example.com" {
		t.Fatalf("endpoint = %q", ep.Endpoint)
	}
	if ep.APIKeyEnv != "MY_KEY" {
		t.Fatalf("api_key_env = %q", ep.APIKeyEnv)
	}
	if ep.SupportedClient != "claude,aider" {
		t.Fatalf("supported_client = %q", ep.SupportedClient)
	}
	if len(ep.Models) != 1 || ep.Models[0] != "gpt-4o" {
		t.Fatalf("models = %v", ep.Models)
	}
	if ep.Description != "My API" {
		t.Fatalf("description = %q", ep.Description)
	}
	if ep.UseProxy {
		t.Fatal("use_proxy should be false")
	}
	if ep.KeepProxyConfig {
		t.Fatal("keep_proxy_config should be false")
	}
	if !ep.IsEnabled() {
		t.Fatal("should be enabled")
	}
}

func TestProviderWizard_UpdateEnterThroughAll(t *testing.T) {
	existing := providers.Endpoint{
		Endpoint:        "https://old.example.com",
		APIKeyEnv:       "OLD_KEY",
		SupportedClient: "claude",
		Models:          []string{"old-model"},
		ListModelsCmd:   "list-cmd",
		Description:     "Old desc",
		UseProxy:        true,
		KeepProxyConfig: false,
	}
	enabled := true
	existing.Enabled = &enabled

	m := newProviderWizardModel(wizardModeUpdate, &existing, "oldname", nil)

	if m.phase != wizPhaseEndpoint {
		t.Fatalf("update should start at Endpoint, got %v", m.phase)
	}

	for m.phase != wizPhaseDone {
		m = driveProvWiz(t, m, "enter")
	}

	name, ep := m.result()
	if name != "oldname" {
		t.Fatalf("name = %q, want oldname", name)
	}
	if ep.Endpoint != "https://old.example.com" {
		t.Fatalf("endpoint = %q, want old value", ep.Endpoint)
	}
	if ep.APIKeyEnv != "OLD_KEY" {
		t.Fatalf("api_key_env = %q, want OLD_KEY", ep.APIKeyEnv)
	}
	if ep.SupportedClient != "claude" {
		t.Fatalf("supported_client = %q", ep.SupportedClient)
	}
	if len(ep.Models) != 1 || ep.Models[0] != "old-model" {
		t.Fatalf("models = %v", ep.Models)
	}
	if ep.Description != "Old desc" {
		t.Fatalf("description = %q", ep.Description)
	}
	if !ep.UseProxy {
		t.Fatal("use_proxy should be preserved as true")
	}
}

func TestProviderWizard_UpdateEditOneField(t *testing.T) {
	existing := providers.Endpoint{
		Endpoint:        "https://old.example.com",
		APIKeyEnv:       "OLD_KEY",
		SupportedClient: "claude",
		Description:     "Old desc",
	}
	m := newProviderWizardModel(wizardModeUpdate, &existing, "myapi", nil)

	m = driveProvWiz(t, m, "enter")
	m = driveProvWiz(t, m, "enter")
	keys := append(typeKeys("claude,aider"), "enter")
	m = driveProvWiz(t, m, keys...)
	for m.phase != wizPhaseDone {
		m = driveProvWiz(t, m, "enter")
	}

	_, ep := m.result()
	if ep.Endpoint != "https://old.example.com" {
		t.Fatalf("endpoint should be preserved, got %q", ep.Endpoint)
	}
	if ep.SupportedClient != "claude,aider" {
		t.Fatalf("supported_client = %q, want claude,aider", ep.SupportedClient)
	}
}

func TestProviderWizard_BackNavigation(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected Endpoint, got %v", m.phase)
	}

	keys = append(typeKeys("https://x"), "enter")
	m = driveProvWiz(t, m, keys...)
	if m.phase != wizPhaseAPIKeyEnv {
		t.Fatalf("expected APIKeyEnv, got %v", m.phase)
	}

	m = driveProvWiz(t, m, "esc")
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected Endpoint after esc, got %v", m.phase)
	}

	m = driveProvWiz(t, m, "esc")
	if m.phase != wizPhaseName {
		t.Fatalf("expected Name after second esc, got %v", m.phase)
	}
}

func TestProviderWizard_EscAtFirstPhaseIsNoOp(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)
	m = driveProvWiz(t, m, "esc")
	if !m.aborted {
		t.Fatal("esc at first phase should abort")
	}
}

func TestProviderWizard_CtrlCAborts(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)
	m = driveProvWiz(t, m, "ctrl+c")
	if !m.aborted {
		t.Fatal("ctrl+c should abort")
	}
}

func TestProviderWizard_DuplicateNameRejected(t *testing.T) {
	existing := []string{"taken-name", "other"}
	m := newProviderWizardModel(wizardModeAdd, nil, "", existing)

	keys := append(typeKeys("taken-name"), "enter")
	m = driveProvWiz(t, m, keys...)
	if m.phase != wizPhaseName {
		t.Fatalf("should stay on Name phase, got %v", m.phase)
	}
	if m.nameStep.errMsg == "" {
		t.Fatal("expected error message for duplicate name")
	}
}

func TestProviderWizard_AddRequiredEndpoint(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)

	m = driveProvWiz(t, m, "enter")
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("should stay on Endpoint when empty, got %v", m.phase)
	}
	if m.endpointStep.errMsg == "" {
		t.Fatal("expected error for required endpoint")
	}
}

func TestProviderWizard_BoolPickerSelectsYes(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	keys := append(typeKeys("n"), "enter")
	keys = append(keys, append(typeKeys("http://x"), "enter")...)
	keys = append(keys, "enter") // api key
	keys = append(keys, "enter") // clients
	keys = append(keys, "enter") // models
	keys = append(keys, "enter") // list models cmd
	keys = append(keys, "enter") // description

	m = driveProvWiz(t, m, keys...)

	if m.phase != wizPhaseUseProxy {
		t.Fatalf("expected UseProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "up", "enter") // move to yes, then select

	m = driveProvWiz(t, m, "enter") // keep proxy "no"
	m = driveProvWiz(t, m, "enter") // enabled "yes"

	_, ep := m.result()
	if !ep.UseProxy {
		t.Fatal("use_proxy should be true after selecting yes")
	}
}

func TestProviderWizard_ViewRendersCurrentPhase(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)
	view := m.View()
	if !strings.Contains(view, "Provider Name") {
		t.Fatalf("view should contain Name title, got: %s", view)
	}
}
