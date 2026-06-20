package cli

import (
	"context"
	"fmt"
	"io"
	"os"

	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

// applyCommand resolves the tool/provider/model triple exactly like launch
// (interactive wizard on TTY, auto-resolve otherwise), then writes the tool's
// native config file — and stops. It does NOT exec the agent. This is the
// cc-switch "switch" operation: point an agent at a provider without running it.
func (a *App) applyCommand(state *globalState) *cobra.Command {
	var (
		endpointName string
		modelName    string
	)
	cmd := &cobra.Command{
		Use:     "apply [TOOL]",
		Aliases: []string{"ap"},
		Short:   "Write a provider's config into an agent's config file without launching it",
		Args:    cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			registry, err := tools.LoadDefault()
			if err != nil {
				return err
			}

			var positionalTool string
			if len(args) > 0 {
				positionalTool = args[0]
			}

			// Validate the positional tool name BEFORE touching providers
			// so an unknown name surfaces the right error even when no
			// providers config exists.
			pinned := launchSelection{
				EndpointName: endpointName,
				Model:        modelName,
			}
			if positionalTool != "" {
				tool, ok := lookupTool(registry, positionalTool)
				if !ok {
					return fmt.Errorf("Unknown tool: %s", positionalTool)
				}
				pinned.Tool = tool
			}

			file, perr := makeProviderAPI(state).File(context.Background())
			if perr != nil {
				return perr
			}

			sel, cancelled, err := resolveLaunchSelection(
				cmd.OutOrStdout(),
				cmd.ErrOrStderr(),
				file, registry, pinned,
			)
			if err != nil {
				return err
			}
			if cancelled {
				return nil
			}

			apiKey := providers.ResolveAPIKey(sel.Endpoint, os.Getenv)

			path, werr := tools.WriteConfig(sel.Tool, sel.Endpoint, sel.EndpointName, sel.Model, apiKey)
			if werr != nil {
				return fmt.Errorf("apply: write %s config: %w", sel.Tool.Name, werr)
			}

			printApplyResult(cmd.OutOrStdout(), sel, path)
			return nil
		},
	}
	cmd.Flags().StringVarP(&endpointName, "endpoint", "e", "", "Endpoint to use (defaults to first supporting client)")
	cmd.Flags().StringVarP(&modelName, "model", "m", "", "Model to use (defaults to endpoint's first model)")
	return cmd
}

// printApplyResult reports what was written. An empty path means the tool has
// no config_target — there was nothing to apply.
func printApplyResult(out io.Writer, sel launchSelection, path string) {
	if path == "" {
		fmt.Fprintf(out, "%s has no config file to write; nothing applied.\n", sel.Tool.Name)
		return
	}
	fmt.Fprintf(out, "Applied %s → %s\n", sel.Tool.Name, path)
	fmt.Fprintf(out, "  provider: %s\n", sel.EndpointName)
	fmt.Fprintf(out, "  model: %s\n", sel.Model)
}
