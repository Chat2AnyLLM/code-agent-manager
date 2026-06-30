package cli_test

import (
	"strings"
	"testing"
)

// `cam --help` and `cam help` must list every visible subcommand plus aliases
// so users see the full surface from a single entry point.
func TestRootHelpListsEverySubcommandAndAlias(t *testing.T) {
	for _, args := range [][]string{{"--help"}, {"help"}} {
		t.Run(strings.Join(args, " "), func(t *testing.T) {
			stdout, stderr, code := execute(t, args...)
			if code != 0 {
				t.Fatalf("exit = %d; stderr=%s", code, stderr)
			}
			for _, want := range []string{
				"Code Assistant Manager",
				"agent",
				"completion",
				"config",
				"doctor",
				"extension",
				"install",
				"instruction",
				"launch",
				"mcp",
				"plugin",
				"prompt",
				"skill",
				"uninstall",
				"upgrade",
				"version",
			} {
				if !strings.Contains(stdout, want) {
					t.Fatalf("root help missing %q\nstdout:\n%s", want, stdout)
				}
			}
		})
	}
}

// `cam help <command>` mirrors Cobra's built-in behaviour: it renders the
// command's --help output.  We test one command from each category to cover
// leaf/group/passthrough cases.
func TestHelpSubcommandDelegatesToCommandHelp(t *testing.T) {
	for _, cmd := range []string{"launch", "config", "mcp", "extension", "doctor"} {
		t.Run(cmd, func(t *testing.T) {
			stdout, _, code := execute(t, "help", cmd)
			if code != 0 {
				t.Fatalf("exit = %d", code)
			}
			if !strings.Contains(stdout, "Usage:") {
				t.Fatalf("help %s missing Usage section:\n%s", cmd, stdout)
			}
		})
	}
}

func TestRootTopLevelCommandsShowHelp(t *testing.T) {
	commands := []string{
		"agent",
		"apply",
		"completion",
		"config",
		"doctor",
		"extension",
		"install",
		"instruction",
		"launch",
		"mcp",
		"metadata",
		"plugin",
		"prompt",
		"provider",
		"skill",
		"uninstall",
		"upgrade",
		"version",
	}
	for _, cmd := range commands {
		t.Run(cmd, func(t *testing.T) {
			stdout, stderr, code := execute(t, cmd, "--help")
			if code != 0 {
				t.Fatalf("exit = %d; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, "Usage:") {
				t.Fatalf("command %s help missing Usage section:\n%s", cmd, stdout)
			}
		})
	}
}

// Every alias resolves to a real command (Cobra falls back to "unknown command"
// otherwise).  Testing this prevents regressions when subcommands are renamed.
func TestRootShortAliasesShowOwnHelp(t *testing.T) {
	for _, alias := range []string{"l", "d", "ag", "prompt", "p", "s", "pl", "m", "pr", "u", "i", "un", "cf", "comp", "c", "v"} {
		t.Run(alias, func(t *testing.T) {
			stdout, stderr, code := execute(t, alias, "--help")
			if code != 0 {
				t.Fatalf("exit = %d; stderr=%s", code, stderr)
			}
			if !strings.Contains(stdout, "Usage:") {
				t.Fatalf("alias %s help missing Usage section:\n%s", alias, stdout)
			}
		})
	}
}
