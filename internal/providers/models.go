package providers

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// modelDiscoveryTimeout caps how long ResolveModels will wait for a
// list_models_cmd to produce output. Hard ceiling; not configurable.
const modelDiscoveryTimeout = 15 * time.Second

// proxyVars are the env vars stripped before invoking list_models_cmd
// when KeepProxyConfig is false. Matches the Python CAM behaviour.
var proxyVars = []string{
	"http_proxy", "HTTP_PROXY",
	"https_proxy", "HTTPS_PROXY",
	"no_proxy", "NO_PROXY",
	"all_proxy", "ALL_PROXY",
}

// ErrEmptyModelList signals that the discovery command succeeded but
// returned no models. Wizard treats this the same as a non-zero exit:
// offer manual entry or step back to provider selection.
var ErrEmptyModelList = errors.New("providers: list_models_cmd returned no models")

// cacheEntry is the on-disk format under cacheDir/<epName>.json.
type cacheEntry struct {
	Models    []string  `json:"models"`
	FetchedAt time.Time `json:"fetched_at"`
}

// ResolveModels returns the model list to present for endpoint ep,
// identified by epName. Priority:
//
//  1. Built-in /v1/models discovery → combined with ep.Models.
//  2. ep.Models when API discovery fails or returns no models.
//  3. Deprecated ep.ListModelsCmd fallback when no static models exist.
//  4. No source configured → empty slice, nil error.
//
// API and command discovery results are cached for cacheTTL under
// cacheDir/<epName>.json. cacheDir defaults to pathutil.CacheDir()/models
// when empty.
//
// On list_models_cmd timeout, non-zero exit, or empty output, returns
// ([], err). Callers treat err as a recoverable signal.
func ResolveModels(
	ep Endpoint,
	epName string,
	cacheTTL time.Duration,
	cacheDir string,
	getenv func(string) string,
) ([]string, error) {
	if cacheDir == "" {
		cacheDir = filepath.Join(pathutil.CacheDir(), "models")
	}
	cachePath := filepath.Join(cacheDir, epName+".json")

	if cached, ok := readModelsCache(cachePath, cacheTTL); ok {
		return mergeModels(cached, ep.Models), nil
	}

	models, err := fetchAPIModels(ep, getenv)
	if err == nil && len(models) > 0 {
		merged := mergeModels(models, ep.Models)
		_ = writeModelsCache(cachePath, models)
		return merged, nil
	}

	if len(ep.Models) > 0 {
		return append([]string(nil), ep.Models...), nil
	}
	if ep.ListModelsCmd == "" {
		return nil, nil
	}

	models, err = runListModelsCmd(ep, epName, getenv)
	if err != nil {
		return nil, nil
	}

	_ = writeModelsCache(cachePath, models)
	return models, nil
}

type modelsResponse struct {
	Data []struct {
		ID string `json:"id"`
	} `json:"data"`
}

func fetchAPIModels(ep Endpoint, getenv func(string) string) ([]string, error) {
	if ep.Endpoint == "" {
		return nil, nil
	}
	if getenv == nil {
		getenv = os.Getenv
	}

	for _, endpoint := range modelDiscoveryURLs(ep.Endpoint) {
		models, err := fetchModelsURL(ep, endpoint, getenv)
		if err == nil && len(models) > 0 {
			return models, nil
		}
	}
	return nil, nil
}

func fetchModelsURL(ep Endpoint, endpoint string, getenv func(string) string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), modelDiscoveryTimeout)
	defer cancel()

	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	apiKey := ResolveAPIKey(ep, getenv)
	if apiKey != "" {
		request.Header.Set("Authorization", "Bearer "+apiKey)
		request.Header.Set("x-litellm-api-key", apiKey)
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("accept", "application/json")

	client := &http.Client{
		Timeout:   modelDiscoveryTimeout,
		Transport: discoveryTransport(ep),
	}
	response, err := client.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return nil, fmt.Errorf("providers: fetch models from %s returned %s", request.URL, response.Status)
	}

	var payload modelsResponse
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		return nil, err
	}
	models := make([]string, 0, len(payload.Data))
	for _, model := range payload.Data {
		id := strings.TrimSpace(model.ID)
		if id != "" {
			models = append(models, id)
		}
	}
	return models, nil
}

func modelDiscoveryURLs(endpoint string) []string {
	primary := modelsURL(endpoint)
	root := rootModelsURL(endpoint)
	if root == primary {
		return []string{primary}
	}
	return []string{primary, root}
}

func modelsURL(endpoint string) string {
	trimmed := strings.TrimRight(endpoint, "/")
	modelsEndpoint := trimmed + "/v1/models"
	if strings.HasSuffix(trimmed, "/v1/models") {
		modelsEndpoint = trimmed
	} else if strings.HasSuffix(trimmed, "/v1") {
		modelsEndpoint = trimmed + "/models"
	}
	return withModelQuery(modelsEndpoint)
}

