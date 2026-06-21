package cli

import (
	"context"
	"fmt"
	"os"
	"sort"

	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/doctor"
	"github.com/chat2anyllm/code-agent-manager/internal/ui"
)

// doctorCommand wires the `cam doctor` subcommand.  Output is layered so that
// existing assertion-based tests keep passing: the legacy "Providers: N"
// summary header appears first, followed by the new structured check sections.
func (a *App) doctorCommand(state *globalState) *cobra.Command {
	var verbose bool
	cmd := &cobra.Command{
		Use:     "doctor",
		Aliases: []string{"d"},
		Short:   "Run diagnostic checks on environment and API keys",
		Args:    cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			printer := ui.New(out, cmd.ErrOrStderr())

			// --- legacy summary header (preserves existing test assertions).
			file, providersErr := makeProviderAPI(state).File(context.Background())
			if providersErr == nil {
				names := file.SortedNames()
				fmt.Fprintf(out, "Providers: %d\n", len(names))
				for _, name := range names {
					ep := file.Endpoints[name]
					fmt.Fprintf(out, "- %s: %s\n", name, ep.Endpoint)
					if ep.APIKeyEnv != "" {
						status := "missing"
						if os.Getenv(ep.APIKeyEnv) != "" {
							status = "set"
						}
						fmt.Fprintf(out, "  Environment: %s %s\n", ep.APIKeyEnv, status)
					}
					if verbose && ep.SupportedClient != "" {
						clients := ep.Clients()
						sort.Strings(clients)
						fmt.Fprintf(out, "  Supported clients: %s\n", joinComma(clients))
					}
				}
				fmt.Fprintln(out)
			} else {
				fmt.Fprintf(out, "Providers config could not be loaded: %v\n\n", providersErr)
			}

			// --- structured doctor checks (new in sub-project #1).
			checks := []doctor.Check{
				doctor.InstallationCheck{Version: a.version},
				doctor.ConfigCheck{Path: state.storePath},
				doctor.EnvCheck{},
				doctor.EndpointFormatCheck{File: file},
				doctor.CacheCheck{},
				doctor.ToolsAvailableCheck{},
			}
			doctor.Run(context.Background(), printer, checks)
			return nil
		},
	}
	cmd.Flags().BoolVar(&verbose, "verbose", false, "Show verbose diagnostics")
	return cmd
}
