package cli

import (
	"bytes"
	"errors"
	"fmt"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

// testRegistry builds a tools.Registry with a small fixed set so the
// wizard's LaunchNames/ByCLICommand calls are deterministic.
func testRegistry(t *testing.T) *tools.Registry {
	t.Helper()
	enabled := true
	reg := &tools.Registry{Tools: map[string]tools.Tool{
		"claude-code":  {Name: "claude-code", CLICommand: "claude", Enabled: &enabled},
		"openai-codex": {Name: "openai-codex", CLICommand: "codex", Enabled: &enabled},
		"qwen-code":    {Name: "qwen-code", CLICommand: "qwen", Enabled: &enabled},
	}}
	return reg
}

func testProviders() providers.File {
	return providers.File{
		Endpoints: map[string]providers.Endpoint{
			"alpha": {Endpoint: "https://alpha", SupportedClient: "claude,codex", Models: []string{"m-a1", "m-a2"}},
			"beta":  {Endpoint: "https://beta", SupportedClient: "qwen", Models: []string{"m-b1"}},
			"gamma": {Endpoint: "https://gamma", SupportedClient: "claude", Models: []string{"m-g1"}},
		},
	}
}

func resolveModelsFromEndpoint(ep providers.Endpoint, _ string) ([]string, error) {
	return append([]string(nil), ep.Models...), nil
}

func resolveModelsErr(err error) func(providers.Endpoint, string) ([]string, error) {
	return func(providers.Endpoint, string) ([]string, error) {
		return nil, err
	}
}

func numberedModels(prefix string, count int) []string {
	models := make([]string, 0, count)
	for i := 1; i <= count; i++ {
		models = append(models, fmt.Sprintf("%s-%02d", prefix, i))
	}
	return models
}

func TestValidatePinned_AllPinnedHappyPath(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned: launchSelection{
			Tool:         tool,
			EndpointName: "alpha",
			Model:        "m-a1",
		},
		Providers: testProviders(),
		Registry:  reg,
	}
	sel, needT, needE, needM, err := validatePinned(in)
	if err != nil {
		t.Fatal(err)
	}
	if needT || needE || needM {
		t.Fatalf("expected no needs, got %v %v %v", needT, needE, needM)
	}
	if sel.EndpointName != "alpha" || sel.Endpoint.Endpoint != "https://alpha" {
		t.Fatalf("endpoint not resolved: %+v", sel)
	}
}

func TestValidatePinned_UnknownEndpoint(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:    launchSelection{Tool: tool, EndpointName: "nope", Model: "x"},
		Providers: testProviders(),
		Registry:  reg,
	}
	if _, _, _, _, err := validatePinned(in); err == nil ||
		!strings.Contains(err.Error(), "Unknown endpoint") {
		t.Fatalf("expected unknown endpoint error, got %v", err)
	}
}

func TestValidatePinned_UnsupportedEndpointForTool(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:    launchSelection{Tool: tool, EndpointName: "beta", Model: "m-b1"},
		Providers: testProviders(),
		Registry:  reg,
	}
	if _, _, _, _, err := validatePinned(in); err == nil ||
		!strings.Contains(err.Error(), "does not support tool") {
		t.Fatalf("expected unsupported-client error, got %v", err)
	}
}

func TestRunLaunchWizard_AllPinned_NoTUI(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	var buf bytes.Buffer
	sel, cancelled, err := runLaunchWizard(&buf, wizardInput{
		Pinned: launchSelection{
			Tool: tool, EndpointName: "alpha", Model: "m-a1",
		},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	})
	if err != nil {
		t.Fatal(err)
	}
	if cancelled {
		t.Fatal("should not have cancelled when fully pinned")
	}
	if sel.Model != "m-a1" || sel.EndpointName != "alpha" {
		t.Fatalf("selection wrong: %+v", sel)
	}
	if buf.Len() != 0 {
		t.Fatalf("no output expected when fully pinned, got %q", buf.String())
	}
}

// Below: drive the wizard model directly (skipping the bubbletea
// Program) by feeding key events and inspecting state. This avoids
// needing a real TTY in tests.

func keyEvent(s string) tea.KeyMsg {
	switch s {
	case "enter":
		return tea.KeyMsg{Type: tea.KeyEnter}
	case "esc":
		return tea.KeyMsg{Type: tea.KeyEsc}
	case "up":
		return tea.KeyMsg{Type: tea.KeyUp}
	case "down":
		return tea.KeyMsg{Type: tea.KeyDown}
	case "backspace":
		return tea.KeyMsg{Type: tea.KeyBackspace}
	case "ctrl+c":
		return tea.KeyMsg{Type: tea.KeyCtrlC}
	}
	return tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune(s)}
}

func drive(t *testing.T, m launchWizardModel, keys ...string) launchWizardModel {
	t.Helper()
	for _, k := range keys {
		next, cmd := m.Update(keyEvent(k))
		m = next.(launchWizardModel)
		_ = cmd
	}
	return m
}

