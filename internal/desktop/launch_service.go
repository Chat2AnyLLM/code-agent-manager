package desktop

import (
	"context"
	"os"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/appapi"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

type LaunchService struct {
	dbPath string
}

func NewLaunchService(dbPath string) *LaunchService {
	return &LaunchService{dbPath: dbPath}
}

func (s *LaunchService) ListTools() ([]ToolDTO, error) {
	return NewToolService().List()
}

func (s *LaunchService) providerAPI() appapi.ProviderAPI {
	return appapi.ProviderAPI{DBPath: s.dbPath}
}

func (s *LaunchService) ListProvidersForTool(toolName string) ([]ProviderDTO, error) {
	tool, err := loadTool(toolName)
	if err != nil {
		return nil, err
	}
	file, err := s.providerAPI().File(context.Background())
	if err != nil {
		return nil, wrapError("PROVIDER_LOAD_FAILED", err)
	}
	out := []ProviderDTO{}
	for _, name := range file.SortedNames() {
		ep := file.Endpoints[name]
		if !ep.IsEnabled() {
			continue
		}
		if ep.SupportsClient(tool.LaunchCommand()) || ep.SupportsClient(tool.Name) || len(ep.Clients()) == 0 {
			out = append(out, providerDTO(name, ep))
		}
	}
	return out, nil
}

func (s *LaunchService) ListModelsForProvider(providerName string) ([]string, error) {
	file, err := s.providerAPI().File(context.Background())
	if err != nil {
		return nil, wrapError("PROVIDER_LOAD_FAILED", err)
	}
	ep, ok := file.Endpoints[providerName]
	if !ok {
		return nil, NewError("PROVIDER_NOT_FOUND", "provider not found", map[string]string{"name": providerName})
	}
	models, err := providers.ResolveModels(ep, providerName, 24*time.Hour, "", os.Getenv)
	if err != nil {
		return nil, wrapError("MODEL_DISCOVERY_FAILED", err)
	}
	return models, nil
}

func (s *LaunchService) DryRun(toolName, providerName, model string, extraArgs []string) (LaunchPlanDTO, error) {
	tool, err := loadTool(toolName)
	if err != nil {
		return LaunchPlanDTO{}, err
	}
	file, err := s.providerAPI().File(context.Background())
	if err != nil {
		return LaunchPlanDTO{}, wrapError("PROVIDER_LOAD_FAILED", err)
	}
	ep, ok := file.Endpoints[providerName]
	if !ok {
		return LaunchPlanDTO{}, NewError("PROVIDER_NOT_FOUND", "provider not found", map[string]string{"name": providerName})
	}
	launch := tools.ResolveLaunchEnv(tool, ep, providerName, model)
	args := append([]string{}, launch.Inject...)
	args = append(args, extraArgs...)
	return LaunchPlanDTO{
		Tool: toolDTO(tool), Provider: providerDTO(providerName, ep), Model: model,
		Command: tool.LaunchCommand(), Args: args,
	}, nil
}

// ApplyConfig writes a provider's configuration into the agent's native config
// file (e.g. ~/.claude/settings.json) WITHOUT launching the agent — the
// cc-switch "switch" operation. It mirrors the write that cam launch performs
// (cli/launch.go) but stops after the write. ConfigPath is empty when the tool
// has no config_target. The Writes slice is the resolved plan, surfaced so the
// UI can show exactly which keys changed.
func (s *LaunchService) ApplyConfig(toolName, providerName, model string) (ApplyResultDTO, error) {
	tool, err := loadTool(toolName)
	if err != nil {
		return ApplyResultDTO{}, err
	}
	file, err := s.providerAPI().File(context.Background())
	if err != nil {
		return ApplyResultDTO{}, wrapError("PROVIDER_LOAD_FAILED", err)
	}
	ep, ok := file.Endpoints[providerName]
	if !ok {
		return ApplyResultDTO{}, NewError("PROVIDER_NOT_FOUND", "provider not found", map[string]string{"name": providerName})
	}
	apiKey := providers.ResolveAPIKey(ep, os.Getenv)

	// Plan is called only to surface the writes in the result; WriteConfig is
	// the single source of truth for the actual disk write (Plan + Apply +
	// codexPostWrite). The plan is deterministic, so the two agree.
	plan, err := tools.Plan(tool, ep, providerName, model, apiKey)
	if err != nil {
		return ApplyResultDTO{}, wrapError("CONFIG_PLAN_FAILED", err)
	}
	path, err := tools.WriteConfig(tool, ep, providerName, model, apiKey)
	if err != nil {
		return ApplyResultDTO{}, wrapError("CONFIG_WRITE_FAILED", err)
	}
	return ApplyResultDTO{
		Tool: toolDTO(tool), Provider: providerDTO(providerName, ep), Model: model,
		ConfigPath: path, Writes: plannedWriteDTOs(plan),
	}, nil
}

func plannedWriteDTOs(plan []tools.PlannedWrite) []PlannedWriteDTO {
	out := make([]PlannedWriteDTO, 0, len(plan))
	for _, p := range plan {
		out = append(out, PlannedWriteDTO{KeyPath: p.KeyPath, Value: p.Value, Op: p.Op})
	}
	return out
}
