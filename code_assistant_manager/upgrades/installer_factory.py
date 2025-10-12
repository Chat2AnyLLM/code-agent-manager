from typing import Optional

from .base import BaseUpgrade
from .npm_upgrade import NpmUpgrade
from .shell_upgrade import ShellUpgrade


def pick_installer(
    name: str,
    install_cmd: str,
    command_name: Optional[str] = None,
    target_version: Optional[str] = None,
    dry_run: bool = False,
    executor=None,
    logger=None,
) -> BaseUpgrade:
    """Return an installer instance appropriate for the given install_cmd.

    Heuristics:
    - If command contains 'npm' and 'install', use NpmUpgrade
    - If it's a curl|sh pattern or contains 'curl' + '|' + 'sh', use ShellUpgrade
    - Otherwise default to ShellUpgrade
    """
    cmd_lower = install_cmd.lower()
    if "npm" in cmd_lower and "install" in cmd_lower:
        return NpmUpgrade(
            name=name,
            install_cmd=install_cmd,
            command_name=command_name,
            target_version=target_version,
            dry_run=dry_run,
            executor=executor,
            logger=logger,
        )
    # detect curl pipe to sh
    if "curl" in cmd_lower and (
        "| sh" in cmd_lower or "|bash" in cmd_lower or "| sh -" in cmd_lower
    ):
        return ShellUpgrade(
            name=name,
            install_cmd=install_cmd,
            command_name=command_name,
            target_version=target_version,
            dry_run=dry_run,
            executor=executor,
            logger=logger,
        )

    # default
    return ShellUpgrade(
        name=name,
        install_cmd=install_cmd,
        command_name=command_name,
        target_version=target_version,
        dry_run=dry_run,
        executor=executor,
        logger=logger,
    )
