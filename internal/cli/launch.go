package cli

import (
	"fmt"
	"io"
	"os"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

// launchCommand exec's the underlying tool binary with the right endpoint,
// model, and env vars.
func (a *App) launchCommand(state *globalState) *cobra.Command {
	var (
		dryRun       bool
		endpointName string
		modelName    string
	)
	cmd := &cobra.Command{
		Use:     "launch [TOOL] [-- ARGS...]",
		Aliases: []string{"l"},
		Short:   "Launch interactive TUI or a specific assistant",
		Args:    cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			registry, err := tools.LoadDefault()
			if err != nil {
				return err
			}
			if len(args) == 0 {
				selected, err := runToolMenu(cmd.OutOrStdout(), registry.LaunchNames())
				if err != nil {
					return err
				}
				if selected == "" {
					return nil
				}
				args = []string{selected}
			}
			binName := args[0]
			tool, ok := registry.ByCLICommand(binName)
			if !ok {
				if t, ok2 := registry.Get(binName); ok2 {
					tool = t
				} else {
					return fmt.Errorf("Unknown tool: %s", binName)
				}
			}
			toolArgs := args[1:]

			endpoint, epName, err := resolveEndpoint(state.providersPath, tool.LaunchCommand(), endpointName)
			if err != nil && !dryRun {
				return err
			}
			model := modelName
			if model == "" && len(endpoint.Models) > 0 {
				model = endpoint.Models[0]
			}

			apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)

			if dryRun {
				plan, perr := tools.Plan(tool, endpoint, epName, model, apiKey)
				if perr != nil {
					return perr
				}
				printDryRun(cmd.OutOrStdout(), tool, endpoint, model, plan, toolArgs)
				return nil
			}

			if _, werr := tools.WriteConfig(tool, endpoint, epName, model, apiKey); werr != nil {
				return fmt.Errorf("launch: write %s config: %w", tool.Name, werr)
			}

			launch := tools.ResolveLaunchEnv(tool, endpoint, epName, model)
			code, err := tools.Run(launch, toolArgs)
			if err != nil {
				return err
			}
			if code != 0 {
				os.Exit(code)
			}
			return nil
		},
	}
	cmd.Flags().BoolVar(&dryRun, "dry-run", false, "Print resolved launch environment without executing the tool")
	cmd.Flags().StringVarP(&endpointName, "endpoint", "e", "", "Endpoint to use (defaults to first supporting client)")
	cmd.Flags().StringVarP(&modelName, "model", "m", "", "Model to use (defaults to endpoint's first model)")
	return cmd
}

func resolveEndpoint(providersPath, client, requested string) (providers.Endpoint, string, error) {
	file, err := providers.Load(providersPath)
	if err != nil {
		return providers.Endpoint{}, "", err
	}
	if requested != "" {
		ep, ok := file.Endpoints[requested]
		if !ok {
			return providers.Endpoint{}, "", fmt.Errorf("Unknown endpoint: %s", requested)
		}
		return ep, requested, nil
	}
	for _, name := range file.SortedNames() {
		ep := file.Endpoints[name]
		if !ep.IsEnabled() {
			continue
		}
		if ep.SupportsClient(client) {
			return ep, name, nil
		}
	}
	return providers.Endpoint{}, "", fmt.Errorf("no provider supports tool: %s", client)
}

func printDryRun(out io.Writer, tool tools.Tool, ep providers.Endpoint, model string, plan []tools.PlannedWrite, args []string) {
	fmt.Fprintf(out, "Tool: %s\n", tool.LaunchCommand())
	if ep.Endpoint != "" {
		fmt.Fprintf(out, "Endpoint: %s\n", ep.Endpoint)
	}
	if model != "" {
		fmt.Fprintf(out, "Model: %s\n", model)
	}
	if tool.ConfigTarget != nil && len(plan) > 0 {
		fmt.Fprintf(out, "Config writes (%s):\n", tool.ConfigTarget.Path)
		for _, p := range plan {
			v := p.Value
			keyU := strings.ToUpper(p.KeyPath)
			if s, ok := v.(string); ok && (strings.Contains(keyU, "AUTH") || strings.Contains(keyU, "KEY") || strings.Contains(keyU, "TOKEN")) {
				v = providers.MaskedAPIKey(s)
			}
			fmt.Fprintf(out, "  %s %s = %q\n", p.Op, p.KeyPath, fmt.Sprintf("%v", v))
		}
	}
	if len(args) > 0 {
		fmt.Fprintf(out, "Args: %s\n", strings.Join(args, " "))
	}
}

// runToolMenu launches the bubbletea picker.  Non-TTY callers receive the
// rendered initial view followed by an empty selection so scripts can still
// inspect the menu output.
func runToolMenu(out io.Writer, items []string) (string, error) {
	model := newToolMenuModel(items)
	file, ok := out.(*os.File)
	if !ok || !isTerminal(file) {
		_, err := fmt.Fprint(out, model.View())
		return "", err
	}
	program := tea.NewProgram(model, tea.WithOutput(out))
	finalModel, err := program.Run()
	if err != nil {
		return "", err
	}
	if menu, ok := finalModel.(toolMenuModel); ok {
		return menu.selected, nil
	}
	return "", nil
}

func isTerminal(file *os.File) bool {
	info, err := file.Stat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}
