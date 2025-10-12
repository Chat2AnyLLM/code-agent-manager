import abc
import logging
from typing import Dict, Optional


class UpgradeError(Exception):
    pass


class RollbackError(Exception):
    pass


class BaseUpgrade(abc.ABC):
    """
    Parent upgrade class that defines the lifecycle and common helpers.

    Subclasses should implement fetch() and install(). They may override
    pre_check(), post_check(), rollback(), and cleanup().
    """

    def __init__(
        self,
        name: str,
        target_version: Optional[str] = None,
        dry_run: bool = False,
        executor=None,
        logger=None,
    ):
        self.name = name
        self.target_version = target_version
        self.dry_run = dry_run
        self.executor = executor
        self.logger = logger or logging.getLogger(f"upgrade.{name}")

    def run(self) -> Dict:
        """
        Orchestrate the full upgrade. This is the Template Method.
        """
        self.logger.info("Starting upgrade: %s -> %s", self.name, self.target_version)
        try:
            self.pre_check()
            self.fetch()
            if self.dry_run:
                self.logger.info("Dry run enabled; skipping install step.")
            else:
                self.install()
                self.post_check()
        except Exception as e:
            self.logger.exception("Upgrade failed, attempting rollback.")
            try:
                self.rollback()
            except Exception as rb_e:
                self.logger.exception("Rollback failed")
                raise RollbackError("rollback failed") from rb_e
            raise UpgradeError("upgrade failed") from e
        finally:
            try:
                self.cleanup()
            except Exception:
                self.logger.exception("Cleanup failed (non-fatal)")

        return {"name": self.name, "version": self.target_version, "status": "success"}

    # lifecycle hooks
    def pre_check(self):
        """Default pre-check: subclasses may override."""
        self.logger.debug("default pre_check (no-op)")

    @abc.abstractmethod
    def fetch(self):
        """Download or prepare artifacts (must implement)."""

    @abc.abstractmethod
    def install(self):
        """Perform the actual installation (must implement)."""

    def post_check(self):
        """Verify installation success; subclasses may override."""
        self.logger.debug("default post_check (no-op)")

    def rollback(self):
        """Rollback to previous state; best-effort."""
        self.logger.warning("default rollback (no-op)")

    def cleanup(self):
        """Cleanup temporary artifacts; optional."""
        self.logger.debug("default cleanup (no-op)")

    # helpers
    def _run(self, cmd: str, check: bool = True) -> str:
        if self.dry_run:
            self.logger.info("[dry-run] would run: %s", cmd)
            return ""
        if not self.executor:
            raise RuntimeError("No executor configured")
        return self.executor.run(cmd, check=check)
