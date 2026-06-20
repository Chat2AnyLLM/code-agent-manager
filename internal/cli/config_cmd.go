package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/pelletier/go-toml/v2"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// configCommand wires `cam config <list|validate|show|set|unset>`.
//
// Two modes:
//  1. Legacy CAM-config mode: `--config <file>` (without `--app`) operates
//     on the YAML/JSON/TOML file at that path.
//  2. Editor mode: `--app <editor>` operates on the per-editor config files
//     through the editorconfig.Registry.
func (a *App) configCommand(state *globalState) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "config",
		Aliases: []string{"cf"},
		Short:   "Manage CAM and editor configuration files",
	}
	cmd.AddCommand(a.configListCommand(state))
	cmd.AddCommand(a.configValidateCommand(state))
	cmd.AddCommand(a.configShowCommand(state))
	cmd.AddCommand(a.configSetCommand(state))
	cmd.AddCommand(a.configUnsetCommand(state))
	return cmd
}

func (a *App) configListCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List configuration files",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			fmt.Fprintln(out, "CAM configuration:")
			for _, p := range []string{
				filepath.Join(pathutil.ConfigDir(), "cam.db"),
				filepath.Join(pathutil.ConfigDir(), "config.yaml"),
				filepath.Join(pathutil.Home(), ".env"),
			} {
				marker := " "
				if pathutil.Exists(p) {
					marker = "✓"
				}
				fmt.Fprintf(out, "  %s %s\n", marker, p)
			}
			fmt.Fprintln(out, "\nEditor configurations:")
			registry := editorconfig.DefaultRegistry()
			for _, name := range registry.Names() {
				tool, _ := registry.Get(name)
				fmt.Fprintf(out, "\n  %s (%s):\n", tool.Description(), tool.Name())
				for _, p := range tool.UserPaths() {
					marker := " "
					if pathutil.Exists(p) {
						marker = "✓"
					}
					fmt.Fprintf(out, "    %s %s\n", marker, p)
				}
				if pp := tool.ProjectPath(); pp != "" {
					marker := " "
					if pathutil.Exists(pp) {
						marker = "✓"
					}
					fmt.Fprintf(out, "    %s %s\n", marker, pp)
				}
			}
			return nil
		},
	}
}

func (a *App) configValidateCommand(state *globalState) *cobra.Command {
	return &cobra.Command{
		Use:   "validate",
		Short: "Validate configuration",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			if state.configPath != "" {
				if _, err := loadConfigFile(state.configPath); err != nil {
					return err
				}
			}
			fmt.Fprintln(cmd.OutOrStdout(), "Configuration is valid")
			return nil
		},
	}
}

func (a *App) configShowCommand(state *globalState) *cobra.Command {
	var app string
	var scope string
	cmd := &cobra.Command{
		Use:   "show [KEY]",
		Short: "Show configuration",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			// Editor mode wins when --app is explicit.
			if app != "" {
				return showEditorConfig(out, app, scope, args)
			}
			// Legacy CAM-config mode: dump the contents of --config.
			if state.configPath != "" {
				data, err := os.ReadFile(state.configPath)
				if err != nil {
					return err
				}
				_, err = out.Write(data)
				return err
			}
			// Default to editor mode with claude as in Python.
			return showEditorConfig(out, "claude", scope, args)
		},
	}
	cmd.Flags().StringVarP(&app, "app", "a", "", "Editor to show configuration for")
	cmd.Flags().StringVarP(&scope, "scope", "s", "", "Filter by scope (user|project)")
	return cmd
}

func showEditorConfig(out interface{ Write(p []byte) (int, error) }, app string, scope string, args []string) error {
	tool, ok := editorconfig.DefaultRegistry().Get(app)
	if !ok {
		return fmt.Errorf("Unknown app: %s", app)
	}
	configs := tool.LoadAll()
	scopes := []string{"user", "project"}
	if scope != "" {
		scopes = []string{scope}
	}
	merged := map[string]string{}
	for _, s := range scopes {
		scoped, ok := configs[s]
		if !ok {
			continue
		}
		for k, v := range editorconfig.Flatten(scoped.Data, app) {
			merged[k] = v
		}
	}
	if len(merged) == 0 {
		fmt.Fprintf(out, "No configuration found for %s\n", app)
		return nil
	}
	keys := make([]string, 0, len(merged))
	for k := range merged {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	filter := ""
	if len(args) == 1 {
		filter = args[0]
	}
	for _, k := range keys {
		if filter != "" && !strings.HasPrefix(k, filter) {
			continue
		}
		fmt.Fprintf(out, "%s = %s\n", k, merged[k])
	}
	return nil
}

func (a *App) configSetCommand(state *globalState) *cobra.Command {
	var app string
	var scope string
	cmd := &cobra.Command{
		Use:   "set KEY[=VALUE] [VALUE]",
		Short: "Set a configuration key",
		Args:  cobra.RangeArgs(1, 2),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			key, value, ok := splitKeyValue(args)
			if !ok {
				return fmt.Errorf("expected KEY=VALUE or KEY VALUE")
			}
			// Legacy CAM-config mode: when --config is set and --app is not.
			if app == "" && state.configPath != "" {
				if err := legacyApplyValue(state.configPath, key, value); err != nil {
					return err
				}
				fmt.Fprintf(out, "Updated %s\n", key)
				return nil
			}
			editor := app
			if editor == "" {
				return fmt.Errorf("--app is required (no --config supplied)")
			}
			tool, ok := editorconfig.DefaultRegistry().Get(editor)
			if !ok {
				return fmt.Errorf("Unknown app: %s", editor)
			}
			coerced := editorconfig.ParseScalar(value)
			savedPath, err := tool.Set(scopeOrDefault(scope), key, coerced)
			if err != nil {
				return err
			}
			fmt.Fprintf(out, "Set %s = %v (%s scope)\n", key, coerced, scopeOrDefault(scope))
			fmt.Fprintf(out, "  Config: %s\n", savedPath)
			return nil
		},
	}
	cmd.Flags().StringVarP(&app, "app", "a", "", "Editor to set configuration for")
	cmd.Flags().StringVarP(&scope, "scope", "s", "user", "Configuration scope (user|project)")
	return cmd
}

