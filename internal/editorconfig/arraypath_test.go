package editorconfig

import (
	"reflect"
	"testing"
)

func TestParseSegment_PlainKey(t *testing.T) {
	seg := ParseSegment("plain")
	if seg.Key != "plain" || seg.IsArray {
		t.Errorf("seg = %+v, want plain key", seg)
	}
}

func TestParseSegment_Append(t *testing.T) {
	seg := ParseSegment("models[+]")
	if seg.Key != "models" || !seg.IsArray || !seg.Append || seg.MatchKey != "" {
		t.Errorf("seg = %+v, want array append on 'models'", seg)
	}
}

func TestParseSegment_MatchByKey(t *testing.T) {
	seg := ParseSegment("customModels[displayName=foo/bar]")
	if seg.Key != "customModels" || !seg.IsArray || seg.Append {
		t.Errorf("seg = %+v, want array match", seg)
	}
	if seg.MatchKey != "displayName" || seg.MatchValue != "foo/bar" {
		t.Errorf("match = %s=%s, want displayName=foo/bar", seg.MatchKey, seg.MatchValue)
	}
}

func TestSetArray_AppendCreatesElement(t *testing.T) {
	data := map[string]any{}
	parts := []string{"customModels[+]", "name"}
	SetArray(data, parts, "alpha")
	got := data["customModels"].([]any)
	if len(got) != 1 {
		t.Fatalf("len = %d, want 1", len(got))
	}
	el := got[0].(map[string]any)
	if el["name"] != "alpha" {
		t.Errorf("el.name = %v, want alpha", el["name"])
	}
}

func TestSetArray_MatchUpsertsInPlace(t *testing.T) {
	data := map[string]any{
		"customModels": []any{
			map[string]any{"displayName": "x", "model": "old"},
			map[string]any{"displayName": "y", "model": "keep"},
		},
	}
	parts := []string{"customModels[displayName=x]", "model"}
	SetArray(data, parts, "new")
	got := data["customModels"].([]any)
	if len(got) != 2 {
		t.Fatalf("len = %d, want 2 (no append)", len(got))
	}
	el := got[0].(map[string]any)
	if el["model"] != "new" {
		t.Errorf("first.model = %v, want new", el["model"])
	}
	if got[1].(map[string]any)["model"] != "keep" {
		t.Errorf("second.model = %v, want keep", got[1].(map[string]any)["model"])
	}
}

func TestSetArray_MatchAppendsWhenAbsent(t *testing.T) {
	data := map[string]any{
		"customModels": []any{
			map[string]any{"displayName": "x"},
		},
	}
	parts := []string{"customModels[displayName=y]", "model"}
	SetArray(data, parts, "yval")
	got := data["customModels"].([]any)
	if len(got) != 2 {
		t.Fatalf("len = %d, want 2 (append)", len(got))
	}
	el := got[1].(map[string]any)
	if el["displayName"] != "y" {
		t.Errorf("new.displayName = %v, want y", el["displayName"])
	}
	if el["model"] != "yval" {
		t.Errorf("new.model = %v, want yval", el["model"])
	}
}

func TestSetArray_SameMatchSharesElement(t *testing.T) {
	// Two consecutive Sets with the same match clause must write to one element.
	data := map[string]any{}
	SetArray(data, []string{"customModels[displayName=foo]", "model"}, "m1")
	SetArray(data, []string{"customModels[displayName=foo]", "baseUrl"}, "https://x")
	got := data["customModels"].([]any)
	if len(got) != 1 {
		t.Fatalf("len = %d, want 1 element", len(got))
	}
	el := got[0].(map[string]any)
	if el["model"] != "m1" || el["baseUrl"] != "https://x" || el["displayName"] != "foo" {
		t.Errorf("el = %v", el)
	}
}

func TestParse_DispatchesArraySegments(t *testing.T) {
	// Top-level Parse must still split on dots; bracket content must not
	// confuse the dot splitter.
	parts, err := Parse("customModels[displayName=a.b/c-d].field")
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	want := []string{"customModels[displayName=a.b/c-d]", "field"}
	if !reflect.DeepEqual(parts, want) {
		t.Errorf("parts = %v, want %v", parts, want)
	}
}
