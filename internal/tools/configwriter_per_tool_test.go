package tools

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	tomlv2 "github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

// loadToolFromRegistry returns the tool's Tool entry and overrides its
// ConfigTarget.Path to live in a tmpdir so tests don't touch the real HOME.
func loadToolFromRegistry(t *testing.T, name, filename string) (Tool, string) {
	t.Helper()
	reg, err := LoadDefault()
	if err != nil {
		t.Fatalf("LoadDefault: %v", err)
	}
	tool, ok := reg.Get(name)
	if !ok {
		t.Fatalf("%s missing from registry", name)
	}
	if tool.ConfigTarget == nil {
		t.Fatalf("%s config_target missing", name)
	}
	tmp := t.TempDir()
	tool.ConfigTarget.Path = filepath.Join(tmp, filename)
	return tool, tool.ConfigTarget.Path
}

func TestPerTool_ClaudeCode_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "claude-code", "settings.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "litellm", "claude-sonnet-4", "sk-1234"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	env := got["env"].(map[string]any)
	checks := map[string]any{
		"ANTHROPIC_BASE_URL":                       "https://api.test",
		"ANTHROPIC_API_KEY":                        "sk-1234",
		"ANTHROPIC_MODEL":                          "claude-sonnet-4",
		"ANTHROPIC_DEFAULT_SONNET_MODEL":           "claude-sonnet-4",
		"ANTHROPIC_DEFAULT_HAIKU_MODEL":            "claude-sonnet-4",
		"DISABLE_NON_ESSENTIAL_MODEL_CALLS":        1,
		"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
	}
	for k, want := range checks {
		if gotv := fmt.Sprint(env[k]); gotv != fmt.Sprint(want) {
			t.Errorf("env[%q] = %v, want %v", k, env[k], want)
		}
	}
	for _, removed := range []string{"ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"} {
		if _, ok := env[removed]; ok {
			t.Errorf("env[%q] should be removed", removed)
		}
	}
}

func TestPerTool_OpenAICodex_GoldenTOML_GPT(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "openai-codex", "config.toml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "gpt-4o", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := tomlv2.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	mp := got["model_providers"].(map[string]any)["myprov"].(map[string]any)
	if mp["name"] != "myprov" {
		t.Errorf("name = %v", mp["name"])
	}
	if mp["base_url"] != "https://api.test" {
		t.Errorf("base_url = %v", mp["base_url"])
	}
	// With no explicit api_key_env, the env-var name is derived from the
	// endpoint name (myprov -> MYPROV_API_KEY).
	if mp["env_key"] != "MYPROV_API_KEY" {
		t.Errorf("env_key = %v", mp["env_key"])
	}
	if mp["wire_api"] != "responses" {
		t.Errorf("wire_api = %v, want responses (GPT model)", mp["wire_api"])
	}
	prof := got["profiles"].(map[string]any)["gpt-4o"].(map[string]any)
	if prof["model"] != "gpt-4o" {
		t.Errorf("profile.model = %v", prof["model"])
	}
	if prof["model_provider"] != "myprov" {
		t.Errorf("profile.model_provider = %v", prof["model_provider"])
	}
	if prof["model_reasoning_effort"] != "low" {
		t.Errorf("profile.model_reasoning_effort = %v", prof["model_reasoning_effort"])
	}
}

func TestPerTool_OpenAICodex_NonGPTUnsetsWireAPI(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "openai-codex", "config.toml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "claude-sonnet-4", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	if strings.Contains(string(raw), "wire_api") {
		t.Errorf("wire_api present for non-GPT model:\n%s", raw)
	}
}

// When the provider sets api_key_env explicitly, codex's env_key uses that exact
// name (e.g. OMNILLM_API_KEY) rather than a derived one.
func TestPerTool_OpenAICodex_ExplicitEnvKey(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "openai-codex", "config.toml")
	ep := providers.Endpoint{Endpoint: "https://api.test", APIKeyEnv: "OMNILLM_API_KEY"}
	if _, err := WriteConfig(tool, ep, "omnillm", "claude-sonnet-4", ""); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := tomlv2.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	mp := got["model_providers"].(map[string]any)["omnillm"].(map[string]any)
	if mp["env_key"] != "OMNILLM_API_KEY" {
		t.Errorf("env_key = %v, want OMNILLM_API_KEY", mp["env_key"])
	}
}

