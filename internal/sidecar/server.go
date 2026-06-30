package sidecar

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/desktop"
	"github.com/chat2anyllm/code-agent-manager/internal/mcp"
)

// Server exposes CAM app operations over a localhost-only HTTP API for Tauri.
type Server struct {
	version  string
	token    string
	services desktop.Services
}

// Options configures the sidecar HTTP server.
type Options struct {
	Version string
	Token   string
}

// Startup describes the selected listen address after the server starts.
type Startup struct {
	Host  string `json:"host"`
	Port  int    `json:"port"`
	Token string `json:"token,omitempty"`
}

// New constructs a sidecar server.
func New(opts Options) *Server {
	version := opts.Version
	if version == "" {
		version = "dev"
	}
	return &Server{
		version:  version,
		token:    opts.Token,
		services: desktop.NewServices(version, ""),
	}
}

// Handler returns the sidecar HTTP handler.
func (s *Server) Handler() http.Handler {
	return s.withMiddleware(s.routes())
}

func (s *Server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/app/version", s.handleVersion)
	mux.HandleFunc("/api/providers", s.handleProviders)
	mux.HandleFunc("/api/providers/", s.handleProvider)
	mux.HandleFunc("/api/tools", s.handleTools)
	mux.HandleFunc("/api/tools/", s.handleToolAction)
	mux.HandleFunc("/api/mcp/clients", s.handleMCPClients)
	mux.HandleFunc("/api/mcp/servers", s.handleMCPServers)
	mux.HandleFunc("/api/mcp/registry", s.handleMCPRegistry)
	mux.HandleFunc("/api/mcp/install", s.handleMCPInstall)
	mux.HandleFunc("/api/mcp/uninstall", s.handleMCPUninstall)
	mux.HandleFunc("/api/entities", s.handleEntities)
	mux.HandleFunc("/api/entities/uninstall", s.handleEntityUninstall)
	mux.HandleFunc("/api/instructions", s.handleInstructions)
	mux.HandleFunc("/api/instructions/", s.handleInstructionsSub)
	mux.HandleFunc("/api/metadata/refresh", s.handleMetadataRefresh)
	mux.HandleFunc("/api/metadata/search", s.handleMetadataSearch)
	mux.HandleFunc("/api/metadata/install", s.handleMetadataInstall)
	mux.HandleFunc("/api/metadata/uninstall", s.handleMetadataUninstall)
	mux.HandleFunc("/api/metadata/targets", s.handleMetadataTargets)
	mux.HandleFunc("/api/metadata/detail", s.handleMetadataDetail)
	mux.HandleFunc("/api/metadata/refresh-item", s.handleMetadataRefreshItem)
	mux.HandleFunc("/api/config/files", s.handleConfigFiles)
	mux.HandleFunc("/api/doctor/checks", s.handleDoctorChecks)
	mux.HandleFunc("/api/launch/dry-run", s.handleLaunchDryRun)
	mux.HandleFunc("/api/launch/apply", s.handleLaunchApply)
	mux.HandleFunc("/api/prompts", s.handlePrompts)
	mux.HandleFunc("/api/prompts/search", s.handlePromptsSearch)
	mux.HandleFunc("/api/prompts/sync", s.handlePromptsSync)
	mux.HandleFunc("/api/prompts/sources", s.handlePromptsSources)
	return mux
}

// ListenAndServe starts the HTTP server on host:port. Use port 0 for a random port.
func (s *Server) ListenAndServe(ctx context.Context, host string, port int) (Startup, error) {
	if host == "" {
		host = "127.0.0.1"
	}
	listener, err := net.Listen("tcp", fmt.Sprintf("%s:%d", host, port))
	if err != nil {
		return Startup{}, err
	}
	actual := listener.Addr().(*net.TCPAddr)
	startup := Startup{Host: host, Port: actual.Port, Token: s.token}
	server := &http.Server{Handler: s.withMiddlewareForHost(s.routes(), actual.Port)}
	go func() {
		<-ctx.Done()
		_ = server.Shutdown(context.Background())
	}()
	go func() {
		if err := server.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Printf("sidecar: serve error: %v", err)
		}
	}()
	return startup, nil
}

func (s *Server) withMiddleware(next http.Handler) http.Handler {
	return s.withMiddlewareForHost(next, 0)
}

func (s *Server) withMiddlewareForHost(next http.Handler, port int) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !isAllowedHost(r.Host, port) {
			writeError(w, http.StatusForbidden, "forbidden")
			return
		}
		origin := r.Header.Get("Origin")
		if origin == "tauri://localhost" || strings.HasPrefix(origin, "http://127.0.0.1:") || strings.HasPrefix(origin, "http://localhost:") {
			w.Header().Set("Access-Control-Allow-Origin", origin)
		}
		w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		if s.token != "" && r.Header.Get("Authorization") != "Bearer "+s.token {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) handleVersion(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	writeJSON(w, map[string]string{"version": s.services.App.Version(), "platform": s.services.App.Platform()})
}