func TestPickerStep_DefaultPickerShowsAllItems(t *testing.T) {
	items := numberedModels("model", 20)
	step := newPickerStep("Select a model", items, "type to filter")

	visible := step.visible()
	if len(visible) != 20 {
		t.Fatalf("visible count = %d, want 20", len(visible))
	}
	if visible[19] != "model-20" {
		t.Fatalf("last visible item = %q, want model-20", visible[19])
	}
}

func TestPickerStep_LimitedPickerCapsVisibleItems(t *testing.T) {
	items := numberedModels("model", 20)
	step := newLimitedPickerStep("Select a model", items, "type to filter", 15)

	visible := step.visible()
	if len(visible) != 15 {
		t.Fatalf("visible count = %d, want 15", len(visible))
	}
	if visible[14] != "model-15" {
		t.Fatalf("last visible item = %q, want model-15", visible[14])
	}
}

func TestPickerStep_LimitedPickerFiltersAcrossAllItems(t *testing.T) {
	items := numberedModels("model", 20)
	step := newLimitedPickerStep("Select a model", items, "type to filter", 15)

	step.update(keyEvent("2"))
	step.update(keyEvent("0"))

	visible := step.visible()
	if len(visible) != 1 {
		t.Fatalf("visible count = %d, want 1; visible=%v", len(visible), visible)
	}
	if visible[0] != "model-20" {
		t.Fatalf("visible item = %q, want model-20", visible[0])
	}
}

func TestWizard_AllUnpinned_HappyPath(t *testing.T) {
	reg := testRegistry(t)
	in := wizardInput{
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, needT, needE, needM, err := validatePinned(in)
	if err != nil {
		t.Fatal(err)
	}
	m := newLaunchWizardModel(sel, in, needT, needE, needM)
	if m.phase != phasePickTool {
		t.Fatalf("first phase should be tool, got %v", m.phase)
	}
	// Pick "claude" (first alphabetically in LaunchNames).
	m = drive(t, m, "enter") // selects first item: "claude"
	if m.sel.Tool.LaunchCommand() != "claude" {
		t.Fatalf("tool selection wrong: %+v", m.sel.Tool)
	}
	if m.phase != phasePickEndpoint {
		t.Fatalf("should be on endpoint, got %v", m.phase)
	}
	// Endpoint picker should list alpha and gamma (both support claude),
	// alphabetical → alpha is first.
	m = drive(t, m, "enter")
	if m.sel.EndpointName != "alpha" {
		t.Fatalf("endpoint selection wrong: %s", m.sel.EndpointName)
	}
	if m.phase != phasePickModel {
		t.Fatalf("should be on model phase, got %v", m.phase)
	}
	// Models from alpha = m-a1, m-a2.
	m = drive(t, m, "down", "enter")
	if m.sel.Model != "m-a2" {
		t.Fatalf("model selection wrong: %s", m.sel.Model)
	}
	if m.phase != phaseDone {
		t.Fatalf("should be done, got %v", m.phase)
	}
}

func TestWizard_PinnedTool_SkipsPhase1(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:        launchSelection{Tool: tool},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, needT, needE, needM, err := validatePinned(in)
	if err != nil {
		t.Fatal(err)
	}
	if needT {
		t.Fatal("tool should be pinned")
	}
	m := newLaunchWizardModel(sel, in, needT, needE, needM)
	if m.phase != phasePickEndpoint {
		t.Fatalf("should start at endpoint, got %v", m.phase)
	}
}

func TestWizard_EndpointFiltersByClient(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:        launchSelection{Tool: tool},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, _, needE, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, false, needE, needM)
	visible := m.endpointStep.visible()
	want := []string{"alpha", "gamma"}
	if len(visible) != len(want) {
		t.Fatalf("expected %v got %v", want, visible)
	}
	for i, v := range visible {
		if v != want[i] {
			t.Fatalf("expected %v got %v", want, visible)
		}
	}
}

func TestWizard_ModelPickerShowsCappedPreviewAndFiltersAllModels(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	providerFile := testProviders()
	providerFile.Endpoints["alpha"] = providers.Endpoint{
		Endpoint:        "https://alpha",
		SupportedClient: "claude,codex",
		Models:          numberedModels("model", 20),
	}
	in := wizardInput{
		Pinned: launchSelection{
			Tool: tool, EndpointName: "alpha",
		},
		Providers:     providerFile,
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}

	sel, _, _, needM, err := validatePinned(in)
	if err != nil {
		t.Fatal(err)
	}
	m := newLaunchWizardModel(sel, in, false, false, needM)

	visible := m.modelStep.visible()
	if len(visible) != 15 {
		t.Fatalf("initial model count = %d, want 15", len(visible))
	}
	if visible[14] != "model-15" {
		t.Fatalf("last initial model = %q, want model-15", visible[14])
	}

	m = drive(t, m, "2", "0")
	visible = m.modelStep.visible()
	if len(visible) != 1 {
		t.Fatalf("filtered model count = %d, want 1; visible=%v", len(visible), visible)
	}
	if visible[0] != "model-20" {
		t.Fatalf("filtered model = %q, want model-20", visible[0])
	}
}