func TestPerTool_QwenCode_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "qwen-code", "settings.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "ep", "qwen3-coder-plus", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	env := got["env"].(map[string]any)
	checks := map[string]any{
		"OPENAI_BASE_URL": "https://api.test",
		"OPENAI_API_KEY":  "sk-1",
		"OPENAI_MODEL":    "qwen3-coder-plus",
	}
	for k, want := range checks {
		if gotv := fmt.Sprint(env[k]); gotv != fmt.Sprint(want) {
			t.Errorf("env[%q] = %v, want %v", k, env[k], want)
		}
	}
}

func TestPerTool_CodeBuddy_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "codebuddy", "codebuddy.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "ep", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	env := got["env"].(map[string]any)
	if env["CODEBUDDY_BASE_URL"] != "https://api.test" {
		t.Errorf("CODEBUDDY_BASE_URL = %v", env["CODEBUDDY_BASE_URL"])
	}
	if env["CODEBUDDY_API_KEY"] != "sk-1" {
		t.Errorf("CODEBUDDY_API_KEY = %v", env["CODEBUDDY_API_KEY"])
	}
}

func TestPerTool_iFlow_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "iflow", "settings.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "ep", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	env := got["env"].(map[string]any)
	if env["IFLOW_BASE_URL"] != "https://api.test" {
		t.Errorf("IFLOW_BASE_URL = %v", env["IFLOW_BASE_URL"])
	}
	if env["IFLOW_API_KEY"] != "sk-1" {
		t.Errorf("IFLOW_API_KEY = %v", env["IFLOW_API_KEY"])
	}
	if env["IFLOW_MODEL_NAME"] != "model-x" {
		t.Errorf("IFLOW_MODEL_NAME = %v", env["IFLOW_MODEL_NAME"])
	}
}

func TestPerTool_AIChat_GoldenYAML(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "aichat", "config.yaml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := yaml.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	clients := got["clients"].(map[string]any)
	mp := clients["myprov"].(map[string]any)
	if mp["type"] != "openai-compatible" {
		t.Errorf("type = %v", mp["type"])
	}
	if mp["api_base"] != "https://api.test" {
		t.Errorf("api_base = %v", mp["api_base"])
	}
	if mp["api_key"] != "sk-1" {
		t.Errorf("api_key = %v", mp["api_key"])
	}
	models := mp["models"].([]any)
	if len(models) != 1 {
		t.Fatalf("models len = %d, want 1", len(models))
	}
	if models[0].(map[string]any)["name"] != "model-x" {
		t.Errorf("models[0].name = %v", models[0].(map[string]any)["name"])
	}
}

func TestPerTool_Kimi_GoldenTOML(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "kimi", "config.toml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "kimi-coder", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	tomlv2.Unmarshal(raw, &got)
	if got["provider"] != "myprov" {
		t.Errorf("provider = %v", got["provider"])
	}
	providers := got["providers"].(map[string]any)["myprov"].(map[string]any)
	if providers["base_url"] != "https://api.test" {
		t.Errorf("base_url = %v", providers["base_url"])
	}
	if providers["api_key"] != "sk-1" {
		t.Errorf("api_key = %v", providers["api_key"])
	}
	if providers["model"] != "kimi-coder" {
		t.Errorf("model = %v", providers["model"])
	}
}

