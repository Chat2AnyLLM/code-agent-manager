package desktop

import (
	"context"
	"sync"

	"github.com/chat2anyllm/code-agent-manager/internal/appapi"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

type ProviderService struct {
	path string
	mu   sync.Mutex
}

func NewProviderService(path string) *ProviderService {
	return &ProviderService{path: path}
}

func (s *ProviderService) api() appapi.ProviderAPI {
	return appapi.ProviderAPI{ProvidersPath: s.path}
}

func (s *ProviderService) providersPath() string {
	if s.path != "" {
		return s.path
	}
	return providers.DefaultPath()
}

func (s *ProviderService) Init() (OperationResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	result, err := s.api().Init(context.Background())
	if err != nil {
		return OperationResult{}, wrapError("PROVIDER_INIT_FAILED", err)
	}
	return operationResultDTO(result), nil
}

func (s *ProviderService) List() ([]ProviderDTO, error) {
	listed, err := s.api().List(context.Background())
	if err != nil {
		return nil, wrapError("PROVIDER_LOAD_FAILED", err)
	}
	out := make([]ProviderDTO, 0, len(listed))
	for _, provider := range listed {
		out = append(out, providerDTOFromAPI(provider))
	}
	return out, nil
}

func (s *ProviderService) Show(name string) (ProviderDTO, error) {
	provider, err := s.api().Show(context.Background(), name)
	if err != nil {
		return ProviderDTO{}, wrapProviderError("PROVIDER_NOT_FOUND", err, name)
	}
	return providerDTOFromAPI(provider), nil
}

func (s *ProviderService) Add(input ProviderInput) (ProviderDTO, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	provider, err := s.api().Add(context.Background(), providerInputFromDTO(input))
	if err != nil {
		return ProviderDTO{}, wrapError("PROVIDER_ADD_FAILED", err)
	}
	return providerDTOFromAPI(provider), nil
}

func (s *ProviderService) Update(name string, input ProviderInput) (ProviderDTO, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	provider, err := s.api().Update(context.Background(), name, providerPatchFromDTO(input))
	if err != nil {
		return ProviderDTO{}, wrapError("PROVIDER_UPDATE_FAILED", err)
	}
	return providerDTOFromAPI(provider), nil
}

func (s *ProviderService) Remove(name string) (OperationResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	result, err := s.api().Remove(context.Background(), name)
	if err != nil {
		return OperationResult{}, wrapProviderError("PROVIDER_NOT_FOUND", err, name)
	}
	return operationResultDTO(result), nil
}

func (s *ProviderService) Enable(name string) (ProviderDTO, error) {
	return s.setEnabled(name, true)
}

func (s *ProviderService) Disable(name string) (ProviderDTO, error) {
	return s.setEnabled(name, false)
}

func (s *ProviderService) Rename(oldName, newName string) (ProviderDTO, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	provider, err := s.api().Rename(context.Background(), oldName, newName)
	if err != nil {
		return ProviderDTO{}, wrapError("PROVIDER_RENAME_FAILED", err)
	}
	return providerDTOFromAPI(provider), nil
}

func (s *ProviderService) ResolveModels(name string) ([]string, error) {
	models, err := s.api().ResolveModels(context.Background(), name)
	if err != nil {
		return nil, wrapError("MODEL_DISCOVERY_FAILED", err)
	}
	return models, nil
}

func (s *ProviderService) setEnabled(name string, enabled bool) (ProviderDTO, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	provider, err := s.api().SetEnabled(context.Background(), name, enabled)
	if err != nil {
		return ProviderDTO{}, wrapError("PROVIDER_UPDATE_FAILED", err)
	}
	return providerDTOFromAPI(provider), nil
}

func operationResultDTO(result appapi.OperationResult) OperationResult {
	return OperationResult{OK: result.OK, Message: result.Message, Path: result.Path}
}

func providerDTOFromAPI(provider appapi.Provider) ProviderDTO {
	return ProviderDTO{
		Name:            provider.Name,
		Endpoint:        provider.Endpoint,
		APIKeyEnv:       provider.APIKeyEnv,
		SupportedClient: provider.SupportedClient,
		Clients:         provider.Clients,
		Models:          provider.Models,
		KeepProxyConfig: provider.KeepProxyConfig,
		UseProxy:        provider.UseProxy,
		Enabled:         provider.Enabled,
		Description:     provider.Description,
		MaskedAPIKey:    provider.MaskedAPIKey,
	}
}

func providerDTO(name string, endpoint providers.Endpoint) ProviderDTO {
	return providerDTOFromAPI(appapi.Provider{
		Name:            name,
		Endpoint:        endpoint.Endpoint,
		APIKeyEnv:       endpoint.APIKeyEnv,
		SupportedClient: endpoint.SupportedClient,
		Clients:         endpoint.Clients(),
		Models:          append([]string(nil), endpoint.Models...),
		KeepProxyConfig: endpoint.KeepProxyConfig,
		UseProxy:        endpoint.UseProxy,
		Enabled:         endpoint.IsEnabled(),
		Description:     endpoint.Description,
		ListModelsCmd:   endpoint.ListModelsCmd,
		MaskedAPIKey:    providers.MaskedAPIKey(providers.ResolveAPIKey(endpoint, nil)),
	})
}

func providerInputFromDTO(input ProviderInput) appapi.ProviderInput {
	return appapi.ProviderInput{
		Name:            input.Name,
		Endpoint:        input.Endpoint,
		APIKey:          input.APIKey,
		APIKeyEnv:       input.APIKeyEnv,
		SupportedClient: input.SupportedClient,
		Clients:         input.Clients,
		Models:          input.Models,
		ListModelsCmd:   input.ListModelsCmd,
		KeepProxyConfig: input.KeepProxyConfig,
		UseProxy:        input.UseProxy,
		Enabled:         input.Enabled,
		Description:     input.Description,
	}
}

func providerPatchFromDTO(input ProviderInput) appapi.ProviderPatch {
	patch := appapi.ProviderPatch{
		Enabled: input.Enabled,
	}
	if input.Endpoint != "" {
		patch.Endpoint = &input.Endpoint
	}
	if input.APIKey != "" {
		patch.APIKey = &input.APIKey
	}
	if input.APIKeyEnv != "" {
		patch.APIKeyEnv = &input.APIKeyEnv
	}
	if input.SupportedClient != "" {
		patch.SupportedClient = &input.SupportedClient
	} else if len(input.Clients) > 0 {
		patch.Clients = &providers.ListPatch{Op: providers.ListOpReplace, Items: input.Clients}
	}
	if input.Models != nil {
		patch.Models = &providers.ListPatch{Op: providers.ListOpReplace, Items: input.Models}
	}
	if input.ListModelsCmd != "" {
		patch.ListModelsCmd = &input.ListModelsCmd
	}
	if input.KeepProxyConfig {
		patch.KeepProxyConfig = &input.KeepProxyConfig
	}
	if input.UseProxy {
		patch.UseProxy = &input.UseProxy
	}
	if input.Description != "" {
		patch.Description = &input.Description
	}
	return patch
}

func wrapProviderError(code string, err error, name string) error {
	if err == nil {
		return nil
	}
	if code == "PROVIDER_NOT_FOUND" {
		return NewError(code, "provider not found", map[string]string{"name": name})
	}
	return wrapError(code, err)
}
