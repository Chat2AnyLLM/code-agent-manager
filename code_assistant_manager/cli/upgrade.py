# Keep the backward compatibility functions
import logging
import time

import typer

logger = logging.getLogger(__name__)


def handle_upgrade_command(
    target: str, registered_tools: dict, config, verbose: bool = False
) -> int:
    """Handle the upgrade command for tools."""
    import os
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from code_assistant_manager.menu.base import Colors
    from code_assistant_manager.tools import TOOL_REGISTRY

    def _is_test_mode() -> bool:
        return bool(os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules)

    # Helper: npm package extraction and registry check (best-effort)
    def _extract_npm_package(install_cmd: str):
        try:
            clean_cmd = install_cmd.replace('"', "").replace("'", "")
            parts = clean_cmd.split()
            i = 0
            while i < len(parts) and parts[i] in [
                "npm",
                "install",
                "i",
                "-g",
                "--global",
                "--save",
                "--save-dev",
            ]:
                i += 1
            if i < len(parts):
                package_part = parts[i]
                if package_part.startswith("@"):
                    if "@" in package_part[1:]:
                        idx = package_part.rfind("@")
                        return package_part[:idx]
                    return package_part
                else:
                    if "@" in package_part:
                        return package_part.split("@")[0]
                    return package_part
        except Exception:
            return None
        return None

    def _get_latest_npm_version(package_name: str) -> str:
        try:
            import json
            import urllib.parse
            import urllib.request

            encoded = urllib.parse.quote(package_name, safe="@/")
            url = f"https://registry.npmjs.org/{encoded}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
            latest = data.get("dist-tags", {}).get("latest")
            if latest:
                return str(latest)
            return str(data.get("version", "unknown"))
        except Exception:
            return "unknown"

    def _extract_semver(s: str) -> str:
        import re

        if not s:
            return ""
        m = re.search(r"\d+\.\d+(?:\.\d+)?(?:[-+][\w\.]+)?", str(s))
        return m.group(0) if m else ""

    def _format_version(value) -> str:
        import re

        if value is None:
            return "unknown"
        text = str(value).strip()
        if not text:
            return "unknown"
        # Remove ANSI escape codes
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        text = ansi_escape.sub("", text)
        # Remove spinner/braille characters (used by some CLIs for progress indication)
        spinner_pattern = re.compile(r"[\u2800-\u28FF]")
        text = spinner_pattern.sub("", text)
        # Take the last non-empty line (version is typically at the end)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "unknown"
        text = lines[-1]
        return text or "unknown"

    # Track tools that we skipped via pre-check
    precheck_skipped = {}

    # Exclude MCP from upgradeable tools since it's now a subcommand
    upgradeable_tools = {k: v for k, v in registered_tools.items() if k != "mcp"}
    status_by_tool = {name: "pending" for name in upgradeable_tools}

    if target == "all":
        # Minimize output in test mode to avoid filling pytest capture buffers
        if not _is_test_mode():
            # typer.echo(f"{Colors.GREEN}Upgrading all tools...{Colors.RESET}")
            pass
        # Capture pre-upgrade versions
        pre_versions = {}
        for tool_name, tool_class in upgradeable_tools.items():
            try:
                tool_instance = tool_class(config)
                version = tool_instance._get_version()
            except Exception:
                version = "unknown"
            pre_versions[tool_name] = _format_version(version)
        success_count = 0
        total_count = 0
        actual_upgrades = 0
        processed_tools = 0

        # Prepare upgrade tasks
        upgrade_tasks = []

        # Track all tools that went through preparation
        prepared_tools = []

        for tool_name, tool_class in upgradeable_tools.items():
            # typer.echo(f"{Colors.BLUE}Preparing upgrade for {tool_name}...{Colors.RESET}")

            # Create tool instance to access its properties
            tool = tool_class(config)

            # Get tool key or use command name
            tool_key = getattr(tool, "tool_key", None) or getattr(
                tool, "command_name", tool_name
            )

            # Get install command from registry
            install_cmd = TOOL_REGISTRY.get_install_command(tool_key)
            if not install_cmd:
                status_by_tool[tool_name] = "no-command"
                # typer.echo(f"{Colors.YELLOW}No upgrade command found for {tool_name}{Colors.RESET}")
                continue

            # Best-effort pre-check for npm packages: skip if already at latest
            pkg_name = None
            try:
                if install_cmd.strip().startswith(("npm install", "npm i")):
                    pkg_name = _extract_npm_package(install_cmd)
            except Exception:
                pkg_name = None

            if pkg_name:
                # Get current version and latest registry version
                try:
                    current_v_raw = tool._get_version()
                except Exception:
                    current_v_raw = "unknown"
                current_v_display = _format_version(current_v_raw)
                current_v = _extract_semver(current_v_raw)
                latest_v = _get_latest_npm_version(pkg_name)
                latest_v_clean = _extract_semver(latest_v)
                latest_v_display = _format_version(latest_v)

                if current_v and latest_v_clean and current_v == latest_v_clean:
                    # typer.echo(f"  {tool_name}: {Colors.YELLOW}No upgrade available (installed: {current_v}){Colors.RESET}")
                    # Mark as skipped so we can report later
                    if "precheck_skipped" not in locals():
                        precheck_skipped = {}
                    precheck_skipped[tool_name] = {
                        "current": current_v_display,
                        "latest": latest_v_display,
                    }
                    status_by_tool[tool_name] = "skipped"
                    prepared_tools.append(
                        (tool_name, "skipped", None)
                    )  # Track as prepared but skipped
                    continue

            upgrade_tasks.append((tool_name, tool, install_cmd, pkg_name))
            prepared_tools.append(
                (tool_name, "upgrade", install_cmd)
            )  # Track as prepared for upgrade

        # Execute upgrades in parallel
        if prepared_tools:
            # typer.echo(f"\n{Colors.GREEN}Processing upgrades for {len(prepared_tools)} tools...{Colors.RESET}")

            results = {}
            completed = 0
            total = len(prepared_tools)
            is_tty = sys.stdout.isatty()
            bar_len = 30

            # Show initial progress bar
            if is_tty:
                percent = completed / total if total else 1.0
                filled = int(percent * bar_len)
                bar = "█" * filled + "-" * (bar_len - filled)
                # Use \r to ensure we start at the beginning of the line
                typer.echo(
                    f"Upgrading: [{bar}] {completed}/{total} tools processed", nl=False
                )

            # First, count the skipped tools as completed
            for _tool_name, action, _ in prepared_tools:
                if action == "skipped":
                    completed += 1
                    if is_tty:
                        percent = completed / total if total else 1.0
                        filled = int(percent * bar_len)
                        bar = "█" * filled + "-" * (bar_len - filled)
                        # Clear line and update progress
                        typer.echo(
                            f"\033[2K\rUpgrading: [{bar}] {completed}/{total} tools processed",
                            nl=False,
                        )
                        time.sleep(
                            0.05
                        )  # Small delay to make incremental progress visible
                    else:
                        typer.echo(f"  [{completed}/{total}] tools processed")

            # Then process the actual upgrades if any
            if upgrade_tasks:
                # Use ThreadPoolExecutor to run upgrades in parallel
                with ThreadPoolExecutor(
                    max_workers=5
                ) as executor:  # Limit to 5 concurrent upgrades
                    # Submit all upgrade tasks
                    future_to_tool = {
                        executor.submit(
                            _perform_upgrade_task,
                            tool_name,
                            tool,
                            install_cmd,
                            not verbose,
                        ): tool_name
                        for tool_name, tool, install_cmd, _pkg in upgrade_tasks
                    }

                    # Process the actual upgrades
                    for future in as_completed(future_to_tool):
                        tool_name = future_to_tool[future]
                        try:
                            task_result = future.result()
                            # task_result may be a boolean (legacy) or a dict from CLITool._perform_upgrade
                            if isinstance(task_result, dict):
                                success = bool(task_result.get("success"))
                                results[tool_name] = task_result
                            else:
                                success = bool(task_result)
                                results[tool_name] = {"success": success}

                        except Exception as e:
                            # Record failure but do not print stack traces to stderr
                            results[tool_name] = {"success": False, "error": str(e)}
                        finally:
                            completed += 1
                            # Always update a single progress bar line (TTY) or a compact per-line update
                            if is_tty:
                                # Update in-place progress bar
                                percent = completed / total if total else 1.0
                                filled = int(percent * bar_len)
                                bar = "█" * filled + "-" * (bar_len - filled)
                                typer.echo(
                                    f"\033[2K\rUpgrading: [{bar}] {completed}/{total} tools processed",
                                    nl=False,
                                )
                            else:
                                # Compact per-line update, keep only minimal text
                                typer.echo(f"  [{completed}/{total}] tools processed")

            if is_tty:
                # Finish the progress bar line and ensure clean terminal state
                typer.echo("")

            # Display results for ALL upgradeable tools, including ones skipped by pre-check
            typer.echo(f"{Colors.GREEN}Upgrade results:{Colors.RESET}")
            for tool_name in upgradeable_tools.keys():
                before_v = _format_version(pre_versions.get(tool_name, "unknown"))

                # If precheck indicated skip due to already latest
                if tool_name in precheck_skipped:
                    info = precheck_skipped[tool_name]
                    current = info.get("current") or before_v
                    # Print as: name: ✓ No upgrade (version unchanged) (current)
                    typer.echo(
                        f"  {tool_name}: {Colors.YELLOW}✓ No upgrade (version unchanged){Colors.RESET} {Colors.BLUE}({current}){Colors.RESET}"
                    )
                    status_by_tool[tool_name] = "skipped"
                    continue

                # If tool had no install command (we decremented total_count earlier), report accordingly
                install_cmd = TOOL_REGISTRY.get_install_command(
                    getattr(
                        upgradeable_tools[tool_name](config),
                        "tool_key",
                        getattr(
                            upgradeable_tools[tool_name](config),
                            "command_name",
                            tool_name,
                        ),
                    )
                )
                if not install_cmd:
                    typer.echo(
                        f"  {tool_name}: {Colors.YELLOW}No upgrade command available{Colors.RESET}"
                    )
                    status_by_tool[tool_name] = "no-command"
                    continue

                # If tool was part of the executed results
                if tool_name in results:
                    result_data = results[tool_name]
                    success = bool(result_data.get("success"))
                    # Attempt post-upgrade version
                    try:
                        post_version_raw = upgradeable_tools[tool_name](
                            config
                        )._get_version()
                    except Exception:
                        post_version_raw = "unknown"
                    post_version = _format_version(post_version_raw)

                    try:
                        same_version = before_v == post_version
                    except Exception:
                        same_version = False

                    if same_version:
                        if success:
                            status_by_tool[tool_name] = "no-change"
                            typer.echo(
                                f"  {tool_name}: {Colors.YELLOW}✓ No upgrade (version unchanged){Colors.RESET} {Colors.BLUE}({before_v}){Colors.RESET}"
                            )
                        else:
                            status_by_tool[tool_name] = "failed"
                            typer.echo(
                                f"  {tool_name}: {Colors.RED}✗ Failed during upgrade{Colors.RESET} {Colors.BLUE}({before_v} -> {post_version}){Colors.RESET}"
                            )
                    else:
                        if success:
                            status_by_tool[tool_name] = "upgraded"
                            typer.echo(
                                f"  {tool_name}: {Colors.GREEN}✓ Upgraded{Colors.RESET} {Colors.BLUE}({before_v} -> {post_version}){Colors.RESET}"
                            )
                        else:
                            status_by_tool[tool_name] = "failed"
                            typer.echo(
                                f"  {tool_name}: {Colors.RED}✗ Failed{Colors.RESET} {Colors.BLUE}({before_v} -> {post_version}){Colors.RESET}"
                            )
                else:
                    # Tool was not part of results (maybe skipped earlier), but not in precheck_skipped; show unknown status
                    typer.echo(
                        f"  {tool_name}: {Colors.YELLOW}No action taken{Colors.RESET} {Colors.BLUE}({before_v}){Colors.RESET}"
                    )
                    status_by_tool[tool_name] = "no-action"

            # Skip original loop as we've replaced it

        actual_upgrades = sum(
            1 for status in status_by_tool.values() if status == "upgraded"
        )

        typer.echo(
            f"\n{Colors.GREEN}Upgrade complete: {actual_upgrades}/{len(upgradeable_tools)} tools upgraded successfully{Colors.RESET}"
        )
        return (
            0 if actual_upgrades >= 0 else 1
        )  # Always return 0 for now, since we want success even if no upgrades were needed
    else:
        # Upgrade specific tool
        if target not in upgradeable_tools:
            typer.echo(f"{Colors.RED}Error: Unknown tool {target!r}{Colors.RESET}")
            return 1

        # Capture pre-upgrade version
        try:
            temp_tool = upgradeable_tools[target](config)
            before_version = _format_version(temp_tool._get_version())
        except Exception:
            before_version = "unknown"
        typer.echo(
            f"{Colors.GREEN}Upgrading {target}...{Colors.RESET} (current: {before_version})"
        )

        # Create tool instance
        tool_class = upgradeable_tools[target]
        tool = tool_class(config)

        # Get tool key or use command name
        tool_key = getattr(tool, "tool_key", None) or getattr(
            tool, "command_name", target
        )

        # Get install command from registry
        install_cmd = TOOL_REGISTRY.get_install_command(tool_key)
        if not install_cmd:
            typer.echo(
                f"{Colors.RED}No upgrade command found for {target}{Colors.RESET}"
            )
            return 1

        logger.debug(f"Using install command for {target}: {install_cmd}")

        # Perform upgrade directly without prompting
        try:
            if tool._perform_upgrade(
                getattr(tool, "install_description", target), install_cmd
            ):
                try:
                    after_version = _format_version(
                        upgradeable_tools[target](config)._get_version()
                    )
                except Exception:
                    after_version = "unknown"

                # Check if version actually changed
                if before_version == after_version and before_version != "unknown":
                    typer.echo(
                        f"  {target}: {Colors.YELLOW}✓ No upgrade (version unchanged){Colors.RESET} {Colors.BLUE}({before_version}){Colors.RESET}"
                    )
                else:
                    typer.echo(
                        f"{Colors.GREEN}Successfully upgraded {target}{Colors.RESET} {Colors.BLUE}({before_version} -> {after_version}){Colors.RESET}"
                    )
                return 0
            else:
                typer.echo(f"{Colors.RED}Failed to upgrade {target}{Colors.RESET}")
                return 1
        except Exception as e:
            typer.echo(f"{Colors.RED}Error upgrading {target}: {e}{Colors.RESET}")
            return 1


def _perform_upgrade_task(tool_name, tool, install_cmd, quiet: bool = False):
    """Helper function to perform upgrade task in parallel."""

    logger.debug(
        f"Starting parallel upgrade for {tool_name} with command: {install_cmd} (quiet={quiet})"
    )
    try:
        desc = getattr(tool, "install_description", tool_name)
        # If quiet mode, avoid per-task messages — rely on single overall progress bar
        if not quiet:
            # typer.echo(f"{Colors.BLUE}Starting upgrade for {tool_name}...{Colors.RESET}")
            pass

        # Perform the upgrade
        # Note: CommandRunner (used by _perform_upgrade) captures output, so it is inherently quiet.
        # We do not need to wrap commands in 'script' or redirects which can corrupt terminal state.
        result = tool._perform_upgrade(desc, install_cmd)
        return result
    except Exception as e:
        # Do not print exception stack traces to stderr; return structured failure
        logger.debug(f"Error in upgrade task for {tool_name}: {e}")
        return {"success": False, "error": str(e)}
