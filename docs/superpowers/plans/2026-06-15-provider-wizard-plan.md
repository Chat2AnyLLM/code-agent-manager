# Provider Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guided Bubble Tea wizard to `cam provider add` and `cam provider update` so that running either command without flags launches a step-by-step interactive TUI, while flag-based usage remains fully backward compatible.

**Architecture:** Two new components — `textInputStep` (reusable text input matching the existing `pickerStep` contract) and `providerWizardModel` (multi-phase `tea.Model` following the same pattern as `launchWizardModel`). The existing `providerAddCommand` and `providerUpdateCommand` are modified to detect missing args/flags and dispatch to the wizard when running in a TTY.

**Tech Stack:** Go, Cobra (CLI framework), Bubble Tea (TUI framework), existing `pickerStep` component

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `internal/cli/text_input_step.go` | Create | Reusable text input step component |
| `internal/cli/text_input_step_test.go` | Create | Unit tests for textInputStep |
| `internal/cli/provider_wizard.go` | Create | Provider wizard model + entry point |
| `internal/cli/provider_wizard_test.go` | Create | Unit tests for wizard model |
| `internal/cli/provider_cmd.go` | Modify | Wire wizard into add/update commands |
| `internal/cli/cmd_provider_test.go` | Modify | Integration tests for wizard fallback |

---

### Task 1: textInputStep — Failing Tests

**Files:**
- Create: `internal/cli/text_input_step_test.go`

This task writes all the tests for `textInputStep` before any implementation exists. The tests use the same `keyEvent` helper from `launch_wizard_test.go` (which is in the same `cli` package).

- [ ] **Step 1: Create the test file with all textInputStep tests**

Create `internal/cli/text_input_step_test.go`:

```go
package cli

import (
	"strings"
	"testing"
)

func TestTextInputStep_TypeAndAdvance(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", false, "hint")
	for _, ch := range "hello" {
		action := s.update(keyEvent(string(ch)))
		if action != pickerActionNone {
			t.Fatalf("typing should return None, got %v", action)
		}
	}
	if s.value != "hello" {
		t.Fatalf("value = %q, want hello", s.value)
	}
	action := s.update(keyEvent("enter"))
	if action != pickerActionAdvance {
		t.Fatalf("enter should advance, got %v", action)
	}
	if s.selected() != "hello" {
		t.Fatalf("selected() = %q, want hello", s.selected())
	}
}

func TestTextInputStep_EscReturnsBack(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", false, "hint")
	action := s.update(keyEvent("esc"))
	if action != pickerActionBack {
		t.Fatalf("esc should return Back, got %v", action)
	}
}

func TestTextInputStep_CtrlCAborts(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", false, "hint")
	action := s.update(keyEvent("ctrl+c"))
	if action != pickerActionAbort {
		t.Fatalf("ctrl+c should abort, got %v", action)
	}
}

func TestTextInputStep_RequiredRejectsEmpty(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", true, "hint")
	action := s.update(keyEvent("enter"))
	if action != pickerActionNone {
		t.Fatalf("enter on empty required should return None, got %v", action)
	}
	if s.errMsg == "" {
		t.Fatal("expected errMsg set on empty required field")
	}
}

func TestTextInputStep_RequiredClearsErrOnKeystroke(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", true, "hint")
	s.update(keyEvent("enter")) // triggers error
	if s.errMsg == "" {
		t.Fatal("expected errMsg after empty enter")
	}
	s.update(keyEvent("a"))
	if s.errMsg != "" {
		t.Fatalf("errMsg should be cleared after keystroke, got %q", s.errMsg)
	}
}

func TestTextInputStep_Backspace(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", false, "hint")
	s.update(keyEvent("a"))
	s.update(keyEvent("b"))
	s.update(keyEvent("backspace"))
	if s.value != "a" {
		t.Fatalf("value = %q after backspace, want a", s.value)
	}
}

func TestTextInputStep_BackspaceOnEmpty(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", false, "hint")
	action := s.update(keyEvent("backspace"))
	if action != pickerActionNone {
		t.Fatalf("backspace on empty should be no-op, got %v", action)
	}
	if s.value != "" {
		t.Fatalf("value should remain empty, got %q", s.value)
	}
}

func TestTextInputStep_PlaceholderOnOptionalEmptyEnter(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "default-val", false, "hint")
	action := s.update(keyEvent("enter"))
	if action != pickerActionAdvance {
		t.Fatalf("enter on optional with placeholder should advance, got %v", action)
	}
	if s.selected() != "default-val" {
		t.Fatalf("selected() = %q, want default-val", s.selected())
	}
}

func TestTextInputStep_TypingOverridesPlaceholder(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "default-val", false, "hint")
	s.update(keyEvent("x"))
	s.update(keyEvent("enter"))
	if s.selected() != "x" {
		t.Fatalf("selected() = %q, want x", s.selected())
	}
}

func TestTextInputStep_ViewContainsTitleAndHint(t *testing.T) {
	s := newTextInputStep("My Title", "Prompt:", "", false, "my hint")
	view := s.view()
	if !strings.Contains(view, "My Title") {
		t.Fatalf("view missing title: %s", view)
	}
	if !strings.Contains(view, "my hint") {
		t.Fatalf("view missing hint: %s", view)
	}
}

func TestTextInputStep_ViewShowsPlaceholder(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "current-val", false, "hint")
	view := s.view()
	if !strings.Contains(view, "[current-val]") {
		t.Fatalf("view missing placeholder: %s", view)
	}
}

func TestTextInputStep_ViewShowsError(t *testing.T) {
	s := newTextInputStep("Title", "Name:", "", true, "hint")
	s.update(keyEvent("enter")) // triggers error
	view := s.view()
	if !strings.Contains(view, s.errMsg) {
		t.Fatalf("view missing error: %s", view)
	}
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -run TestTextInputStep -v -count=1`

