package cli

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"

	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// providerCommand wires `cam provider <list|show|add|update|remove|enable|
// disable|rename|init>`. All subcommands operate on providers.json at the
// path resolved by state.providersPath (or providers.DiscoverPath() when
// the flag is empty). The file is auto-created when missing.
func (a *App) providerCommand(state *globalState) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "provider",
		Aliases: []string{"pr", "providers"},
		Short:   "Manage providers.json entries (no manual editing required)",
	}
	cmd.AddCommand(a.providerListCommand(state))
	cmd.AddCommand(a.providerShowCommand(state))
	cmd.AddCommand(a.providerAddCommand(state))
	cmd.AddCommand(a.providerUpdateCommand(state))
	cmd.AddCommand(a.providerRemoveCommand(state))
	cmd.AddCommand(a.providerEnableCommand(state))
	cmd.AddCommand(a.providerDisableCommand(state))
	cmd.AddCommand(a.providerRenameCommand(state))
	cmd.AddCommand(a.providerInitCommand(state))
	return cmd
}

// resolveProvidersPath honours --providers when set; otherwise falls back to
// providers.DefaultPath so a fresh machine still gets a deterministic
// location for the auto-created file.
func resolveProvidersPath(state *globalState) string {
	if state != nil && state.providersPath != "" {
		return state.providersPath
	}
	return providers.DefaultPath()
}

func (a *App) providerInitCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "init",
		Short: "Create an empty providers.json if it does not already exist",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			path := resolveProvidersPath(state)
			file, created, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			if !created {
				fmt.Fprintf(cmd.OutOrStdout(), "providers.json already exists at %s\n", path)
				return nil
			}
			if err := providers.Save(path, file); err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Created empty providers.json at %s\n", path)
			return nil
		},
	}
}

func (a *App) providerListCommand(state *globalState) *cobra.Command {
	var asJSON bool
	var enabledOnly bool
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List configured providers",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			out := cmd.OutOrStdout()
			names := file.SortedNames()
			filtered := make([]string, 0, len(names))
			for _, n := range names {
				if enabledOnly && !file.Endpoints[n].IsEnabled() {
					continue
				}
				filtered = append(filtered, n)
			}
			if asJSON {
				subset := map[string]providers.Endpoint{}
				for _, n := range filtered {
					subset[n] = file.Endpoints[n]
				}
				return writeJSON(out, subset)
			}
			if len(filtered) == 0 {
				fmt.Fprintf(out, "No providers configured. Add one with 'cam provider add NAME --endpoint URL'.\n")
				return nil
			}
			writeProviderTable(out, file, filtered)
			return nil
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "Emit JSON instead of a table")
	cmd.Flags().BoolVar(&enabledOnly, "enabled-only", false, "Skip disabled providers")
	return cmd
}

func writeProviderTable(out io.Writer, file providers.File, names []string) {
	nameWidth := len("NAME")
	endpointWidth := len("ENDPOINT")
	clientsWidth := len("CLIENTS")
	for _, n := range names {
		if len(n) > nameWidth {
			nameWidth = len(n)
		}
		ep := file.Endpoints[n]
		if len(ep.Endpoint) > endpointWidth {
			endpointWidth = len(ep.Endpoint)
		}
		clients := joinComma(ep.Clients())
		if len(clients) > clientsWidth {
			clientsWidth = len(clients)
		}
	}
	row := fmt.Sprintf("%%-%ds  %%-%ds  %%-%ds  %%s\n", nameWidth, endpointWidth, clientsWidth)
	fmt.Fprintf(out, row, "NAME", "ENDPOINT", "CLIENTS", "ENABLED")
	for _, n := range names {
		ep := file.Endpoints[n]
		fmt.Fprintf(out, row, n, ep.Endpoint, joinComma(ep.Clients()), enabledString(ep))
	}
}

func enabledString(ep providers.Endpoint) string {
	if ep.IsEnabled() {
		return "yes"
	}
	return "no"
}

