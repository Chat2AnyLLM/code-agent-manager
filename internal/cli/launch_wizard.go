package cli

import (
	"fmt"
	"io"
	"os"
	"sort"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

// launchSelection is the resolved triple the wizard returns. The Tool
// and Endpoint values are concrete copies (not pointers) so callers do
// not race against later registry/file mutations.
type launchSelection struct {
	Tool         tools.Tool
	EndpointName string
	Endpoint     providers.Endpoint
	Model        string
}

// wizardInput bundles everything the wizard needs to function.
// ResolveModels is injected so tests can substitute a fake without
// spawning shell commands.
type wizardInput struct {
	Pinned        launchSelection
	Providers     providers.File
	Registry      *tools.Registry
	ResolveModels func(ep providers.Endpoint, epName string) ([]string, error)
}

// runLaunchWizard validates pinned values, skips phases that are
// already pinned, and runs a bubbletea program for whatever remains.
// Returns cancelled=true when the user aborts via q/Ctrl+C.
//
// When all three fields are pinned and valid, it returns immediately
// without starting bubbletea.
func runLaunchWizard(out io.Writer, in wizardInput) (launchSelection, bool, error) {
	resolved, needTool, needEndpoint, needModel, err := validatePinned(in)
	if err != nil {
		return launchSelection{}, false, err
	}
	if !needTool && !needEndpoint && !needModel {
		return resolved, false, nil
	}

	model := newLaunchWizardModel(resolved, in, needTool, needEndpoint, needModel)

	file, ok := out.(*os.File)
	if !ok || !isTerminal(file) {
		// Non-TTY callers should never reach here — launch.go calls
		// autoResolve instead. Defensive: render the first phase to
		// help debugging and return cancelled.
		_, _ = fmt.Fprint(out, model.View())
		return resolved, true, nil
	}

	program := tea.NewProgram(model, tea.WithOutput(out))
	final, err := program.Run()
	if err != nil {
		return launchSelection{}, false, err
	}
	wizard, ok := final.(launchWizardModel)
	if !ok {
		return launchSelection{}, true, nil
	}
	if wizard.aborted {
		return launchSelection{}, true, nil
	}
	return wizard.sel, false, nil
}

// validatePinned looks up pinned tool/endpoint values up-front so the
// caller never enters the TUI with garbage. Returns the partially-
// resolved selection plus per-phase need flags.
func validatePinned(in wizardInput) (sel launchSelection, needTool, needEndpoint, needModel bool, err error) {
	pinned := in.Pinned

	// Tool.
	switch {
	case pinned.Tool.Name == "":
		needTool = true
	default:
		sel.Tool = pinned.Tool
	}

	// Endpoint.
	switch {
	case pinned.EndpointName == "":
		needEndpoint = true
	default:
		ep, ok := in.Providers.Endpoints[pinned.EndpointName]
		if !ok {
			return launchSelection{}, false, false, false,
				fmt.Errorf("Unknown endpoint: %s", pinned.EndpointName)
		}
		// When the tool is also pinned, validate the supported_client
		// match here so we fail fast.
		if !needTool && !ep.SupportsClient(sel.Tool.LaunchCommand()) {
			return launchSelection{}, false, false, false,
				fmt.Errorf("endpoint %s does not support tool %s (check supported_client)",
					pinned.EndpointName, sel.Tool.LaunchCommand())
		}
		sel.EndpointName = pinned.EndpointName
		sel.Endpoint = ep
	}

	// Model.
	switch {
	case pinned.Model == "":
		needModel = true
	default:
		sel.Model = pinned.Model
	}

	return sel, needTool, needEndpoint, needModel, nil
}

// launchWizardPhase identifies the active phase.
type launchWizardPhase int

const (
	phasePickTool launchWizardPhase = iota
	phasePickEndpoint
	phasePickModel
	phaseDone
)

const launchModelPickerVisibleLimit = 15

// launchWizardModel is the bubbletea model for the three-phase picker.
// At any time, exactly one of {toolStep, endpointStep, modelStep, modelEntry}
// is visible. Phase pinned by CLI flag is skipped on entry.
type launchWizardModel struct {
	in           wizardInput
	sel          launchSelection
	phase        launchWizardPhase
	needTool     bool
	needEndpoint bool
	needModel    bool

	// Active picker for the current phase. modelStep is non-empty when
	// the model list is non-empty; manualEntry replaces it when the
	// list is empty.
	toolStep     pickerStep
	endpointStep pickerStep
	modelStep    pickerStep
	manualEntry  bool
	manualValue  string
	modelErr     error // last error from ResolveModels, shown above manual entry

	aborted bool
}

func newLaunchWizardModel(initial launchSelection, in wizardInput,
	needTool, needEndpoint, needModel bool) launchWizardModel {
	m := launchWizardModel{
		in:           in,
		sel:          initial,
		needTool:     needTool,
		needEndpoint: needEndpoint,
		needModel:    needModel,
	}
	m.advanceToNextNeededPhase()
	return m
}

func (m launchWizardModel) Init() tea.Cmd { return nil }

func (m launchWizardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}
	if m.manualEntry {
		return m.updateManualEntry(key)
	}
	step := m.activeStep()
	if step == nil {
		// Defensive: should not happen.
		m.aborted = true
		return m, tea.Quit
	}
	action := step.update(key)
	switch action {
	case pickerActionAbort:
		m.aborted = true
		return m, tea.Quit
	case pickerActionBack:
		m.stepBack()
		return m, nil
	case pickerActionAdvance:
		return m.advanceFromStep(*step)
	}
	return m, nil
}

