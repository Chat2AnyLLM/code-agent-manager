package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/spf13/cobra"
)

func (a *App) mcpCommand(state *globalState) *cobra.Command {
	cmd := &cobra.Command{Use: "mcp", Aliases: []string{"m"}, Short: "Manage MCP servers"}
	cmd.AddCommand(&cobra.Command{Use: "list", Short: "List MCP servers", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		store, err := loadMCPStore(state.storePath)
		if err != nil {
			return err
		}
		if len(store.Servers) == 0 {
			fmt.Fprintln(cmd.OutOrStdout(), "No MCP servers installed")
			return nil
		}
		names := make([]string, 0, len(store.Servers))
		for name := range store.Servers {
			names = append(names, name)
		}
		sort.Strings(names)
		for _, name := range names {
			server := store.Servers[name]
			fmt.Fprintf(cmd.OutOrStdout(), "%s\t%s\t%v\n", name, server.Command, server.Args)
		}
		return nil
	}})
	var command string
	var serverArgs []string
	add := &cobra.Command{Use: "add NAME", Short: "Add MCP server", Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		if command == "" {
			return fmt.Errorf("--command is required")
		}
		store, err := loadMCPStore(state.storePath)
		if err != nil {
			return err
		}
		if store.Servers == nil {
			store.Servers = map[string]mcpServer{}
		}
		store.Servers[args[0]] = mcpServer{Command: command, Args: serverArgs}
		if err := writeMCPStore(state.storePath, store); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Added %s\n", args[0])
		return nil
	}}
	add.Flags().StringVar(&command, "command", "", "Server command")
	add.Flags().StringArrayVar(&serverArgs, "arg", nil, "Server command argument")
	cmd.AddCommand(add)
	cmd.AddCommand(&cobra.Command{Use: "remove NAME", Aliases: []string{"delete"}, Short: "Remove MCP server", Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		store, err := loadMCPStore(state.storePath)
		if err != nil {
			return err
		}
		delete(store.Servers, args[0])
		if err := writeMCPStore(state.storePath, store); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Removed %s\n", args[0])
		return nil
	}})
	server := &cobra.Command{Use: "server", Short: "Manage MCP server registry"}
	server.AddCommand(&cobra.Command{Use: "list", Short: "List registry servers", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		return cmd.Parent().Parent().Commands()[0].RunE(cmd, args)
	}})
	cmd.AddCommand(server)
	return cmd
}

type mcpStore struct {
	Servers map[string]mcpServer `json:"servers"`
}

type mcpServer struct {
	Command string   `json:"command"`
	Args    []string `json:"args,omitempty"`
}

func resolveMCPStorePath(path string) string {
	if path != "" {
		return path
	}
	return filepath.Join(os.Getenv("HOME"), ".config", "code-agent-manager", "mcp.json")
}

func loadMCPStore(path string) (mcpStore, error) {
	path = resolveMCPStorePath(path)
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return mcpStore{Servers: map[string]mcpServer{}}, nil
	}
	if err != nil {
		return mcpStore{}, err
	}
	store := mcpStore{Servers: map[string]mcpServer{}}
	if err := json.Unmarshal(data, &store); err != nil {
		return mcpStore{}, err
	}
	if store.Servers == nil {
		store.Servers = map[string]mcpServer{}
	}
	return store, nil
}

func writeMCPStore(path string, store mcpStore) error {
	path = resolveMCPStorePath(path)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(store, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}
