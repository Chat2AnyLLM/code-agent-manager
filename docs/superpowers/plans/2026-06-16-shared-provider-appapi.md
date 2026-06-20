# Shared Provider App API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move provider business workflows into a shared app-facing API so both CLI and Wails desktop call the same provider logic.

**Architecture:** Add `internal/appapi` as a use-case layer below `internal/cli` and `internal/desktop`, above `internal/providers`. CLI remains responsible for flags/output, desktop remains responsible for Wails DTO mapping, and `internal/appapi.ProviderAPI` owns provider workflows and persistence behavior.

**Tech Stack:** Go, Cobra CLI, Wails desktop services, existing `internal/providers`, table-driven Go tests.

---

## Files

### Create
- `internal/appapi/providers.go` — shared provider API types and workflows.
- `internal/appapi/providers_test.go` — shared provider API tests.

### Modify
- `internal/desktop/provider_service.go` — delegate provider workflows to `appapi.ProviderAPI`.
- `internal/desktop/provider_service_test.go` — keep existing desktop DTO tests passing through shared API.
- `internal/cli/provider_cmd.go` — delegate provider workflows to `appapi.ProviderAPI` while preserving CLI rendering/flags.
- `internal/cli/cmd_provider_test.go` — add/adjust tests proving CLI behavior remains unchanged.

---

## Task 1: Shared provider API types and list/init/show

**Files:**
- Create: `internal/appapi/providers.go`
- Create: `internal/appapi/providers_test.go`

- [ ] **Step 1: Write failing tests for shared provider init/list/show**

Create `internal/appapi/providers_test.go` with tests that call `ProviderAPI` directly using a temp SQLite store path. Include these test cases:

```go
package appapi

import (
    "context"
    "encoding/json"
    "os"
    "path/filepath"
    "testing"

    "github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestProviderAPIInitListShow(t *testing.T) {
    path := filepath.Join(t.TempDir(), "providers.json")
    api := ProviderAPI{ProvidersPath: path, Env: os.Getenv}

    result, err := api.Init(context.Background())
    if err != nil {
        t.Fatalf("Init error = %v", err)
    }
    if !result.OK || result.Message == "" {
        t.Fatalf("Init result = %+v, want ok message", result)
    }

    raw, err := os.ReadFile(path)
    if err != nil {
        t.Fatalf("providers file missing: %v", err)
    }
    parsed := map[string]any{}
    if err := json.Unmarshal(raw, &parsed); err != nil {
        t.Fatalf("providers json invalid: %v", err)
    }
    if _, ok := parsed["endpoints"]; !ok {
        t.Fatalf("providers file missing endpoints: %s", raw)
    }

    file := providers.File{Endpoints: map[string]providers.Endpoint{
        "local": {
            Name:            "local",
            Endpoint:        "http://localhost:4000/v1",
            APIKeyEnv:       "LOCAL_KEY",
            SupportedClient: "claude,codex",
            Models:          []string{"m1", "m2"},
            Enabled:         boolPtr(true),
        },
    }}
    store := providers.NewStore(path)
    if err := store.Save(file); err != nil {
        t.Fatalf("save fixture: %v", err)
    }

    listed, err := api.List(context.Background())
    if err != nil {
        t.Fatalf("List error = %v", err)
    }
    if len(listed) != 1 || listed[0].Name != "local" || listed[0].Endpoint != "http://localhost:4000/v1" {
        t.Fatalf("List = %+v, want local provider", listed)
    }

    shown, err := api.Show(context.Background(), "local")
    if err != nil {
        t.Fatalf("Show error = %v", err)
    }
    if shown.Name != "local" || len(shown.Models) != 2 {
        t.Fatalf("Show = %+v, want local with models", shown)
    }
}

func boolPtr(v bool) *bool { return &v }
```

- [ ] **Step 2: Run failing test**

Run: `go test ./internal/appapi -run TestProviderAPIInitListShow -v`

Expected: compile failure because `ProviderAPI` does not exist.

