package desktop

import (
	"sort"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/mcp"
)

type MCPService struct{}

func NewMCPService() *MCPService { return &MCPService{} }

func (s *MCPService) ListClients() []MCPClientDTO {
	out := make([]MCPClientDTO, 0, len(mcp.SupportedClients))
	for _, client := range mcp.SupportedClients {
		out = append(out, MCPClientDTO{
			Name:         client.Name,
			UserPath:     client.UserPath,
			ProjectPath:  client.ProjectPath,
			Container:    client.Container,
			Format:       client.Format,
			SupportsUser: client.UserPath != "",
			SupportsProj: client.ProjectPath != "",
		})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

func (s *MCPService) ListInstalled(clientName, scope string) ([]MCPServerDTO, error) {
	client, ok := mcp.ClientByName(clientName)
	if !ok {
		return nil, NewError("MCP_CLIENT_NOT_FOUND", "unsupported MCP client", map[string]string{"client": clientName})
	}
	servers, path, err := mcp.ListServers(client, mcp.Scope(scope))
	if err != nil {
		return nil, wrapError("MCP_LIST_FAILED", err)
	}
	out := make([]MCPServerDTO, 0, len(servers))
	for _, server := range servers {
		out = append(out, mcpServerDTO(server, clientName, scope, path))
	}
	return out, nil
}

func (s *MCPService) Add(clientName, scope string, input MCPServerDTO) (OperationResult, error) {
	client, ok := mcp.ClientByName(clientName)
	if !ok {
		return OperationResult{}, NewError("MCP_CLIENT_NOT_FOUND", "unsupported MCP client", map[string]string{"client": clientName})
	}
	path, err := mcp.AddServer(client, mcp.Scope(scope), mcp.Server{
		Name: input.Name, Command: input.Command, Args: input.Args, Env: input.Env, URL: input.URL, Type: input.Type,
	})
	if err != nil {
		return OperationResult{}, wrapError("MCP_ADD_FAILED", err)
	}
	return OperationResult{OK: true, Message: "MCP server added", Path: path}, nil
}

func (s *MCPService) Remove(clientName, scope, name string) (OperationResult, error) {
	client, ok := mcp.ClientByName(clientName)
	if !ok {
		return OperationResult{}, NewError("MCP_CLIENT_NOT_FOUND", "unsupported MCP client", map[string]string{"client": clientName})
	}
	path, removed, err := mcp.RemoveServer(client, mcp.Scope(scope), name)
	if err != nil {
		return OperationResult{}, wrapError("MCP_REMOVE_FAILED", err)
	}
	if !removed {
		return OperationResult{}, NewError("MCP_SERVER_NOT_FOUND", "MCP server not found", map[string]string{"name": name})
	}
	return OperationResult{OK: true, Message: "MCP server removed", Path: path}, nil
}

func (s *MCPService) SearchRegistry(query string) ([]mcp.ServerSchema, error) {
	registry, err := mcp.LoadBundledRegistry()
	if err != nil {
		return nil, wrapError("MCP_REGISTRY_LOAD_FAILED", err)
	}
	return registry.Search(query), nil
}

func (s *MCPService) ShowServer(name string) (mcp.ServerSchema, error) {
	registry, err := mcp.LoadBundledRegistry()
	if err != nil {
		return mcp.ServerSchema{}, wrapError("MCP_REGISTRY_LOAD_FAILED", err)
	}
	schema, ok := registry.Get(name)
	if !ok {
		return mcp.ServerSchema{}, NewError("MCP_SERVER_SCHEMA_NOT_FOUND", "MCP registry server not found", map[string]string{"name": name})
	}
	return schema, nil
}

// ListRegistry returns the discovered (bundled) MCP servers, optionally filtered
// by query, each enriched with the clients it is already installed into at scope.
// Installed status is computed by reading each client's config once; clients that
// cannot be read (e.g. TOML configs via the JSON path, or missing files) are
// skipped rather than failing the whole listing.
func (s *MCPService) ListRegistry(query string, scope mcp.Scope) ([]MCPRegistryItemDTO, error) {
	registry, err := mcp.LoadBundledRegistry()
	if err != nil {
		return nil, wrapError("MCP_REGISTRY_LOAD_FAILED", err)
	}
	installedByClient := installedServerNames(scope)

	var schemas []mcp.ServerSchema
	if strings.TrimSpace(query) == "" {
		schemas = registry.All()
	} else {
		schemas = registry.Search(query)
	}

	out := make([]MCPRegistryItemDTO, 0, len(schemas))
	for _, schema := range schemas {
		item := MCPRegistryItemDTO{
			Name:        schema.Name,
			DisplayName: schema.DisplayName,
			Description: schema.Description,
			RepoURL:     schema.Repository.URL,
			Homepage:    schema.Homepage,
			License:     schema.License,
			Categories:  schema.Categories,
			Tags:        schema.Tags,
		}
		if key, _, ok := schema.PreferredInstallation(); ok {
			item.InstallType = key
		}
		// Build installed-clients in stable (alphabetical) order.
		for _, clientName := range sortedClientNames() {
			if installedByClient[clientName][schema.Name] {
				item.InstalledClients = append(item.InstalledClients, clientName)
			}
		}
		out = append(out, item)
	}
	return out, nil
}

// InstallFromRegistry writes a registry server into a client's config at scope,
// choosing the schema's preferred installation method. It reuses the same
// ServerFromSchema + AddServer path the CLI uses.
func (s *MCPService) InstallFromRegistry(clientName, scope, serverName string) (OperationResult, error) {
	client, ok := mcp.ClientByName(clientName)
	if !ok {
		return OperationResult{}, NewError("MCP_CLIENT_NOT_FOUND", "unsupported MCP client", map[string]string{"client": clientName})
	}
	registry, err := mcp.LoadBundledRegistry()
	if err != nil {
		return OperationResult{}, wrapError("MCP_REGISTRY_LOAD_FAILED", err)
	}
	schema, ok := registry.Get(serverName)
	if !ok {
		return OperationResult{}, NewError("MCP_SERVER_SCHEMA_NOT_FOUND", "MCP registry server not found", map[string]string{"name": serverName})
	}
	server, err := mcp.ServerFromSchema(schema)
	if err != nil {
		return OperationResult{}, wrapError("MCP_INSTALL_FAILED", err)
	}
	path, err := mcp.AddServer(client, mcp.Scope(scope), server)
	if err != nil {
		return OperationResult{}, wrapError("MCP_ADD_FAILED", err)
	}
	return OperationResult{OK: true, Message: "MCP server installed", Path: path}, nil
}

// installedServerNames returns, for each supported client, the set of installed
// server names at scope. Clients whose config cannot be parsed (e.g. codex's
// TOML via the JSON path, or missing files) contribute an empty set instead of
// failing the listing.
func installedServerNames(scope mcp.Scope) map[string]map[string]bool {
	out := map[string]map[string]bool{}
	for _, client := range mcp.SupportedClients {
		names := map[string]bool{}
		if servers, _, err := mcp.ListServers(client, scope); err == nil {
			for _, server := range servers {
				names[server.Name] = true
			}
		}
		out[client.Name] = names
	}
	return out
}

func sortedClientNames() []string {
	names := mcp.ClientNames()
	out := make([]string, len(names))
	copy(out, names)
	return out
}

func mcpServerDTO(server mcp.Server, client, scope, path string) MCPServerDTO {
	return MCPServerDTO{
		Name: server.Name, Client: client, Scope: scope, Path: path, Command: server.Command,
		Args: server.Args, Env: server.Env, URL: server.URL, Type: server.Type,
	}
}
