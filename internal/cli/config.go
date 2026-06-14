package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/pelletier/go-toml/v2"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

func (a *App) configCommand(state *globalState) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "config",
		Aliases: []string{"cf"},
		Short:   "Manage CAM configuration files",
	}
	cmd.AddCommand(&cobra.Command{Use: "list", Short: "List configuration files", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		for _, p := range []string{
			filepath.Join(configDir(), "providers.json"),
			filepath.Join(configDir(), "config.yaml"),
			filepath.Join(os.Getenv("HOME"), ".env"),
		} {
			fmt.Fprintln(cmd.OutOrStdout(), p)
		}
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "validate", Short: "Validate configuration", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		if _, err := loadStructuredConfig(state.configPath); err != nil {
			return err
		}
		fmt.Fprintln(cmd.OutOrStdout(), "Configuration is valid")
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "show", Short: "Show configuration", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		data, err := os.ReadFile(resolveConfigPath(state.configPath))
		if err != nil {
			return err
		}
		_, err = cmd.OutOrStdout().Write(data)
		return err
	}})
	cmd.AddCommand(&cobra.Command{Use: "set KEY=VALUE", Short: "Set a configuration key", Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		parts := strings.SplitN(args[0], "=", 2)
		if len(parts) != 2 || strings.TrimSpace(parts[0]) == "" {
			return fmt.Errorf("expected KEY=VALUE")
		}
		cfg, err := loadStructuredConfig(state.configPath)
		if err != nil {
			return err
		}
		setPath(cfg, strings.Split(parts[0], "."), parseScalar(parts[1]))
		if err := writeStructuredConfig(resolveConfigPath(state.configPath), cfg); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Updated %s\n", parts[0])
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "unset KEY", Short: "Unset a configuration key", Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := loadStructuredConfig(state.configPath)
		if err != nil {
			return err
		}
		unsetPath(cfg, strings.Split(args[0], "."))
		if err := writeStructuredConfig(resolveConfigPath(state.configPath), cfg); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Removed %s\n", args[0])
		return nil
	}})
	return cmd
}

func configDir() string {
	if dir := os.Getenv("CAM_CONFIG_DIR"); dir != "" {
		return dir
	}
	return filepath.Join(os.Getenv("HOME"), ".config", "code-agent-manager")
}

func resolveConfigPath(path string) string {
	if path != "" {
		return path
	}
	return filepath.Join(configDir(), "config.yaml")
}

func loadStructuredConfig(path string) (map[string]any, error) {
	path = resolveConfigPath(path)
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

func writeStructuredConfig(path string, cfg map[string]any) error {
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

func setPath(root map[string]any, path []string, value any) {
	cursor := root
	for _, part := range path[:len(path)-1] {
		next, ok := cursor[part].(map[string]any)
		if !ok {
			next = map[string]any{}
			cursor[part] = next
		}
		cursor = next
	}
	cursor[path[len(path)-1]] = value
}

func unsetPath(root map[string]any, path []string) {
	cursor := root
	for _, part := range path[:len(path)-1] {
		next, ok := cursor[part].(map[string]any)
		if !ok {
			return
		}
		cursor = next
	}
	delete(cursor, path[len(path)-1])
}

func parseScalar(raw string) any {
	if i, err := strconv.Atoi(raw); err == nil {
		return i
	}
	if b, err := strconv.ParseBool(raw); err == nil {
		return b
	}
	return raw
}

func (a *App) managementCommand(group, alias string, state *globalState) *cobra.Command {
	cmd := &cobra.Command{Use: group, Aliases: []string{alias}, Short: "Manage " + group + " configurations"}
	plural := group + "s"
	cmd.AddCommand(&cobra.Command{Use: "list", Short: "List installed " + plural, Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		items, err := loadStringStore(state.storePath, group)
		if err != nil {
			return err
		}
		if len(items) == 0 {
			fmt.Fprintf(cmd.OutOrStdout(), "No %s installed\n", plural)
			return nil
		}
		sort.Strings(items)
		for _, item := range items {
			fmt.Fprintln(cmd.OutOrStdout(), item)
		}
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "install NAME", Short: "Install " + group, Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		items, err := loadStringStore(state.storePath, group)
		if err != nil {
			return err
		}
		items = addUnique(items, args[0])
		if err := writeStringStore(state.storePath, group, items); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Installed %s\n", args[0])
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "remove NAME", Aliases: []string{"uninstall", "delete"}, Short: "Remove " + group, Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		items, err := loadStringStore(state.storePath, group)
		if err != nil {
			return err
		}
		items = removeString(items, args[0])
		if err := writeStringStore(state.storePath, group, items); err != nil {
			return err
		}
		fmt.Fprintf(cmd.OutOrStdout(), "Removed %s\n", args[0])
		return nil
	}})
	cmd.AddCommand(&cobra.Command{Use: "show NAME", Short: "Show " + group, Args: cobra.ExactArgs(1), RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Fprintf(cmd.OutOrStdout(), "%s: %s\n", group, args[0])
		return nil
	}})
	return cmd
}

type genericStore map[string][]string

func resolveStorePath(path, group string) string {
	if path != "" {
		return path
	}
	return filepath.Join(os.Getenv("HOME"), ".config", "code-agent-manager", group+"s.json")
}

func loadStringStore(path, group string) ([]string, error) {
	path = resolveStorePath(path, group)
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	store := genericStore{}
	if err := json.Unmarshal(data, &store); err != nil {
		return nil, err
	}
	return store[group], nil
}

func writeStringStore(path, group string, items []string) error {
	path = resolveStorePath(path, group)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	store := genericStore{group: items}
	data, err := json.MarshalIndent(store, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}

func addUnique(items []string, item string) []string {
	for _, existing := range items {
		if existing == item {
			return items
		}
	}
	return append(items, item)
}

func removeString(items []string, item string) []string {
	out := items[:0]
	for _, existing := range items {
		if existing != item {
			out = append(out, existing)
		}
	}
	return out
}