func (m launchWizardModel) View() string {
	if m.manualEntry {
		var header string
		if m.modelErr != nil {
			header = fmt.Sprintf("Model discovery failed: %s\n\n", m.modelErr)
		} else {
			header = "No models advertised by this endpoint.\n\n"
		}
		return fmt.Sprintf(
			"%sType a model name and press Enter (Esc to pick a different endpoint).\n\nModel: %s_\n",
			header, m.manualValue,
		)
	}
	step := m.activeStep()
	if step == nil {
		return ""
	}
	return step.view()
}

// activeStep returns the picker for the current phase, or nil when
// the wizard is done / in manual-entry mode.
func (m *launchWizardModel) activeStep() *pickerStep {
	switch m.phase {
	case phasePickTool:
		return &m.toolStep
	case phasePickEndpoint:
		return &m.endpointStep
	case phasePickModel:
		if m.manualEntry {
			return nil
		}
		return &m.modelStep
	}
	return nil
}

// advanceToNextNeededPhase sets m.phase to the first phase that still
// needs user input. Skipped phases are recorded in m.sel already.
func (m *launchWizardModel) advanceToNextNeededPhase() {
	switch {
	case m.needTool:
		m.phase = phasePickTool
		m.toolStep = newPickerStep(
			"Select a tool",
			m.in.Registry.LaunchNames(),
			"↑/↓ to move, type to filter, Enter to select, Esc back, q to quit.",
		)
	case m.needEndpoint:
		m.phase = phasePickEndpoint
		m.buildEndpointStep()
	case m.needModel:
		m.phase = phasePickModel
		m.buildModelStep()
	default:
		m.phase = phaseDone
	}
}

func (m *launchWizardModel) buildEndpointStep() {
	client := m.sel.Tool.LaunchCommand()
	var names []string
	for _, name := range m.in.Providers.SortedNames() {
		ep := m.in.Providers.Endpoints[name]
		if !ep.IsEnabled() {
			continue
		}
		if !ep.SupportsClient(client) {
			continue
		}
		names = append(names, name)
	}
	sort.Strings(names)
	hint := fmt.Sprintf("Endpoints supporting %s. Esc back, q to quit.", client)
	m.endpointStep = newPickerStep("Select a provider", names, hint)
}

func (m *launchWizardModel) buildModelStep() {
	models, err := m.in.ResolveModels(m.sel.Endpoint, m.sel.EndpointName)
	if err != nil || len(models) == 0 {
		m.manualEntry = true
		m.manualValue = ""
		m.modelErr = err
		return
	}
	m.manualEntry = false
	m.modelErr = nil
	hint := fmt.Sprintf("Models for %s. Showing up to %d matches; type to filter, Esc back, q to quit.",
		m.sel.EndpointName, launchModelPickerVisibleLimit)
	m.modelStep = newLimitedPickerStep("Select a model", models, hint, launchModelPickerVisibleLimit)
}

// advanceFromStep records the picker's selection in m.sel and moves
// to the next needed phase. Returns tea.Quit when the wizard is done.
func (m launchWizardModel) advanceFromStep(step pickerStep) (tea.Model, tea.Cmd) {
	switch m.phase {
	case phasePickTool:
		name := step.selected()
		tool, ok := m.in.Registry.ByCLICommand(name)
		if !ok {
			// Picker shows registry.LaunchNames(); this shouldn't
			// fail.
			m.aborted = true
			return m, tea.Quit
		}
		m.sel.Tool = tool
		// Advancing past tool means subsequent phases may need
		// fresh state.
		m.needTool = false
		m.advanceToNextNeededPhase()
	case phasePickEndpoint:
		name := step.selected()
		ep, ok := m.in.Providers.Endpoints[name]
		if !ok {
			m.aborted = true
			return m, tea.Quit
		}
		m.sel.EndpointName = name
		m.sel.Endpoint = ep
		m.needEndpoint = false
		m.advanceToNextNeededPhase()
	case phasePickModel:
		m.sel.Model = step.selected()
		m.needModel = false
		m.phase = phaseDone
	}
	if m.phase == phaseDone {
		return m, tea.Quit
	}
	return m, nil
}

// stepBack moves to the previous phase that needs input. Esc at the
// first needed phase is a no-op.
func (m *launchWizardModel) stepBack() {
	switch m.phase {
	case phasePickTool:
		// no-op
	case phasePickEndpoint:
		if m.in.Pinned.Tool.Name == "" {
			m.needTool = true
			m.sel.Tool = tools.Tool{}
		}
		m.advanceToNextNeededPhase()
	case phasePickModel:
		// Stepping back from model clears manual-entry state.
		m.manualEntry = false
		m.manualValue = ""
		m.modelErr = nil
		if m.in.Pinned.EndpointName == "" {
			m.needEndpoint = true
			m.sel.EndpointName = ""
			m.sel.Endpoint = providers.Endpoint{}
		}
		m.advanceToNextNeededPhase()
	}
}

func (m launchWizardModel) updateManualEntry(key tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch key.String() {
	case "ctrl+c":
		m.aborted = true
		return m, tea.Quit
	case "esc":
		m.stepBack()
		return m, nil
	case "enter":
		v := trimSpace(m.manualValue)
		if v == "" {
			return m, nil // require non-empty
		}
		m.sel.Model = v
		m.needModel = false
		m.phase = phaseDone
		return m, tea.Quit
	case "backspace":
		if m.manualValue != "" {
			m.manualValue = m.manualValue[:len(m.manualValue)-1]
		}
		return m, nil
	default:
		text := key.String()
		if len(text) == 1 {
			m.manualValue += text
		}
		return m, nil
	}
}

// trimSpace mirrors strings.TrimSpace without importing strings here
// (kept local for the one-liner).
func trimSpace(s string) string {
	start, end := 0, len(s)
	for start < end && (s[start] == ' ' || s[start] == '\t') {
		start++
	}
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t') {
		end--
	}
	return s[start:end]
}
