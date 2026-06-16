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

	m.existingNames = map[string]bool{}
	for _, n := range existingNamesList {
		m.existingNames[n] = true
	}

	var ep providers.Endpoint
	if existing != nil {
		ep = *existing
	}

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
		"List Models Command (Deprecated)",
		"Command:",
		ep.ListModelsCmd,
		false,
		"Deprecated fallback. CAM fetches /v1/models directly; leave empty unless required. Enter to continue, Esc back.",
	)

	m.descriptionStep = newTextInputStep(
		"Description",
		"Description:",
		ep.Description,
		false,
		"Human-readable description (optional). Enter to continue, Esc back.",
	)

	useProxyCursor := 1
	if ep.UseProxy {
		useProxyCursor = 0
	}
	m.useProxyStep = newPickerStep(
		"Use Proxy",
		[]string{"yes", "no"},
		"Route requests through the configured proxy? Enter to continue, Esc back.",
	)
	m.useProxyStep.cursor = useProxyCursor

	keepProxyCursor := 1
	if ep.KeepProxyConfig {
		keepProxyCursor = 0
	}
	m.keepProxyStep = newPickerStep(
		"Keep Proxy Config",
		[]string{"yes", "no"},
		"Preserve proxy environment variables during model discovery? Enter to continue, Esc back.",
	)
	m.keepProxyStep.cursor = keepProxyCursor

	enabledCursor := 0
	if existing != nil && !ep.IsEnabled() {
		enabledCursor = 1
	}
	m.enabledStep = newPickerStep(
		"Enabled",
		[]string{"yes", "no"},
		"Enable this provider for use in tool launches? Enter to finish, Esc back.",
	)
	m.enabledStep.cursor = enabledCursor

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

func (m *providerWizardModel) advance() {
	next := m.phase + 1
	if next == wizPhaseName && m.mode == wizardModeUpdate {
		next++
	}
	m.phase = next
}

func (m *providerWizardModel) stepBack() {
	if m.phase <= m.startPhase {
		m.aborted = true
		return
	}
	prev := m.phase - 1
	if prev == wizPhaseName && m.mode == wizardModeUpdate {
		m.aborted = true
		return
	}
	m.phase = prev
}

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

	ep.UseProxy = m.useProxyStep.selected() == "yes"
	ep.KeepProxyConfig = m.keepProxyStep.selected() == "yes"

	enabledVal := m.enabledStep.selected() == "yes"
	ep.Enabled = &enabledVal

	return name, ep
}

// runProviderWizard is the entry point called from provider_cmd.go.
func runProviderWizard(
	out io.Writer,
	stdin io.Reader,
	mode wizardMode,
	existing *providers.Endpoint,
	existingName string,
	existingNames []string,
) (name string, ep providers.Endpoint, cancelled bool, err error) {
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