func rootModelsURL(endpoint string) string {
	trimmed := strings.TrimRight(endpoint, "/")
	if strings.HasSuffix(trimmed, "/models") {
		return withModelQuery(trimmed)
	}
	return withModelQuery(trimmed + "/models")
}

func withModelQuery(endpoint string) string {
	parsed, err := url.Parse(endpoint)
	if err != nil {
		return endpoint
	}
	query := parsed.Query()
	query.Set("return_wildcard_routes", "false")
	query.Set("include_model_access_groups", "false")
	query.Set("only_model_access_groups", "false")
	query.Set("include_metadata", "false")
	parsed.RawQuery = query.Encode()
	return parsed.String()
}

func discoveryTransport(ep Endpoint) http.RoundTripper {
	transport := http.DefaultTransport.(*http.Transport).Clone()
	if !ep.KeepProxyConfig {
		transport.Proxy = nil
	}
	if isPrivateEndpoint(ep.Endpoint) {
		transport.TLSClientConfig = &tls.Config{InsecureSkipVerify: true} //nolint:gosec // Match existing private/loopback provider behavior.
	}
	return transport
}

func isPrivateEndpoint(endpoint string) bool {
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Hostname() == "" {
		return false
	}
	ip := net.ParseIP(parsed.Hostname())
	if ip == nil {
		return false
	}
	return ip.IsPrivate() || ip.IsLoopback()
}

func mergeModels(groups ...[]string) []string {
	seen := map[string]struct{}{}
	merged := []string{}
	for _, group := range groups {
		for _, raw := range group {
			model := strings.TrimSpace(raw)
			if model == "" {
				continue
			}
			if _, ok := seen[model]; ok {
				continue
			}
			seen[model] = struct{}{}
			merged = append(merged, model)
		}
	}
	return merged
}

func readModelsCache(path string, ttl time.Duration) ([]string, bool) {
	if ttl <= 0 {
		return nil, false
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, false
	}
	var entry cacheEntry
	if err := json.Unmarshal(raw, &entry); err != nil {
		return nil, false
	}
	if entry.FetchedAt.IsZero() || time.Since(entry.FetchedAt) > ttl {
		return nil, false
	}
	if len(entry.Models) == 0 {
		return nil, false
	}
	return append([]string(nil), entry.Models...), true
}

func writeModelsCache(path string, models []string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	entry := cacheEntry{Models: models, FetchedAt: time.Now()}
	payload, err := json.MarshalIndent(entry, "", "  ")
	if err != nil {
		return err
	}
	tmp := fmt.Sprintf("%s.tmp.%d", path, os.Getpid())
	if err := os.WriteFile(tmp, payload, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func runListModelsCmd(ep Endpoint, epName string, getenv func(string) string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), modelDiscoveryTimeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", "-c", ep.ListModelsCmd)
	cmd.Env = buildDiscoveryEnv(ep, getenv)

	out, err := cmd.Output()
	if ctx.Err() == context.DeadlineExceeded {
		return nil, fmt.Errorf("providers: list_models_cmd for %s timed out after %s", epName, modelDiscoveryTimeout)
	}
	if err != nil {
		if exit, ok := err.(*exec.ExitError); ok {
			return nil, fmt.Errorf("providers: list_models_cmd for %s exited %d: %s",
				epName, exit.ExitCode(), strings.TrimSpace(string(exit.Stderr)))
		}
		return nil, fmt.Errorf("providers: list_models_cmd for %s: %w", epName, err)
	}

	models := parseModelsOutput(string(out))
	if len(models) == 0 {
		return nil, ErrEmptyModelList
	}
	return models, nil
}

// parseModelsOutput splits stdout on \n and drops empty/whitespace lines.
// Each surviving line is trimmed.
func parseModelsOutput(raw string) []string {
	var models []string
	for _, line := range strings.Split(raw, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		models = append(models, trimmed)
	}
	return models
}

// buildDiscoveryEnv constructs the env slice passed to list_models_cmd.
// Starts from os.Environ() (via getenv if injected via tests), strips
// proxy vars when KeepProxyConfig is false, then layers endpoint +
// api_key on top.
func buildDiscoveryEnv(ep Endpoint, getenv func(string) string) []string {
	if getenv == nil {
		getenv = os.Getenv
	}
	apiKey := ResolveAPIKey(ep, getenv)

	current := os.Environ()
	out := make([]string, 0, len(current)+2)
	for _, kv := range current {
		name, _, _ := strings.Cut(kv, "=")
		if !ep.KeepProxyConfig && isProxyVar(name) {
			continue
		}
		// Avoid letting an inherited endpoint/api_key override.
		if name == "endpoint" || name == "api_key" {
			continue
		}
		out = append(out, kv)
	}
	out = append(out, "endpoint="+ep.Endpoint)
	out = append(out, "api_key="+apiKey)
	return out
}

func isProxyVar(name string) bool {
	for _, p := range proxyVars {
		if name == p {
			return true
		}
	}
	return false
}
