package desktop

import (
	"errors"
	"fmt"
)

// AppError is the structured error shape returned by desktop services.
type AppError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details any    `json:"details,omitempty"`
}

func (e AppError) Error() string {
	if e.Code == "" {
		return e.Message
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func NewError(code, message string, details any) AppError {
	return AppError{Code: code, Message: message, Details: details}
}

func wrapError(code string, err error) error {
	if err == nil {
		return nil
	}
	var appErr AppError
	if errors.As(err, &appErr) {
		return appErr
	}
	return NewError(code, err.Error(), nil)
}

// ProviderDTO is a frontend-safe provider representation.
type ProviderDTO struct {
	Name            string   `json:"name"`
	Endpoint        string   `json:"endpoint"`
	APIKeyEnv       string   `json:"apiKeyEnv"`
	SupportedClient string   `json:"supportedClient"`
	Clients         []string `json:"clients"`
	Models          []string `json:"models"`
	KeepProxyConfig bool     `json:"keepProxyConfig"`
	UseProxy        bool     `json:"useProxy"`
	Enabled         bool     `json:"enabled"`
	Description     string   `json:"description"`
	MaskedAPIKey    string   `json:"maskedApiKey,omitempty"`
}

type ProviderInput struct {
	Name            string   `json:"name"`
	Endpoint        string   `json:"endpoint"`
	APIKey          string   `json:"apiKey"`
	APIKeyEnv       string   `json:"apiKeyEnv"`
	SupportedClient string   `json:"supportedClient"`
	Clients         []string `json:"clients"`
	Models          []string `json:"models"`
	ListModelsCmd   string   `json:"listModelsCmd"`
	KeepProxyConfig bool     `json:"keepProxyConfig"`
	UseProxy        bool     `json:"useProxy"`
	Enabled         *bool    `json:"enabled,omitempty"`
	Description     string   `json:"description"`
}

type OperationResult struct {
	OK      bool   `json:"ok"`
	Message string `json:"message"`
	Path    string `json:"path,omitempty"`
}

type MCPClientDTO struct {
	Name         string `json:"name"`
	UserPath     string `json:"userPath"`
	ProjectPath  string `json:"projectPath,omitempty"`
	Container    string `json:"container"`
	Format       string `json:"format"`
	SupportsUser bool   `json:"supportsUser"`
	SupportsProj bool   `json:"supportsProject"`
}

type MCPServerDTO struct {
	Name    string            `json:"name"`
	Client  string            `json:"client,omitempty"`
	Scope   string            `json:"scope,omitempty"`
	Path    string            `json:"path,omitempty"`
	Command string            `json:"command,omitempty"`
	Args    []string          `json:"args,omitempty"`
	Env     map[string]string `json:"env,omitempty"`
	URL     string            `json:"url,omitempty"`
	Type    string            `json:"type,omitempty"`
}

type EntityDTO struct {
	Kind        string         `json:"kind"`
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Content     string         `json:"content,omitempty"`
	Path        string         `json:"path,omitempty"`
	Apps        []string       `json:"apps,omitempty"`
	Tags        []string       `json:"tags,omitempty"`
	Metadata    map[string]any `json:"metadata,omitempty"`
	UpdatedAt   string         `json:"updatedAt"`
}

type ToolDTO struct {
	Name        string `json:"name"`
	Command     string `json:"command"`
	Description string `json:"description"`
	Enabled     bool   `json:"enabled"`
	Installed   bool   `json:"installed"`
	Version     string `json:"version"`
}

type LaunchPlanDTO struct {
	Tool        ToolDTO           `json:"tool"`
	Provider    ProviderDTO       `json:"provider"`
	Model       string            `json:"model"`
	Command     string            `json:"command"`
	Args        []string          `json:"args"`
	Environment map[string]string `json:"environment"`
}

// PlannedWriteDTO is one config key that ApplyConfig wrote (or would write).
type PlannedWriteDTO struct {
	KeyPath string `json:"keyPath"`
	Value   any    `json:"value,omitempty"`
	Op      string `json:"op"` // "upsert" | "remove"
}

// ApplyResultDTO is the outcome of writing a provider's config into an agent's
// config file without launching it. ConfigPath is empty when the tool has no
// config_target (nothing to write).
type ApplyResultDTO struct {
	Tool       ToolDTO           `json:"tool"`
	Provider   ProviderDTO       `json:"provider"`
	Model      string            `json:"model"`
	ConfigPath string            `json:"configPath"`
	Writes     []PlannedWriteDTO `json:"writes"`
}

type ConfigFileDTO struct {
	App         string `json:"app"`
	Scope       string `json:"scope"`
	Path        string `json:"path"`
	Format      string `json:"format"`
	Description string `json:"description,omitempty"`
	Exists      bool   `json:"exists"`
}

type DoctorMessageDTO struct {
	Level string `json:"level"`
	Text  string `json:"text"`
	Hint  string `json:"hint,omitempty"`
}

type DoctorCheckDTO struct {
	Name     string             `json:"name"`
	Issues   int                `json:"issues"`
	Messages []DoctorMessageDTO `json:"messages"`
}
