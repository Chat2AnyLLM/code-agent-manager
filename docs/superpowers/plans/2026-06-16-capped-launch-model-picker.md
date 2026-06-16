# Capped Launch Model Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cam launch` show only a 15-model preview in the model picker while still allowing typed filtering across every discovered model.

**Architecture:** Extend the shared `pickerStep` with an optional visible-result cap. Keep existing picker construction unlimited by default, and opt into the cap only when `launchWizardModel.buildModelStep()` builds the model picker.

**Tech Stack:** Go, Bubble Tea (`github.com/charmbracelet/bubbletea`), existing Go unit tests in `internal/cli`.

---

## File Structure

- Modify: `internal/cli/tool_menu.go`
  - Owns the reusable filterable picker used by the tool menu and launch wizard.
  - Add `visibleLimit int`, a limited constructor, and limit application in `visible()`.

- Modify: `internal/cli/launch_wizard.go`
  - Owns the multi-step `cam launch` wizard.
  - Add a model picker limit constant and use the limited picker for model selection only.

- Modify: `internal/cli/launch_wizard_test.go`
  - Existing tests already inspect `pickerStep.visible()` and launch wizard state directly.
  - Add unit tests for unlimited picker behavior, capped picker behavior, filtering outside the preview, and launch wizard model cap.

- Reference only: `docs/superpowers/specs/2026-06-16-capped-launch-model-picker-design.md`
  - Design source for this plan.

---

### Task 1: Add failing picker limit tests

**Files:**
- Modify: `internal/cli/launch_wizard_test.go`

- [ ] **Step 1: Add helper for generated model names**

Add this helper after `resolveModelsErr` in `internal/cli/launch_wizard_test.go`:

```go
func numberedModels(prefix string, count int) []string {
	models := make([]string, 0, count)
	for i := 1; i <= count; i++ {
		models = append(models, fmt.Sprintf("%s-%02d", prefix, i))
	}
	return models
}
```

Also add `fmt` to the import block:

```go
import (
	"bytes"
	"errors"
	"fmt"
	"strings"
	"testing"
```

- [ ] **Step 2: Add tests for unlimited and limited picker visibility**

Add these tests after `drive` in `internal/cli/launch_wizard_test.go`:

```go
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
go test ./internal/cli -run 'TestPickerStep_(DefaultPickerShowsAllItems|LimitedPickerCapsVisibleItems|LimitedPickerFiltersAcrossAllItems)' -count=1
```

Expected: FAIL because `newLimitedPickerStep` is undefined.

---

### Task 2: Implement optional picker visible limit

**Files:**
- Modify: `internal/cli/tool_menu.go:14-29`
- Modify: `internal/cli/tool_menu.go:114-126`
- Test: `internal/cli/launch_wizard_test.go`

- [ ] **Step 1: Add the limit field and constructor**

Change `pickerStep` and constructors in `internal/cli/tool_menu.go` to this:

```go
type pickerStep struct {
	title        string
	items        []string
	cursor       int
	filter       string
	visibleLimit int
	// hint is the footer line shown beneath the list.
	hint string
}

func newPickerStep(title string, items []string, hint string) pickerStep {
	return newLimitedPickerStep(title, items, hint, 0)
}

func newLimitedPickerStep(title string, items []string, hint string, limit int) pickerStep {
	return pickerStep{
		title:        title,
		items:        append([]string(nil), items...),
		visibleLimit: limit,
		hint:         hint,
	}
}
```

- [ ] **Step 2: Apply the limit after filtering**

Replace `visible()` in `internal/cli/tool_menu.go` with:

```go
func (s pickerStep) visible() []string {
	var out []string
	if s.filter == "" {
		out = s.items
	} else {
		out = make([]string, 0, len(s.items))
		filter := strings.ToLower(s.filter)
		for _, item := range s.items {
			if strings.Contains(strings.ToLower(item), filter) {
				out = append(out, item)
			}
		}
	}
	if s.visibleLimit > 0 && len(out) > s.visibleLimit {
		return out[:s.visibleLimit]
	}
	return out
}
```

- [ ] **Step 3: Run picker tests to verify they pass**

Run:

```bash
go test ./internal/cli -run 'TestPickerStep_(DefaultPickerShowsAllItems|LimitedPickerCapsVisibleItems|LimitedPickerFiltersAcrossAllItems)' -count=1
```