func (a *App) providerShowCommand(state *globalState) *cobra.Command {
	var revealKey bool
	cmd := &cobra.Command{
		Use:   "show NAME",
		Short: "Show the configuration for a single provider",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			ep, ok := file.Endpoints[args[0]]
			if !ok {
				return fmt.Errorf("provider %q not found (try 'cam provider list')", args[0])
			}
			out := cmd.OutOrStdout()
			// Build a copy of the endpoint with a calculated API-key
			// display so we don't leak the raw env variable name twice.
			payload := map[string]any{
				"name":              args[0],
				"endpoint":          ep.Endpoint,
				"api_key_env":       ep.APIKeyEnv,
				"supported_client":  ep.SupportedClient,
				"list_of_models":    ep.Models,
				"list_models_cmd":   ep.ListModelsCmd,
				"use_proxy":         ep.UseProxy,
				"keep_proxy_config": ep.KeepProxyConfig,
				"enabled":           ep.IsEnabled(),
				"description":       ep.Description,
			}
			if ep.APIKeyEnv != "" {
				raw := os.Getenv(ep.APIKeyEnv)
				if revealKey {
					payload["api_key"] = raw
				} else {
					payload["api_key"] = providers.MaskedAPIKey(raw)
				}
			}
			return writeJSON(out, payload)
		},
	}
	cmd.Flags().BoolVar(&revealKey, "reveal-key", false, "Show the resolved API key instead of masking it")
	return cmd
}

// addOrUpdateFlags is the common flag set shared by `add` and `update`. The
// returned pointers stay live until cobra has parsed args; the bool-set
// trackers tell Update which flags the user touched so unspecified flags
// don't accidentally clobber values.
type addOrUpdateFlags struct {
	endpoint        string
	apiKeyEnv       string
	clients         string
	models          string
	listModelsCmd   string
	description     string
	useProxy        bool
	noUseProxy      bool
	keepProxyConfig bool
	noKeepProxy     bool
	enabled         bool
	disabled        bool
}

func bindAddOrUpdateFlags(cmd *cobra.Command, f *addOrUpdateFlags) {
	cmd.Flags().StringVar(&f.endpoint, "endpoint", "", "Endpoint URL")
	cmd.Flags().StringVar(&f.apiKeyEnv, "api-key-env", "", "Name of the env var holding the API key")
	cmd.Flags().StringVar(&f.clients, "client", "", "Supported clients (comma-separated; '+x' adds, '-x' removes, '=x,y' replaces on update)")
	cmd.Flags().StringVar(&f.models, "model", "", "Models (comma-separated; '+x' adds, '-x' removes, '=x,y' replaces on update)")
	cmd.Flags().StringVar(&f.listModelsCmd, "list-models-cmd", "", "Shell command for dynamic model discovery")
	cmd.Flags().StringVar(&f.description, "description", "", "Human-readable description")
	cmd.Flags().BoolVar(&f.useProxy, "use-proxy", false, "Set use_proxy=true")
	cmd.Flags().BoolVar(&f.noUseProxy, "no-use-proxy", false, "Set use_proxy=false")
	cmd.Flags().BoolVar(&f.keepProxyConfig, "keep-proxy-config", false, "Set keep_proxy_config=true")
	cmd.Flags().BoolVar(&f.noKeepProxy, "no-keep-proxy-config", false, "Set keep_proxy_config=false")
	cmd.Flags().BoolVar(&f.enabled, "enabled", false, "Set enabled=true on add")
	cmd.Flags().BoolVar(&f.disabled, "disabled", false, "Set enabled=false on add")
}

