package catalogconfig

import "testing"

func TestParseReadsSourcesAndOutput(t *testing.T) {
	raw := []byte(`version: "1.0.0"
description: Example catalog
output:
  dir: dist
  formats: [json, csv]
sources:
  - name: Local Prompts
    type: local
    path: prompts/
  - name: Prompts Chat
    type: github
    url: https://github.com/f/prompts.chat
    format: csv
    file_path: prompts.csv
`)

	cfg, err := Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if cfg.Output.Dir != "dist" {
		t.Fatalf("Output.Dir = %q, want dist", cfg.Output.Dir)
	}
	if len(cfg.Output.Formats) != 2 || cfg.Output.Formats[0] != "json" || cfg.Output.Formats[1] != "csv" {
		t.Fatalf("Output.Formats = %#v", cfg.Output.Formats)
	}
	if len(cfg.Sources) != 2 {
		t.Fatalf("Sources len = %d, want 2", len(cfg.Sources))
	}
	first := cfg.Sources[0]
	if first.Name != "Local Prompts" || first.Type != "local" || first.Path != "prompts/" {
		t.Fatalf("first source = %#v", first)
	}
	second := cfg.Sources[1]
	if second.Name != "Prompts Chat" || second.Type != "github" || second.URL != "https://github.com/f/prompts.chat" || second.Format != "csv" || second.FilePath != "prompts.csv" {
		t.Fatalf("second source = %#v", second)
	}
}

func TestDataFileStillUsesOutput(t *testing.T) {
	raw := []byte(`output:
  dir: dist
  formats: [json, csv]
sources:
  - name: Ignored
    type: local
    path: prompts/
`)

	got, err := DataFile("prompts", raw)
	if err != nil {
		t.Fatalf("DataFile: %v", err)
	}
	if got != "dist/prompts.json" {
		t.Fatalf("DataFile = %q, want dist/prompts.json", got)
	}
}