- [ ] **Step 3: Implement shared provider API init/list/show**

Create `internal/appapi/providers.go` with:

```go
package appapi

import (
    "context"
    "fmt"
    "os"
    "time"

    "github.com/chat2anyllm/code-agent-manager/internal/pathutil"
    "github.com/chat2anyllm/code-agent-manager/internal/providers"
)

type OperationResult struct {
    OK      bool
    Message string
}

type Provider struct {
    Name            string
    Endpoint        string
    APIKeyEnv       string
    SupportedClient string
    Clients         []string
    Models          []string
    KeepProxyConfig bool
    UseProxy        bool
    Enabled         bool
    Description     string
    MaskedAPIKey    string
}

type ProviderInput struct {
    Name            string
    Endpoint        string
    APIKeyEnv       string
    SupportedClient string
    Clients         []string
    Models          []string
    KeepProxyConfig bool
    UseProxy        bool
    Enabled         *bool
    Description     string
}

type ProviderAPI struct {
    ProvidersPath string
    CacheTTL      time.Duration
    Env           func(string) string
}

func (api ProviderAPI) store() *providers.Store {
    return providers.NewStore(api.ProvidersPath)
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

func (api ProviderAPI) Init(ctx context.Context) (OperationResult, error) {
    _ = ctx
    path := api.store().Path()
    if _, err := os.Stat(path); err == nil {
        return OperationResult{OK: true, Message: fmt.Sprintf("providers.json already exists at %s", path)}, nil
    } else if !os.IsNotExist(err) {
        return OperationResult{}, err
    }
    if err := api.store().Save(providers.File{Endpoints: map[string]providers.Endpoint{}}); err != nil {
        return OperationResult{}, err
    }
    return OperationResult{OK: true, Message: fmt.Sprintf("Created empty providers.json at %s", path)}, nil
}

func (api ProviderAPI) List(ctx context.Context) ([]Provider, error) {
    _ = ctx
    file, err := api.store().LoadOrInit()
    if err != nil {
        return nil, err
    }
    out := make([]Provider, 0, len(file.Endpoints))
    for name, endpoint := range file.Endpoints {
        out = append(out, providerFromEndpoint(name, endpoint, api.getenv()))
    }
    return out, nil
}

func (api ProviderAPI) Show(ctx context.Context, name string) (Provider, error) {
    _ = ctx
    file, err := api.store().LoadOrInit()
    if err != nil {
        return Provider{}, err
    }
    endpoint, ok := file.Endpoints[name]
    if !ok {
        return Provider{}, fmt.Errorf("provider %q not found", name)
    }
    return providerFromEndpoint(name, endpoint, api.getenv()), nil
}

func providerFromEndpoint(name string, endpoint providers.Endpoint, getenv func(string) string) Provider {
    return Provider{
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
        MaskedAPIKey:    providers.MaskedAPIKey(providers.ResolveAPIKey(endpoint, getenv)),
    }
}

func endpointFromInput(input ProviderInput) providers.Endpoint {
    supportedClient := input.SupportedClient
    if supportedClient == "" && len(input.Clients) > 0 {
        supportedClient = providers.JoinClients(input.Clients)
    }
    endpoint := providers.Endpoint{
        Name:            input.Name,
        Endpoint:        input.Endpoint,
        APIKeyEnv:       input.APIKeyEnv,
        SupportedClient: supportedClient,
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

func modelsCacheDir() string {
    return pathutil.CacheDir() + string(os.PathSeparator) + "models"
}
```

- [ ] **Step 4: Run passing test**

Run: `go test ./internal/appapi -run TestProviderAPIInitListShow -v`

Expected: PASS.

## Task 2: Shared provider mutation workflows

**Files:**
- Modify: `internal/appapi/providers.go`
- Modify: `internal/appapi/providers_test.go`

- [ ] **Step 1: Write failing tests for add/update/remove/enable/rename**

Add test cases to `internal/appapi/providers_test.go` for:

```go
func TestProviderAPIMutations(t *testing.T) {
    path := filepath.Join(t.TempDir(), "providers.json")
    api := ProviderAPI{ProvidersPath: path, Env: os.Getenv}
    enabled := true

    added, err := api.Add(context.Background(), ProviderInput{
        Name:            "alpha",
        Endpoint:        "https://alpha.example",
        APIKeyEnv:       "ALPHA_KEY",
        SupportedClient: "claude,codex",
        Models:          []string{"m1"},
        Enabled:         &enabled,
        Description:     "alpha provider",
    })
    if err != nil {
        t.Fatalf("Add error = %v", err)
    }
    if added.Name != "alpha" || !added.Enabled || len(added.Models) != 1 {
        t.Fatalf("Add = %+v", added)
    }

    updated, err := api.Update(context.Background(), "alpha", ProviderInput{
        Endpoint:        "https://updated.example",
        SupportedClient: "claude",
        Models:          []string{"m2", "m3"},
        Description:     "updated provider",
    })
    if err != nil {
        t.Fatalf("Update error = %v", err)
    }
    if updated.Endpoint != "https://updated.example" || updated.Description != "updated provider" || len(updated.Models) != 2 {
        t.Fatalf("Update = %+v", updated)
    }

    disabled, err := api.SetEnabled(context.Background(), "alpha", false)
    if err != nil {
        t.Fatalf("SetEnabled false error = %v", err)
    }
    if disabled.Enabled {
        t.Fatalf("SetEnabled false = %+v", disabled)
    }

    renamed, err := api.Rename(context.Background(), "alpha", "beta")
    if err != nil {
        t.Fatalf("Rename error = %v", err)
    }
    if renamed.Name != "beta" {
        t.Fatalf("Rename = %+v", renamed)
    }
    if _, err := api.Show(context.Background(), "alpha"); err == nil {
        t.Fatal("old provider name should be missing")
    }

    result, err := api.Remove(context.Background(), "beta")
    if err != nil {
        t.Fatalf("Remove error = %v", err)
    }
    if !result.OK {
        t.Fatalf("Remove result = %+v", result)
    }
    listed, err := api.List(context.Background())
    if err != nil {
        t.Fatalf("List after remove error = %v", err)
    }
    if len(listed) != 0 {
        t.Fatalf("List after remove = %+v", listed)
    }
}
```

- [ ] **Step 2: Run failing tests**

Run: `go test ./internal/appapi -run TestProviderAPIMutations -v`

Expected: compile failure for missing methods.

- [ ] **Step 3: Implement mutations in `internal/appapi/providers.go`**

Add methods:

```go
func (api ProviderAPI) Add(ctx context.Context, input ProviderInput) (Provider, error) {
    _ = ctx
    if input.Name == "" {
        return Provider{}, fmt.Errorf("provider name is required")
    }
    if input.Endpoint == "" {
        return Provider{}, fmt.Errorf("endpoint is required")
    }
    store := api.store()
    file, err := store.LoadOrInit()
    if err != nil {
        return Provider{}, err
    }
    if _, exists := file.Endpoints[input.Name]; exists {
        return Provider{}, fmt.Errorf("provider %q already exists", input.Name)
    }
    endpoint := endpointFromInput(input)
    file.Endpoints[input.Name] = endpoint
    if err := store.Save(file); err != nil {
        return Provider{}, err
    }
    return providerFromEndpoint(input.Name, endpoint, api.getenv()), nil
}

func (api ProviderAPI) Update(ctx context.Context, name string, input ProviderInput) (Provider, error) {
    _ = ctx
    store := api.store()
    file, err := store.LoadOrInit()
    if err != nil {
        return Provider{}, err
    }
    endpoint, ok := file.Endpoints[name]
    if !ok {
        return Provider{}, fmt.Errorf("provider %q not found", name)
    }
    if input.Endpoint != "" {
        endpoint.Endpoint = input.Endpoint
    }
    if input.APIKeyEnv != "" {
        endpoint.APIKeyEnv = input.APIKeyEnv
    }
    if input.SupportedClient != "" {
        endpoint.SupportedClient = input.SupportedClient
    } else if len(input.Clients) > 0 {
        endpoint.SupportedClient = providers.JoinClients(input.Clients)
    }
    if input.Models != nil {
        endpoint.Models = append([]string(nil), input.Models...)
    }
    endpoint.KeepProxyConfig = input.KeepProxyConfig
    endpoint.UseProxy = input.UseProxy
    if input.Enabled != nil {
        endpoint.Enabled = input.Enabled
    }
    if input.Description != "" {
        endpoint.Description = input.Description
    }
    file.Endpoints[name] = endpoint
    if err := store.Save(file); err != nil {
        return Provider{}, err
    }
    return providerFromEndpoint(name, endpoint, api.getenv()), nil
}

func (api ProviderAPI) Remove(ctx context.Context, name string) (OperationResult, error) {
    _ = ctx
    store := api.store()
    file, err := store.LoadOrInit()
    if err != nil {
        return OperationResult{}, err
    }
    if _, ok := file.Endpoints[name]; !ok {
        return OperationResult{}, fmt.Errorf("provider %q not found", name)
    }
    delete(file.Endpoints, name)
    if err := store.Save(file); err != nil {
        return OperationResult{}, err
    }
    return OperationResult{OK: true, Message: fmt.Sprintf("Removed provider %q", name)}, nil
}

func (api ProviderAPI) SetEnabled(ctx context.Context, name string, enabled bool) (Provider, error) {
    value := enabled
    return api.Update(ctx, name, ProviderInput{Enabled: &value})
}

func (api ProviderAPI) Rename(ctx context.Context, oldName, newName string) (Provider, error) {
    _ = ctx
    if newName == "" {
        return Provider{}, fmt.Errorf("new provider name is required")
    }
    store := api.store()
    file, err := store.LoadOrInit()
    if err != nil {
        return Provider{}, err
    }
    endpoint, ok := file.Endpoints[oldName]
    if !ok {
        return Provider{}, fmt.Errorf("provider %q not found", oldName)
    }
    if _, exists := file.Endpoints[newName]; exists {
        return Provider{}, fmt.Errorf("provider %q already exists", newName)
    }
    delete(file.Endpoints, oldName)
    endpoint.Name = newName
    file.Endpoints[newName] = endpoint
    if err := store.Save(file); err != nil {
        return Provider{}, err
    }
    return providerFromEndpoint(newName, endpoint, api.getenv()), nil
}
```

- [ ] **Step 4: Run appapi tests**

Run: `go test ./internal/appapi -v`

Expected: PASS.

## Task 3: Shared provider model resolution

**Files:**
- Modify: `internal/appapi/providers.go`
- Modify: `internal/appapi/providers_test.go`

- [ ] **Step 1: Write failing test for ResolveModels**

Add:

```go
func TestProviderAPIResolveModels(t *testing.T) {
    path := filepath.Join(t.TempDir(), "providers.json")
    api := ProviderAPI{ProvidersPath: path, Env: os.Getenv}
    enabled := true
    _, err := api.Add(context.Background(), ProviderInput{
        Name:            "alpha",
        Endpoint:        "https://alpha.example",
        SupportedClient: "claude",
        Models:          []string{"static-a", "static-b"},
        Enabled:         &enabled,
    })
    if err != nil {
        t.Fatalf("Add error = %v", err)
    }
    models, err := api.ResolveModels(context.Background(), "alpha")
    if err != nil {
        t.Fatalf("ResolveModels error = %v", err)
    }
    if len(models) != 2 || models[0] != "static-a" || models[1] != "static-b" {
        t.Fatalf("models = %v", models)
    }
}
```

- [ ] **Step 2: Run failing test**

Run: `go test ./internal/appapi -run TestProviderAPIResolveModels -v`

Expected: compile failure for missing `ResolveModels`.

