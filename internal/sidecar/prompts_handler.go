package sidecar

import (
	"encoding/json"
	"net/http"

	"github.com/chat2anyllm/code-agent-manager/internal/prompts"
)

// handlePrompts handles GET /api/prompts and POST /api/prompts.
func (s *Server) handlePrompts(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.handleListPrompts(w, r)
	case http.MethodPost:
		s.handleCreatePrompt(w, r)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleListPrompts(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	store := prompts.NewStore()

	source := r.URL.Query().Get("source")
	category := r.URL.Query().Get("category")

	promptList, err := store.ListPrompts(ctx, source, category)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(promptList)
}

func (s *Server) handleCreatePrompt(w http.ResponseWriter, r *http.Request) {
	var p prompts.Prompt
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	store := prompts.NewStore()
	if err := store.UpsertPrompt(r.Context(), &p); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(p)
}

// handlePromptsSearch handles GET /api/prompts/search.
func (s *Server) handlePromptsSearch(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	store := prompts.NewStore()

	q := r.URL.Query().Get("q")
	if q == "" {
		http.Error(w, "query parameter 'q' is required", http.StatusBadRequest)
		return
	}

	source := r.URL.Query().Get("source")
	promptList, err := store.SearchPrompts(ctx, q, source)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(promptList)
}

// handlePromptsSync handles POST /api/prompts/sync.
func (s *Server) handlePromptsSync(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	ctx := r.Context()
	svc := prompts.NewService()

	// Parse optional source parameter
	var req struct {
		Source string `json:"source"`
	}
	if r.Body != nil {
		_ = json.NewDecoder(r.Body).Decode(&req)
	}

	var count int
	var err error
	if req.Source != "" {
		count, err = svc.RefreshSource(ctx, req.Source)
	} else {
		count, err = svc.SyncAll(ctx)
	}

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"synced": count,
		"source": req.Source,
	})
}

// handlePromptsSources handles GET /api/prompts/sources.
func (s *Server) handlePromptsSources(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	svc := prompts.NewService()

	statuses, err := svc.GetSourceStatus(ctx)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(statuses)
}