func (a *App) providerAddCommand(state *globalState) *cobra.Command {
	flags := &addOrUpdateFlags{}
	cmd := &cobra.Command{
		Use:   "add [NAME] [--endpoint URL] [flags]",
		Short: "Add a new provider (interactive wizard when flags omitted)",
		Args:  cobra.RangeArgs(0, 1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := ""
			if len(args) > 0 {
				name = args[0]
			}
			if name != "" && cmd.Flags().Changed("endpoint") {
				return a.providerAddFlagMode(cmd, state, name, flags)
			}

			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			existingNames := file.SortedNames()
			name, ep, cancelled, err := runProviderWizard(cmd.OutOrStdout(), cmd.InOrStdin(), wizardModeAdd, nil, "", existingNames)
			if err != nil {
				return err
			}
			if cancelled {
				return nil
			}
			file, _, err = providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			if err := providers.Add(&file, name, ep); err != nil {
				if errors.Is(err, providers.ErrAlreadyExists) {
					return fmt.Errorf("provider %q already exists (use 'cam provider update %s ...' to change it)", name, name)
				}
				return err
			}
			if err := providers.Save(path, file); err != nil {
				return err
			}
			out := cmd.OutOrStdout()
			fmt.Fprintf(out, "Added provider %q\n", name)
			return nil
		},
	}
	bindAddOrUpdateFlags(cmd, flags)
	return cmd
}

func (a *App) providerAddFlagMode(cmd *cobra.Command, state *globalState, name string, flags *addOrUpdateFlags) error {
	if flags.endpoint == "" {
		return errors.New("--endpoint is required")
	}
	if flags.useProxy && flags.noUseProxy {
		return errors.New("--use-proxy and --no-use-proxy are mutually exclusive")
	}
	if flags.keepProxyConfig && flags.noKeepProxy {
		return errors.New("--keep-proxy-config and --no-keep-proxy-config are mutually exclusive")
	}
	if flags.enabled && flags.disabled {
		return errors.New("--enabled and --disabled are mutually exclusive")
	}

	path := resolveProvidersPath(state)
	file, created, err := providers.LoadOrInit(path)
	if err != nil {
		return err
	}

	ep := providers.Endpoint{
		Endpoint:        flags.endpoint,
		APIKeyEnv:       flags.apiKeyEnv,
		ListModelsCmd:   flags.listModelsCmd,
		Description:     flags.description,
		UseProxy:        flags.useProxy,
		KeepProxyConfig: flags.keepProxyConfig,
	}
	if flags.clients != "" {
		_, items, err := parseListFlag(flags.clients, true)
		if err != nil {
			return fmt.Errorf("--client: %w", err)
		}
		ep.SupportedClient = strings.Join(items, ",")
	}
	if flags.models != "" {
		_, items, err := parseListFlag(flags.models, true)
		if err != nil {
			return fmt.Errorf("--model: %w", err)
		}
		ep.Models = items
	}
	if flags.disabled {
		v := false
		ep.Enabled = &v
	} else if flags.enabled {
		v := true
		ep.Enabled = &v
	}

	if err := providers.Add(&file, name, ep); err != nil {
		if errors.Is(err, providers.ErrAlreadyExists) {
			return fmt.Errorf("provider %q already exists (use 'cam provider update %s ...' to change it)", name, name)
		}
		return err
	}
	if err := providers.Save(path, file); err != nil {
		return err
	}
	out := cmd.OutOrStdout()
	if created {
		fmt.Fprintf(out, "Created %s\n", path)
	}
	fmt.Fprintf(out, "Added provider %q\n", name)
	return nil
}

func (a *App) providerUpdateCommand(state *globalState) *cobra.Command {
	flags := &addOrUpdateFlags{}
	cmd := &cobra.Command{
		Use:   "update NAME [flags]",
		Short: "Update fields on an existing provider (interactive wizard when flags omitted)",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			changedFlags := []string{"endpoint", "api-key-env", "client", "model", "list-models-cmd", "description", "use-proxy", "no-use-proxy", "keep-proxy-config", "no-keep-proxy-config", "enabled", "disabled"}
			for _, flagName := range changedFlags {
				if cmd.Flags().Changed(flagName) {
					return a.providerUpdateFlagMode(cmd, state, name, flags)
				}
			}

			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			ep, ok := file.Endpoints[name]
			if !ok {
				return fmt.Errorf("provider %q not found (try 'cam provider list')", name)
			}
			name, newEp, cancelled, err := runProviderWizard(cmd.OutOrStdout(), cmd.InOrStdin(), wizardModeUpdate, &ep, name, file.SortedNames())
			if err != nil {
				return err
			}
			if cancelled {
				return nil
			}
			file.Endpoints[name] = newEp
			if err := providers.Save(path, file); err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Updated provider %q\n", name)
			return nil
		},
	}
	bindAddOrUpdateFlags(cmd, flags)
	return cmd
}