Expected: Compilation error — `newTextInputStep` undefined.

- [ ] **Step 3: Commit**

```bash
git add internal/cli/text_input_step_test.go
git commit --author="James Zhu <zhujian0805@gmail.com>" -m "test: add failing tests for textInputStep component"
```

---

### Task 2: textInputStep — Implementation

**Files:**
- Create: `internal/cli/text_input_step.go`
- Test: `internal/cli/text_input_step_test.go` (written in Task 1)

- [ ] **Step 1: Create the textInputStep implementation**

Create `internal/cli/text_input_step.go`:

```go
package cli

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// textInputStep is a reusable free-text input component that follows the
// same update/view/selected contract as pickerStep. It handles typing,
// backspace, Enter (advance), Esc (back), and Ctrl+C (abort).
type textInputStep struct {
	title       string
	prompt      string
	value       string
	placeholder string // shown when value is empty (e.g. current value for update)
	required    bool
	hint        string
	errMsg      string // validation error, cleared on next keystroke
}

// newTextInputStep constructs a textInputStep. placeholder is the default
// value shown/returned when value is empty (used for update mode pre-population).
func newTextInputStep(title, prompt, placeholder string, required bool, hint string) textInputStep {
	return textInputStep{
		title:       title,
		prompt:      prompt,
		placeholder: placeholder,
		required:    required,
		hint:        hint,
	}
}

// update processes a key event and returns the action the wrapping model
// should take. Same contract as pickerStep.update.
func (s *textInputStep) update(msg tea.KeyMsg) pickerAction {
	switch msg.Type {
	case tea.KeyCtrlC:
		return pickerActionAbort
	case tea.KeyEsc:
		return pickerActionBack
	case tea.KeyEnter:
		if s.value == "" && s.required && s.placeholder == "" {
			s.errMsg = "This field is required"
			return pickerActionNone
		}
		return pickerActionAdvance
	case tea.KeyBackspace:
		if s.value != "" {
			s.value = s.value[:len(s.value)-1]
		}
		return pickerActionNone
	default:
		text := msg.String()
		if len(text) == 1 {
			s.errMsg = ""
			s.value += text
		}
		return pickerActionNone
	}
}

// selected returns the current value, falling back to placeholder when the
// user typed nothing and the field is optional.
func (s textInputStep) selected() string {
	if s.value != "" {
		return s.value
	}
	return s.placeholder
}

// view renders the step for display.
func (s textInputStep) view() string {
	var b strings.Builder
	b.WriteString(s.title)
	b.WriteString("\n\n")
	if s.errMsg != "" {
		fmt.Fprintf(&b, "  ⚠ %s\n\n", s.errMsg)
	}
	if s.value != "" {
		fmt.Fprintf(&b, "  %s %s_\n", s.prompt, s.value)
	} else if s.placeholder != "" {
		fmt.Fprintf(&b, "  %s [%s] _\n", s.prompt, s.placeholder)
	} else {
		fmt.Fprintf(&b, "  %s _\n", s.prompt)
	}
	if s.hint != "" {
		b.WriteString("\n")
		b.WriteString(s.hint)
		b.WriteString("\n")
	}
	return b.String()
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -run TestTextInputStep -v -count=1`

Expected: All 12 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add internal/cli/text_input_step.go
git commit --author="James Zhu <zhujian0805@gmail.com>" -m "feat: add textInputStep component for provider wizard"
```

---

### Task 3: providerWizardModel — Failing Tests

**Files:**
- Create: `internal/cli/provider_wizard_test.go`

These tests drive the wizard model directly by feeding key events (same pattern as `launch_wizard_test.go`). They reuse the `keyEvent` helper from `launch_wizard_test.go` which is in the same package.

- [ ] **Step 1: Create the test file with all providerWizardModel tests**

Create `internal/cli/provider_wizard_test.go`:

```go
package cli

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"

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

// typeString returns key events for each character in s.
func typeKeys(s string) []string {
	keys := make([]string, len(s))
	for i, ch := range s {
		keys[i] = string(ch)
	}
	return keys
}