func (a *App) configUnsetCommand(state *globalState) *cobra.Command {
	var app string
	var scope string
	cmd := &cobra.Command{
		Use:   "unset KEY",
		Short: "Unset a configuration key",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			out := cmd.OutOrStdout()
			key := args[0]
			if app == "" && state.configPath != "" {
				if err := legacyUnsetConfig(state.configPath, key); err != nil {
					return err
				}
				fmt.Fprintf(out, "Removed %s\n", key)
				return nil
			}
			editor := app
			if editor == "" {
				return fmt.Errorf("--app is required (no --config supplied)")
			}
			tool, ok := editorconfig.DefaultRegistry().Get(editor)
			if !ok {
				return fmt.Errorf("Unknown app: %s", editor)
			}
			found, _, err := tool.Unset(scopeOrDefault(scope), key)
			if err != nil {
				return err
			}
			if !found {
				fmt.Fprintf(out, "Key not found: %s\n", key)
				return nil
			}
			fmt.Fprintf(out, "Unset %s from %s scope\n", key, scopeOrDefault(scope))
			return nil
		},
	}
	cmd.Flags().StringVarP(&app, "app", "a", "", "Editor to unset configuration for")
	cmd.Flags().StringVarP(&scope, "scope", "s", "user", "Configuration scope (user|project)")
	return cmd
}

func scopeOrDefault(scope string) editorconfig.Scope {
	if scope == "project" {
		return editorconfig.ProjectScope
	}
	return editorconfig.UserScope
}

func splitKeyValue(args []string) (string, string, bool) {
	switch len(args) {
	case 1:
		raw := args[0]
		idx := strings.IndexByte(raw, '=')
		if idx <= 0 {
			return "", "", false
		}
		return strings.TrimSpace(raw[:idx]), strings.TrimSpace(raw[idx+1:]), true
	case 2:
		return args[0], args[1], true
	default:
		return "", "", false
	}
}

// --- legacy CAM-config helpers (operate on the file at --config) ---------

func loadConfigFile(path string) (map[string]any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config %s: %w", path, err)
	}
	cfg := map[string]any{}
	switch strings.ToLower(filepath.Ext(path)) {
	case ".json":
		err = json.Unmarshal(data, &cfg)
	case ".toml":
		err = toml.Unmarshal(data, &cfg)
	default:
		err = yaml.Unmarshal(data, &cfg)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to parse config %s: %w", path, err)
	}
	return cfg, nil
}

func writeConfigFile(path string, cfg map[string]any) error {
	var data []byte
	var err error
	switch strings.ToLower(filepath.Ext(path)) {
	case ".json":
		data, err = json.MarshalIndent(cfg, "", "  ")
	case ".toml":
		data, err = toml.Marshal(cfg)
	default:
		data, err = yaml.Marshal(cfg)
	}
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}

func legacyUnsetConfig(path, key string) error {
	cfg, err := loadConfigFile(path)
	if err != nil {
		return err
	}
	parts, err := editorconfig.Parse(key)
	if err != nil {
		return err
	}
	editorconfig.Unset(cfg, parts)
	return writeConfigFile(path, cfg)
}

// legacyApplyValue is the real implementation used by the legacy `set` path.
// It is kept separate from legacyUnsetConfig so the `set` and `unset` flows
// can evolve independently without sharing a boolean toggle.
func legacyApplyValue(path, key, value string) error {
	cfg, err := loadConfigFile(path)
	if err != nil {
		return err
	}
	parts, err := editorconfig.Parse(key)
	if err != nil {
		return err
	}
	editorconfig.Set(cfg, parts, editorconfig.ParseScalar(value))
	return writeConfigFile(path, cfg)
}
