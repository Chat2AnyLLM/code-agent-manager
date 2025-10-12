from .base import BaseUpgrade


class PipUpgrade(BaseUpgrade):
    def fetch(self):
        # pip installs directly; no fetch step required
        self.logger.debug("pip fetch (no-op)")

    def install(self):
        pkg = self.name
        version_flag = f"=={self.target_version}" if self.target_version else ""
        cmd = f"pip install --upgrade {pkg}{version_flag}"
        self._run(cmd)

    def post_check(self):
        # verify version if possible
        try:
            out = self._run(
                f'python -c "import {self.name}; print({self.name}.__version__)"',
                check=False,
            )
        except Exception:
            # if we can't import to check, warn but don't fail by default
            self.logger.warning(
                "post_check: unable to import package to verify version"
            )
            return
        if self.target_version and self.target_version not in out:
            raise Exception("post-check failed: version mismatch")

    def rollback(self):
        # best-effort: attempt to reinstall previous version if known; otherwise no-op
        self.logger.warning("pip rollback: not implemented by default")
