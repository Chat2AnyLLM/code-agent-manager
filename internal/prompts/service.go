package prompts

import (
	"context"
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const (
	awesomePromptsSource    = "awesome_prompts"
	awesomePromptsName      = "Awesome Prompts"
	awesomePromptsURL       = "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-prompts/master/dist/prompts.json"
	awesomePromptsConfigURL = "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-prompts/master/config.yaml"
	awesomePromptsRepoURL   = "https://github.com/Chat2AnyLLM/awesome-prompts/blob/master/prompts"
	awesomePromptsURLEnv    = "CAM_AWESOME_PROMPTS_URL"
	githubRawBaseURL        = "https://raw.githubusercontent.com"
)

var retiredPromptSources = []string{"claude", "prompts_chat", "promptingguide"}

// awesomePromptsJSON holds the bundled Chat2AnyLLM/awesome-prompts prompt library.
//
//go:embed embed/awesome_prompts.json
var awesomePromptsJSON []byte

// Service handles fetching and syncing prompts from external sources.
type Service struct {
	store                 *Store
	client                *http.Client
	configURL             string
	sourceURL             string
	repoRawBaseURL        string
	githubAPIBaseURL      string
	preferSourceURLDirect bool
}

// NewService creates a new prompts service.
func NewService() *Service {
	sourceURL := os.Getenv(awesomePromptsURLEnv)
	if strings.TrimSpace(sourceURL) == "" {
		sourceURL = awesomePromptsURL
	}
	return &Service{
		store: NewStore(),
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		configURL:        awesomePromptsConfigURL,
		sourceURL:        sourceURL,
		repoRawBaseURL:   githubRawBaseURL,
		githubAPIBaseURL: "https://api.github.com/repos",
	}
}

// Store returns the underlying store.
func (s *Service) Store() *Store {
	return s.store
}

// SyncAll fetches prompts from the Chat2AnyLLM/awesome-prompts source of truth.
func (s *Service) SyncAll(ctx context.Context) (int, error) {
	prompts, err := s.FetchAwesomePrompts(ctx)
	if err != nil {
		return 0, err
	}
	count, err := s.syncAwesomePrompts(ctx, prompts)
	if err != nil {
		return count, err
	}
	if err := s.store.DeletePromptsBySources(ctx, retiredPromptSources); err != nil {
		return count, err
	}
	return count, nil
}

// RefreshSource syncs a specific source.
func (s *Service) RefreshSource(ctx context.Context, source string) (int, error) {
	if source != awesomePromptsSource {
		return 0, fmt.Errorf("unknown source: %s", source)
	}
	return s.SyncAll(ctx)
}

// FetchAwesomePrompts fetches prompts by reading the upstream catalog config sources.
// Explicit direct JSON override remains available for tests and development.
func (s *Service) FetchAwesomePrompts(ctx context.Context) ([]AwesomePrompt, error) {
	if strings.TrimSpace(os.Getenv(awesomePromptsURLEnv)) != "" || s.preferSourceURLDirect {
		return s.fetchRemoteAwesomePrompts(ctx)
	}
	return s.fetchConfigSources(ctx)
}

func (s *Service) fetchRemoteAwesomePrompts(ctx context.Context) ([]AwesomePrompt, error) {
	sourceURL := s.sourceURL
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, sourceURL, nil)
	if err != nil {
		return nil, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("awesome_prompts: fetch: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("awesome_prompts: status %d", resp.StatusCode)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	return parseAwesomePrompts(body)
}

func (s *Service) syncAwesomePrompts(ctx context.Context, prompts []AwesomePrompt) (int, error) {
	var count int
	for _, prompt := range prompts {
		p := prompt.ToPrompt()
		if p == nil {
			continue
		}
		if err := s.store.UpsertPrompt(ctx, p); err != nil {
			continue
		}
		count++
	}
	return count, nil
}

// SourceStatus returns the status of each prompt source.
type SourceStatus struct {
	Source      string `json:"source"`
	Name        string `json:"name"`
	LastSync    string `json:"last_sync"`
	PromptCount int    `json:"prompt_count"`
	Enabled     bool   `json:"enabled"`
}

// GetSourceStatus returns the status of all prompt sources.
func (s *Service) GetSourceStatus(ctx context.Context) ([]SourceStatus, error) {
	count, err := s.store.CountPrompts(ctx, awesomePromptsSource, "")
	if err != nil {
		return nil, err
	}
	return []SourceStatus{{
		Source:      awesomePromptsSource,
		Name:        awesomePromptsName,
		PromptCount: count,
		Enabled:     true,
	}}, nil
}

// AwesomePrompt represents one prompt from Chat2AnyLLM/awesome-prompts.
type AwesomePrompt struct {
	Slug        string   `json:"slug"`
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Prompt      string   `json:"prompt"`
	Tags        []string `json:"tags"`
	Category    string   `json:"category"`
	Author      string   `json:"author"`
	Source      string   `json:"source,omitempty"`
	SourceURL   string   `json:"source_url,omitempty"`
}

func (p AwesomePrompt) ToPrompt() *Prompt {
	slug := strings.TrimSpace(p.Slug)
	title := strings.TrimSpace(p.Title)
	content := strings.TrimSpace(p.Prompt)
	if slug == "" || title == "" || content == "" {
		return nil
	}
	source := strings.TrimSpace(p.Source)
	if source == "" {
		source = awesomePromptsSource
	}
	sourceURL := strings.TrimSpace(p.SourceURL)
	if sourceURL == "" {
		sourceURL = fmt.Sprintf("%s/%s.yaml", awesomePromptsRepoURL, slug)
	}
	return &Prompt{
		Source:      source,
		SourceURL:   sourceURL,
		Category:    strings.TrimSpace(p.Category),
		Title:       title,
		Description: strings.TrimSpace(p.Description),
		Content:     content,
		Author:      strings.TrimSpace(p.Author),
		Tags:        strings.Join(p.Tags, ", "),
	}
}

type awesomePromptsLibrary struct {
	Prompts []AwesomePrompt `json:"prompts"`
}

func parseAwesomePrompts(data []byte) ([]AwesomePrompt, error) {
	var lib awesomePromptsLibrary
	if err := json.Unmarshal(data, &lib); err != nil {
		return nil, fmt.Errorf("awesome_prompts: parse: %w", err)
	}
	return lib.Prompts, nil
}