Expected: PASS.

---

### Task 3: Add failing launch wizard model cap test

**Files:**
- Modify: `internal/cli/launch_wizard_test.go`

- [ ] **Step 1: Add launch wizard model cap test**

Add this test after `TestWizard_EndpointFiltersByClient` in `internal/cli/launch_wizard_test.go`:

```go
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
go test ./internal/cli -run TestWizard_ModelPickerShowsCappedPreviewAndFiltersAllModels -count=1
```

Expected: FAIL because `buildModelStep()` still uses the unlimited picker and returns 20 visible models.

---

### Task 4: Use the 15-item cap for launch model selection

**Files:**
- Modify: `internal/cli/launch_wizard.go:121-129`
- Modify: `internal/cli/launch_wizard.go:276-288`
- Test: `internal/cli/launch_wizard_test.go`

- [ ] **Step 1: Add model picker limit constant**

Add this constant after the launch wizard phase constants in `internal/cli/launch_wizard.go`:

```go
const launchModelPickerVisibleLimit = 15
```

- [ ] **Step 2: Build model picker with the capped helper**

Replace the final two lines of `buildModelStep()` in `internal/cli/launch_wizard.go` with:

```go
	hint := fmt.Sprintf("Models for %s. Showing up to %d matches; type to filter, Esc back, q to quit.",
		m.sel.EndpointName, launchModelPickerVisibleLimit)
	m.modelStep = newLimitedPickerStep("Select a model", models, hint, launchModelPickerVisibleLimit)
```

The complete successful branch of `buildModelStep()` should be:

```go
	m.manualEntry = false
	m.modelErr = nil
	hint := fmt.Sprintf("Models for %s. Showing up to %d matches; type to filter, Esc back, q to quit.",
		m.sel.EndpointName, launchModelPickerVisibleLimit)
	m.modelStep = newLimitedPickerStep("Select a model", models, hint, launchModelPickerVisibleLimit)
```

- [ ] **Step 3: Run launch wizard model cap test**

Run:

```bash
go test ./internal/cli -run TestWizard_ModelPickerShowsCappedPreviewAndFiltersAllModels -count=1
```

Expected: PASS.

- [ ] **Step 4: Run focused launch wizard tests**

Run:

```bash
go test ./internal/cli -run 'TestPickerStep_|TestWizard_' -count=1
```

Expected: PASS.

---

### Task 5: Repository-required verification and reinstall

**Files:**
- No code changes in this task.

- [ ] **Step 1: Find Go test files as required by repository instructions**

Run:

```bash
find internal/cli -name '*test.go' -print
```

Expected: output includes `internal/cli/launch_wizard_test.go`, `internal/cli/cmd_launch_test.go`, and other `internal/cli` test files.

- [ ] **Step 2: Run each relevant package test command one by one**

Run these commands separately:

```bash
go test ./internal/cli -count=1
```

Expected: PASS.

```bash
go test ./internal/tools -count=1
```

Expected: PASS.

The changed code is in `internal/cli`, and `internal/tools` is included because launch behavior integrates with tool registry state.

- [ ] **Step 3: Reinstall project after code changes as required by repository instructions**

Run:

```bash
rm -rf dist/*
./install.sh uninstall
./install.sh
cp ~/.config/code-agent-manager/providers.json.bak ~/.config/code-agent-manager/providers.json
```

Expected: install completes successfully. If `providers.json.bak` is missing, report that the reinstall command failed at the restore step and do not hide the failure.

- [ ] **Step 4: Check git diff**

Run:

```bash
git diff -- internal/cli/tool_menu.go internal/cli/launch_wizard.go internal/cli/launch_wizard_test.go docs/superpowers/specs/2026-06-16-capped-launch-model-picker-design.md docs/superpowers/plans/2026-06-16-capped-launch-model-picker.md
```

Expected: diff only contains the capped model picker implementation, tests, design spec, and this plan.

---

## Self-Review Notes

- Spec coverage: the plan covers a 15-item model picker preview, filtering across the full model list, unchanged manual entry behavior, unchanged regular picker behavior, tests, and repository verification.
- Placeholder scan: no TBD/TODO/implement-later placeholders are present.
- Type consistency: `visibleLimit`, `newLimitedPickerStep`, and `launchModelPickerVisibleLimit` are used consistently across tasks.
