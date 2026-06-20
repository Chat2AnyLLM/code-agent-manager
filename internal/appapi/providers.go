package appapi

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/appstate"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// OperationResult describes a completed app operation.
type OperationResult struct {
	OK      bool
	Message string
	Path    string
}

// Provider is the shared provider shape consumed by CLI and desktop adapters.
type Provider struct {
	Name            string
	Endpoint        string
	APIKey          string
	APIKeyEnv       string
	SupportedClient string
	Clients         []string
	Models          []string
	KeepProxyConfig bool
	UseProxy        bool
	Enabled         bool
	Description     string
	ListModelsCmd   string
	MaskedAPIKey    string
}

// ProviderInput creates a provider from complete user input.
type ProviderInput struct {
	Name            string
	Endpoint        string
	APIKey          string
	APIKeyEnv       string
	SupportedClient string
	Clients         []string
	Models          []string
	KeepProxyConfig bool
	UseProxy        bool
	Enabled         *bool
	Description     string
	ListModelsCmd   string
}

// ProviderPatch updates a provider without forcing callers to overwrite every field.
type ProviderPatch struct {
	Endpoint        *string
	APIKey          *string
	APIKeyEnv       *string
	SupportedClient *string
	Clients         *providers.ListPatch
	Models          *providers.ListPatch
	KeepProxyConfig *bool
	UseProxy        *bool
	Enabled         *bool
	Description     *string
	ListModelsCmd   *string
}

// ProviderAPI contains provider workflows shared by CLI and desktop adapters.
type ProviderAPI struct {
	DBPath   string
	CacheTTL time.Duration
	Env      func(string) string
}

func deleteProvidersJSON() {
	if p := filepath.Join(pathutil.ConfigDir(), "providers.json"); p != "" {
		if _, err := os.Stat(p); err == nil {
			_ = os.Remove(p)
		}
	}
}

func (api ProviderAPI) dbPath() string {
	if api.DBPath != "" {
		return api.DBPath
	}
	return appstate.DefaultPath()
}

func (api ProviderAPI) store() appstate.Store {
	return appstate.New(api.dbPath())
}

func (api ProviderAPI) getenv() func(string) string {
	if api.Env != nil {
		return api.Env
	}
	return os.Getenv
}

func (api ProviderAPI) cacheTTL() time.Duration {
	if api.CacheTTL > 0 {
		return api.CacheTTL
	}
	return time.Hour
}

func (api ProviderAPI) prepareProviderOperation() error {
	deleteProvidersJSON()
	return nil
}

func (api ProviderAPI) listProvidersFile(ctx context.Context) (providers.File, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return providers.File{}, err
	}
	return api.store().ListProviders(ctx)
}

// Init creates the SQLite app state database and deletes the legacy providers.json.
func (api ProviderAPI) Init(ctx context.Context) (OperationResult, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return OperationResult{}, err
	}
	store := api.store()
	if err := store.Init(ctx); err != nil {
		return OperationResult{}, err
	}
	return OperationResult{OK: true, Message: fmt.Sprintf("SQLite app state ready at %s", store.Path()), Path: store.Path()}, nil
}

// File returns providers in providers.File shape for adapters that still need existing helpers.
func (api ProviderAPI) File(ctx context.Context) (providers.File, error) {
	return api.listProvidersFile(ctx)
}

// List returns all configured providers.
func (api ProviderAPI) List(ctx context.Context) ([]Provider, error) {
	file, err := api.listProvidersFile(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]Provider, 0, len(file.Endpoints))
	for _, name := range file.SortedNames() {
		out = append(out, providerFromEndpoint(name, file.Endpoints[name], api.getenv()))
	}
	return out, nil
}

// Show returns one provider by name.
func (api ProviderAPI) Show(ctx context.Context, name string) (Provider, error) {
	file, err := api.listProvidersFile(ctx)
	if err != nil {
		return Provider{}, err
	}
	endpoint, ok := file.Endpoints[name]
	if !ok {
		return Provider{}, fmt.Errorf("provider %q not found: %w", name, providers.ErrNotFound)
	}
	return providerFromEndpoint(name, endpoint, api.getenv()), nil
}

// Add inserts a new provider.
func (api ProviderAPI) Add(ctx context.Context, input ProviderInput) (Provider, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return Provider{}, err
	}
	endpoint := endpointFromInput(input)
	if err := api.store().AddProvider(ctx, input.Name, endpoint); err != nil {
		return Provider{}, err
	}
	return providerFromEndpoint(input.Name, endpoint, api.getenv()), nil
}

