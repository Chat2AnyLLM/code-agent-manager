package tools

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/google/shlex"
)

// Installer executes the install_cmd for a tool.  The CommandRunner indirection
// keeps the implementation easy to unit-test by providing a fake runner.
type Installer struct {
	Runner CommandRunner
}

// CommandRunner is the seam tests use to capture commands without spawning
// processes.
type CommandRunner interface {
	Run(name string, args []string, stdout, stderr io.Writer) (int, error)
}

// ShellRunner is the default CommandRunner; it executes via /bin/sh -c when the
// install_cmd contains shell metacharacters and via exec.Command otherwise.
type ShellRunner struct{}

// Run executes name with args.  If name is empty, it falls back to shell mode
// using the first arg as the full command.
func (ShellRunner) Run(name string, args []string, stdout, stderr io.Writer) (int, error) {
	if name == "" {
		return 1, errors.New("tools: empty command")
	}
	cmd := exec.Command(name, args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return exitErr.ExitCode(), nil
		}
		return 1, err
	}
	return 0, nil
}

// Install runs the install_cmd for the given tool, streaming output through w.
// Empty install_cmd returns nil with a "no install command" sentinel.
var ErrNoInstallCommand = errors.New("tools: tool has no install_cmd")

// shellCommand returns the platform shell invocation for a command string.
func shellCommand(command string) (string, []string) {
	if runtime.GOOS == "windows" {
		return "cmd", []string{"/C", command}
	}
	return "/bin/sh", []string{"-c", command}
}

// Install installs the tool by executing its install_cmd through the shell.
func Install(tool Tool, runner CommandRunner, stdout, stderr io.Writer) (int, error) {
	if runner == nil {
		runner = ShellRunner{}
	}
	if strings.TrimSpace(tool.InstallCmd) == "" {
		return 0, ErrNoInstallCommand
	}
	name, args := shellCommand(tool.InstallCmd)
	return runner.Run(name, args, stdout, stderr)
}

// Uninstall best-effort removes the tool.  npm-installed tools are removed via
// `npm uninstall -g <pkg>`; for other install styles we fall back to deleting
// the binary discovered on PATH.  The returned message is suitable for stdout.
func Uninstall(tool Tool, runner CommandRunner, stdout, stderr io.Writer) (int, string, error) {
	if runner == nil {
		runner = ShellRunner{}
	}
	pkg, isNPM := npmPackage(tool.InstallCmd)
	if isNPM {
		cmd := fmt.Sprintf("npm uninstall -g %s", pkg)
		name, args := shellCommand(cmd)
		code, err := runner.Run(name, args, stdout, stderr)
		return code, cmd, err
	}
	bin := tool.LaunchCommand()
	if bin == "" {
		return 0, "no binary to remove", nil
	}
	path, err := exec.LookPath(bin)
	if err != nil {
		return 0, fmt.Sprintf("%s not found on PATH", bin), nil
	}
	if rmErr := os.Remove(path); rmErr != nil {
		return 1, fmt.Sprintf("rm %s", path), rmErr
	}
	return 0, fmt.Sprintf("removed %s", path), nil
}

// npmPackage extracts the npm package name from a shell install_cmd like
// `npm install -g @scope/name@latest`.  Returns false when the command is not
// an npm install.
func npmPackage(installCmd string) (string, bool) {
	cmd := strings.TrimSpace(installCmd)
	if !strings.HasPrefix(cmd, "npm ") {
		return "", false
	}
	parts, err := shlex.Split(cmd)
	if err != nil {
		return "", false
	}
	skip := map[string]bool{"npm": true, "install": true, "i": true, "-g": true, "--global": true}
	for _, p := range parts {
		if skip[p] {
			continue
		}
		// Strip version suffix after @, preserving @scope/name.
		if strings.HasPrefix(p, "@") {
			idx := strings.Index(p[1:], "@")
			if idx >= 0 {
				return p[:idx+1], true
			}
			return p, true
		}
		if idx := strings.Index(p, "@"); idx > 0 {
			return p[:idx], true
		}
		return p, true
	}
	return "", false
}

// versionProbeTimeout bounds how long a single `<bin> --version` probe waits
// for the process to exit. versionProbeWaitDelay bounds how long CombinedOutput
// then waits for the process's pipes to close after the process is killed —
// necessary because npm-installed CLIs spawn a child node process that inherits
// (and holds open) the stdout pipe, which would otherwise deadlock the read
// forever even after the wrapper process is killed.
var (
	versionProbeTimeout   = 2 * time.Second
	versionProbeWaitDelay = 1 * time.Second
)

// IsInstalled reports whether the tool's CLI binary is reachable via PATH.
func IsInstalled(tool Tool) bool {
	bin := tool.LaunchCommand()
	if bin == "" {
		return false
	}
	_, err := exec.LookPath(bin)
	return err == nil
}

// Detect reports whether the tool's CLI binary is on PATH and, when installed,
// its version string in a single pass. Version detection is skipped for missing
// binaries — we never spawn a doomed process just to learn the binary is absent —
// and each probe is bounded by versionProbeTimeout so one hung binary can't
// stall the caller. Prefer this over IsInstalled + DetectVersion when you need
// both values.
func Detect(tool Tool) (installed bool, version string) {
	bin := tool.LaunchCommand()
	if bin == "" {
		return false, ""
	}
	if _, err := exec.LookPath(bin); err != nil {
		return false, ""
	}
	return true, detectVersion(bin)
}

// DetectVersion returns the tool's version string by running `<bin> --version`.
// Returns "unknown" when the binary is missing or every probe fails (including
// timeout). Prefer Detect when the installed flag is also needed.
func DetectVersion(tool Tool) string {
	bin := tool.LaunchCommand()
	if bin == "" {
		return "unknown"
	}
	return detectVersion(bin)
}

// detectVersion probes the binary with a sequence of version flags, returning
// the first non-empty response. Each probe is bounded: the process is killed
// after versionProbeTimeout, and its pipes are forcibly closed after
// versionProbeWaitDelay so a hung grandchild can't deadlock the read. If a flag
// times out, the remaining flags are skipped — a binary that hangs on one
// version flag will hang on the others too.
func detectVersion(bin string) string {
	for _, flag := range []string{"--version", "-v", "version"} {
		ctx, cancel := context.WithTimeout(context.Background(), versionProbeTimeout)
		cmd := exec.CommandContext(ctx, bin, flag)
		cmd.WaitDelay = versionProbeWaitDelay
		out, err := cmd.CombinedOutput()
		timedOut := ctx.Err() != nil // deadline fired (cancel runs below)
		cancel()
		if err != nil {
			if timedOut {
				break
			}
			continue
		}
		s := strings.TrimSpace(string(out))
		if s == "" {
			continue
		}
		// Take the last non-empty line.
		lines := strings.Split(s, "\n")
		for i := len(lines) - 1; i >= 0; i-- {
			line := strings.TrimSpace(lines[i])
			if line != "" {
				return line
			}
		}
	}
	return "unknown"
}