func TestPerTool_Droid_GoldenJSON_ArrayUpsert(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "droid", "settings.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}

	// First write.
	if _, err := WriteConfig(tool, ep, "ep1", "model-A", "sk-1"); err != nil {
		t.Fatalf("WriteConfig 1: %v", err)
	}
	// Second write with the SAME (endpointName, model) must upsert in place.
	if _, err := WriteConfig(tool, ep, "ep1", "model-A", "sk-2"); err != nil {
		t.Fatalf("WriteConfig 2: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	arr := got["customModels"].([]any)
	if len(arr) != 1 {
		t.Fatalf("len = %d, want 1 (in-place upsert)", len(arr))
	}
	el := arr[0].(map[string]any)
	if el["displayName"] != "ep1/model-A" {
		t.Errorf("displayName = %v", el["displayName"])
	}
	if el["model"] != "model-A" {
		t.Errorf("model = %v", el["model"])
	}
	if el["baseUrl"] != "https://api.test" {
		t.Errorf("baseUrl = %v", el["baseUrl"])
	}
	if el["apiKey"] != "sk-2" {
		t.Errorf("apiKey = %v, want sk-2 (latest)", el["apiKey"])
	}
	if el["provider"] != "openai" {
		t.Errorf("provider = %v", el["provider"])
	}
	// maxOutputTokens should be the int64 8192, but JSON roundtrip turns
	// ints into float64.  Accept either.
	switch v := el["maxOutputTokens"].(type) {
	case float64:
		if v != 8192 {
			t.Errorf("maxOutputTokens = %v, want 8192", v)
		}
	case int64:
		if v != 8192 {
			t.Errorf("maxOutputTokens = %v, want 8192", v)
		}
	default:
		t.Errorf("maxOutputTokens unexpected type %T = %v", v, v)
	}

	// Third write with a DIFFERENT model must append a new element.
	if _, err := WriteConfig(tool, ep, "ep1", "model-B", "sk-3"); err != nil {
		t.Fatalf("WriteConfig 3: %v", err)
	}
	raw, _ = os.ReadFile(path)
	json.Unmarshal(raw, &got)
	arr = got["customModels"].([]any)
	if len(arr) != 2 {
		t.Fatalf("len = %d, want 2 (append for new model)", len(arr))
	}
}

func TestPerTool_Neovate_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "neovate", "config.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	json.Unmarshal(raw, &got)
	if got["defaultProvider"] != "myprov" {
		t.Errorf("defaultProvider = %v", got["defaultProvider"])
	}
	mp := got["providers"].(map[string]any)["myprov"].(map[string]any)
	if mp["baseURL"] != "https://api.test" {
		t.Errorf("baseURL = %v", mp["baseURL"])
	}
	if mp["apiKey"] != "sk-1" {
		t.Errorf("apiKey = %v", mp["apiKey"])
	}
	if mp["model"] != "model-x" {
		t.Errorf("model = %v", mp["model"])
	}
}

func TestPerTool_Crush_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "crush", "crush.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v\n%s", err, raw)
	}
	mp := got["providers"].(map[string]any)["myprov"].(map[string]any)
	if mp["type"] != "openai-compat" {
		t.Errorf("type = %v", mp["type"])
	}
	if mp["base_url"] != "https://api.test" {
		t.Errorf("base_url = %v", mp["base_url"])
	}
	if mp["api_key"] != "sk-1" {
		t.Errorf("api_key = %v", mp["api_key"])
	}
	models := mp["models"].([]any)
	if len(models) != 1 {
		t.Fatalf("models len = %d, want 1", len(models))
	}
	if models[0].(map[string]any)["id"] != "model-x" {
		t.Errorf("models[0].id = %v", models[0].(map[string]any)["id"])
	}
}

func TestPerTool_Opencode_GoldenJSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "opencode", "opencode.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v\n%s", err, raw)
	}
	if got["model"] != "myprov/model-x" {
		t.Errorf("model = %v, want myprov/model-x", got["model"])
	}
	prov := got["provider"].(map[string]any)["myprov"].(map[string]any)
	if prov["npm"] != "@ai-sdk/openai-compatible" {
		t.Errorf("provider.npm = %v", prov["npm"])
	}
	if prov["name"] != "myprov" {
		t.Errorf("provider.name = %v", prov["name"])
	}
	options := prov["options"].(map[string]any)
	if options["baseURL"] != "https://api.test" {
		t.Errorf("options.baseURL = %v", options["baseURL"])
	}
	if options["apiKey"] != "sk-1" {
		t.Errorf("options.apiKey = %v", options["apiKey"])
	}
}

