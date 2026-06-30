package cli_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/entities"
)

// --- list ------------------------------------------------------------------

func TestInstructionListWhenEmpty(t *testing.T) {
	isolatedHome(t)
	stdout, _, code := execute(t, "instruction", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "No instructions installed across agents") {
		t.Fatalf("missing empty state:\n%s", stdout)
	}
}

func TestInstructionListShowsInstalled(t *testing.T) {
	home := isolatedHome(t)
	installEntityToApp(t, home, entities.KindInstruction, "", "instruction content", "claude")
	stdout, _, code := execute(t, "instruction", "list")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "claude") {
		t.Fatalf("list missing claude:\n%s", stdout)
	}
}

// --- search ----------------------------------------------------------------

func TestInstructionSearchFindsMatch(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindInstruction, "greeting", "Hello", "A greeting instruction")
	seedEntity(t, entities.KindInstruction, "farewell", "Bye", "A farewell instruction")
	stdout, _, code := execute(t, "instruction", "search", "greeting", "--local")
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if !strings.Contains(stdout, "greeting") {
		t.Fatalf("search missing match:\n%s", stdout)
	}
	if strings.Contains(stdout, "farewell") {
		t.Fatalf("search should not include non-matching:\n%s", stdout)
	}
}

// --- install ---------------------------------------------------------------

func TestInstructionInstallWritesContentToAppPath(t *testing.T) {
	home := isolatedHome(t)
	seedEntity(t, entities.KindInstruction, "demo", "instruction body", "")
	stdout, _, code := execute(t, "instruction", "install", "demo", "--app", "claude")
	if code != 0 {
		t.Fatalf("install exit = %d", code)
	}
	if !strings.Contains(stdout, "Installed demo") || !strings.Contains(stdout, "claude") {
		t.Fatalf("install output:\n%s", stdout)
	}
	data, err := os.ReadFile(filepath.Join(home, ".claude", "CLAUDE.md"))
	if err != nil {
		t.Fatalf("expected CLAUDE.md: %v", err)
	}
	if string(data) != "instruction body" {
		t.Fatalf("content = %q", data)
	}
}

func TestInstructionInstallWithoutAppErrors(t *testing.T) {
	isolatedHome(t)
	seedEntity(t, entities.KindInstruction, "demo", "body", "")
	_, stderr, code := execute(t, "instruction", "install", "demo")
	if code == 0 {
		t.Fatal("expected non-zero exit without --app")
	}
	if !strings.Contains(stderr, "--app is required") {
		t.Fatalf("stderr missing --app guidance: %s", stderr)
	}
}

// --- prompt/p compatibility aliases ----------------------------------------

func TestPromptCommandShowsInstructionHelp(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "prompt", "--help")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Manage instruction configurations") {
		t.Fatalf("prompt help should show instruction help:\n%s", stdout)
	}
}

func TestPromptAliasPShowsInstructionHelp(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "p", "--help")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "Manage instruction configurations") {
		t.Fatalf("p help should show instruction help:\n%s", stdout)
	}
}

func TestPromptSubcommandRunsInstructionSubcommand(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "prompt", "list")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "No instructions installed across agents") {
		t.Fatalf("prompt list should run instruction list:\n%s", stdout)
	}
}

func TestPromptAliasPSubcommandRunsInstructionSubcommand(t *testing.T) {
	isolatedHome(t)
	stdout, stderr, code := execute(t, "p", "list")
	if code != 0 {
		t.Fatalf("exit = %d; stderr=%s", code, stderr)
	}
	if !strings.Contains(stdout, "No instructions installed across agents") {
		t.Fatalf("p list should run instruction list:\n%s", stdout)
	}
}
