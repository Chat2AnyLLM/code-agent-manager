package main_test

import (
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestBuiltBinarySupportsBothExecutableNames(t *testing.T) {
	dir := t.TempDir()
	binary := filepath.Join(dir, "cam")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}

	build := exec.Command("go", "build", "-o", binary, "./cmd/cam")
	build.Dir = "../.."
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("go build failed: %v\n%s", err, output)
	}

	for _, args := range [][]string{{"--version"}, {"version"}, {"doctor", "--help"}, {"mcp", "--help"}} {
		run := exec.Command(binary, args...)
		run.Dir = "../.."
		output, err := run.CombinedOutput()
		if err != nil {
			t.Fatalf("cam %s failed: %v\n%s", strings.Join(args, " "), err, output)
		}
		if len(output) == 0 {
			t.Fatalf("cam %s produced no output", strings.Join(args, " "))
		}
	}

	alias := filepath.Join(dir, "code-agent-manager")
	if runtime.GOOS == "windows" {
		alias += ".exe"
	}
	build = exec.Command("go", "build", "-o", alias, "./cmd/code-agent-manager")
	build.Dir = "../.."
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("go build alias failed: %v\n%s", err, output)
	}

	run := exec.Command(alias, "--version")
	run.Dir = "../.."
	output, err := run.CombinedOutput()
	if err != nil {
		t.Fatalf("code-agent-manager --version failed: %v\n%s", err, output)
	}
	if !strings.Contains(string(output), "dev") {
		t.Fatalf("version output = %q, want dev", output)
	}
}
