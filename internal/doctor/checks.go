package doctor

import (
	"context"
	_ "embed"
	"errors"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/appstate"
	"github.com/chat2anyllm/code-agent-manager/internal/envfile"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
	"github.com/chat2anyllm/code-agent-manager/internal/providers"
	"gopkg.in/yaml.v3"
)

//go:embed embed/tools.yaml
var bundledToolsYAML []byte

// InstallationCheck reports CAM's version and the host's Go runtime version.
// Version is the binary's own version string; HostExe is os.Executable() at
// runtime, but tests may override either field to keep output deterministic.
type InstallationCheck struct {
	Version string
	HostExe string
}

func (c InstallationCheck) Name() string { return "Installation Check" }
func (c InstallationCheck) Run(_ context.Context, r Reporter) Result {
	res := Result{}
	version := c.Version
	if version == "" {
		version = "dev"
	}
	r.Pass(fmt.Sprintf("Code Assistant Manager installed (version: %s)", version))
	r.Pass(fmt.Sprintf("Go runtime: %s", runtime.Version()))
	exe := c.HostExe
	if exe == "" {
		if e, err := os.Executable(); err == nil {
			exe = e
		} else {
			res.Issues++
			r.Warn("Unable to determine executable path", err.Error())
		}
	}
	if exe != "" {
		r.Pass(fmt.Sprintf("Executable: %s", exe))
	}
	return res
}

// ConfigCheck verifies that the SQLite app state store exists and has the
// correct schema. The store path is resolved from --store (or defaults to
// cam.db in the config directory).
type ConfigCheck struct {
	Path string
}

func (c ConfigCheck) Name() string { return "Configuration Check" }
func (c ConfigCheck) Run(ctx context.Context, r Reporter) Result {
	res := Result{}
	store := appstate.New(c.Path)
	if !pathutil.Exists(store.Path()) {
		res.Issues++
		r.Fail("SQLite store not found", "Run 'cam provider init' to create it, or use --store to specify the path")
		return res
	}
	r.Pass(fmt.Sprintf("SQLite store: %s", store.Path()))
	file, err := store.ListProviders(ctx)
	if err != nil {
		res.Issues++
		r.Fail("SQLite store failed to read providers", err.Error())
		return res
	}
	r.Pass(fmt.Sprintf("Providers in store: %d", len(file.Endpoints)))
	return res
}

// EnvCheck looks for a .env file via envfile.Find and warns when permissions
// look too permissive.
type EnvCheck struct {
	Custom string
}

func (c EnvCheck) Name() string { return "Environment File Check" }
func (c EnvCheck) Run(_ context.Context, r Reporter) Result {
	res := Result{}
	path, err := envfile.Find(c.Custom, false)
	if err != nil {
		if errors.Is(err, envfile.ErrNotFound) {
			res.Issues++
			r.Warn("No .env file found", "Create one for sensitive credentials")
			return res
		}
		res.Issues++
		r.Fail("Unable to locate .env", err.Error())
		return res
	}
	r.Pass(fmt.Sprintf("Environment file found: %s", path))
	if info, err := os.Stat(path); err == nil {
		perms := info.Mode().Perm()
		if perms == 0o600 || perms == 0o400 {
			r.Pass("Environment file has secure permissions")
		} else {
			res.Issues++
			r.Warn(fmt.Sprintf("Environment file permissions: %o", perms),
				"Consider chmod 600 for secure storage of API keys")
		}
	}
	return res
}

// EndpointFormatCheck verifies every endpoint URL starts with http(s)://.
type EndpointFormatCheck struct {
	File providers.File
}

func (c EndpointFormatCheck) Name() string { return "Endpoint Format Check" }
func (c EndpointFormatCheck) Run(_ context.Context, r Reporter) Result {
	res := Result{}
	if len(c.File.Endpoints) == 0 {
		r.Info("No endpoints to check")
		return res
	}
	for _, name := range c.File.SortedNames() {
		ep := c.File.Endpoints[name]
		if ep.Endpoint == "" {
			res.Issues++
			r.Warn(fmt.Sprintf("%s has no endpoint URL", name),
				"Add a provider endpoint with 'cam provider add NAME --endpoint URL'")
			continue
		}
		parsed, err := url.Parse(ep.Endpoint)
		if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") {
			res.Issues++
			r.Fail(fmt.Sprintf("%s endpoint URL invalid: %s", name, ep.Endpoint),
				"Use http:// or https://")
			continue
		}
		r.Pass(fmt.Sprintf("%s endpoint URL format is valid", name))
	}
	return res
}

// CacheCheck reports the size of the CAM cache directory.
type CacheCheck struct {
	Dir string
}

func (c CacheCheck) Name() string { return "Cache Check" }
func (c CacheCheck) Run(_ context.Context, r Reporter) Result {
	res := Result{}
	dir := c.Dir
	if dir == "" {
		dir = filepath.Join(pathutil.CacheDir(), "repos")
	}
	if !pathutil.Exists(dir) {
		r.Info(fmt.Sprintf("Cache directory does not yet exist: %s", dir))
		return res
	}
	var (
		fileCount int
		totalSize int64
	)
	err := filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return nil
		}
		fileCount++
		totalSize += info.Size()
		return nil
	})
	if err != nil {
		res.Issues++
		r.Warn("Unable to walk cache directory", err.Error())
		return res
	}
	r.Pass(fmt.Sprintf("Cache directory exists: %s", dir))
	r.Pass(fmt.Sprintf("Cache size: %s across %d files", humanBytes(totalSize), fileCount))
	return res
}