func (a *App) providerUpdateFlagMode(cmd *cobra.Command, state *globalState, name string, flags *addOrUpdateFlags) error {
	if flags.useProxy && flags.noUseProxy {
		return errors.New("--use-proxy and --no-use-proxy are mutually exclusive")
	}
	if flags.keepProxyConfig && flags.noKeepProxy {
		return errors.New("--keep-proxy-config and --no-keep-proxy-config are mutually exclusive")
	}
	if flags.enabled && flags.disabled {
		return errors.New("--enabled and --disabled are mutually exclusive")
	}

	patch := providers.Patch{}
	if cmd.Flags().Changed("endpoint") {
		v := flags.endpoint
		patch.Endpoint = &v
	}
	if cmd.Flags().Changed("api-key-env") {
		v := flags.apiKeyEnv
		patch.APIKeyEnv = &v
	}
	if cmd.Flags().Changed("description") {
		v := flags.description
		patch.Description = &v
	}
	if cmd.Flags().Changed("list-models-cmd") {
		v := flags.listModelsCmd
		patch.ListModelsCmd = &v
	}
	if flags.useProxy {
		v := true
		patch.UseProxy = &v
	} else if flags.noUseProxy {
		v := false
		patch.UseProxy = &v
	}
	if flags.keepProxyConfig {
		v := true
		patch.KeepProxyConfig = &v
	} else if flags.noKeepProxy {
		v := false
		patch.KeepProxyConfig = &v
	}
	if flags.enabled {
		v := true
		patch.Enabled = &v
	} else if flags.disabled {
		v := false
		patch.Enabled = &v
	}
	if cmd.Flags().Changed("client") {
		op, items, err := parseListFlag(flags.clients, false)
		if err != nil {
			return fmt.Errorf("--client: %w", err)
		}
		patch.Clients = &providers.ListPatch{Op: op, Items: items}
	}
	if cmd.Flags().Changed("model") {
		op, items, err := parseListFlag(flags.models, false)
		if err != nil {
			return fmt.Errorf("--model: %w", err)
		}
		patch.Models = &providers.ListPatch{Op: op, Items: items}
	}

	path := resolveProvidersPath(state)
	file, _, err := providers.LoadOrInit(path)
	if err != nil {
		return err
	}
	if err := providers.Update(&file, name, patch); err != nil {
		if errors.Is(err, providers.ErrNotFound) {
			return fmt.Errorf("provider %q not found (try 'cam provider list')", name)
		}
		return err
	}
	if err := providers.Save(path, file); err != nil {
		return err
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Updated provider %q\n", name)
	return nil
}

func (a *App) providerRemoveCommand(state *globalState) *cobra.Command {
	var yes bool
	cmd := &cobra.Command{
		Use:     "remove NAME",
		Aliases: []string{"rm", "delete"},
		Short:   "Remove a provider",
		Args:    cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			if _, ok := file.Endpoints[name]; !ok {
				return fmt.Errorf("provider %q not found", name)
			}
			if !yes {
				// Non-interactive contexts (no TTY) must opt out via
				// --yes so scripts don't hang on stdin. We bail with a
				// clear error rather than silently skipping.
				if !inIsTTY(cmd.InOrStdin()) {
					return fmt.Errorf("remove requires --yes when stdin is not a TTY")
				}
				fmt.Fprintf(cmd.OutOrStdout(), "Remove provider %q? [y/N]: ", name)
				answer := readLine(cmd.InOrStdin())
				if !strings.EqualFold(strings.TrimSpace(answer), "y") {
					fmt.Fprintln(cmd.OutOrStdout(), "Aborted.")
					return nil
				}
			}
			providers.Remove(&file, name)
			if err := providers.Save(path, file); err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Removed provider %q\n", name)
			return nil
		},
	}
	cmd.Flags().BoolVarP(&yes, "yes", "y", false, "Do not prompt for confirmation")
	return cmd
}

