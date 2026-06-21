package prompts

import (
	"context"
	"encoding/csv"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

// Service handles fetching and syncing prompts from external sources.
type Service struct {
	store  *Store
	client *http.Client
}

// NewService creates a new prompts service.
func NewService() *Service {
	return &Service{
		store: NewStore(),
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Store returns the underlying store.
func (s *Service) Store() *Store {
	return s.store
}

// SyncAll fetches prompts from all configured sources.
func (s *Service) SyncAll(ctx context.Context) (added int, err error) {
	n1, e1 := s.syncPromptsChat(ctx)
	if e1 != nil {
		err = e1
	}
	added += n1

	n2, e2 := s.syncPromptingGuide(ctx)
	if e2 != nil {
		err = e2
	}
	added += n2
	return added, err
}

// syncPromptsChat fetches prompts from f/prompts.chat GitHub repo (prompts.csv).
func (s *Service) syncPromptsChat(ctx context.Context) (int, error) {
	url := "https://raw.githubusercontent.com/f/prompts.chat/main/prompts.csv"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("prompts.chat: fetch: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("prompts.chat: status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	reader := csv.NewReader(strings.NewReader(string(body)))
	records, err := reader.ReadAll()
	if err != nil {
		return 0, fmt.Errorf("prompts.chat: parse csv: %w", err)
	}

	var count int
	for i, record := range records {
		if i == 0 {
			continue // skip header
		}
		if len(record) < 4 {
			continue
		}
		// CSV columns: act, prompt, description, tags
		act := strings.TrimSpace(record[0])
		prompt := strings.TrimSpace(record[1])
		description := strings.TrimSpace(record[2])
		tags := strings.TrimSpace(record[3])

		if act == "" || prompt == "" {
			continue
		}

		p := &Prompt{
			Source:      "prompts_chat",
			SourceURL:   fmt.Sprintf("https://prompts.chat/prompts#%s", strings.ToLower(strings.ReplaceAll(act, " ", "-"))),
			Category:    categorizePrompt(tags, description),
			Title:       act,
			Description: description,
			Content:     prompt,
			Author:      "community",
			Tags:        tags,
		}
		if err := s.store.UpsertPrompt(ctx, p); err != nil {
			continue
		}
		count++
	}
	return count, nil
}

// syncPromptingGuide fetches prompts from dair-ai/Prompt-Engineering-Guide.
func (s *Service) syncPromptingGuide(ctx context.Context) (int, error) {
	// Fetch the examples page content
	url := "https://raw.githubusercontent.com/dair-ai/Prompt-Engineering-Guide/main/guides/prompts-basic-usage.md"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, err
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("promptingguide: fetch: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("promptingguide: status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	// Parse prompts from markdown
	prompts := parsePromptsFromMarkdown(string(body))
	var count int
	for _, p := range prompts {
		p.Source = "promptingguide"
		p.SourceURL = "https://www.promptingguide.ai/introduction/examples"
		p.Author = "DAIR.AI"
		if err := s.store.UpsertPrompt(ctx, p); err != nil {
			continue
		}
		count++
	}
	return count, nil
}

// parsePromptsFromMarkdown extracts prompts from markdown content.
func parsePromptsFromMarkdown(content string) []*Prompt {
	var prompts []*Prompt

	// Split by headers
	sections := regexp.MustCompile(`(?m)^## `).Split(content, -1)

	for _, section := range sections {
		lines := strings.Split(section, "\n")
		if len(lines) == 0 {
			continue
		}

		title := strings.TrimSpace(lines[0])
		if title == "" || strings.HasPrefix(title, "#") {
			continue
		}

		// Look for prompt blocks (indented text or code blocks)
		var promptLines []string
		inPrompt := false
		for _, line := range lines[1:] {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "Prompt:") || strings.HasPrefix(trimmed, "*Prompt:*") {
				inPrompt = true
				continue
			}
			if inPrompt {
				if trimmed == "" || strings.HasPrefix(trimmed, "*") || strings.HasPrefix(trimmed, "Here") {
					if len(promptLines) > 0 {
						break
				}
				} else {
					promptLines = append(promptLines, line)
				}
			}
		}

		if len(promptLines) > 0 {
			prompts = append(prompts, &Prompt{
				Category:    categorizePrompt("", title),
				Title:       title,
				Description: title,
				Content:     strings.Join(promptLines, "\n"),
			})
		}
	}
	return prompts
}

// categorizePrompt determines the category based on tags and description.
func categorizePrompt(tags, description string) string {
	combined := strings.ToLower(tags + " " + description)

	switch {
	case strings.Contains(combined, "code") || strings.Contains(combined, "programming") || strings.Contains(combined, "developer"):
		return "coding"
	case strings.Contains(combined, "write") || strings.Contains(combined, "creative") || strings.Contains(combined, "story"):
		return "writing"
	case strings.Contains(combined, "analyz") || strings.Contains(combined, "research") || strings.Contains(combined, "summariz"):
		return "analysis"
	case strings.Contains(combined, "learn") || strings.Contains(combined, "teach") || strings.Contains(combined, "explain"):
		return "education"
	case strings.Contains(combined, "business") || strings.Contains(combined, "market") || strings.Contains(combined, "plan"):
		return "business"
	case strings.Contains(combined, "image") || strings.Contains(combined, "photo") || strings.Contains(combined, "art"):
		return "creative"
	case strings.Contains(combined, "math") || strings.Contains(combined, "logic") || strings.Contains(combined, "reason"):
		return "reasoning"
	default:
		return "general"
	}
}

// ClaudePrompt represents a prompt from the Claude prompt library.
type ClaudePrompt struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Content     string `json:"content"`
	Category    string `json:"category"`
}

// FetchClaudePrompts fetches prompts from the Claude prompt library.
// This is a placeholder that returns known prompts since the library is behind auth.
func (s *Service) FetchClaudePrompts(ctx context.Context) ([]*ClaudePrompt, error) {
	// The Claude prompt library requires authentication, so we return known prompts
	// These are from the public documentation
	prompts := []*ClaudePrompt{
		{Name: "Citation Finder", Description: "Extract citations from text", Category: "analysis"},
		{Name: "Code Debugger", Description: "Help debug code issues", Category: "coding"},
		{Name: "Content Summarizer", Description: "Summarize long content", Category: "analysis"},
		{Name: "Data Extractor", Description: "Extract structured data", Category: "coding"},
		{Name: "Email Writer", Description: "Write professional emails", Category: "writing"},
		{Name: "Essay Outliner", Description: "Create essay outlines", Category: "writing"},
		{Name: "SQL Query Builder", Description: "Generate SQL queries", Category: "coding"},
		{Name: "Translation Assistant", Description: "Translate text between languages", Category: "writing"},
		{Name: "JSON Converter", Description: "Convert data to JSON", Category: "coding"},
		{Name: "Meeting Summarizer", Description: "Summarize meeting notes", Category: "analysis"},
	}
	return prompts, nil
}

// RefreshSource syncs a specific source.
func (s *Service) RefreshSource(ctx context.Context, source string) (int, error) {
	switch source {
	case "prompts_chat":
		return s.syncPromptsChat(ctx)
	case "promptingguide":
		return s.syncPromptingGuide(ctx)
	case "claude":
		// For Claude, we use the known prompts
		prompts, err := s.FetchClaudePrompts(ctx)
		if err != nil {
			return 0, err
		}
		var count int
		for _, cp := range prompts {
			p := &Prompt{
				Source:      "claude",
				SourceURL:   fmt.Sprintf("https://platform.claude.com/docs/en/resources/prompt-library/library#%s", strings.ToLower(strings.ReplaceAll(cp.Name, " ", "-"))),
				Category:    cp.Category,
				Title:       cp.Name,
				Description: cp.Description,
				Content:     cp.Content,
				Author:      "Anthropic",
				Tags:        cp.Category,
			}
			if err := s.store.UpsertPrompt(ctx, p); err != nil {
				continue
			}
			count++
		}
		return count, nil
	default:
		return 0, fmt.Errorf("unknown source: %s", source)
	}
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
	sources := []string{"claude", "prompts_chat", "promptingguide"}
	var statuses []SourceStatus

	for _, source := range sources {
		count, _ := s.store.CountPrompts(ctx, source, "")
		statuses = append(statuses, SourceStatus{
			Source:      source,
			Name:        sourceDisplayName(source),
			PromptCount: count,
			Enabled:     true,
		})
	}
	return statuses, nil
}

func sourceDisplayName(source string) string {
	switch source {
	case "claude":
		return "Claude Prompt Library"
	case "prompts_chat":
		return "prompts.chat"
	case "promptingguide":
		return "Prompt Engineering Guide"
	default:
		return source
	}
}
