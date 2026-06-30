package cli

import (
	"errors"
	"fmt"
	"io"
	"os"

	"github.com/spf13/cobra"
)

// Options configures App.  Empty Stdout/Stderr default to os.Stdout/os.Stderr;
// an empty Stdin defaults to os.Stdin; an empty Version defaults to "dev".
type Options struct {
	Version string
	Stdout  io.Writer
	Stderr  io.Writer
	Stdin   io.Reader
}

// App is the top-level CLI entrypoint.  Construct one with New, then call
// Run with the process args (excluding argv[0]).
type App struct {
	version string
	stdout  io.Writer
	stderr  io.Writer
	stdin   io.Reader
}

// New constructs an App from Options.
func New(opts Options) *App {
	if opts.Version == "" {
		opts.Version = "dev"
	}
	if opts.Stdout == nil {
		opts.Stdout = os.Stdout
	}
	if opts.Stderr == nil {
		opts.Stderr = os.Stderr
	}
	if opts.Stdin == nil {
		opts.Stdin = os.Stdin
	}
	return &App{version: opts.Version, stdout: opts.Stdout, stderr: opts.Stderr, stdin: opts.Stdin}
}

// Run executes the CLI and returns the process exit code.  errEndpointsHandled
// from PersistentPreRunE is translated to a successful exit so the global
// --endpoints short-circuit behaves identically to Python's typer.Exit().
func (a *App) Run(args []string) int {
	cmd := a.rootCommand()
	cmd.SetArgs(args)
	cmd.SetOut(a.stdout)
	cmd.SetErr(a.stderr)
	cmd.SetIn(a.stdin)
	cmd.SilenceUsage = true
	cmd.SilenceErrors = true

	if err := cmd.Execute(); err != nil {
		if errors.Is(err, errEndpointsHandled) {
			return 0
		}
		fmt.Fprintln(a.stderr, err.Error())
		return 1
	}
	return 0
}

func (a *App) rootCommand() *cobra.Command {
	state := &globalState{}
	root := &cobra.Command{
		Use:   "cam",
		Short: "Code Assistant Manager",
		Long: "Code Assistant Manager (CAM) manages AI coding assistant configuration, instructions, " +
			"skills, plugins, MCP servers, and launch commands.\n\n" +
			"Aliases: launch/l, doctor/d, agent/ag, instruction/prompt/p, skill/s, plugin/pl, mcp/m, " +
			"provider/pr, upgrade/u, install/i, uninstall/un, config/cf, completion/comp/c, version/v.",
		Version: a.version,
	}
	root.SetVersionTemplate("{{.Version}}\n")

	root.PersistentFlags().StringVar(&state.configPath, "config", "", "Path to CAM config.yaml")
	root.PersistentFlags().StringVar(&state.storePath, "store", "", "Path to SQLite state store (default: ~/.config/code-agent-manager/cam.db)")
	root.PersistentFlags().StringVar(&state.endpoints, "endpoints", "",
		"Print endpoint information for all tools or a specific tool")
	root.PersistentFlags().BoolVarP(&state.debug, "debug", "d", false,
		"Enable debug logging")

	root.PersistentPreRunE = func(cmd *cobra.Command, args []string) error {
		return handleEndpointsShortCircuit(cmd, state)
	}

	root.AddCommand(a.versionCommand())
	root.AddCommand(a.completionCommand(root))
	root.AddCommand(a.launchCommand(state))
	root.AddCommand(a.applyCommand(state))
	root.AddCommand(a.doctorCommand(state))
	root.AddCommand(a.configCommand(state))
	root.AddCommand(a.providerCommand(state))
	root.AddCommand(a.managementCommand("agent", "ag", state))
	root.AddCommand(a.managementCommand("instruction", "prompt,p", state))
	root.AddCommand(a.managementCommand("skill", "s", state))
	root.AddCommand(a.managementCommand("plugin", "pl", state))
	root.AddCommand(a.mcpCommand(state))
	root.AddCommand(a.metadataCommand(state))
	root.AddCommand(a.extensionsCommand())
	root.AddCommand(a.lifecycleCommand("upgrade", "u"))
	root.AddCommand(a.lifecycleCommand("install", "i"))
	root.AddCommand(a.lifecycleCommand("uninstall", "un"))
	return root
}

func (a *App) deprecatedPromptCommand(name string) *cobra.Command {
	msg := "cam prompt was renamed to cam instruction. Use cam instruction --help."
	cmd := &cobra.Command{
		Use:   name,
		Short: msg,
		RunE: func(cmd *cobra.Command, args []string) error {
			return errors.New(msg)
		},
	}
	cmd.SetFlagErrorFunc(func(cmd *cobra.Command, err error) error {
		return errors.New(msg)
	})
	cmd.ValidArgsFunction = func(cmd *cobra.Command, args []string, toComplete string) ([]string, cobra.ShellCompDirective) {
		return nil, cobra.ShellCompDirectiveNoFileComp
	}
	return cmd
}
