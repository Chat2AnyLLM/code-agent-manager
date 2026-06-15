package tools

import (
	"strings"

	"github.com/chat2anyllm/code-agent-manager/internal/editorconfig"
	"github.com/chat2anyllm/code-agent-manager/internal/pathutil"
)

// codexPostWrite runs after the generic Apply for the openai-codex tool.
// If the selected model starts with "gpt", it sets
//
//	[model_providers.<endpointName>] wire_api = "responses"
//
// Otherwise it unsets wire_api on that provider. No-op for other tools.
func codexPostWrite(tool Tool, endpointName, model, configPath string) error {
	if tool.Name != "openai-codex" {
		return nil
	}
	path := configPath
	if path == "" && tool.ConfigTarget != nil {
		path = pathutil.Expand(tool.ConfigTarget.Path)
	}
	if path == "" || endpointName == "" {
		return nil
	}
	return applyCodexWireAPI(path, endpointName, model)
}

func applyCodexWireAPI(path, endpointName, model string) error {
	data, err := readConfigFile(path, "toml")
	if err != nil {
		return err
	}
	keyPath := "model_providers." + quoteSegmentIfNeeded(endpointName) + ".wire_api"
	parts, err := editorconfig.Parse(keyPath)
	if err != nil {
		return err
	}
	if strings.HasPrefix(model, "gpt") {
		editorconfig.Set(data, parts, "responses")
	} else {
		editorconfig.Unset(data, parts)
	}
	return writeConfigFile(path, "toml", data)
}

// quoteSegmentIfNeeded wraps name in TOML quotes when it would not be a
// bare key (e.g. contains a hyphen or slash).
func quoteSegmentIfNeeded(name string) string {
	for _, ch := range name {
		isAlnum := (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_'
		if !isAlnum {
			return `"` + name + `"`
		}
	}
	return name
}
