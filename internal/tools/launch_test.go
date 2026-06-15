package tools

import (
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func TestResolveLaunchEnv_NoEndpointVarsForRefactoredTools(t *testing.T) {
	cases := []struct {
		toolName string
		absent   []string
	}{
		{"claude-code", []string{"ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"}},
		{"openai-codex", []string{"BASE_URL", "OPENAI_API_KEY"}},
		{"qwen-code", []string{"OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"}},
		{"codebuddy", []string{"CODEBUDDY_BASE_URL", "CODEBUDDY_API_KEY"}},
	}
	for _, tc := range cases {
		t.Run(tc.toolName, func(t *testing.T) {
			for _, k := range tc.absent {
				t.Setenv(k, "")
			}
			tool := Tool{Name: tc.toolName}
			ep := providers.Endpoint{Endpoint: "https://x"}
			launch := ResolveLaunchEnv(tool, ep, "ep", "model-x")
			for _, k := range tc.absent {
				v, ok := launch.Env[k]
				if ok && v != "" {
					t.Errorf("%s: env[%q] = %q, want unset/empty after refactor", tc.toolName, k, v)
				}
			}
		})
	}
}
