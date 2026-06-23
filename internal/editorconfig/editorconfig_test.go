package editorconfig_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
)

func TestParseDottedKeyPath(t *testing.T) {
	tests := []struct {
		in   string
		want []string
	}{
		{in: "foo", want: []string{"foo"}},
		{in: "foo.bar", want: []string{"foo", "bar"}},
		{in: "foo.bar.baz", want: []string{"foo", "bar", "baz"}},
		{in: `codex.profiles."alibaba/glm-4.5".model`, want: []string{"codex", "profiles", "alibaba/glm-4.5", "model"}},
		{in: `codex.profiles."alibaba/deepseek-v3.2-exp"`, want: []string{"codex", "profiles", "alibaba/deepseek-v3.2-exp"}},
	}
	for _, tc := range tests {
		tc := tc
		t.Run(tc.in, func(t *testing.T) {
			t.Parallel()
			got, err := editorconfig.Parse(tc.in)
			if err != nil {
				t.Fatalf("Parse err = %v", err)
			}
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("Parse(%q) = %v, want %v", tc.in, got, tc.want)
			}
		})
	}
}

func TestParseRejectsInvalid(t *testing.T) {
	for _, raw := range []string{"", " ", ".", "..foo", `"unterminated`} {
		raw := raw
		t.Run(strings.ReplaceAll(raw, " ", "_space_"), func(t *testing.T) {
			t.Parallel()
			if _, err := editorconfig.Parse(raw); err == nil {
				t.Fatalf("expected error for %q", raw)
			}
		})
	}
}

func TestSetGetUnsetRoundTrip(t *testing.T) {
	data := map[string]any{}
	parts := []string{"a", "b", "c"}
	editorconfig.Set(data, parts, 42)
	got, ok := editorconfig.Get(data, parts)
	if !ok || got != 42 {
		t.Fatalf("Get after Set = %v %v, want 42 true", got, ok)
	}
	if !editorconfig.Unset(data, parts) {
		t.Fatal("Unset should report true")
	}
	if _, ok := editorconfig.Get(data, parts); ok {
		t.Fatal("Get after Unset should be false")
	}
}

func TestUnsetMissingKeyReturnsFalse(t *testing.T) {
	if editorconfig.Unset(map[string]any{}, []string{"x"}) {
		t.Fatal("Unset on empty map should return false")
	}
	if editorconfig.Unset(map[string]any{"x": "y"}, []string{"x", "z"}) {
		t.Fatal("Unset on intermediate non-map should return false")
	}
}

func TestFlatten(t *testing.T) {
	data := map[string]any{
		"top": "value",
		"nested": map[string]any{
			"foo": "bar",
			"list": []any{
				map[string]any{"k": "v"},
				"second",
			},
		},
	}
	got := editorconfig.Flatten(data, "claude")
	want := map[string]string{
		"claude.top":             "value",
		"claude.nested.foo":      "bar",
		"claude.nested.list.0.k": "v",
		"claude.nested.list.1":   "second",
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("Flatten = %v, want %v", got, want)
	}
}

func TestParseScalar(t *testing.T) {
	tests := []struct {
		in   string
		want any
	}{
		{in: "true", want: true},
		{in: "false", want: false},
		{in: "0", want: 0},
		{in: "42", want: 42},
		{in: "-7", want: -7},
		{in: "3.14", want: 3.14},
		{in: "hello", want: "hello"},
		{in: "", want: ""},
	}
	for _, tc := range tests {
		tc := tc
		t.Run(tc.in, func(t *testing.T) {
			t.Parallel()
			got := editorconfig.ParseScalar(tc.in)
			if got != tc.want {
				t.Fatalf("ParseScalar(%q) = %v (%T), want %v (%T)", tc.in, got, got, tc.want, tc.want)
			}
		})
	}
}

func TestDefaultRegistryContainsThirteenEditors(t *testing.T) {
	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	got := r.Names()
	sort.Strings(got)
	want := []string{
		"claude", "codebuddy", "codex", "copilot", "crush", "cursor-agent",
		"droid", "gemini", "iflow", "neovate", "qodercli", "qwen", "zed",
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("registry names = %v, want %v", got, want)
	}
	for _, name := range want {
		tool, ok := r.Get(name)
		if !ok {
			t.Fatalf("Get(%q) returned false", name)
		}
		if tool.Name() != name {
			t.Fatalf("Get(%q).Name() = %q", name, tool.Name())
		}
		if len(tool.UserPaths()) == 0 {
			t.Fatalf("%s has no user paths", name)
		}
		if name == "codex" && tool.Format() != editorconfig.FormatTOML {
			t.Fatalf("codex format = %v, want toml", tool.Format())
		}
		if name != "codex" && tool.Format() != editorconfig.FormatJSON {
			t.Fatalf("%s format = %v, want json", name, tool.Format())
		}
	}
}