- [ ] **Step 3: Implement ResolveModels**

Add:

```go
func (api ProviderAPI) ResolveModels(ctx context.Context, name string) ([]string, error) {
    _ = ctx
    file, err := api.store().LoadOrInit()
    if err != nil {
        return nil, err
    }
    endpoint, ok := file.Endpoints[name]
    if !ok {
        return nil, fmt.Errorf("provider %q not found", name)
    }
    return providers.ResolveModels(endpoint, name, api.cacheTTL(), modelsCacheDir(), api.getenv())
}
```

- [ ] **Step 4: Run appapi tests**

Run: `go test ./internal/appapi -v`

Expected: PASS.

## Task 4: Desktop ProviderService delegates to appapi

**Files:**
- Modify: `internal/desktop/provider_service.go`
- Test: `internal/desktop/provider_service_test.go`

- [ ] **Step 1: Update ProviderService to hold appapi.ProviderAPI**

Change `ProviderService` so it constructs and calls `appapi.ProviderAPI{ProvidersPath: s.providersPath}` instead of directly loading/saving `providers.Store`.

Use helper methods:

```go
func (s *ProviderService) api() appapi.ProviderAPI {
    return appapi.ProviderAPI{ProvidersPath: s.providersPath}
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
```

For each service method:
- `Init` calls `s.api().Init(context.Background())`.
- `List` calls `s.api().List(context.Background())`.
- `Add` maps `ProviderInput` to `appapi.ProviderInput` and calls `Add`.
- `Update` maps and calls `Update`.
- `Remove` calls `Remove`.
- `Enable` / `Disable` call `SetEnabled`.
- `ResolveModels` calls `ResolveModels`.

- [ ] **Step 2: Run desktop provider tests**

Run: `go test ./internal/desktop -run TestProviderService -v`

Expected: PASS.

## Task 5: CLI provider commands delegate to appapi

**Files:**
- Modify: `internal/cli/provider_cmd.go`
- Test: `internal/cli/cmd_provider_test.go`

- [ ] **Step 1: Add a provider API helper in provider_cmd.go**

Add:

```go
func providerAPI(state *globalState) appapi.ProviderAPI {
    return appapi.ProviderAPI{ProvidersPath: resolveProvidersPath(state)}
}
```

- [ ] **Step 2: Refactor provider init/list/show/add/update/remove/enable/disable/rename**

Keep all Cobra flag definitions and output formatting unchanged, but replace direct `providers.NewStore(resolveProvidersPath(state))` mutations with calls to `providerAPI(state)`.

Mapping rules:
- Existing provider table rendering can consume `appapi.Provider` values or convert back to `providers.File` for minimal diff.
- `provider add` calls `ProviderAPI.Add`.
- `provider update` calls `ProviderAPI.Update`.
- `provider remove` calls `ProviderAPI.Remove` after `--yes` validation.
- `provider enable/disable` calls `ProviderAPI.SetEnabled`.
- `provider rename` calls `ProviderAPI.Rename`.

- [ ] **Step 3: Run CLI provider tests**

Run: `go test ./internal/cli -run TestProvider -v`

Expected: PASS.

## Task 6: Full verification

**Files:** all changed files.

- [ ] Run: `go test ./internal/appapi ./internal/desktop ./internal/cli -run 'TestProvider|TestProviderService' -v`.
- [ ] Run: `go test ./...`.
- [ ] Run: `npm --prefix frontend test -- --run`.
- [ ] Run: `npm --prefix frontend run build`.
- [ ] Run: `go vet ./...`.
- [ ] Run: `go build -tags dev ./cmd/cam-desktop`.
- [ ] Run: `go build -tags production ./cmd/cam-desktop`.
- [ ] Report exact pass/fail results.

## Self-Review

- Spec coverage: provider shared API, CLI delegation, desktop delegation, tests, and full verification are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders remain.
- Type consistency: `appapi.ProviderInput`, `appapi.Provider`, and desktop `ProviderDTO` mappings are explicit.
