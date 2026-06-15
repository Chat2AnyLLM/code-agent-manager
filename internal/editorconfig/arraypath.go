package editorconfig

import (
	"strings"
)

// Segment represents one component of a key path.  Plain keys have IsArray
// false.  Array segments carry either Append (the [+] operator) or a
// MatchKey/MatchValue pair (the [k=v] operator).
type Segment struct {
	Key        string // map key holding the array
	IsArray    bool
	Append     bool   // true for [+]
	MatchKey   string // non-empty for [k=v]
	MatchValue string
}

// ParseSegment classifies one already-split dotted-key segment.
// "plain"           -> {Key:"plain"}
// "models[+]"       -> {Key:"models", IsArray:true, Append:true}
// "models[k=v]"     -> {Key:"models", IsArray:true, MatchKey:"k", MatchValue:"v"}
func ParseSegment(raw string) Segment {
	open := strings.IndexByte(raw, '[')
	closeIdx := strings.LastIndexByte(raw, ']')
	if open < 0 || closeIdx < 0 || closeIdx < open {
		return Segment{Key: raw}
	}
	key := raw[:open]
	body := raw[open+1 : closeIdx]
	if body == "+" {
		return Segment{Key: key, IsArray: true, Append: true}
	}
	eq := strings.IndexByte(body, '=')
	if eq < 0 {
		return Segment{Key: raw}
	}
	return Segment{
		Key:        key,
		IsArray:    true,
		MatchKey:   strings.TrimSpace(body[:eq]),
		MatchValue: strings.TrimSpace(body[eq+1:]),
	}
}

// SetArray walks data using parts (which may include array segments) and
// assigns value at the leaf, creating maps and arrays as needed.  It is the
// array-aware companion to Set.
func SetArray(data map[string]any, parts []string, value any) {
	if len(parts) == 0 {
		return
	}
	cursor := any(data)
	for i, raw := range parts {
		seg := ParseSegment(raw)
		isLeaf := i == len(parts)-1
		cursorMap, ok := cursor.(map[string]any)
		if !ok {
			return // can't descend through scalars
		}
		if !seg.IsArray {
			if isLeaf {
				cursorMap[seg.Key] = value
				return
			}
			next, ok := cursorMap[seg.Key].(map[string]any)
			if !ok {
				next = map[string]any{}
				cursorMap[seg.Key] = next
			}
			cursor = next
			continue
		}
		// Array segment.
		arr, _ := cursorMap[seg.Key].([]any)
		var elem map[string]any
		var idx int
		switch {
		case seg.Append:
			elem = map[string]any{}
			arr = append(arr, elem)
			idx = len(arr) - 1
		default: // MatchKey=MatchValue
			idx = -1
			for j, raw := range arr {
				m, ok := raw.(map[string]any)
				if !ok {
					continue
				}
				if asString(m[seg.MatchKey]) == seg.MatchValue {
					idx = j
					elem = m
					break
				}
			}
			if idx < 0 {
				elem = map[string]any{seg.MatchKey: seg.MatchValue}
				arr = append(arr, elem)
				idx = len(arr) - 1
			}
		}
		cursorMap[seg.Key] = arr
		if isLeaf {
			arr[idx] = value
			cursorMap[seg.Key] = arr
			return
		}
		cursor = elem
	}
}

func asString(v any) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
