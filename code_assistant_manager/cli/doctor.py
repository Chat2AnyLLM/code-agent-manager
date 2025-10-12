"""Doctor functionality for Code Assistant Manager CLI."""

import json
import logging
import os
import sys
from pathlib import Path

import typer

from code_assistant_manager.menu.base import Colors

logger = logging.getLogger(__name__)


def run_doctor_checks(config, verbose: bool = False) -> int:
    """Run comprehensive diagnostic checks on the code-assistant-manager installation."""
    issues_found = 0

    def check_passed(message: str):
        typer.echo(f"{Colors.GREEN}✓{Colors.RESET} {message}")

    def check_failed(message: str, suggestion: str = ""):
        nonlocal issues_found
        issues_found += 1
        typer.echo(f"{Colors.RED}✗{Colors.RESET} {message}")
        if suggestion:
            typer.echo(f"  {Colors.YELLOW}Suggestion: {suggestion}{Colors.RESET}")

    def check_warning(message: str, suggestion: str = ""):
        nonlocal issues_found
        issues_found += 1
        typer.echo(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")
        if suggestion:
            typer.echo(f"  {Colors.YELLOW}Suggestion: {suggestion}{Colors.RESET}")

    typer.echo(f"{Colors.BLUE}🔍 Running diagnostic checks...{Colors.RESET}")
    typer.echo()

    # 1. Installation Check
    typer.echo(f"{Colors.BOLD}Installation Check{Colors.RESET}")
    try:
        import code_assistant_manager

        version = getattr(code_assistant_manager, "__version__", "unknown")
        check_passed(f"Code Assistant Manager installed (version: {version})")
    except ImportError as e:
        check_failed(f"Failed to import code_assistant_manager: {e}")
        return 1

    # 2. Python Environment Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Python Environment Check{Colors.RESET}")
    check_passed(f"Python version: {sys.version}")
    check_passed(f"Python executable: {sys.executable}")

    # 3. Configuration Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Configuration Check{Colors.RESET}")
    try:
        config_path = Path(config.config_path)
        if config_path.exists():
            check_passed(f"Configuration file exists: {config_path}")
            # Check file permissions
            perms = oct(config_path.stat().st_mode)[-3:]
            if perms in ["600", "400"]:
                check_passed("Configuration file has secure permissions")
            else:
                check_warning(
                    f"Configuration file permissions: {perms}",
                    "Consider setting permissions to 600 for security",
                )
        else:
            check_failed("Configuration file not found")
    except Exception as e:
        check_failed(f"Error checking configuration: {e}")

    # 4. Environment Variables Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Environment Variables Check{Colors.RESET}")
    from code_assistant_manager.env_loader import find_env_file

    # Candidate env file locations to check (include common locations + repo and any discovered via env_loader)
    env_file_paths = [
        Path(__file__).parent.parent.parent / ".env",
        Path.cwd() / ".env",
        Path.home() / ".env",
        Path.home() / ".config" / "code-assistant-manager" / ".env",
    ]

    # If dotenv can find an env file, include it as well
    found_env = find_env_file()
    if found_env and found_env not in env_file_paths:
        env_file_paths.insert(0, Path(found_env))

    config_file_paths = [
        Path.home() / ".config" / "code-assistant-manager" / "providers.json",
        Path.cwd() / "providers.json",
        Path.home() / "providers.json",
    ]
    env_found = False
    config_found = False

    # Check for .env files
    for env_path in env_file_paths:
        try:
            if env_path.exists():
                env_found = True
                check_passed(f"Environment file found: {env_path}")
                # Check permissions
                perms = oct(env_path.stat().st_mode)[-3:]
                if perms in ["600", "400"]:
                    check_passed("Environment file has secure permissions")
                else:
                    check_warning(
                        f"Environment file permissions: {perms}",
                        "Consider setting permissions to 600 for security",
                    )
                break
        except Exception as e:
            logger.debug(f"Error while checking env file {env_path}: {e}")

    # Check for providers.json files
    for config_path in config_file_paths:
        if config_path.exists():
            config_found = True
            check_passed(f"Providers config file found: {config_path}")
            # Check permissions
            perms = oct(config_path.stat().st_mode)[-3:]
            if perms in ["600", "400"]:
                check_passed("Providers config file has secure permissions")
            else:
                check_warning(
                    f"Providers config file permissions: {perms}",
                    "Consider setting permissions to 600 for security",
                )
            break

    if not env_found:
        check_warning(
            "No .env file found", "Create a .env file for sensitive configuration"
        )

    if not config_found:
        check_warning(
            "No providers.json file found",
            "Create a providers.json file for configuration",
        )

    # 5. Tool Installation Check

    # 4b. Gemini / Google Vertex Authentication Check
    typer.echo()
    typer.echo(
        f"{Colors.BOLD}Gemini / Google Vertex Authentication Check{Colors.RESET}"
    )
    try:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        vertex_vars = [
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_GENAI_USE_VERTEXAI",
        ]
        present_vertex = [v for v in vertex_vars if os.environ.get(v)]

        if gemini_key:
            check_passed("GEMINI_API_KEY is set in the environment")
        elif len(present_vertex) == len(vertex_vars):
            # If GOOGLE_APPLICATION_CREDENTIALS is set, ensure the file exists
            gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if gac:
                try:
                    gac_path = Path(gac).expanduser()
                    if gac_path.exists():
                        check_passed(
                            "Vertex AI credentials appear configured (GOOGLE_APPLICATION_CREDENTIALS file exists)"
                        )
                    else:
                        check_warning(
                            "GOOGLE_APPLICATION_CREDENTIALS is set but file does not exist",
                            f"Check path: {gac}",
                        )
                except Exception:
                    check_warning(
                        "Unable to verify GOOGLE_APPLICATION_CREDENTIALS file path",
                        f"Value: {gac}",
                    )
            else:
                check_passed("Vertex AI variables are set")
        elif present_vertex:
            missing = [v for v in vertex_vars if v not in present_vertex]
            check_warning(
                f"Partial Vertex AI configuration present (missing: {', '.join(missing)})",
                "Set all required GOOGLE_* vars or use GEMINI_API_KEY for Gemini authentication",
            )
        else:
            check_warning(
                "No Gemini or Vertex authentication detected",
                "Set GEMINI_API_KEY or configure Vertex AI environment variables (GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI)",
            )
    except Exception as e:
        check_warning(f"Error while checking Gemini/Vertex environment: {e}")
    # 4c. GitHub Copilot Authentication Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}GitHub Copilot Authentication Check{Colors.RESET}")
    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            check_passed("GITHUB_TOKEN is set in the environment")
        else:
            check_warning(
                "GITHUB_TOKEN is not set",
                "Set GITHUB_TOKEN environment variable for GitHub Copilot API access",
            )
    except Exception as e:
        check_warning(f"Error while checking GitHub Copilot environment: {e}")

    # 5. Tool Installation Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Tool Installation Check{Colors.RESET}")
    from code_assistant_manager.tools import get_registered_tools

    registered_tools = get_registered_tools()
    available_tools = 0
    total_tools = 0

    for tool_name, tool_class in registered_tools.items():
        if tool_name == "mcp":
            continue  # Skip MCP as it's handled separately
        total_tools += 1
        try:
            tool = tool_class(config)
            # Use the command_name to check if the tool is installed via PATH
            if tool._check_command_available(tool.command_name):
                available_tools += 1
                check_passed(f"{tool_name} is installed")
            else:
                check_warning(
                    f"{tool_name} is not installed",
                    f"Run 'code-assistant-manager upgrade {tool_name}' to install",
                )
        except Exception as e:
            check_warning(f"Error checking {tool_name}: {e}")

    check_passed(f"Tools available: {available_tools}/{total_tools}")

    # 6. Endpoint Connectivity Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Endpoint Connectivity Check{Colors.RESET}")
    endpoints = config.get_sections()
    for endpoint_name in endpoints:
        endpoint_url = config.get_value(endpoint_name, "endpoint")
        if endpoint_url:
            # Basic connectivity check (just URL format, not actual request)
            if endpoint_url.startswith(("http://", "https://")):
                check_passed(f"{endpoint_name} endpoint URL format is valid")
            else:
                check_failed(
                    f"{endpoint_name} endpoint URL format is invalid: {endpoint_url}"
                )
        else:
            check_warning(f"{endpoint_name} has no endpoint URL configured")

    # 7. Cache Check
    typer.echo()
    typer.echo(f"{Colors.BOLD}Cache Check{Colors.RESET}")
    try:
        cache_dir = Path.home() / ".cache" / "code-assistant-manager"
        if cache_dir.exists():
            check_passed(f"Cache directory exists: {cache_dir}")
            # Check cache size (rough estimate)
            # Gather cache files
            files = [f for f in cache_dir.rglob("*") if f.is_file()]
            file_count = len(files)
            cache_size = sum(f.stat().st_size for f in files)
            cache_size_mb = cache_size / (1024 * 1024)

            def human_readable_size(num_bytes: int) -> str:
                # Converts bytes to human-friendly string (B, KB, MB, GB, ...)
                for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
                    if num_bytes < 1024.0:
                        return f"{num_bytes:.2f} {unit}"
                    num_bytes /= 1024.0
                return f"{num_bytes:.2f} PB"

            human_size = human_readable_size(cache_size)
            check_passed(
                f"Cache size: {human_size} ({cache_size_mb:.2f} MB) across {file_count} files"
            )

            if file_count > 0:
                from datetime import datetime

                # Collect stats once to avoid multiple syscalls
                stats = [(f, f.stat()) for f in files]
                latest_file, latest_stat = max(stats, key=lambda x: x[1].st_mtime)
                oldest_file, oldest_stat = min(stats, key=lambda x: x[1].st_mtime)

                latest_time = datetime.fromtimestamp(latest_stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                oldest_time = datetime.fromtimestamp(oldest_stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                typer.echo(
                    f"  Most recent: {latest_file.relative_to(cache_dir)} ({human_readable_size(latest_stat.st_size)}), modified {latest_time}"
                )
                typer.echo(
                    f"  Oldest: {oldest_file.relative_to(cache_dir)} ({human_readable_size(oldest_stat.st_size)}), modified {oldest_time}"
                )

                # Top N largest files
                top_n = 5
                typer.echo(f"  Top {top_n} largest cache files:")
                for f, st in sorted(stats, key=lambda x: x[1].st_size, reverse=True)[
                    :top_n
                ]:
                    mtime = datetime.fromtimestamp(st.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    size_hr = human_readable_size(st.st_size)
                    typer.echo(
                        f"    - {f.relative_to(cache_dir)}: {size_hr} ({st.st_size / (1024 * 1024):.2f} MB), modified {mtime}"
                    )
        else:
            check_passed("No cache directory found (cache will be created as needed)")
    except Exception as e:
        check_warning(f"Error checking cache: {e}")

    # 8. Security Audit
    typer.echo()
    typer.echo(f"{Colors.BOLD}Security Audit{Colors.RESET}")

    # Check for exposed API keys in configuration
    for endpoint_name in endpoints:
        api_key_env = config.get_value(endpoint_name, "api_key_env")
        if api_key_env:
            if os.environ.get(api_key_env):
                check_passed(f"{endpoint_name} uses environment variable for API key")
            else:
                check_warning(f"{endpoint_name} API key environment variable not set")

    # Check for hardcoded credentials in config (basic check)
    config_str = json.dumps(config.config_data, indent=2)
    suspicious_patterns = ["sk-", "pk_", "secret", "password", "token"]
    for _pattern in suspicious_patterns:
        if _pattern in config_str.lower():
            # This is a very basic check - in practice, this would need more sophisticated analysis
            check_warning(
                f"Potential sensitive data pattern {_pattern!r} found in configuration",
                "Ensure sensitive data is stored in environment variables, not config files",
            )

    # Summary
    typer.echo()
    typer.echo(f"{Colors.BOLD}Summary{Colors.RESET}")
    if issues_found == 0:
        typer.echo(
            f"{Colors.GREEN}✓ All checks passed! Your code-assistant-manager installation is healthy.{Colors.RESET}"
        )
        return 0
    else:
        typer.echo(
            f"{Colors.YELLOW}⚠ Found {issues_found} issue(s) that may need attention.{Colors.RESET}"
        )
        return 1