func TestPerTool_Continue_GoldenYAML(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "continue", "config.yaml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := yaml.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v\n%s", err, raw)
	}
	if got["schema"] != "v1" {
		t.Errorf("schema = %v", got["schema"])
	}
	models := got["models"].([]any)
	if len(models) != 1 {
		t.Fatalf("models len = %d, want 1", len(models))
	}
	m := models[0].(map[string]any)
	if m["name"] != "myprov/model-x" {
		t.Errorf("model name = %v", m["name"])
	}
	if m["provider"] != "openai" {
		t.Errorf("model provider = %v", m["provider"])
	}
	if m["model"] != "model-x" {
		t.Errorf("model model = %v", m["model"])
	}
	if m["apiBase"] != "https://api.test" {
		t.Errorf("model apiBase = %v", m["apiBase"])
	}
	if m["apiKey"] != "sk-1" {
		t.Errorf("model apiKey = %v", m["apiKey"])
	}
}

func TestPerTool_Continue_ArrayUpsertByName(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "continue", "config.yaml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-1"); err != nil {
		t.Fatal(err)
	}
	// Second write with same (provider, model) must upsert in place.
	if _, err := WriteConfig(tool, ep, "myprov", "model-x", "sk-2"); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	yaml.Unmarshal(raw, &got)
	models := got["models"].([]any)
	if len(models) != 1 {
		t.Fatalf("len = %d, want 1 (upsert in place)", len(models))
	}
	if models[0].(map[string]any)["apiKey"] != "sk-2" {
		t.Errorf("apiKey = %v, want sk-2 (latest)", models[0].(map[string]any)["apiKey"])
	}
	// Third write with a different model must append.
	if _, err := WriteConfig(tool, ep, "myprov", "model-y", "sk-3"); err != nil {
		t.Fatal(err)
	}
	raw, _ = os.ReadFile(path)
	yaml.Unmarshal(raw, &got)
	models = got["models"].([]any)
	if len(models) != 2 {
		t.Fatalf("len = %d, want 2 (append for new model)", len(models))
	}
}

func TestPerTool_GeminiCLI_ModelOnly_JSON(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "gemini-cli", "settings.json")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "gemini-1.5-pro", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v\n%s", err, raw)
	}
	model := got["model"].(map[string]any)
	if model["name"] != "gemini-1.5-pro" {
		t.Errorf("model.name = %v", model["name"])
	}
	// No endpoint/api_key keys should appear anywhere.
	if strings.Contains(string(raw), "api.test") {
		t.Errorf("endpoint leaked into Gemini settings:\n%s", raw)
	}
	if strings.Contains(string(raw), "sk-1") {
		t.Errorf("api key leaked into Gemini settings:\n%s", raw)
	}
}

func TestPerTool_Goose_ProviderAndModelOnly_YAML(t *testing.T) {
	tool, path := loadToolFromRegistry(t, "goose", "config.yaml")
	ep := providers.Endpoint{Endpoint: "https://api.test"}
	if _, err := WriteConfig(tool, ep, "myprov", "gpt-4o", "sk-1"); err != nil {
		t.Fatalf("WriteConfig: %v", err)
	}
	raw, _ := os.ReadFile(path)
	var got map[string]any
	if err := yaml.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal: %v\n%s", err, raw)
	}
	if got["GOOSE_PROVIDER"] != "myprov" {
		t.Errorf("GOOSE_PROVIDER = %v", got["GOOSE_PROVIDER"])
	}
	if got["GOOSE_MODEL"] != "gpt-4o" {
		t.Errorf("GOOSE_MODEL = %v", got["GOOSE_MODEL"])
	}
	// No endpoint/api_key keys should appear.
	if strings.Contains(string(raw), "api.test") {
		t.Errorf("endpoint leaked into Goose config:\n%s", raw)
	}
	if strings.Contains(string(raw), "sk-1") {
		t.Errorf("api key leaked into Goose config:\n%s", raw)
	}
}