func (s *Server) handleProviders(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		providers, err := s.services.Providers.List()
		writeResult(w, providers, err)
	case http.MethodPost:
		var input desktop.ProviderInput
		if err := decodeJSON(r, &input); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		provider, err := s.services.Providers.Add(input)
		writeResult(w, provider, err)
	default:
		methodNotAllowed(w)
	}
}

func (s *Server) handleProvider(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/providers/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		writeError(w, http.StatusNotFound, "provider not found")
		return
	}
	name := parts[0]
	action := ""
	if len(parts) > 1 {
		action = parts[1]
	}

	if action != "" {
		s.handleProviderAction(w, r, name, action)
		return
	}

	switch r.Method {
	case http.MethodGet:
		provider, err := s.services.Providers.Show(name)
		writeResult(w, provider, err)
	case http.MethodPatch:
		var input desktop.ProviderInput
		if err := decodeJSON(r, &input); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		provider, err := s.services.Providers.Update(name, input)
		writeResult(w, provider, err)
	case http.MethodDelete:
		result, err := s.services.Providers.Remove(name)
		writeResult(w, result, err)
	default:
		methodNotAllowed(w)
	}
}

func (s *Server) handleProviderAction(w http.ResponseWriter, r *http.Request, name, action string) {
	if r.Method != http.MethodPost && action != "models" {
		methodNotAllowed(w)
		return
	}
	switch action {
	case "enable":
		provider, err := s.services.Providers.Enable(name)
		writeResult(w, provider, err)
	case "disable":
		provider, err := s.services.Providers.Disable(name)
		writeResult(w, provider, err)
	case "rename":
		var input struct {
			NewName string `json:"newName"`
		}
		if err := decodeJSON(r, &input); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		provider, err := s.services.Providers.Rename(name, input.NewName)
		writeResult(w, provider, err)
	case "models":
		if r.Method != http.MethodGet {
			methodNotAllowed(w)
			return
		}
		models, err := s.services.Providers.ResolveModels(name)
		writeResult(w, models, err)
	default:
		writeError(w, http.StatusNotFound, "unknown provider action")
	}
}

func (s *Server) handleTools(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	tools, err := s.services.Tools.List()
	writeResult(w, tools, err)
}

func (s *Server) handleToolAction(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/tools/"), "/")
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		writeError(w, http.StatusNotFound, "tool action not found")
		return
	}
	name, action := parts[0], parts[1]
	var input struct {
		DryRun bool `json:"dryRun"`
	}
	if r.Body != nil && r.ContentLength != 0 {
		if err := decodeJSON(r, &input); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
	}
	var result desktop.OperationResult
	var err error
	switch action {
	case "install":
		result, err = s.services.Tools.Install(name, input.DryRun)
	case "upgrade":
		result, err = s.services.Tools.Upgrade(name, input.DryRun)
	default:
		writeError(w, http.StatusNotFound, "unknown tool action")
		return
	}
	if err != nil {
		writeResult(w, nil, err)
		return
	}
	tool, err := s.services.Tools.Detect(name)
	writeResult(w, desktop.ToolOperationDTO{Result: result, Tool: tool}, err)
}

func (s *Server) handleMCPClients(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	writeJSON(w, s.services.MCP.ListClients())
}

func (s *Server) handleMCPServers(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	client := queryDefault(r, "client", "claude")
	scope := queryDefault(r, "scope", "user")
	servers, err := s.services.MCP.ListInstalled(client, scope)
	writeResult(w, servers, err)
}

// handleMCPRegistry lists the discovered (bundled) MCP servers, optionally
// filtered by a query, each enriched with the clients it is installed into.
func (s *Server) handleMCPRegistry(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	query := r.URL.Query().Get("q")
	scope := mcp.Scope(queryDefault(r, "scope", "user"))
	items, err := s.services.MCP.ListRegistry(query, scope)
	writeResult(w, items, err)
}

