package sidecar

import (
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
	summary, err := svc.RefreshAll(r.Context())
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

	resp, err := svc.SearchPaged(r.Context(), metadata.SearchQuery{
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
	switch input.Kind {
	case "skill", "agent", "instruction", "plugin":
		// valid
	default:
		writeError(w, http.StatusBadRequest, "invalid kind: must be skill, agent, instruction, or plugin")
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
		err := svc.InstallInstructionToTargets(r.Context(), input.InstallKey, targets, level, input.ProjectDir)
		writeResult(w, map[string]any{"status": "installed", "install_key": input.InstallKey, "targets": targets, "level": level, "project_dir": input.ProjectDir}, err)
		return
	}
	err := svc.InstallToTargets(r.Context(), input.Kind, input.InstallKey, targets)
	writeResult(w, map[string]any{"status": "installed", "install_key": input.InstallKey, "targets": targets}, err)
}

// handleMetadataUninstall removes an entity from the specified apps and clears
// the installed status in the metadata store.
func (s *Server) handleMetadataUninstall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Kind       string   `json:"kind"`
		InstallKey string   `json:"install_key"`
		TargetApps []string `json:"target_apps"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if input.Kind == "" {
		writeError(w, http.StatusBadRequest, "kind is required")
		return
	}
	switch input.Kind {
	case "skill", "agent", "instruction", "plugin":
		// valid
	default:
		writeError(w, http.StatusBadRequest, "invalid kind: must be skill, agent, instruction, or plugin")
		return
	}
	if input.InstallKey == "" {
		writeError(w, http.StatusBadRequest, "install_key is required")
		return
	}
	targets := input.TargetApps
	if len(targets) == 0 {
		writeError(w, http.StatusBadRequest, "no target agents specified")
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	err := svc.UninstallFromTargets(r.Context(), input.Kind, input.InstallKey, targets)
	writeResult(w, map[string]any{"status": "uninstalled", "install_key": input.InstallKey, "targets": targets}, err)
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
// user expands a card. When the "force" query parameter is "true", the cache
// is bypassed and the manifest is always re-fetched from source.
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
	force := r.URL.Query().Get("force") == "true"
	var detail metadata.ItemDetail
	var err error
	if force {
		detail, err = svc.DetailForceRefresh(r.Context(), kind, installKey)
	} else {
		detail, err = svc.Detail(r.Context(), kind, installKey)
	}
	writeResult(w, detail, err)
}

// handleMetadataRefreshItem re-fetches a single item's manifest content from
// its source repository, updates the description if it has changed, and saves
// the content to the database cache. Returns the refreshed detail view.
func (s *Server) handleMetadataRefreshItem(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Kind       string `json:"kind"`
		InstallKey string `json:"install_key"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if input.Kind == "" || input.InstallKey == "" {
		writeError(w, http.StatusBadRequest, "kind and install_key are required")
		return
	}
	if input.Kind == "prompt" {
		writeError(w, http.StatusBadRequest, "kind 'prompt' has been renamed to 'instruction'; use kind=instruction")
		return
	}
	store := metadata.NewStore("")
	svc := metadata.NewService(store)
	detail, err := svc.RefreshItem(r.Context(), input.Kind, input.InstallKey)
	writeResult(w, detail, err)
}