// GeminiAuthCheck reports whether Gemini or Vertex AI credentials are
// configured.  Env defaults to os.Getenv but tests may override it.
type GeminiAuthCheck struct {
	Env func(string) string
}

func (c GeminiAuthCheck) Name() string { return "Gemini / Vertex Authentication Check" }
func (c GeminiAuthCheck) Run(_ context.Context, r Reporter) Result {
	env := c.Env
	if env == nil {
		env = os.Getenv
	}
	res := Result{}
	if env("GEMINI_API_KEY") != "" {
		r.Pass("GEMINI_API_KEY is set in the environment")
		return res
	}
	vertexVars := []string{
		"GOOGLE_APPLICATION_CREDENTIALS",
		"GOOGLE_CLOUD_PROJECT",
		"GOOGLE_CLOUD_LOCATION",
		"GOOGLE_GENAI_USE_VERTEXAI",
	}
	present := []string{}
	missing := []string{}
	for _, v := range vertexVars {
		if env(v) != "" {
			present = append(present, v)
		} else {
			missing = append(missing, v)
		}
	}
	if len(present) == len(vertexVars) {
		gac := env("GOOGLE_APPLICATION_CREDENTIALS")
		if gac != "" {
			if pathutil.Exists(pathutil.Expand(gac)) {
				r.Pass("Vertex AI credentials configured (GOOGLE_APPLICATION_CREDENTIALS file exists)")
			} else {
				res.Issues++
				r.Warn("GOOGLE_APPLICATION_CREDENTIALS file does not exist",
					"Check path: "+gac)
			}
		} else {
			r.Pass("Vertex AI variables are set")
		}
		return res
	}
	if len(present) > 0 {
		res.Issues++
		r.Warn("Partial Vertex AI configuration present (missing: "+strings.Join(missing, ", ")+")",
			"Set all required GOOGLE_* vars or use GEMINI_API_KEY")
		return res
	}
	res.Issues++
	r.Warn("No Gemini or Vertex authentication detected",
		"Set GEMINI_API_KEY or configure Vertex AI environment variables")
	return res
}

// CopilotAuthCheck reports whether GITHUB_TOKEN is set.
type CopilotAuthCheck struct {
	Env func(string) string
}

func (c CopilotAuthCheck) Name() string { return "GitHub Copilot Authentication Check" }
func (c CopilotAuthCheck) Run(_ context.Context, r Reporter) Result {
	env := c.Env
	if env == nil {
		env = os.Getenv
	}
	res := Result{}
	if env("GITHUB_TOKEN") != "" {
		r.Pass("GITHUB_TOKEN is set in the environment")
		return res
	}
	res.Issues++
	r.Warn("GITHUB_TOKEN is not set",
		"Set GITHUB_TOKEN environment variable for GitHub Copilot API access")
	return res
}

// ToolsAvailableCheck reports which configured tools resolve via PATH.  By
// default the bundled tools.yaml is consulted; tests may supply Tools
// directly to avoid reading the embedded file.
type ToolsAvailableCheck struct {
	Tools  []ToolEntry
	Lookup func(string) (string, error)
}

// ToolEntry is the subset of tools.yaml we care about for availability.
type ToolEntry struct {
	Name    string
	Command string
}

func (c ToolsAvailableCheck) Name() string { return "Tool Installation Check" }
func (c ToolsAvailableCheck) Run(_ context.Context, r Reporter) Result {
	res := Result{}
	tools := c.Tools
	if len(tools) == 0 {
		parsed, err := loadBundledTools(bundledToolsYAML)
		if err != nil {
			res.Issues++
			r.Warn("Unable to parse bundled tools.yaml", err.Error())
			return res
		}
		tools = parsed
	}
	lookup := c.Lookup
	if lookup == nil {
		lookup = exec.LookPath
	}
	available := 0
	for _, t := range tools {
		if t.Command == "" {
			continue
		}
		if _, err := lookup(t.Command); err == nil {
			available++
			r.Pass(fmt.Sprintf("%s is installed", t.Name))
		} else {
			res.Issues++
			r.Warn(fmt.Sprintf("%s is not installed", t.Name),
				fmt.Sprintf("Run 'cam upgrade %s' to install", t.Name))
		}
	}
	r.Pass(fmt.Sprintf("Tools available: %d/%d", available, len(tools)))
	return res
}

type bundledToolsFile struct {
	Tools map[string]struct {
		Enabled    *bool  `yaml:"enabled"`
		CLICommand string `yaml:"cli_command"`
	} `yaml:"tools"`
}

func loadBundledTools(data []byte) ([]ToolEntry, error) {
	var parsed bundledToolsFile
	if err := yaml.Unmarshal(data, &parsed); err != nil {
		return nil, err
	}
	out := make([]ToolEntry, 0, len(parsed.Tools))
	for name, entry := range parsed.Tools {
		if entry.Enabled != nil && !*entry.Enabled {
			continue
		}
		cmd := entry.CLICommand
		if cmd == "" {
			cmd = name
		}
		out = append(out, ToolEntry{Name: name, Command: cmd})
	}
	return out, nil
}

func humanBytes(n int64) string {
	const unit = 1024.0
	if n < int64(unit) {
		return fmt.Sprintf("%d B", n)
	}
	div, exp := unit, 0
	for v := float64(n) / unit; v >= unit; v /= unit {
		div *= unit
		exp++
	}
	suffixes := []string{"KB", "MB", "GB", "TB", "PB"}
	if exp >= len(suffixes) {
		exp = len(suffixes) - 1
	}
	return fmt.Sprintf("%.2f %s", float64(n)/div, suffixes[exp])
}