func TestProviderWizard_AddFullFlow(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	// Phase 1: Name
	if m.phase != wizPhaseName {
		t.Fatalf("expected phase Name, got %v", m.phase)
	}
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 2: Endpoint
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected phase Endpoint, got %v", m.phase)
	}
	keys = append(typeKeys("https://api.example.com"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 3: API Key Env
	if m.phase != wizPhaseAPIKeyEnv {
		t.Fatalf("expected phase APIKeyEnv, got %v", m.phase)
	}
	keys = append(typeKeys("MY_KEY"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 4: Clients
	if m.phase != wizPhaseClients {
		t.Fatalf("expected phase Clients, got %v", m.phase)
	}
	keys = append(typeKeys("claude,aider"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 5: Models
	if m.phase != wizPhaseModels {
		t.Fatalf("expected phase Models, got %v", m.phase)
	}
	keys = append(typeKeys("gpt-4o"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 6: List Models Cmd
	if m.phase != wizPhaseListModelsCmd {
		t.Fatalf("expected phase ListModelsCmd, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter") // skip (optional)

	// Phase 7: Description
	if m.phase != wizPhaseDescription {
		t.Fatalf("expected phase Description, got %v", m.phase)
	}
	keys = append(typeKeys("My API"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Phase 8: Use Proxy (bool picker, default "no" = index 1)
	if m.phase != wizPhaseUseProxy {
		t.Fatalf("expected phase UseProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter") // select "no" (default)

	// Phase 9: Keep Proxy Config
	if m.phase != wizPhaseKeepProxy {
		t.Fatalf("expected phase KeepProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter") // select "no" (default)

	// Phase 10: Enabled (default "yes" = index 0)
	if m.phase != wizPhaseEnabled {
		t.Fatalf("expected phase Enabled, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter") // select "yes" (default)

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

	// Update skips name phase, starts at endpoint
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("update should start at Endpoint, got %v", m.phase)
	}

	// Enter through all steps without typing anything (keep current values)
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

	// Enter to keep endpoint
	m = driveProvWiz(t, m, "enter")
	// Enter to keep api key env
	m = driveProvWiz(t, m, "enter")
	// Type new clients
	keys := append(typeKeys("claude,aider"), "enter")
	m = driveProvWiz(t, m, keys...)
	// Enter through rest
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

	// Type name and advance
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected Endpoint, got %v", m.phase)
	}

	// Type endpoint and advance
	keys = append(typeKeys("https://x"), "enter")
	m = driveProvWiz(t, m, keys...)
	if m.phase != wizPhaseAPIKeyEnv {
		t.Fatalf("expected APIKeyEnv, got %v", m.phase)
	}

	// Esc back to endpoint
	m = driveProvWiz(t, m, "esc")
	if m.phase != wizPhaseEndpoint {
		t.Fatalf("expected Endpoint after esc, got %v", m.phase)
	}

	// Esc back to name
	m = driveProvWiz(t, m, "esc")
	if m.phase != wizPhaseName {
		t.Fatalf("expected Name after second esc, got %v", m.phase)
	}
}

func TestProviderWizard_EscAtFirstPhaseIsNoOp(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)
	m = driveProvWiz(t, m, "esc")
	// Esc at first phase aborts
	if !m.aborted {
		t.Fatal("esc at first phase should abort")
	}
}

func TestProviderWizard_CtrlCAborts(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)
	// Now at endpoint, ctrl+c
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
	// Should still be on name phase with an error
	if m.phase != wizPhaseName {
		t.Fatalf("should stay on Name phase, got %v", m.phase)
	}
	if m.nameStep.errMsg == "" {
		t.Fatal("expected error message for duplicate name")
	}
}

func TestProviderWizard_AddRequiredEndpoint(t *testing.T) {
	m := newProviderWizardModel(wizardModeAdd, nil, "", nil)

	// Name
	keys := append(typeKeys("myapi"), "enter")
	m = driveProvWiz(t, m, keys...)

	// Endpoint: try to skip with empty enter
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

	// Skip through text steps quickly
	keys := append(typeKeys("n"), "enter")           // name
	keys = append(keys, append(typeKeys("http://x"), "enter")...) // endpoint
	keys = append(keys, "enter")                      // api key (skip)
	keys = append(keys, "enter")                      // clients (skip)
	keys = append(keys, "enter")                      // models (skip)
	keys = append(keys, "enter")                      // list models cmd (skip)
	keys = append(keys, "enter")                      // description (skip)

	m = driveProvWiz(t, m, keys...)

	// Now at UseProxy — select "yes" (it's the first item)
	if m.phase != wizPhaseUseProxy {
		t.Fatalf("expected UseProxy, got %v", m.phase)
	}
	m = driveProvWiz(t, m, "enter") // "yes" is first

	// KeepProxy
	m = driveProvWiz(t, m, "enter") // "no" default

	// Enabled
	m = driveProvWiz(t, m, "enter") // "yes" default

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -run TestProviderWizard -v -count=1`

Expected: Compilation error — `wizardModeAdd`, `newProviderWizardModel`, `providerWizardModel` undefined.

- [ ] **Step 3: Commit**

```bash
git add internal/cli/provider_wizard_test.go
git commit --author="James Zhu <zhujian0805@gmail.com>" -m "test: add failing tests for providerWizardModel"
```

---

### Task 4: providerWizardModel — Implementation

**Files:**
- Create: `internal/cli/provider_wizard.go`
- Test: `internal/cli/provider_wizard_test.go` (written in Task 3)

- [ ] **Step 1: Create the provider wizard implementation**

Create `internal/cli/provider_wizard.go`:

```go
package cli

import (
	"fmt"
	"io"
	"os"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// wizardMode distinguishes add from update.
type wizardMode int

const (
	wizardModeAdd wizardMode = iota
	wizardModeUpdate
)

// providerWizardPhase identifies the active wizard step.
type providerWizardPhase int

const (
	wizPhaseName providerWizardPhase = iota
	wizPhaseEndpoint
	wizPhaseAPIKeyEnv
	wizPhaseClients
	wizPhaseModels
	wizPhaseListModelsCmd
	wizPhaseDescription
	wizPhaseUseProxy
	wizPhaseKeepProxy
	wizPhaseEnabled
	wizPhaseDone
)

// providerWizardModel is the Bubble Tea model for the provider add/update
// wizard. It follows the same architecture as launchWizardModel: each phase
// has a step, and navigation advances/retreats through phases.
type providerWizardModel struct {
	mode       wizardMode
	phase      providerWizardPhase
	startPhase providerWizardPhase

	// Text input steps
	nameStep          textInputStep
	endpointStep      textInputStep
	apiKeyEnvStep     textInputStep
	clientsStep       textInputStep
	modelsStep        textInputStep
	listModelsCmdStep textInputStep
	descriptionStep   textInputStep

	// Bool picker steps
	useProxyStep  pickerStep
	keepProxyStep pickerStep
	enabledStep   pickerStep

	// Pre-set name for update mode
	existingName  string
	existingNames map[string]bool

	aborted bool
}

// newProviderWizardModel constructs the wizard. For update mode, pass the
// existing endpoint and name. existingNames is used for duplicate checking
// on add.
func newProviderWizardModel(
	mode wizardMode,
	existing *providers.Endpoint,
	existingName string,
	existingNamesList []string,
) providerWizardModel {
	m := providerWizardModel{
		mode:         mode,
		existingName: existingName,
	}

	// Build duplicate-name lookup set.
	m.existingNames = map[string]bool{}
	for _, n := range existingNamesList {
		m.existingNames[n] = true
	}

	// Determine defaults from existing endpoint (update mode).
	var ep providers.Endpoint
	if existing != nil {
		ep = *existing
	}

	// Text steps.
	m.nameStep = newTextInputStep(
		"Provider Name",
		"Name:",
		"",
		true,
		"Enter a unique name for this provider. Press Enter to continue, Esc to cancel.",
	)

	m.endpointStep = newTextInputStep(
		"Endpoint URL",
		"URL:",
		ep.Endpoint,
		true,
		"The base URL for this provider's API. Press Enter to continue, Esc to go back.",
	)

	m.apiKeyEnvStep = newTextInputStep(
		"API Key Environment Variable",
		"Env var:",
		ep.APIKeyEnv,
		false,
		"Name of the env var holding the API key (leave empty to skip). Enter to continue, Esc back.",
	)

	m.clientsStep = newTextInputStep(
		"Supported Clients",
		"Clients:",
		ep.SupportedClient,
		false,
		"Comma-separated client names (e.g. claude,aider,codex). Enter to continue, Esc back.",
	)

	modelsPlaceholder := strings.Join(ep.Models, ",")
	m.modelsStep = newTextInputStep(
		"Models",
		"Models:",
		modelsPlaceholder,
		false,
		"Comma-separated model names. Enter to continue, Esc back.",
	)

	m.listModelsCmdStep = newTextInputStep(
		"List Models Command",
		"Command:",
		ep.ListModelsCmd,
		false,
		"Shell command for dynamic model discovery (optional). Enter to continue, Esc back.",
	)

	m.descriptionStep = newTextInputStep(
		"Description",
		"Description:",
		ep.Description,
		false,
		"Human-readable description (optional). Enter to continue, Esc back.",
	)

	// Bool picker steps.
	useProxyCursor := 1 // default "no"
	if ep.UseProxy {
		useProxyCursor = 0 // "yes"
	}
	m.useProxyStep = newPickerStep(
		"Use Proxy",
		[]string{"yes", "no"},
		"Route requests through the configured proxy? Enter to continue, Esc back.",
	)
	m.useProxyStep.cursor = useProxyCursor

	keepProxyCursor := 1 // default "no"
	if ep.KeepProxyConfig {
		keepProxyCursor = 0
	}
	m.keepProxyStep = newPickerStep(
		"Keep Proxy Config",
		[]string{"yes", "no"},
		"Preserve proxy environment variables during model discovery? Enter to continue, Esc back.",
	)
	m.keepProxyStep.cursor = keepProxyCursor

	enabledCursor := 0 // default "yes"
	if existing != nil && !ep.IsEnabled() {
		enabledCursor = 1 // "no"
	}
	m.enabledStep = newPickerStep(
		"Enabled",
		[]string{"yes", "no"},
		"Enable this provider for use in tool launches? Enter to finish, Esc back.",
	)
	m.enabledStep.cursor = enabledCursor

	// Set start phase.
	if mode == wizardModeUpdate {
		m.phase = wizPhaseEndpoint
		m.startPhase = wizPhaseEndpoint
	} else {
		m.phase = wizPhaseName
		m.startPhase = wizPhaseName
	}

	return m
}

func (m providerWizardModel) Init() tea.Cmd { return nil }

func (m providerWizardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}

	// Dispatch to the active step.
	var action pickerAction
	switch m.phase {
	case wizPhaseName:
		action = m.nameStep.update(key)
	case wizPhaseEndpoint:
		action = m.endpointStep.update(key)
	case wizPhaseAPIKeyEnv:
		action = m.apiKeyEnvStep.update(key)
	case wizPhaseClients:
		action = m.clientsStep.update(key)
	case wizPhaseModels:
		action = m.modelsStep.update(key)
	case wizPhaseListModelsCmd:
		action = m.listModelsCmdStep.update(key)
	case wizPhaseDescription:
		action = m.descriptionStep.update(key)
	case wizPhaseUseProxy:
		action = m.useProxyStep.update(key)
	case wizPhaseKeepProxy:
		action = m.keepProxyStep.update(key)
	case wizPhaseEnabled:
		action = m.enabledStep.update(key)
	default:
		return m, nil
	}

	switch action {
	case pickerActionAbort:
		m.aborted = true
		return m, tea.Quit
	case pickerActionBack:
		m.stepBack()
		return m, nil
	case pickerActionAdvance:
		// Validate before advancing.
		if m.phase == wizPhaseName {
			name := m.nameStep.selected()
			if m.existingNames[name] {
				m.nameStep.errMsg = fmt.Sprintf("Provider %q already exists", name)
				return m, nil
			}
		}
		m.advance()
		if m.phase == wizPhaseDone {
			return m, tea.Quit
		}
		return m, nil
	}

	return m, nil
}

func (m providerWizardModel) View() string {
	switch m.phase {
	case wizPhaseName:
		return m.nameStep.view()
	case wizPhaseEndpoint:
		return m.endpointStep.view()
	case wizPhaseAPIKeyEnv:
		return m.apiKeyEnvStep.view()
	case wizPhaseClients:
		return m.clientsStep.view()
	case wizPhaseModels:
		return m.modelsStep.view()
	case wizPhaseListModelsCmd:
		return m.listModelsCmdStep.view()
	case wizPhaseDescription:
		return m.descriptionStep.view()
	case wizPhaseUseProxy:
		return m.useProxyStep.view()
	case wizPhaseKeepProxy:
		return m.keepProxyStep.view()
	case wizPhaseEnabled:
		return m.enabledStep.view()
	}
	return ""
}

// advance moves to the next phase.
func (m *providerWizardModel) advance() {
	next := m.phase + 1
	// Skip name phase on update.
	if next == wizPhaseName && m.mode == wizardModeUpdate {
		next++
	}
	m.phase = next
}

// stepBack moves to the previous phase. At the start phase, aborts.
func (m *providerWizardModel) stepBack() {
	if m.phase <= m.startPhase {
		m.aborted = true
		return
	}
	prev := m.phase - 1
	// Skip name phase on update.
	if prev == wizPhaseName && m.mode == wizardModeUpdate {
		m.aborted = true
		return
	}
	m.phase = prev
}

// result extracts the final provider name and endpoint from the wizard state.
func (m providerWizardModel) result() (string, providers.Endpoint) {
	name := m.existingName
	if m.mode == wizardModeAdd {
		name = m.nameStep.selected()
	}

	ep := providers.Endpoint{
		Endpoint:        m.endpointStep.selected(),
		APIKeyEnv:       m.apiKeyEnvStep.selected(),
		SupportedClient: m.clientsStep.selected(),
		ListModelsCmd:   m.listModelsCmdStep.selected(),
		Description:     m.descriptionStep.selected(),
	}

	// Parse models from comma-separated string.
	modelsRaw := m.modelsStep.selected()
	if modelsRaw != "" {
		parts := strings.Split(modelsRaw, ",")
		models := make([]string, 0, len(parts))
		for _, p := range parts {
			trimmed := strings.TrimSpace(p)
			if trimmed != "" {
				models = append(models, trimmed)
			}
		}
		ep.Models = models
	}

	// Bool pickers: "yes" = index 0, "no" = index 1.
	ep.UseProxy = m.useProxyStep.selected() == "yes"
	ep.KeepProxyConfig = m.keepProxyStep.selected() == "yes"

	enabledVal := m.enabledStep.selected() == "yes"
	ep.Enabled = &enabledVal

	return name, ep
}

// runProviderWizard is the entry point called from provider_cmd.go.
// It checks for TTY, runs the Bubble Tea program, and returns the result.
func runProviderWizard(
	out io.Writer,
	stdin io.Reader,
	mode wizardMode,
	existing *providers.Endpoint,
	existingName string,
	existingNames []string,
) (name string, ep providers.Endpoint, cancelled bool, err error) {
	// TTY check: stdin must be a terminal.
	file, ok := stdin.(*os.File)
	if !ok || !isTerminal(file) {
		hint := "cam provider add NAME --endpoint URL [--api-key-env VAR] ..."
		if mode == wizardModeUpdate {
			hint = "cam provider update NAME --endpoint URL [--description TEXT] ..."
		}
		return "", providers.Endpoint{}, false,
			fmt.Errorf("interactive wizard requires a terminal; use flags instead:\n  %s", hint)
	}

	model := newProviderWizardModel(mode, existing, existingName, existingNames)
	program := tea.NewProgram(model, tea.WithOutput(out))
	final, err := program.Run()
	if err != nil {
		return "", providers.Endpoint{}, false, err
	}

	wizard, ok := final.(providerWizardModel)
	if !ok || wizard.aborted {
		return "", providers.Endpoint{}, true, nil
	}

	n, e := wizard.result()
	return n, e, false, nil
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -run TestProviderWizard -v -count=1`

Expected: All tests PASS.

- [ ] **Step 3: Run all existing tests to check nothing broke**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -v -count=1`

Expected: All tests PASS (existing + new).

- [ ] **Step 4: Commit**

```bash
git add internal/cli/provider_wizard.go
git commit --author="James Zhu <zhujian0805@gmail.com>" -m "feat: add providerWizardModel for interactive provider add/update"
```

---

### Task 5: Integration — Wire Wizard into provider_cmd.go

**Files:**
- Modify: `internal/cli/provider_cmd.go` (lines 227-303 for add, lines 305-396 for update)
- Modify: `internal/cli/cmd_provider_test.go`

- [ ] **Step 1: Add integration tests for wizard fallback paths**

Add these tests to the bottom of `internal/cli/cmd_provider_test.go`:

```go
// When `add` is called with no args in a non-TTY context (test harness uses
// bytes.Buffer for stdin), the command should error with a message directing
// the user to use flags.
func TestProviderAddNoArgsNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add")
	if code == 0 {
		t.Fatal("expected non-zero exit when add has no args in non-TTY")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
	if !strings.Contains(stderr, "--endpoint") {
		t.Fatalf("stderr missing flag hint: %s", stderr)
	}
}

// When `add` is called with a name but no --endpoint in non-TTY, same error.
func TestProviderAddNameOnlyNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add", "myapi")
	if code == 0 {
		t.Fatal("expected non-zero exit")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}

// When `update` is called with no flags in non-TTY, same error.
func TestProviderUpdateNoFlagsNonTTYErrors(t *testing.T) {
	isolatedHome(t)
	// Seed a provider first.
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	_, stderr, code := execute(t, "provider", "update", "alpha")
	if code == 0 {
		t.Fatal("expected non-zero exit when update has no flags in non-TTY")
	}
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}

// Flag-based add still works (backward compat).
func TestProviderAddWithAllFlagsStillWorks(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t,
		"provider", "add", "alpha",
		"--endpoint", "https://alpha.example",
		"--api-key-env", "ALPHA_KEY",
	)
	if code != 0 {
		t.Fatalf("add exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, `Added provider "alpha"`) {
		t.Fatalf("expected added notice: %s", stdout)
	}
}

// Flag-based update still works (backward compat).
func TestProviderUpdateWithFlagsStillWorks(t *testing.T) {
	isolatedHome(t)
	if _, _, code := execute(t, "provider", "add", "alpha",
		"--endpoint", "https://a"); code != 0 {
		t.Fatal("seed failed")
	}
	stdout, stderr, code := execute(t, "provider", "update", "alpha",
		"--description", "updated desc")
	if code != 0 {
		t.Fatalf("update exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, `Updated provider "alpha"`) {
		t.Fatalf("expected updated notice: %s", stdout)
	}
}
```

- [ ] **Step 2: Run new integration tests to verify they fail**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -run "TestProviderAdd(NoArgs|NameOnly)NonTTY|TestProviderUpdateNoFlags" -v -count=1`

Expected: `TestProviderAddNoArgsNonTTYErrors` fails because cobra currently rejects 0 args with a different error ("accepts 1 arg(s), received 0"). `TestProviderAddNameOnlyNonTTYErrors` fails because the current code returns "--endpoint is required" instead of the wizard message. `TestProviderUpdateNoFlagsNonTTYErrors` fails because update currently succeeds silently (no-op patch).

- [ ] **Step 3: Modify providerAddCommand to dispatch to wizard**

In `internal/cli/provider_cmd.go`, modify `providerAddCommand`:

1. Change `Args: cobra.ExactArgs(1)` to `Args: cobra.RangeArgs(0, 1)`
2. Replace the RunE body to detect wizard mode

The updated `providerAddCommand` method:

```go
func (a *App) providerAddCommand(state *globalState) *cobra.Command {
	flags := &addOrUpdateFlags{}
	cmd := &cobra.Command{
		Use:   "add [NAME] [--endpoint URL] [flags]",
		Short: "Add a new provider (interactive wizard when flags omitted)",
		Args:  cobra.RangeArgs(0, 1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := ""
			if len(args) > 0 {
				name = args[0]
			}

			// If name is given AND --endpoint is provided, use the
			// flag-only path (backward compatible).
			if name != "" && cmd.Flags().Changed("endpoint") {
				return a.providerAddFlagMode(cmd, state, name, flags)
			}

			// Otherwise, launch the wizard.
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}

			wizName, ep, cancelled, err := runProviderWizard(
				cmd.OutOrStdout(),
				cmd.InOrStdin(),
				wizardModeAdd,
				nil,
				name,
				file.SortedNames(),
			)
			if err != nil {
				return err
			}
			if cancelled {
				fmt.Fprintln(cmd.OutOrStdout(), "Aborted.")
				return nil
			}

			// Re-load in case the file changed during wizard interaction.
			file, created, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			if err := providers.Add(&file, wizName, ep); err != nil {
				return err
			}
			if err := providers.Save(path, file); err != nil {
				return err
			}
			out := cmd.OutOrStdout()
			if created {
				fmt.Fprintf(out, "Created %s\n", path)
			}
			fmt.Fprintf(out, "Added provider %q\n", wizName)
			return nil
		},
	}
	bindAddOrUpdateFlags(cmd, flags)
	return cmd
}

// providerAddFlagMode is the original flag-based add logic, extracted so
// the wizard path can share the command.
func (a *App) providerAddFlagMode(cmd *cobra.Command, state *globalState, name string, flags *addOrUpdateFlags) error {
	if flags.endpoint == "" {
		return errors.New("--endpoint is required")
	}
	if flags.useProxy && flags.noUseProxy {
		return errors.New("--use-proxy and --no-use-proxy are mutually exclusive")
	}
	if flags.keepProxyConfig && flags.noKeepProxy {
		return errors.New("--keep-proxy-config and --no-keep-proxy-config are mutually exclusive")
	}
	if flags.enabled && flags.disabled {
		return errors.New("--enabled and --disabled are mutually exclusive")
	}

	path := resolveProvidersPath(state)
	file, created, err := providers.LoadOrInit(path)
	if err != nil {
		return err
	}

	ep := providers.Endpoint{
		Endpoint:        flags.endpoint,
		APIKeyEnv:       flags.apiKeyEnv,
		ListModelsCmd:   flags.listModelsCmd,
		Description:     flags.description,
		UseProxy:        flags.useProxy,
		KeepProxyConfig: flags.keepProxyConfig,
	}
	if flags.clients != "" {
		_, items, err := parseListFlag(flags.clients, true)
		if err != nil {
			return fmt.Errorf("--client: %w", err)
		}
		ep.SupportedClient = strings.Join(items, ",")
	}
	if flags.models != "" {
		_, items, err := parseListFlag(flags.models, true)
		if err != nil {
			return fmt.Errorf("--model: %w", err)
		}
		ep.Models = items
	}
	if flags.disabled {
		v := false
		ep.Enabled = &v
	} else if flags.enabled {
		v := true
		ep.Enabled = &v
	}

	if err := providers.Add(&file, name, ep); err != nil {
		if errors.Is(err, providers.ErrAlreadyExists) {
			return fmt.Errorf("provider %q already exists (use 'cam provider update %s ...' to change it)", name, name)
		}
		return err
	}
	if err := providers.Save(path, file); err != nil {
		return err
	}
	out := cmd.OutOrStdout()
	if created {
		fmt.Fprintf(out, "Created %s\n", path)
	}
	fmt.Fprintf(out, "Added provider %q\n", name)
	return nil
}
```

- [ ] **Step 4: Modify providerUpdateCommand to dispatch to wizard**

In `internal/cli/provider_cmd.go`, modify `providerUpdateCommand`. The key change: detect whether any local flags were explicitly changed. If none were, dispatch to the wizard.

```go
func (a *App) providerUpdateCommand(state *globalState) *cobra.Command {
	flags := &addOrUpdateFlags{}
	cmd := &cobra.Command{
		Use:   "update NAME [flags]",
		Short: "Update fields on an existing provider (interactive wizard when flags omitted)",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]

			// Check if ANY local flag was explicitly set.
			anyFlagChanged := false
			for _, flagName := range []string{
				"endpoint", "api-key-env", "client", "model",
				"list-models-cmd", "description",
				"use-proxy", "no-use-proxy",
				"keep-proxy-config", "no-keep-proxy-config",
				"enabled", "disabled",
			} {
				if cmd.Flags().Changed(flagName) {
					anyFlagChanged = true
					break
				}
			}

			if anyFlagChanged {
				return a.providerUpdateFlagMode(cmd, state, name, flags)
			}

			// No flags: launch the wizard.
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			ep, ok := file.Endpoints[name]
			if !ok {
				return fmt.Errorf("provider %q not found (try 'cam provider list')", name)
			}

			_, newEp, cancelled, err := runProviderWizard(
				cmd.OutOrStdout(),
				cmd.InOrStdin(),
				wizardModeUpdate,
				&ep,
				name,
				nil,
			)
			if err != nil {
				return err
			}
			if cancelled {
				fmt.Fprintln(cmd.OutOrStdout(), "Aborted.")
				return nil
			}

			// Replace the endpoint wholesale.
			file.Endpoints[name] = newEp
			if err := providers.Save(path, file); err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Updated provider %q\n", name)
			return nil
		},
	}
	bindAddOrUpdateFlags(cmd, flags)
	return cmd
}

// providerUpdateFlagMode is the original flag-based update logic, extracted
// so the wizard path can share the command.
func (a *App) providerUpdateFlagMode(cmd *cobra.Command, state *globalState, name string, flags *addOrUpdateFlags) error {
	if flags.useProxy && flags.noUseProxy {
		return errors.New("--use-proxy and --no-use-proxy are mutually exclusive")
	}
	if flags.keepProxyConfig && flags.noKeepProxy {
		return errors.New("--keep-proxy-config and --no-keep-proxy-config are mutually exclusive")
	}
	if flags.enabled && flags.disabled {
		return errors.New("--enabled and --disabled are mutually exclusive")
	}

	patch := providers.Patch{}
	if cmd.Flags().Changed("endpoint") {
		v := flags.endpoint
		patch.Endpoint = &v
	}
	if cmd.Flags().Changed("api-key-env") {
		v := flags.apiKeyEnv
		patch.APIKeyEnv = &v
	}
	if cmd.Flags().Changed("description") {
		v := flags.description
		patch.Description = &v
	}
	if cmd.Flags().Changed("list-models-cmd") {
		v := flags.listModelsCmd
		patch.ListModelsCmd = &v
	}
	if flags.useProxy {
		v := true
		patch.UseProxy = &v
	} else if flags.noUseProxy {
		v := false
		patch.UseProxy = &v
	}
	if flags.keepProxyConfig {
		v := true
		patch.KeepProxyConfig = &v
	} else if flags.noKeepProxy {
		v := false
		patch.KeepProxyConfig = &v
	}
	if flags.enabled {
		v := true
		patch.Enabled = &v
	} else if flags.disabled {
		v := false
		patch.Enabled = &v
	}
	if cmd.Flags().Changed("client") {
		op, items, err := parseListFlag(flags.clients, false)
		if err != nil {
			return fmt.Errorf("--client: %w", err)
		}
		patch.Clients = &providers.ListPatch{Op: op, Items: items}
	}
	if cmd.Flags().Changed("model") {
		op, items, err := parseListFlag(flags.models, false)
		if err != nil {
			return fmt.Errorf("--model: %w", err)
		}
		patch.Models = &providers.ListPatch{Op: op, Items: items}
	}

	path := resolveProvidersPath(state)
	file, _, err := providers.LoadOrInit(path)
	if err != nil {
		return err
	}
	if err := providers.Update(&file, name, patch); err != nil {
		if errors.Is(err, providers.ErrNotFound) {
			return fmt.Errorf("provider %q not found (try 'cam provider list')", name)
		}
		return err
	}
	if err := providers.Save(path, file); err != nil {
		return err
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Updated provider %q\n", name)
	return nil
}
```

- [ ] **Step 5: Update the existing TestProviderAddRequiresEndpoint test**

The test `TestProviderAddRequiresEndpoint` currently expects the error "--endpoint is required" when running `cam provider add alpha` with no `--endpoint`. With the new wizard dispatch, this case now tries to launch the wizard but fails with the non-TTY error. Update the test assertion in `cmd_provider_test.go`:

```go
func TestProviderAddRequiresEndpoint(t *testing.T) {
	isolatedHome(t)
	_, stderr, code := execute(t, "provider", "add", "alpha")
	if code == 0 {
		t.Fatal("expected error when --endpoint missing")
	}
	// In non-TTY, the wizard path returns a terminal-required error.
	if !strings.Contains(stderr, "interactive wizard requires a terminal") {
		t.Fatalf("stderr missing wizard hint: %s", stderr)
	}
}
```

- [ ] **Step 6: Run all tests**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/cli/ -v -count=1`

Expected: All tests PASS — existing flag-based tests unchanged, new non-TTY tests pass.

- [ ] **Step 7: Also run providers package tests to confirm no regressions**

Run: `cd /home/jzhu/repos/code-agent-manager && go test ./internal/providers/ -v -count=1`

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add internal/cli/provider_cmd.go internal/cli/cmd_provider_test.go
git commit --author="James Zhu <zhujian0805@gmail.com>" -m "feat: wire provider wizard into add/update commands

Running 'cam provider add' or 'cam provider update NAME' without flags
now launches a guided Bubble Tea wizard in TTY mode. Flag-based usage
is fully backward compatible. Non-TTY contexts get a clear error message
directing to flag syntax."
```

---

### Task 6: Reinstall and Smoke Test

**Files:** None (build verification only)

- [ ] **Step 1: Reinstall the project**

Run:
```bash
cd /home/jzhu/repos/code-agent-manager
rm -rf dist/*
./install.sh uninstall
./install.sh
# providers.json is deprecated; no restore step is needed
```

- [ ] **Step 2: Run the full test suite**

Find and run all test files:

```bash
cd /home/jzhu/repos/code-agent-manager
find . -name '*_test.go' -path '*/internal/*' | sed 's|/[^/]*$||' | sort -u | while read dir; do
    echo "=== Testing $dir ==="
    go test "./$dir" -v -count=1
done
```

Expected: All tests PASS across all packages.

- [ ] **Step 3: Verify flag-based commands still work**

```bash
cam provider add test-smoke --endpoint https://smoke.example --api-key-env SMOKE_KEY --client claude
cam provider list
cam provider show test-smoke
cam provider update test-smoke --description "smoke test"
cam provider show test-smoke
cam provider remove test-smoke --yes
```

Expected: All commands produce expected output, no regressions.

- [ ] **Step 4: Verify non-TTY wizard error**

```bash
echo "" | cam provider add
```

Expected: Error message containing "interactive wizard requires a terminal".
