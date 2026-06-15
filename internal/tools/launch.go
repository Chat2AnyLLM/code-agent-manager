package tools

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// LaunchEnv is the resolved environment for a single launch.  Env holds the
// fully merged env-var map; Inject holds the cli_parameters.injected entries
// with placeholders substituted.
type LaunchEnv struct {
	Tool     Tool
	Endpoint providers.Endpoint
	Model    string
	Env      map[string]string
	Inject   []string
}

// ResolveLaunchEnv builds the environment for a tool launch by combining the
// process environment, the tool's env block, the chosen endpoint, and the
// selected model.  Empty endpoint is allowed for tools that do not require an
// endpoint (e.g. ampcode); callers should validate before launch.
func ResolveLaunchEnv(tool Tool, endpoint providers.Endpoint, endpointName, model string) LaunchEnv {
	env := map[string]string{}
	for _, kv := range os.Environ() {
		idx := strings.IndexByte(kv, '=')
		if idx > 0 {
			env[kv[:idx]] = kv[idx+1:]
		}
	}

	apiKey := providers.ResolveAPIKey(endpoint, os.Getenv)

	// env.exported are populated from the endpoint or model when the value
	// contains a recognised placeholder.  Otherwise the literal value is used.
	for k, v := range tool.Env.Exported {
		env[k] = expandPlaceholders(v, endpoint, model, apiKey)
	}
	for k, v := range tool.Env.Managed {
		env[k] = v
	}
	for _, removed := range tool.Env.Removed {
		delete(env, removed)
	}

	inject := make([]string, 0, len(tool.CLIParameters.Injected))
	for _, raw := range tool.CLIParameters.Injected {
		inject = append(inject, expandPlaceholders(raw, endpoint, model, apiKey))
	}

	return LaunchEnv{
		Tool:     tool,
		Endpoint: endpoint,
		Model:    model,
		Env:      env,
		Inject:   inject,
	}
}

func expandPlaceholders(raw string, ep providers.Endpoint, model, apiKey string) string {
	out := raw
	out = strings.ReplaceAll(out, "{BASE_URL}", ep.Endpoint)
	out = strings.ReplaceAll(out, "{endpoint}", ep.Endpoint)
	out = strings.ReplaceAll(out, "{selected_model}", model)
	out = strings.ReplaceAll(out, "{api_key}", apiKey)
	return out
}

// Run launches the tool's CLI binary inheriting stdio (interactive mode).
// Extra args are appended after the injected cli_parameters.
func Run(launch LaunchEnv, args []string) (int, error) {
	command := launch.Tool.LaunchCommand()
	if command == "" {
		return 1, fmt.Errorf("tools: no cli_command for tool %s", launch.Tool.Name)
	}
	if _, err := exec.LookPath(command); err != nil {
		return 127, fmt.Errorf("tools: %s not found on PATH (install with `cam install %s`)", command, launch.Tool.Name)
	}
	final := append([]string{}, launch.Inject...)
	final = append(final, args...)
	cmd := exec.Command(command, final...)
	cmd.Env = envMapToSlice(launch.Env)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if exit, ok := err.(*exec.ExitError); ok {
			return exit.ExitCode(), nil
		}
		return 1, err
	}
	return 0, nil
}

func envMapToSlice(env map[string]string) []string {
	out := make([]string, 0, len(env))
	for k, v := range env {
		out = append(out, k+"="+v)
	}
	return out
}
