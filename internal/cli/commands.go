package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

var knownTools = []string{
	"blackbox", "claude", "codebuddy", "codex", "continue", "copilot", "crush", "droid", "gemini", "goose", "iflow", "kimi", "neovate", "opencode", "qodercli", "qwen", "zed",
}

func (a *App) launchCommand(state *globalState) *cobra.Command {
	var dryRun bool
	cmd := &cobra.Command{
		Use:     "launch [TOOL] [-- ARGS...]",
		Aliases: []string{"l"},
		Short:   "Launch interactive TUI or a specific assistant",
		Args:    cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				fmt.Fprintln(cmd.OutOrStdout(), "Available tools:")
				for _, tool := range knownTools {
					fmt.Fprintf(cmd.OutOrStdout(), "  %s\n", tool)
				}
				return nil
			}
			tool := args[0]
			if !isKnownTool(tool) {
				return fmt.Errorf("Unknown tool: %s", tool)
			}
			if !dryRun {
				return fmt.Errorf("launching external tool %s requires --dry-run in this Go compatibility build", tool)
			}
			provider, err := firstProviderForTool(state.providersPath, tool)
			if err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Tool: %s\n", tool)
			if provider.Endpoint != "" {
				fmt.Fprintf(cmd.OutOrStdout(), "Endpoint: %s\n", provider.Endpoint)
			}
			if len(provider.Models) > 0 {
				fmt.Fprintf(cmd.OutOrStdout(), "Model: %s\n", provider.Models[0])
			}
			if len(args) > 1 {
				fmt.Fprintf(cmd.OutOrStdout(), "Args: %s\n", strings.Join(args[1:], " "))
			}
			return nil
		},
	}
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Print resolved launch environment without executing the tool")
	return cmd
}

func isKnownTool(tool string) bool {
	for _, known := range knownTools {
		if tool == known {
			return true
		}
	}
	return false
}

func (a *App) doctorCommand(state *globalState) *cobra.Command {
	var verbose bool
	cmd := &cobra.Command{
		Use:     "doctor",
		Aliases: []string{"d"},
		Short:   "Run diagnostic checks on environment and API keys",
		Args:    cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			providers, err := loadProviders(state.providersPath)
			if err != nil {
				return err
			}
			names := make([]string, 0, len(providers.Endpoints))
			for name := range providers.Endpoints {
				names = append(names, name)
			}
			sort.Strings(names)
			fmt.Fprintf(cmd.OutOrStdout(), "Providers: %d\n", len(names))
			for _, name := range names {
				ep := providers.Endpoints[name]
				fmt.Fprintf(cmd.OutOrStdout(), "- %s: %s\n", name, ep.Endpoint)
				if ep.APIKeyEnv != "" {
					status := "missing"
					if os.Getenv(ep.APIKeyEnv) != "" {
						status = "set"
					}
					fmt.Fprintf(cmd.OutOrStdout(), "  Environment: %s %s\n", ep.APIKeyEnv, status)
				}
				if verbose && ep.SupportedClient != "" {
					fmt.Fprintf(cmd.OutOrStdout(), "  Supported clients: %s\n", ep.SupportedClient)
				}
			}
			return nil
		},
	}
	cmd.Flags().BoolVar(&verbose, "verbose", false, "Show verbose diagnostics")
	return cmd
}

func (a *App) lifecycleCommand(name, alias string) *cobra.Command {
	var dryRun bool
	cmd := &cobra.Command{
		Use:     name + " [TARGET]",
		Aliases: []string{alias},
		Short:   strings.Title(name) + " tools",
		Args:    cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			target := "all"
			if len(args) > 0 {
				target = args[0]
			}
			if dryRun {
				_, err := fmt.Fprintf(cmd.OutOrStdout(), "Would %s %s\n", name, target)
				return err
			}
			_, err := fmt.Fprintf(cmd.OutOrStdout(), "%s %s\n", strings.Title(name), target)
			return err
		},
	}
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Print planned action without executing it")
	return cmd
}

type providersFile struct {
	Common    map[string]any      `json:"common"`
	Endpoints map[string]endpoint `json:"endpoints"`
}

type endpoint struct {
	Endpoint        string   `json:"endpoint"`
	APIKeyEnv       string   `json:"api_key_env"`
	Models          []string `json:"list_of_models"`
	SupportedClient string   `json:"supported_client"`
}

func loadProviders(path string) (providersFile, error) {
	if path == "" {
		path = filepath.Join(configDir(), "providers.json")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return providersFile{}, fmt.Errorf("failed to read providers config %s: %w", path, err)
	}
	var providers providersFile
	if err := json.Unmarshal(data, &providers); err != nil {
		return providersFile{}, fmt.Errorf("failed to parse providers config %s: %w", path, err)
	}
	if providers.Endpoints == nil {
		providers.Endpoints = map[string]endpoint{}
	}
	return providers, nil
}

func firstProviderForTool(path, tool string) (endpoint, error) {
	providers, err := loadProviders(path)
	if err != nil {
		return endpoint{}, err
	}
	names := make([]string, 0, len(providers.Endpoints))
	for name := range providers.Endpoints {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		ep := providers.Endpoints[name]
		for _, client := range strings.Split(ep.SupportedClient, ",") {
			if strings.TrimSpace(client) == tool {
				return ep, nil
			}
		}
	}
	return endpoint{}, fmt.Errorf("no provider supports tool: %s", tool)
}
