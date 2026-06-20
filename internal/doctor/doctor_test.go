package doctor_test

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/appstate"
	"github.com/chat2anyllm/code-agent-manager/internal/doctor"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

type fakeReporter struct {
	headers []string
	infos   []string
	passes  []string
	warns   []string
	fails   []string
}

func (f *fakeReporter) Header(msg string)     { f.headers = append(f.headers, msg) }
func (f *fakeReporter) Info(msg string)       { f.infos = append(f.infos, msg) }
func (f *fakeReporter) Pass(msg string)       { f.passes = append(f.passes, msg) }
func (f *fakeReporter) Warn(msg, hint string) { f.warns = append(f.warns, msg) }
func (f *fakeReporter) Fail(msg, hint string) { f.fails = append(f.fails, msg) }

func contains(slice []string, substr string) bool {
	for _, s := range slice {
		if strings.Contains(s, substr) {
			return true
		}
	}
	return false
}

func TestRunInvokesEveryCheckAndSumsIssues(t *testing.T) {
	r := &fakeReporter{}
	a := stubCheck{name: "A", issues: 1}
	b := stubCheck{name: "B", issues: 2}
	got := doctor.Run(context.Background(), r, []doctor.Check{a, b})
	if got != 3 {
		t.Fatalf("total issues = %d, want 3", got)
	}
	if len(r.headers) != 2 {
		t.Fatalf("headers = %v, want 2 entries", r.headers)
	}
}

type stubCheck struct {
	name   string
	issues int
}

func (s stubCheck) Name() string { return s.name }
func (s stubCheck) Run(_ context.Context, r doctor.Reporter) doctor.Result {
	r.Pass(s.name + " ran")
	return doctor.Result{Issues: s.issues}
}

func TestInstallationCheck(t *testing.T) {
	r := &fakeReporter{}
	check := doctor.InstallationCheck{Version: "1.2.3", HostExe: "/usr/local/bin/cam"}
	res := check.Run(context.Background(), r)
	if res.Issues != 0 {
		t.Fatalf("expected no issues, got %d", res.Issues)
	}
	if !contains(r.passes, "version: 1.2.3") {
		t.Fatalf("missing version pass: %v", r.passes)
	}
	if !contains(r.passes, "Executable: /usr/local/bin/cam") {
		t.Fatalf("missing exe pass: %v", r.passes)
	}
}

func TestConfigCheckMissingFile(t *testing.T) {
	r := &fakeReporter{}
	res := doctor.ConfigCheck{Path: filepath.Join(t.TempDir(), "missing.db")}.Run(context.Background(), r)
	if res.Issues == 0 {
		t.Fatal("expected issue for missing file")
	}
	if !contains(r.fails, "SQLite store not found") {
		t.Fatalf("missing fail message: %v", r.fails)
	}
}

func TestConfigCheckParsesValidFile(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "providers.db")
	store := appstate.New(dbPath)
	if err := store.Init(context.Background()); err != nil {
		t.Fatal(err)
	}
	r := &fakeReporter{}
	res := doctor.ConfigCheck{Path: dbPath}.Run(context.Background(), r)
	if res.Issues != 0 {
		t.Fatalf("expected 0 issues, got %d (warns=%v fails=%v)", res.Issues, r.warns, r.fails)
	}
	if !contains(r.passes, "SQLite store") {
		t.Fatalf("expected SQLite store pass, got %v", r.passes)
	}
}

func TestEnvCheckFallbackToHome(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	if err := os.WriteFile(filepath.Join(home, ".env"), []byte("FOO=bar\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	other := t.TempDir()
	if err := os.MkdirAll(filepath.Join(other, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	wd, _ := os.Getwd()
	if err := os.Chdir(other); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(wd) })

	r := &fakeReporter{}
	res := doctor.EnvCheck{}.Run(context.Background(), r)
	if runtime.GOOS == "windows" {
		if res.Issues != 1 || !contains(r.warns, "Environment file permissions") {
			t.Fatalf("expected Windows permission warning, got issues=%d warns=%v", res.Issues, r.warns)
		}
	} else if res.Issues != 0 {
		t.Fatalf("expected 0 issues, got %d (warns=%v)", res.Issues, r.warns)
	}
	if !contains(r.passes, ".env") {
		t.Fatalf("expected env file pass, got %v", r.passes)
	}
}

func TestEnvCheckMissing(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("CAM_CONFIG_DIR", filepath.Join(home, "cfg"))
	other := t.TempDir()
	if err := os.MkdirAll(filepath.Join(other, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	wd, _ := os.Getwd()
	if err := os.Chdir(other); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(wd) })

	r := &fakeReporter{}
	res := doctor.EnvCheck{}.Run(context.Background(), r)
	if res.Issues == 0 || !contains(r.warns, "No .env file found") {
		t.Fatalf("expected missing-env warning, got warns=%v issues=%d", r.warns, res.Issues)
	}
}

func TestEndpointFormatCheck(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"ok":      {Endpoint: "https://example.com"},
		"missing": {},
		"bad":     {Endpoint: "ftp://invalid"},
	}}
	r := &fakeReporter{}
	res := doctor.EndpointFormatCheck{File: file}.Run(context.Background(), r)
	if res.Issues != 2 {
		t.Fatalf("issues = %d, want 2 (warns=%v fails=%v)", res.Issues, r.warns, r.fails)
	}
	if !contains(r.passes, "ok") {
		t.Fatalf("ok endpoint should pass, got %v", r.passes)
	}
}