func TestPickerStep_LimitedPickerViewFollowsCursorPastInitialPreview(t *testing.T) {
	items := numberedModels("model", 20)
	step := newLimitedPickerStep("Select a model", items, "type to filter", 15)

	for i := 0; i < 19; i++ {
		step.update(keyEvent("down"))
	}

	view := step.view()
	if strings.Contains(view, "model-01") {
		t.Fatalf("view should slide past the initial preview after moving down:\n%s", view)
	}
	if !strings.Contains(view, "> model-20") {
		t.Fatalf("view should show cursor on model-20 after moving down:\n%s", view)
	}
}

func TestWizard_ModelPickerCanMovePastCappedPreview(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	providerFile := testProviders()
	providerFile.Endpoints["alpha"] = providers.Endpoint{
		Endpoint:        "https://alpha",
		SupportedClient: "claude,codex",
		Models:          numberedModels("model", 20),
	}
	in := wizardInput{
		Pinned: launchSelection{
			Tool: tool, EndpointName: "alpha",
		},
		Providers:     providerFile,
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}

	sel, _, _, needM, err := validatePinned(in)
	if err != nil {
		t.Fatal(err)
	}
	m := newLaunchWizardModel(sel, in, false, false, needM)

	for i := 0; i < 19; i++ {
		m = drive(t, m, "down")
	}
	m = drive(t, m, "enter")

	if m.sel.Model != "model-20" {
		t.Fatalf("selected model = %q, want model-20", m.sel.Model)
	}
}

func TestWizard_ModelListEmpty_ManualEntry(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned: launchSelection{
			Tool: tool, EndpointName: "alpha",
		},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsErr(errors.New("boom")),
	}
	sel, _, _, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, false, false, needM)
	if !m.manualEntry {
		t.Fatal("expected manual entry when ResolveModels fails")
	}
	// Type "my-model" + enter.
	m = drive(t, m, "m", "y", "-", "m", "o", "d", "e", "l", "enter")
	if m.sel.Model != "my-model" {
		t.Fatalf("model = %q, want my-model", m.sel.Model)
	}
	if m.phase != phaseDone {
		t.Fatalf("phase = %v, want done", m.phase)
	}
}

func TestWizard_ManualEntry_EscReturnsToEndpoint(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:        launchSelection{Tool: tool},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsErr(errors.New("boom")),
	}
	sel, _, needE, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, false, needE, needM)
	// Pick "alpha", which has Models so won't be manual… use endpoint
	// with no models instead by swapping. Use a fake endpoint with no
	// models by patching ResolveModels to always return ([], nil).
	m = drive(t, m, "enter") // pick alpha
	if !m.manualEntry {
		t.Fatal("expected manual entry")
	}
	m = drive(t, m, "esc")
	if m.phase != phasePickEndpoint {
		t.Fatalf("phase = %v, want endpoint after esc", m.phase)
	}
	if m.manualEntry {
		t.Fatal("manual entry should be cleared after esc")
	}
}

func TestWizard_EscAtFirstPhase_NoOp(t *testing.T) {
	reg := testRegistry(t)
	in := wizardInput{
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, needT, needE, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, needT, needE, needM)
	m = drive(t, m, "esc")
	if m.phase != phasePickTool {
		t.Fatalf("esc at phase 1 should be no-op, phase=%v", m.phase)
	}
	if m.aborted {
		t.Fatal("esc at phase 1 should not abort")
	}
}

func TestWizard_QuitAbortsAtAnyPhase(t *testing.T) {
	reg := testRegistry(t)
	tool, _ := reg.ByCLICommand("claude")
	in := wizardInput{
		Pinned:        launchSelection{Tool: tool, EndpointName: "alpha"},
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, _, _, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, false, false, needM)
	m = drive(t, m, "q")
	if !m.aborted {
		t.Fatal("q should abort")
	}
}

func TestWizard_StepBack_ClearsLaterSelections(t *testing.T) {
	reg := testRegistry(t)
	in := wizardInput{
		Providers:     testProviders(),
		Registry:      reg,
		ResolveModels: resolveModelsFromEndpoint,
	}
	sel, needT, needE, needM, _ := validatePinned(in)
	m := newLaunchWizardModel(sel, in, needT, needE, needM)
	// tool=claude, endpoint=alpha, then esc back to endpoint.
	m = drive(t, m, "enter", "enter", "esc")
	if m.phase != phasePickEndpoint {
		t.Fatalf("phase = %v, want endpoint", m.phase)
	}
	if m.sel.EndpointName != "" {
		t.Fatalf("endpoint should be cleared, got %q", m.sel.EndpointName)
	}
	if m.sel.Tool.LaunchCommand() != "claude" {
		t.Fatal("tool should be preserved")
	}
}