func (a *App) providerEnableCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "enable NAME",
		Short: "Mark a provider as enabled",
		Args:  cobra.ExactArgs(1),
		RunE:  toggleEnabledRunE(state, true),
	}
}

func (a *App) providerDisableCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "disable NAME",
		Short: "Mark a provider as disabled",
		Args:  cobra.ExactArgs(1),
		RunE:  toggleEnabledRunE(state, false),
	}
}

func toggleEnabledRunE(state *globalState, enabled bool) func(*cobra.Command, []string) error {
	return func(cmd *cobra.Command, args []string) error {
		name := args[0]
		path := resolveProvidersPath(state)
		file, _, err := providers.LoadOrInit(path)
		if err != nil {
			return err
		}
		if err := providers.SetEnabled(&file, name, enabled); err != nil {
			if errors.Is(err, providers.ErrNotFound) {
				return fmt.Errorf("provider %q not found", name)
			}
			return err
		}
		if err := providers.Save(path, file); err != nil {
			return err
		}
		state := "disabled"
		if enabled {
			state = "enabled"
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Provider %q %s\n", name, state)
		return nil
	}
}

func (a *App) providerRenameCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "rename OLD NEW",
		Short: "Rename a provider entry",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			path := resolveProvidersPath(state)
			file, _, err := providers.LoadOrInit(path)
			if err != nil {
				return err
			}
			if err := providers.Rename(&file, args[0], args[1]); err != nil {
				if errors.Is(err, providers.ErrNotFound) {
					return fmt.Errorf("provider %q not found", args[0])
				}
				if errors.Is(err, providers.ErrAlreadyExists) {
					return fmt.Errorf("provider %q already exists", args[1])
				}
				return err
			}
			if err := providers.Save(path, file); err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Renamed %q to %q\n", args[0], args[1])
			return nil
		},
	}
}

// parseListFlag interprets a value like "+a,b", "-x", "=a,b", or "a,b".
// When add is true (the flag is being parsed for `add`), the leading sigil
// is rejected because mutation operators only make sense on update.
func parseListFlag(raw string, addMode bool) (providers.ListOp, []string, error) {
	if raw == "" {
		return providers.ListOpReplace, nil, nil
	}
	op := providers.ListOpReplace
	body := raw
	switch raw[0] {
	case '+':
		op = providers.ListOpAdd
		body = raw[1:]
	case '-':
		op = providers.ListOpRemove
		body = raw[1:]
	case '=':
		op = providers.ListOpReplace
		body = raw[1:]
	}
	if addMode && op != providers.ListOpReplace {
		return op, nil, errors.New("add does not accept +/- prefixes (use plain or '=' value)")
	}
	parts := strings.Split(body, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		trimmed := strings.TrimSpace(p)
		if trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return op, out, nil
}

// writeJSON pretty-prints v as 2-space indented JSON with a trailing newline.
func writeJSON(out io.Writer, v any) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	_, err = out.Write(data)
	return err
}

// inIsTTY reports whether the supplied reader is a *os.File backed by a
// terminal. Tests using bytes.Buffer return false, which is what we want
// so the buffer-driven test path doesn't block on a confirmation prompt.
func inIsTTY(in io.Reader) bool {
	file, ok := in.(*os.File)
	if !ok {
		return false
	}
	info, err := file.Stat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}

// readLine reads up to a newline from in. Used only on the interactive
// confirmation path; bounded read so we don't hang on a closed stdin.
func readLine(in io.Reader) string {
	buf := make([]byte, 0, 64)
	one := make([]byte, 1)
	for {
		n, err := in.Read(one)
		if n == 0 || err != nil {
			break
		}
		if one[0] == '\n' {
			break
		}
		buf = append(buf, one[0])
		if len(buf) > 1024 {
			break
		}
	}
	return string(buf)
}

// keepSortedNamesUsed is a compile-time guard against accidental dead
// imports while iterating on the file. sort is referenced via this helper.
var _ = sort.Strings
