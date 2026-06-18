package desktop

import (
	"bytes"
	"sync"

	"github.com/chat2anyllm/code-agent-manager/internal/tools"
)

type ToolService struct{}

func NewToolService() *ToolService { return &ToolService{} }

// maxDetectionWorkers caps the detection pool. The work is I/O-bound — each
// probe spends its time waiting on a subprocess — so we run up to one goroutine
// per tool to minimize latency; the cap just keeps a very large registry from
// spawning hundreds of subprocesses at once.
const maxDetectionWorkers = 32

func (s *ToolService) List() ([]ToolDTO, error) {
	registry, err := tools.LoadDefault()
	if err != nil {
		return nil, wrapError("TOOL_REGISTRY_LOAD_FAILED", err)
	}
	names := registry.Names()
	out := make([]ToolDTO, len(names))
	// Each tool's detection blocks on subprocess execution (LookPath + version
	// probes). Run them concurrently — one goroutine per tool, capped — so the
	// Agents page doesn't wait on every binary serially. Writes target distinct
	// slice indices, so no locking is required; output order still matches names.
	workers := len(names)
	if workers > maxDetectionWorkers {
		workers = maxDetectionWorkers
	}
	sem := make(chan struct{}, workers)
	var wg sync.WaitGroup
	for i, name := range names {
		tool := registry.Tools[name]
		wg.Add(1)
		sem <- struct{}{}
		go func(idx int, t tools.Tool) {
			defer wg.Done()
			defer func() { <-sem }()
			out[idx] = toolDTO(t)
		}(i, tool)
	}
	wg.Wait()
	return out, nil
}

func (s *ToolService) Install(name string, dryRun bool) (OperationResult, error) {
	tool, err := loadTool(name)
	if err != nil {
		return OperationResult{}, err
	}
	if dryRun {
		return OperationResult{OK: true, Message: tool.InstallCmd}, nil
	}
	var stdout, stderr bytes.Buffer
	code, err := tools.Install(tool, nil, &stdout, &stderr)
	if err != nil {
		return OperationResult{}, wrapError("TOOL_INSTALL_FAILED", err)
	}
	return OperationResult{OK: code == 0, Message: stdout.String() + stderr.String()}, nil
}

func (s *ToolService) Uninstall(name string, dryRun bool) (OperationResult, error) {
	tool, err := loadTool(name)
	if err != nil {
		return OperationResult{}, err
	}
	if dryRun {
		return OperationResult{OK: true, Message: "uninstall " + tool.LaunchCommand()}, nil
	}
	var stdout, stderr bytes.Buffer
	code, msg, err := tools.Uninstall(tool, nil, &stdout, &stderr)
	if err != nil {
		return OperationResult{}, wrapError("TOOL_UNINSTALL_FAILED", err)
	}
	return OperationResult{OK: code == 0, Message: msg + "\n" + stdout.String() + stderr.String()}, nil
}

func (s *ToolService) Upgrade(name string, dryRun bool) (OperationResult, error) {
	return s.Install(name, dryRun)
}

func loadTool(name string) (tools.Tool, error) {
	registry, err := tools.LoadDefault()
	if err != nil {
		return tools.Tool{}, wrapError("TOOL_REGISTRY_LOAD_FAILED", err)
	}
	tool, ok := registry.Get(name)
	if !ok {
		if byCommand, found := registry.ByCLICommand(name); found {
			return byCommand, nil
		}
		return tools.Tool{}, NewError("TOOL_NOT_FOUND", "tool not found", map[string]string{"name": name})
	}
	return tool, nil
}

func toolDTO(tool tools.Tool) ToolDTO {
	installed, version := tools.Detect(tool)
	return ToolDTO{
		Name: tool.Name, Command: tool.LaunchCommand(), Description: tool.Description,
		Enabled: tool.IsEnabled(), Installed: installed, Version: version,
	}
}
