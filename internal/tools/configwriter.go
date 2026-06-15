package tools

import (
	"sort"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
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