func TestCacheCheckCountsFiles(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "a"), []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "b"), []byte("world!"), 0o600); err != nil {
		t.Fatal(err)
	}
	r := &fakeReporter{}
	res := doctor.CacheCheck{Dir: dir}.Run(context.Background(), r)
	if res.Issues != 0 {
		t.Fatalf("issues = %d, want 0", res.Issues)
	}
	if !contains(r.passes, "across 2 files") {
		t.Fatalf("expected file count pass, got %v", r.passes)
	}
}

func TestCacheCheckMissingDirIsInfo(t *testing.T) {
	r := &fakeReporter{}
	doctor.CacheCheck{Dir: filepath.Join(t.TempDir(), "missing")}.Run(context.Background(), r)
	if !contains(r.infos, "Cache directory does not yet exist") {
		t.Fatalf("expected info on missing cache, got %v", r.infos)
	}
}

func TestGeminiAuthMatrix(t *testing.T) {
	tests := []struct {
		name     string
		env      map[string]string
		wantPass string
		wantWarn string
	}{
		{
			name:     "api key only",
			env:      map[string]string{"GEMINI_API_KEY": "k"},
			wantPass: "GEMINI_API_KEY",
		},
		{
			name: "all vertex vars without file",
			env: map[string]string{
				"GOOGLE_APPLICATION_CREDENTIALS": "/missing/creds.json",
				"GOOGLE_CLOUD_PROJECT":           "p",
				"GOOGLE_CLOUD_LOCATION":          "us",
				"GOOGLE_GENAI_USE_VERTEXAI":      "1",
			},
			wantWarn: "GOOGLE_APPLICATION_CREDENTIALS file does not exist",
		},
		{
			name:     "partial vertex",
			env:      map[string]string{"GOOGLE_CLOUD_PROJECT": "p"},
			wantWarn: "Partial Vertex AI configuration",
		},
		{
			name:     "nothing",
			env:      map[string]string{},
			wantWarn: "No Gemini or Vertex authentication detected",
		},
	}
	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			r := &fakeReporter{}
			doctor.GeminiAuthCheck{Env: func(k string) string { return tc.env[k] }}.Run(context.Background(), r)
			if tc.wantPass != "" && !contains(r.passes, tc.wantPass) {
				t.Fatalf("expected pass containing %q, got %v", tc.wantPass, r.passes)
			}
			if tc.wantWarn != "" && !contains(r.warns, tc.wantWarn) {
				t.Fatalf("expected warn containing %q, got %v", tc.wantWarn, r.warns)
			}
		})
	}
}

func TestCopilotAuthCheck(t *testing.T) {
	r := &fakeReporter{}
	doctor.CopilotAuthCheck{Env: func(k string) string {
		if k == "GITHUB_TOKEN" {
			return "x"
		}
		return ""
	}}.Run(context.Background(), r)
	if !contains(r.passes, "GITHUB_TOKEN") {
		t.Fatalf("expected pass for GITHUB_TOKEN, got %v", r.passes)
	}

	r2 := &fakeReporter{}
	doctor.CopilotAuthCheck{Env: func(string) string { return "" }}.Run(context.Background(), r2)
	if !contains(r2.warns, "GITHUB_TOKEN is not set") {
		t.Fatalf("expected warning, got %v", r2.warns)
	}
}

func TestToolsAvailableCheckUsesLookup(t *testing.T) {
	r := &fakeReporter{}
	res := doctor.ToolsAvailableCheck{
		Tools: []doctor.ToolEntry{
			{Name: "claude", Command: "claude"},
			{Name: "ghost", Command: "ghost"},
		},
		Lookup: func(name string) (string, error) {
			if name == "claude" {
				return "/usr/bin/claude", nil
			}
			return "", errors.New("not found")
		},
	}.Run(context.Background(), r)
	if res.Issues != 1 {
		t.Fatalf("issues = %d, want 1", res.Issues)
	}
	if !contains(r.passes, "claude is installed") {
		t.Fatalf("expected pass, got %v", r.passes)
	}
	if !contains(r.warns, "ghost is not installed") {
		t.Fatalf("expected warn, got %v", r.warns)
	}
}

func TestToolsAvailableCheckDefaultsToBundled(t *testing.T) {
	r := &fakeReporter{}
	res := doctor.ToolsAvailableCheck{
		Lookup: func(string) (string, error) {
			return "", fmt.Errorf("none")
		},
	}.Run(context.Background(), r)
	if res.Issues == 0 {
		t.Fatal("expected at least one warning when no tool exists")
	}
}
