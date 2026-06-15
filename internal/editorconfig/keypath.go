package editorconfig

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// Parse splits a dotted key path into its components, supporting TOML-style
// quoted segments so users can address keys that contain dots or special
// characters (e.g. codex.profiles."alibaba/glm-4.5".model).
func Parse(raw string) ([]string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, fmt.Errorf("editorconfig: empty key path")
	}
	var parts []string
	var buf strings.Builder
	var inQuote bool
	var inBracket bool
	for i := 0; i < len(raw); i++ {
		ch := raw[i]
		switch {
		case ch == '"' && (i == 0 || raw[i-1] != '\\'):
			inQuote = !inQuote
		case ch == '[' && !inQuote:
			inBracket = true
			buf.WriteByte(ch)
		case ch == ']' && !inQuote:
			inBracket = false
			buf.WriteByte(ch)
		case ch == '.' && !inQuote && !inBracket:
			if buf.Len() == 0 {
				return nil, fmt.Errorf("editorconfig: empty segment in %q", raw)
			}
			parts = append(parts, buf.String())
			buf.Reset()
		default:
			if ch == '\\' && i+1 < len(raw) && raw[i+1] == '"' {
				buf.WriteByte('"')
				i++
				continue
			}
			buf.WriteByte(ch)
		}
	}
	if inQuote {
		return nil, fmt.Errorf("editorconfig: unterminated quote in %q", raw)
	}
	if buf.Len() > 0 {
		parts = append(parts, buf.String())
	}
	if len(parts) == 0 {
		return nil, fmt.Errorf("editorconfig: empty key path")
	}
	return parts, nil
}

// Get walks data using parts and returns the leaf value plus whether it was
// found.  Intermediate non-map values cause a not-found result.
func Get(data map[string]any, parts []string) (any, bool) {
	cursor := any(data)
	for _, part := range parts {
		m, ok := cursor.(map[string]any)
		if !ok {
			return nil, false
		}
		val, ok := m[part]
		if !ok {
			return nil, false
		}
		cursor = val
	}
	return cursor, true
}

// Set assigns value at parts inside data, creating intermediate maps as
// needed.  Existing non-map intermediates are overwritten with a fresh map.
func Set(data map[string]any, parts []string, value any) {
	if len(parts) == 0 {
		return
	}
	cursor := data
	for _, part := range parts[:len(parts)-1] {
		next, ok := cursor[part].(map[string]any)
		if !ok {
			next = map[string]any{}
			cursor[part] = next
		}
		cursor = next
	}
	cursor[parts[len(parts)-1]] = value
}

// Unset removes the leaf at parts from data and reports whether the key
// existed.  Intermediate maps are not pruned.
func Unset(data map[string]any, parts []string) bool {
	if len(parts) == 0 {
		return false
	}
	cursor := data
	for _, part := range parts[:len(parts)-1] {
		next, ok := cursor[part].(map[string]any)
		if !ok {
			return false
		}
		cursor = next
	}
	leaf := parts[len(parts)-1]
	if _, ok := cursor[leaf]; !ok {
		return false
	}
	delete(cursor, leaf)
	return true
}

// Flatten returns data as a map of dotted key paths to stringified values,
// prefixed with prefix.  Slices are flattened by index.
func Flatten(data map[string]any, prefix string) map[string]string {
	out := map[string]string{}
	flattenInto(data, prefix, out)
	return out
}

func flattenInto(value any, prefix string, out map[string]string) {
	switch typed := value.(type) {
	case map[string]any:
		for k, v := range typed {
			next := k
			if prefix != "" {
				next = prefix + "." + k
			}
			flattenInto(v, next, out)
		}
	case []any:
		for i, v := range typed {
			next := strconv.Itoa(i)
			if prefix != "" {
				next = prefix + "." + strconv.Itoa(i)
			}
			flattenInto(v, next, out)
		}
	default:
		out[prefix] = fmt.Sprintf("%v", typed)
	}
}

var intRE = regexp.MustCompile(`^-?\d+$`)
var floatRE = regexp.MustCompile(`^-?\d+\.\d+$`)

// ParseScalar coerces a string into a typed value: bool > int > float > string.
func ParseScalar(raw string) any {
	if raw == "true" {
		return true
	}
	if raw == "false" {
		return false
	}
	if intRE.MatchString(raw) {
		if v, err := strconv.Atoi(raw); err == nil {
			return v
		}
	}
	if floatRE.MatchString(raw) {
		if v, err := strconv.ParseFloat(raw, 64); err == nil {
			return v
		}
	}
	return raw
}