func TestJSONToolConfigRoundTrip(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	tool, _ := r.Get("claude")
	savedPath, err := tool.Set(editorconfig.UserScope, "tipsHistory.config-thinking-mode", "off")
	if err != nil {
		t.Fatalf("Set err = %v", err)
	}
	if savedPath != filepath.Join(home, ".claude.json") {
		t.Fatalf("savedPath = %q, want %q", savedPath, filepath.Join(home, ".claude.json"))
	}

	data, path, err := tool.Load(editorconfig.UserScope)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	if path != savedPath {
		t.Fatalf("Load path = %q, want %q", path, savedPath)
	}
	got, ok := editorconfig.Get(data, []string{"tipsHistory", "config-thinking-mode"})
	if !ok || got != "off" {
		t.Fatalf("Get after Set = %v %v", got, ok)
	}

	found, _, err := tool.Unset(editorconfig.UserScope, "tipsHistory.config-thinking-mode")
	if err != nil {
		t.Fatalf("Unset err = %v", err)
	}
	if !found {
		t.Fatal("Unset returned found=false")
	}
	if _, _, err := tool.Unset(editorconfig.UserScope, "tipsHistory.config-thinking-mode"); err != nil {
		t.Fatalf("Unset missing err = %v", err)
	}
}

func TestJSONToolConfigSetCoercedValuesPersistAsTyped(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	tool, _ := r.Get("claude")

	if _, err := tool.Set(editorconfig.UserScope, "feature.enabled", true); err != nil {
		t.Fatalf("Set bool err = %v", err)
	}
	if _, err := tool.Set(editorconfig.UserScope, "feature.threshold", 5); err != nil {
		t.Fatalf("Set int err = %v", err)
	}

	raw, err := os.ReadFile(filepath.Join(home, ".claude.json"))
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatal(err)
	}
	if got["feature"].(map[string]any)["enabled"] != true {
		t.Fatalf("enabled value = %v", got["feature"].(map[string]any)["enabled"])
	}
	if got["feature"].(map[string]any)["threshold"].(float64) != 5 {
		t.Fatalf("threshold value = %v", got["feature"].(map[string]any)["threshold"])
	}
}

func TestTOMLToolConfigRoundTripWithQuotedKey(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	tool, _ := r.Get("codex")
	if _, err := tool.Set(editorconfig.UserScope, `profiles."alibaba/glm-4.5".model`, "alibaba-glm-4.5"); err != nil {
		t.Fatalf("Set err = %v", err)
	}

	data, _, err := tool.Load(editorconfig.UserScope)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	got, ok := editorconfig.Get(data, []string{"profiles", "alibaba/glm-4.5", "model"})
	if !ok || got != "alibaba-glm-4.5" {
		t.Fatalf("Get after TOML Set = %v %v", got, ok)
	}

	found, _, err := tool.Unset(editorconfig.UserScope, `profiles."alibaba/glm-4.5".model`)
	if err != nil {
		t.Fatalf("Unset err = %v", err)
	}
	if !found {
		t.Fatal("Unset returned found=false on TOML")
	}
}

func TestProjectScopePath(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	tool, _ := r.Get("claude")
	if got := tool.ProjectPath(); !strings.HasSuffix(got, filepath.Join(".claude", "settings.json")) {
		t.Fatalf("ProjectPath = %q, want suffix .claude/settings.json", got)
	}
}

func TestUnsupportedScopeReturnsError(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	r, err := editorconfig.DefaultRegistry()
	if err != nil {
		t.Fatalf("DefaultRegistry err = %v", err)
	}
	tool, _ := r.Get("copilot")
	if _, err := tool.Set(editorconfig.ProjectScope, "x.y", "z"); err == nil {
		t.Fatal("Set with unsupported project scope should error")
	}
	if _, _, err := tool.Load(editorconfig.ProjectScope); err == nil {
		t.Fatal("Load with unsupported project scope should error")
	}
}
