package cli

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sort"

	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/appapi"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// globalState holds the persistent flag values bound on the root command.  The
// struct is shared by every subcommand so they can look up --config /
// --store / --endpoints / --debug consistently.
type globalState struct {
	configPath string
	storePath  string
	endpoints  string
	debug      bool
}

// makeProviderAPI constructs an appapi.ProviderAPI from the persistent CLI
// state. --store selects the SQLite DB path.
func makeProviderAPI(state *globalState) appapi.ProviderAPI {
	api := appapi.ProviderAPI{}
	if state != nil && state.storePath != "" {
		api.DBPath = state.storePath
	}
	return api
}

// errEndpointsHandled is returned by PersistentPreRunE when the --endpoints
// short-circuit ran successfully.  App.Run recognises it and exits with code
// 0 without executing the actual subcommand body.
var errEndpointsHandled = errors.New("cli: --endpoints handled")

func handleEndpointsShortCircuit(cmd *cobra.Command, state *globalState) error {
	if state.endpoints == "" {
		return nil
	}
	file, err := makeProviderAPI(state).File(context.Background())
	if err != nil {
		return err
	}
	out := cmd.OutOrStdout()
	target := state.endpoints
	if target == "all" {
		printEndpointTable(out, file)
		return errEndpointsHandled
	}
	matches := map[string]providers.Endpoint{}
	for _, name := range file.SortedNames() {
		ep := file.Endpoints[name]
		if ep.SupportsClient(target) {
			matches[name] = ep
		}
	}
	if len(matches) == 0 {
		return fmt.Errorf("No endpoints support client: %s", target)
	}
	subset := providers.File{Common: file.Common, Endpoints: matches}
	printEndpointTable(out, subset)
	return errEndpointsHandled
}

func printEndpointTable(out interface{ Write(p []byte) (int, error) }, file providers.File) {
	fmt.Fprintf(out, "Endpoints: %d\n", len(file.Endpoints))
	for _, name := range file.SortedNames() {
		ep := file.Endpoints[name]
		fmt.Fprintf(out, "- %s\n", name)
		fmt.Fprintf(out, "  URL:      %s\n", ep.Endpoint)
		if ep.SupportedClient != "" {
			clients := ep.Clients()
			sort.Strings(clients)
			fmt.Fprintf(out, "  Clients:  %s\n", joinComma(clients))
		}
		if ep.APIKeyEnv != "" {
			status := "missing"
			if os.Getenv(ep.APIKeyEnv) != "" {
				status = "set"
			}
			fmt.Fprintf(out, "  API key:  %s (%s)\n", ep.APIKeyEnv, status)
		}
		if len(ep.Models) > 0 {
			fmt.Fprintf(out, "  Models:   %s\n", joinComma(ep.Models))
		}
	}
}

func joinComma(items []string) string {
	out := ""
	for i, it := range items {
		if i > 0 {
			out += ", "
		}
		out += it
	}
	return out
}
