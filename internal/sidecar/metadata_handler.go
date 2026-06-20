package sidecar

import (
	"context"
	"net/http"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
	"github.com/chat2anyllm/code-agent-manager/internal/metadata"
)

func (s *Server) handleMetadataRefresh(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	summary, err := svc.RefreshAll(context.Background())
	writeResult(w, summary, err)
}

func (s *Server) handleMetadataSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	q := r.URL.Query().Get("q")
	kind := r.URL.Query().Get("type")
	if kind == "prompt" {
		writeError(w, http.StatusBadRequest, "kind 'prompt' has been renamed to 'instruction'; use type=instruction")
		return
	}
	limit := atoiDefault(r.URL.Query().Get("limit"), 50)
	offset := atoiDefault(r.URL.Query().Get("offset"), 0)

	resp, err := svc.SearchPaged(context.Background(), metadata.SearchQuery{
		Query:  q,
		Kind:   kind,
		Limit:  limit,
		Offset: offset,
	})
	writeResult(w, resp, err)
}

func atoiDefault(s string, def int) int {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return def
		}
		n = n*10 + int(c-'0')
	}
	if s == "" {
		return def
	}
	return n
}

func (s *Server) handleMetadataInstall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Kind       string   `json:"kind"`
		InstallKey string   `json:"install_key"`
		TargetApp  string   `json:"target_app"`
		TargetApps []string `json:"target_apps"`
		Level      string   `json:"level,omitempty"`
		ProjectDir string   `json:"project_dir,omitempty"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if input.Kind == "prompt" {
		writeError(w, http.StatusBadRequest, "kind 'prompt' has been renamed to 'instruction'; use kind=instruction")
		return
	}
	targets := input.TargetApps
	if len(targets) == 0 && input.TargetApp != "" {
		targets = []string{input.TargetApp}
	}
	if len(targets) == 0 {
		writeError(w, http.StatusBadRequest, "no target agents specified")
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	if input.Kind == "instruction" {
		level := entities.InstallLevel(input.Level)
		if level == "" {
			level = entities.InstallLevelUser
		}
		if level == entities.InstallLevelProject && input.ProjectDir == "" {
			writeError(w, http.StatusBadRequest, "project_dir is required for project-level instruction install")
			return
		}
		err := svc.InstallInstructionToTargets(context.Background(), input.InstallKey, targets, level, input.ProjectDir)
		writeResult(w, map[string]any{"status": "installed", "install_key": input.InstallKey, "targets": targets, "level": level, "project_dir": input.ProjectDir}, err)
		return
	}
	err := svc.InstallToTargets(context.Background(), input.Kind, input.InstallKey, targets)
	writeResult(w, map[string]any{"status": "installed", "install_key": input.InstallKey, "targets": targets}, err)
}

func (s *Server) handleMetadataTargets(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	kind := r.URL.Query().Get("kind")
	if kind == "" {
		kind = "instruction"
	}
	if kind == "prompt" {
		writeError(w, http.StatusBadRequest, "kind 'prompt' has been renamed to 'instruction'; use kind=instruction")
		return
	}
	writeJSON(w, metadata.AvailableTargets(kind))
}

// handleMetadataDetail returns the full detail view (indexed metadata plus the
// on-demand manifest content) for a single item identified by kind and
// install_key. The manifest fetch is a live network call, so this endpoint is
// intentionally separate from search: the UI calls it lazily, only when the
// user expands a card.
func (s *Server) handleMetadataDetail(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	kind := r.URL.Query().Get("kind")
	installKey := r.URL.Query().Get("install_key")
	if kind == "" || installKey == "" {
		writeError(w, http.StatusBadRequest, "kind and install_key are required")
		return
	}
	if kind == "prompt" {
		writeError(w, http.StatusBadRequest, "kind 'prompt' has been renamed to 'instruction'; use kind=instruction")
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	detail, err := svc.Detail(r.Context(), kind, installKey)
	writeResult(w, detail, err)
}
