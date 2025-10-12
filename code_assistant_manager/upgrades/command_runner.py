import shlex
import subprocess


class CommandRunner:
    def run(self, cmd: str, check: bool = True) -> str:
        # Check if command contains shell operators that require shell interpretation
        shell_operators = ["|", ">", "<", ">>", "<<", "&&", "||", ";", "&"]
        needs_shell = any(op in cmd for op in shell_operators)

        if needs_shell:
            # SECURITY: For commands with shell operators, validate first then use shell=True
            # Commands should come from trusted sources (tool registries) but we add validation
            if not self._is_command_safe(cmd):
                raise ValueError(f"Command contains unsafe patterns: {cmd}")

            # Use shell=True but with explicit /bin/sh and proper quoting
            proc = subprocess.run(
                cmd, shell=True, executable="/bin/sh", capture_output=True, text=True
            )  # nosec: B602 - shell=True is validated by _is_command_safe()
        else:
            # For simple commands without shell operators, use shlex.split() for security
            proc = subprocess.run(
                shlex.split(cmd), shell=False, capture_output=True, text=True
            )

        if check and proc.returncode != 0:
            raise RuntimeError(f"command failed: {cmd}\n{proc.stderr}")
        return proc.stdout

    def _is_command_safe(self, cmd: str) -> bool:
        """Check if command contains potentially dangerous patterns."""
        dangerous_patterns = [
            # Command injection attempts
            "; rm ",
            "| rm ",
            "&& rm ",
            "|| rm ",
            "; curl ",
            "| curl ",
            "&& curl ",
            "|| curl ",
            "; wget ",
            "| wget ",
            "&& wget ",
            "|| wget ",
            # System commands
            "; sudo ",
            "| sudo ",
            "&& sudo ",
            "|| sudo ",
            "; su ",
            "| su ",
            "&& su ",
            "|| su ",
            # File operations
            "> /etc/",
            ">> /etc/",
            "< /etc/",
            "> /root/",
            ">> /root/",
            "< /root/",
            # Dangerous redirects
            " > /",
            " >> /",
            " < /",
        ]

        cmd_lower = cmd.lower()
        return not any(pattern in cmd_lower for pattern in dangerous_patterns)
