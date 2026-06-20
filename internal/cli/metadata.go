package cli

import (
	"context"
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/metadata"
)

func (a *App) metadataCommand(state *globalState) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "metadata",
		Aliases: []string{"md"},
		Short:   "Manage the metadata index for agents, skills, and plugins",
	}
	cmd.AddCommand(a.metadataRefreshCommand(state))
	cmd.AddCommand(a.metadataSearchCommand(state))
	cmd.AddCommand(a.metadataInstallCommand(state))
	return cmd
}

func (a *App) metadataRefreshCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "refresh",
		Short: "Refresh metadata index from configured repositories",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			store := metadata.NewStore(state.storePath)
			svc := metadata.NewService(store)

			summary, err := svc.RefreshAll(context.Background())
			if err != nil {
				return fmt.Errorf("refresh failed: %w", err)
			}
			fmt.Fprintf(out, "✓ Refreshed metadata\n")
			fmt.Fprintf(out, "  Sources scanned: %d\n", summary.SourcesScanned)
			fmt.Fprintf(out, "  Items indexed:   %d\n", summary.ItemsAdded)
			if len(summary.FailedSources) > 0 {
				fmt.Fprintf(out, "  Failed sources:  %d\n", len(summary.FailedSources))
				for _, f := range summary.FailedSources {
					fmt.Fprintf(out, "    - %s\n", f)
				}
			}
			return nil
		},
	}
}

func (a *App) metadataSearchCommand(state *globalState) *cobra.Command {
	var kindFilter string
	cmd := &cobra.Command{
		Use:   "search <query>",
		Short: "Search the metadata index",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			store := metadata.NewStore(state.storePath)
			query := strings.Join(args, " ")

			results, err := store.Search(context.Background(), metadata.SearchQuery{
				Query: query,
				Kind:  kindFilter,
			})
			if err != nil {
				return fmt.Errorf("search failed: %w", err)
			}
			if len(results) == 0 {
				fmt.Fprintf(out, "No results for %q\n", query)
				return nil
			}
			fmt.Fprintf(out, "Found %d result(s) for %q:\n\n", len(results), query)
			fmt.Fprintf(out, "  %-8s %-30s %-25s %s\n", "KIND", "NAME", "REPO", "DESCRIPTION")
			fmt.Fprintf(out, "  %-8s %-30s %-25s %s\n",
				strings.Repeat("─", 8), strings.Repeat("─", 30),
				strings.Repeat("─", 25), strings.Repeat("─", 40))
			for _, item := range results {
				repo := item.RepoOwner + "/" + item.RepoName
				desc := item.Description
				if len(desc) > 50 {
					desc = desc[:47] + "..."
				}
				fmt.Fprintf(out, "  %-8s %-30s %-25s %s\n", item.Kind, item.Name, repo, desc)
			}
			return nil
		},
	}
	cmd.Flags().StringVar(&kindFilter, "type", "", "Filter by kind (skill, agent, instruction, plugin)")
	return cmd
}

func (a *App) metadataInstallCommand(state *globalState) *cobra.Command {
	var targets []string
	cmd := &cobra.Command{
		Use:   "install <install-key>",
		Short: "Install a metadata item to one or more target coding agents",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			store := metadata.NewStore(state.storePath)
			svc := metadata.NewService(store)
			installKey := args[0]

			if len(targets) == 0 {
				targets = []string{"claude"}
			}

			// Try each kind until found.
			var lastErr error
			for _, kind := range []string{"skill", "agent", "instruction", "plugin"} {
				err := svc.InstallToTargets(context.Background(), kind, installKey, targets)
				if err == nil {
					fmt.Fprintf(out, "✓ Installed %s to %s\n", installKey, strings.Join(targets, ", "))
					return nil
				}
				lastErr = err
			}
			return fmt.Errorf("install failed: %w", lastErr)
		},
	}
	cmd.Flags().StringSliceVar(&targets, "target", []string{"claude"}, "Target coding agent(s); repeat or comma-separate (e.g. --target claude,codex)")
	return cmd
}