// Update applies a sparse provider patch.
func (api ProviderAPI) Update(ctx context.Context, name string, patch ProviderPatch) (Provider, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return Provider{}, err
	}
	providerPatch := providers.Patch{
		Endpoint:        patch.Endpoint,
		APIKey:          patch.APIKey,
		APIKeyEnv:       patch.APIKeyEnv,
		Description:     patch.Description,
		ListModelsCmd:   patch.ListModelsCmd,
		KeepProxyConfig: patch.KeepProxyConfig,
		UseProxy:        patch.UseProxy,
		Enabled:         patch.Enabled,
		Clients:         patch.Clients,
		Models:          patch.Models,
	}
	if patch.SupportedClient != nil {
		providerPatch.Clients = &providers.ListPatch{Op: providers.ListOpReplace, Items: splitClients(*patch.SupportedClient)}
	}
	store := api.store()
	if err := store.UpdateProvider(ctx, name, providerPatch); err != nil {
		return Provider{}, err
	}
	file, err := store.ListProviders(ctx)
	if err != nil {
		return Provider{}, err
	}
	return providerFromEndpoint(name, file.Endpoints[name], api.getenv()), nil
}

// Remove deletes a provider.
func (api ProviderAPI) Remove(ctx context.Context, name string) (OperationResult, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return OperationResult{}, err
	}
	if !api.store().RemoveProvider(ctx, name) {
		return OperationResult{}, fmt.Errorf("provider %q not found: %w", name, providers.ErrNotFound)
	}
	return OperationResult{OK: true, Message: fmt.Sprintf("Removed provider %q", name), Path: api.dbPath()}, nil
}

// SetEnabled toggles a provider's enabled state.
func (api ProviderAPI) SetEnabled(ctx context.Context, name string, enabled bool) (Provider, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return Provider{}, err
	}
	store := api.store()
	if err := store.SetProviderEnabled(ctx, name, enabled); err != nil {
		return Provider{}, err
	}
	file, err := store.ListProviders(ctx)
	if err != nil {
		return Provider{}, err
	}
	return providerFromEndpoint(name, file.Endpoints[name], api.getenv()), nil
}

// Rename changes a provider key.
func (api ProviderAPI) Rename(ctx context.Context, oldName, newName string) (Provider, error) {
	if err := api.prepareProviderOperation(); err != nil {
		return Provider{}, err
	}
	store := api.store()
	if err := store.RenameProvider(ctx, oldName, newName); err != nil {
		return Provider{}, err
	}
	file, err := store.ListProviders(ctx)
	if err != nil {
		return Provider{}, err
	}
	return providerFromEndpoint(newName, file.Endpoints[newName], api.getenv()), nil
}

// ResolveModels resolves static or dynamically discovered models for a provider.
func (api ProviderAPI) ResolveModels(ctx context.Context, name string) ([]string, error) {
	file, err := api.listProvidersFile(ctx)
	if err != nil {
		return nil, err
	}
	endpoint, ok := file.Endpoints[name]
	if !ok {
		return nil, fmt.Errorf("provider %q not found: %w", name, providers.ErrNotFound)
	}
	return providers.ResolveModels(endpoint, name, api.cacheTTL(), filepath.Join(pathutil.CacheDir(), "models"), api.getenv())
}
func providerFromEndpoint(name string, endpoint providers.Endpoint, getenv func(string) string) Provider {
	return Provider{
		Name:            name,
		Endpoint:        endpoint.Endpoint,
		APIKey:          endpoint.APIKey,
		APIKeyEnv:       endpoint.APIKeyEnv,
		SupportedClient: endpoint.SupportedClient,
		Clients:         endpoint.Clients(),
		Models:          append([]string(nil), endpoint.Models...),
		KeepProxyConfig: endpoint.KeepProxyConfig,
		UseProxy:        endpoint.UseProxy,
		Enabled:         endpoint.IsEnabled(),
		Description:     endpoint.Description,
		ListModelsCmd:   endpoint.ListModelsCmd,
		MaskedAPIKey:    providers.MaskedAPIKey(providers.ResolveAPIKey(endpoint, getenv)),
	}
}

func endpointFromInput(input ProviderInput) providers.Endpoint {
	supportedClient := input.SupportedClient
	if supportedClient == "" && len(input.Clients) > 0 {
		supportedClient = joinClients(input.Clients)
	}
	endpoint := providers.Endpoint{
		Endpoint:        input.Endpoint,
		APIKey:          input.APIKey,
		APIKeyEnv:       input.APIKeyEnv,
		SupportedClient: supportedClient,
		ListModelsCmd:   input.ListModelsCmd,
		Models:          append([]string(nil), input.Models...),
		KeepProxyConfig: input.KeepProxyConfig,
		UseProxy:        input.UseProxy,
		Description:     input.Description,
	}
	if input.Enabled != nil {
		endpoint.Enabled = input.Enabled
	}
	return endpoint
}

func splitClients(raw string) []string {
	return providers.Endpoint{SupportedClient: raw}.Clients()
}

func joinClients(clients []string) string {
	parts := make([]string, 0, len(clients))
	for _, client := range clients {
		if trimmed := strings.TrimSpace(client); trimmed != "" {
			parts = append(parts, trimmed)
		}
	}
	return strings.Join(parts, ",")
}