// handleMCPInstall installs a registry server into one or more clients at a
// scope, mirroring the metadata install endpoint's multi-target shape.
func (s *Server) handleMCPInstall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Server  string   `json:"server"`
		Clients []string `json:"clients"`
		Client  string   `json:"client"`
		Scope   string   `json:"scope"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	clients := input.Clients
	if len(clients) == 0 && input.Client != "" {
		clients = []string{input.Client}
	}
	if len(clients) == 0 {
		writeError(w, http.StatusBadRequest, "no target clients specified")
		return
	}
	if input.Server == "" {
		writeError(w, http.StatusBadRequest, "server is required")
		return
	}
	scope := input.Scope
	if scope == "" {
		scope = "user"
	}
	for _, clientName := range clients {
		if _, err := s.services.MCP.InstallFromRegistry(clientName, scope, input.Server); err != nil {
			writeResult(w, nil, err)
			return
		}
	}
	writeJSON(w, map[string]any{"status": "installed", "server": input.Server, "clients": clients})
}

// handleMCPUninstall removes an MCP server from one or more clients.
func (s *Server) handleMCPUninstall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Server  string   `json:"server"`
		Clients []string `json:"clients"`
		Client  string   `json:"client"`
		Scope   string   `json:"scope"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	clients := input.Clients
	if len(clients) == 0 && input.Client != "" {
		clients = []string{input.Client}
	}
	if len(clients) == 0 {
		writeError(w, http.StatusBadRequest, "no target clients specified")
		return
	}
	if input.Server == "" {
		writeError(w, http.StatusBadRequest, "server is required")
		return
	}
	scope := input.Scope
	if scope == "" {
		scope = "user"
	}
	for _, clientName := range clients {
		if _, err := s.services.MCP.Remove(clientName, scope, input.Server); err != nil {
			writeResult(w, nil, err)
			return
		}
	}
	writeJSON(w, map[string]any{"status": "removed", "server": input.Server, "clients": clients})
}

func (s *Server) handleEntities(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	kind := queryDefault(r, "kind", "skill")
	query := r.URL.Query().Get("query")
	if query != "" {
		entities, err := s.services.Entities.Search(kind, query)
		writeResult(w, entities, err)
		return
	}
	entities, err := s.services.Entities.List(kind)
	writeResult(w, entities, err)
}

// handleEntityUninstall removes an entity (skill/agent/plugin) from the
// registry and its installed filesystem locations.
func (s *Server) handleEntityUninstall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var input struct {
		Kind string `json:"kind"`
		Name string `json:"name"`
	}
	if err := decodeJSON(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if input.Kind == "" {
		writeError(w, http.StatusBadRequest, "kind is required")
		return
	}
	if input.Name == "" {
		writeError(w, http.StatusBadRequest, "name is required")
		return
	}
	result, err := s.services.Entities.Uninstall(input.Kind, input.Name)
	if err != nil {
		writeResult(w, nil, err)
		return
	}
	writeJSON(w, result)
}

func (s *Server) handleConfigFiles(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	writeJSON(w, s.services.Config.ListFiles())
}

func (s *Server) handleDoctorChecks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	checks, err := s.services.Doctor.RunChecks(r.Context())
	writeResult(w, checks, err)
}

func (s *Server) handleLaunchDryRun(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	input := struct {
		Tool     string   `json:"tool"`
		Provider string   `json:"provider"`
		Model    string   `json:"model"`
		Args     []string `json:"args"`
	}{
		Tool:     r.URL.Query().Get("tool"),
		Provider: r.URL.Query().Get("provider"),
		Model:    r.URL.Query().Get("model"),
	}
	if r.Method == http.MethodPost && r.Body != nil {
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}
	plan, err := s.services.Launch.DryRun(input.Tool, input.Provider, input.Model, input.Args)
	writeResult(w, plan, err)
}

func (s *Server) handleLaunchApply(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	input := struct {
		Tool     string `json:"tool"`
		Provider string `json:"provider"`
		Model    string `json:"model"`
	}{}
	if r.Body != nil {
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}
	result, err := s.services.Launch.ApplyConfig(input.Tool, input.Provider, input.Model)
	writeResult(w, result, err)
}

func queryDefault(r *http.Request, key, fallback string) string {
	value := r.URL.Query().Get(key)
	if value == "" {
		return fallback
	}
	return value
}

func decodeJSON(r *http.Request, out any) error {
	r.Body = http.MaxBytesReader(nil, r.Body, 1<<20)
	defer r.Body.Close()
	return json.NewDecoder(r.Body).Decode(out)
}

func isAllowedHost(host string, port int) bool {
	if host == "" {
		return false
	}
	if port > 0 {
		allowed := []string{fmt.Sprintf("127.0.0.1:%d", port), fmt.Sprintf("localhost:%d", port), fmt.Sprintf("[::1]:%d", port)}
		for _, candidate := range allowed {
			if host == candidate {
				return true
			}
		}
		return false
	}
	// port == 0: handler is being used outside ListenAndServe (e.g. tests or
	// embedded use). Skip strict port-matching; accept any host. Production
	// callers must use ListenAndServe so a real port is passed.
	return true
}

func writeResult(w http.ResponseWriter, value any, err error) {
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, value)
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}

// writeJSONStatus writes value as JSON with an explicit status code.
func writeJSONStatus(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"error": message})
}

func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}
