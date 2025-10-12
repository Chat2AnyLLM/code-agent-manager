from typing import Optional

from .base import BaseUpgrade


class ShellUpgrade(BaseUpgrade):
    """Run an arbitrary shell install command provided by install_cmd.

    This is a thin wrapper around BaseUpgrade that simply executes the
    configured command. Subclasses may add verification/rollback logic.
    """

    def __init__(
        self,
        name: str,
        install_cmd: str,
        command_name: Optional[str] = None,
        target_version: Optional[str] = None,
        dry_run: bool = False,
        executor=None,
        logger=None,
    ):
        super().__init__(
            name=name,
            target_version=target_version,
            dry_run=dry_run,
            executor=executor,
            logger=logger,
        )
        self.install_cmd = install_cmd
        self.command_name = command_name

    def fetch(self):
        # Most shell installers do not have a separate fetch step
        self.logger.debug("shell fetch (no-op)")

    def install(self):
        self._run(self.install_cmd)

    def post_check(self):
        # Check if the command is available after installation
        if self.command_name:
            try:
                self._run(f"which {self.command_name}")
                self.logger.debug(
                    f"post_check: command '{self.command_name}' is available"
                )
            except Exception as e:
                raise Exception(
                    f"post-check failed: command '{self.command_name}' not found after installation"
                ) from e
        else:
            self.logger.debug("shell post_check (no-op)")

    def rollback(self):
        # No-op by default
        self.logger.warning("shell rollback (no-op)")
