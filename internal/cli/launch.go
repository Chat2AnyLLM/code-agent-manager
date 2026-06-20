package cli

import (
	"context"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

// launchCommand resolves the tool/provider/model triple (interactively
// when stdin is a TTY and any of the three is unpinned), writes the
// tool's native config file, then exec's the binary.
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

			// Split the positional args: first is the optional tool
			// name; the rest is forwarded to the tool binary.
			var positionalTool string
			var toolArgs []string
			if len(args) > 0 {
				positionalTool = args[0]
				toolArgs = args[1:]
			}

			// Validate the positional tool name BEFORE touching
			// the provider store so an unknown name surfaces the right
			// error even when no providers config exists.
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

			// When the user has not pinned anything and the output is
			// non-TTY, preserve the long-standing behaviour of
			// rendering the tool picker as plain text (the user is
			// running in a script context and just wants to know what
			// would happen). Skip providers loading entirely.
			if pinned.Tool.Name == "" && pinned.EndpointName == "" && pinned.Model == "" && !outIsTTY(cmd.OutOrStdout()) {
				_, _ = fmt.Fprint(cmd.OutOrStdout(), newToolMenuModel(registry.LaunchNames()).View())
				return nil
			}

			// Load the provider store lazily — only when the wizard or
			// auto-resolve actually needs an endpoint.
			file, perr := makeProviderAPI(state).File(context.Background())
			if perr != nil {
				return perr
			}

			// Decide: interactive wizard vs auto-resolve.
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

			if dryRun {
				plan, perr := tools.Plan(sel.Tool, sel.Endpoint, sel.EndpointName, sel.Model, apiKey)
				if perr != nil {
					return perr
				}
				printDryRun(cmd.OutOrStdout(), sel.Tool, sel.Endpoint, sel.Model, plan, toolArgs)
				return nil
			}

			if _, werr := tools.WriteConfig(sel.Tool, sel.Endpoint, sel.EndpointName, sel.Model, apiKey); werr != nil {
				return fmt.Errorf("launch: write %s config: %w", sel.Tool.Name, werr)
			}

			launch := tools.ResolveLaunchEnv(sel.Tool, sel.Endpoint, sel.EndpointName, sel.Model)
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

// lookupTool resolves a CLI-supplied tool name against the registry,
// trying both cli_command match (e.g. "claude") and tool key match
// (e.g. "claude-code") to mirror today's behaviour.
func lookupTool(registry *tools.Registry, name string) (tools.Tool, bool) {
	if t, ok := registry.ByCLICommand(name); ok {
		return t, true
	}
	return registry.Get(name)
}

// resolveLaunchSelection produces the concrete tool/endpoint/model
// triple by either invoking the interactive wizard (TTY + any field
// unpinned) or by auto-resolving from the SQLite provider store (non-TTY).
func resolveLaunchSelection(
	out io.Writer,
	stderr io.Writer,
	file providers.File,
	registry *tools.Registry,
	pinned launchSelection,
) (launchSelection, bool, error) {
	in := wizardInput{
		Pinned:    pinned,
		Providers: file,
		Registry:  registry,
		ResolveModels: func(ep providers.Endpoint, epName string) ([]string, error) {
			return providers.ResolveModels(ep, epName, cacheTTLFromCommon(file.Common), "", os.Getenv)
		},
	}

	if outIsTTY(out) && (pinned.Tool.Name == "" || pinned.EndpointName == "" || pinned.Model == "") {
		return runLaunchWizard(out, in)
	}

	// Non-TTY (or fully pinned): auto-resolve any missing pieces.
	sel, err := autoResolve(in, stderr)
	return sel, false, err
}

// outIsTTY reports whether the provided writer is a *os.File backed by
// a terminal. Tests pass *bytes.Buffer, which returns false; the live
// CLI passes os.Stdout, which returns true on an interactive console.
func outIsTTY(out io.Writer) bool {
	file, ok := out.(*os.File)
	if !ok {
		return false
	}
	return isTerminal(file)
}

// cacheTTLFromCommon reads provider metadata cache_ttl_seconds from the store-backed file shape.
// Default: 24h.
func cacheTTLFromCommon(common map[string]any) time.Duration {
	const defaultSeconds = int64(86400)
	seconds := defaultSeconds
	if common != nil {
		if v, ok := common["cache_ttl_seconds"]; ok {
			switch n := v.(type) {
			case float64:
				seconds = int64(n)
			case int:
				seconds = int64(n)
			case int64:
				seconds = n
			}
		}
	}
	return time.Duration(seconds) * time.Second
}

// autoResolve fills missing pinned fields using today's
// auto-selection logic (first matching endpoint, first model). Used
// when stdin is not a TTY, or when there's nothing left to ask the
// user.
func autoResolve(in wizardInput, stderr io.Writer) (launchSelection, error) {
	sel := in.Pinned

	if sel.Tool.Name == "" {
		return launchSelection{}, fmt.Errorf("launch: no tool specified and no TTY for interactive selection; pass a tool name")
	}

	if sel.EndpointName == "" {
		client := sel.Tool.LaunchCommand()
		for _, name := range in.Providers.SortedNames() {
			ep := in.Providers.Endpoints[name]
			if !ep.IsEnabled() {
				continue
			}
			if !ep.SupportsClient(client) {
				continue
			}
			sel.EndpointName = name
			sel.Endpoint = ep
			if stderr != nil {
				fmt.Fprintf(stderr, "[cam] auto-selected endpoint: %s\n", name)
			}
			break
		}
		if sel.EndpointName == "" {
			return launchSelection{}, fmt.Errorf("no provider supports tool: %s", client)
		}
	} else {
		ep, ok := in.Providers.Endpoints[sel.EndpointName]
		if !ok {
			return launchSelection{}, fmt.Errorf("Unknown endpoint: %s", sel.EndpointName)
		}
		if !ep.SupportsClient(sel.Tool.LaunchCommand()) {
			return launchSelection{}, fmt.Errorf(
				"endpoint %s does not support tool %s (check supported_client)",
				sel.EndpointName, sel.Tool.LaunchCommand())
		}
		sel.Endpoint = ep
	}

	if sel.Model == "" {
		models, mErr := in.ResolveModels(sel.Endpoint, sel.EndpointName)
		if mErr != nil {
			return launchSelection{}, fmt.Errorf(
				"launch: discover models for endpoint %s: %w (pass --model to skip discovery)",
				sel.EndpointName, mErr)
		}
		if len(models) == 0 {
			return launchSelection{}, fmt.Errorf(
				"launch: endpoint %s has no discovered models; pass --model",
				sel.EndpointName)
		}
		sel.Model = models[0]
		if stderr != nil {
			fmt.Fprintf(stderr, "[cam] auto-selected model: %s\n", sel.Model)
		}
	}

	return sel, nil
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

// runToolMenu remains as a fallback used by tests that exercise the
// non-TTY rendering path of the legacy single-step menu. It is no
// longer wired into the launch command, but kept to avoid breaking
// the existing test that asserts on its output.
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

// ensure pathutil import is used (kept for future cache-dir overrides
// done by tests via CAM_CACHE_DIR).
var _ = pathutil.CacheDir
