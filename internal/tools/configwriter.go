package tools

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	tomlv2 "github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"
)

// PlannedWrite is one upsert/remove that the writer will apply.
type PlannedWrite struct {
	KeyPath string // expanded key path (placeholders substituted)
	Value   any    // string|bool|int64|float64; nil for Remove
	Op      string // "upsert" | "remove"
}

// Plan resolves all placeholders and returns the ordered list of writes
// without touching disk. Used by --dry-run and Apply alike.
func Plan(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) ([]PlannedWrite, error) {
	if tool.ConfigTarget == nil {
		return nil, nil
	}
	ct := tool.ConfigTarget

	out := make([]PlannedWrite, 0, len(ct.Upsert)+len(ct.Remove))

	// Upserts.
	for rawKey, rawValue := range ct.Upsert {
		key := expandConfigPlaceholders(rawKey, endpoint, endpointName, model, apiKey)
		value := expandConfigPlaceholders(rawValue, endpoint, endpointName, model, apiKey)
		out = append(out, PlannedWrite{KeyPath: key, Value: coerceScalar(value), Op: "upsert"})
	}

	// Removes.
	for _, rawKey := range ct.Remove {
		key := expandConfigPlaceholders(rawKey, endpoint, endpointName, model, apiKey)
		out = append(out, PlannedWrite{KeyPath: key, Value: nil, Op: "remove"})
	}

	sort.Slice(out, func(i, j int) bool {
		return out[i].KeyPath < out[j].KeyPath
	})
	return out, nil
}

// expandConfigPlaceholders substitutes the five recognised placeholders. It
// is a superset of expandPlaceholders in launch.go (adds {endpoint_name} and
// {model_2}; model_2 is empty until callers thread a secondary model in).
func expandConfigPlaceholders(raw string, ep providers.Endpoint, endpointName, model, apiKey string) string {
	s := raw
	s = strings.ReplaceAll(s, "{endpoint}", ep.Endpoint)
	s = strings.ReplaceAll(s, "{endpoint_name}", endpointName)
	s = strings.ReplaceAll(s, "{api_key}", apiKey)
	s = strings.ReplaceAll(s, "{selected_model}", model)
	s = strings.ReplaceAll(s, "{model_2}", "")
	return s
}

// coerceScalar promotes a raw string into the most specific Go type that fits.
// Order: bool > int64 > float64 > string. Reuses editorconfig.ParseScalar
// but widens int to int64 so the marshallers emit `8192`, not the truncated
// platform int width.
func coerceScalar(raw string) any {
	v := editorconfig.ParseScalar(raw)
	if i, ok := v.(int); ok {
		return int64(i)
	}
	return v
}

// Apply writes the planned writes to tool.ConfigTarget.path atomically.
// Returns the written path or "" when tool has no config_target.
func Apply(tool Tool, plan []PlannedWrite) (string, error) {
	if tool.ConfigTarget == nil {
		return "", nil
	}
	ct := tool.ConfigTarget
	path := pathutil.Expand(ct.Path)

	data, err := readConfigFile(path, ct.Format)
	if err != nil {
		return "", err
	}

	for _, p := range plan {
		parts, err := editorconfig.Parse(p.KeyPath)
		if err != nil {
			return "", fmt.Errorf("configwriter: parse key %q: %w", p.KeyPath, err)
		}
		switch p.Op {
		case "upsert":
			if containsArraySegment(parts) {
				editorconfig.SetArray(data, parts, p.Value)
			} else {
				editorconfig.Set(data, parts, p.Value)
			}
		case "remove":
			editorconfig.Unset(data, parts)
		}
	}

	if err := writeConfigFile(path, ct.Format, data); err != nil {
		return "", err
	}
	return path, nil
}

// WriteConfig is Plan + Apply.  Used by cli/launch.go.
func WriteConfig(tool Tool, endpoint providers.Endpoint, endpointName, model, apiKey string) (string, error) {
	plan, err := Plan(tool, endpoint, endpointName, model, apiKey)
	if err != nil {
		return "", err
	}
	path, err := Apply(tool, plan)
	if err != nil {
		return "", err
	}
	if err := codexPostWrite(tool, endpointName, model, path); err != nil {
		return "", err
	}
	return path, nil
}

func containsArraySegment(parts []string) bool {
	for _, p := range parts {
		if seg := editorconfig.ParseSegment(p); seg.IsArray {
			return true
		}
	}
	return false
}

func readConfigFile(path, format string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]any{}, nil
		}
		return nil, fmt.Errorf("configwriter: read %s: %w", path, err)
	}
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	out := map[string]any{}
	switch format {
	case "json":
		if err := json.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	case "toml":
		if err := tomlv2.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	case "yaml":
		if err := yaml.Unmarshal(raw, &out); err != nil {
			return nil, fmt.Errorf("configwriter: parse %s: %w", path, err)
		}
	default:
		return nil, fmt.Errorf("configwriter: unknown format %q", format)
	}
	return out, nil
}

func writeConfigFile(path, format string, data map[string]any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("configwriter: mkdir %s: %w", filepath.Dir(path), err)
	}
	var encoded []byte
	var err error
	switch format {
	case "json":
		encoded, err = json.MarshalIndent(data, "", "  ")
		if err == nil {
			encoded = append(encoded, '\n')
		}
	case "toml":
		encoded, err = tomlv2.Marshal(data)
	case "yaml":
		encoded, err = yaml.Marshal(data)
	default:
		return fmt.Errorf("configwriter: unknown format %q", format)
	}
	if err != nil {
		return fmt.Errorf("configwriter: marshal %s: %w", path, err)
	}
	if err := os.WriteFile(path, encoded, 0o600); err != nil {
		return fmt.Errorf("configwriter: write %s: %w", path, err)
	}
	return nil
}
