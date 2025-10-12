import pytest

from code_assistant_manager.upgrades.base import (
    BaseUpgrade,
    RollbackError,
    UpgradeError,
)
from code_assistant_manager.upgrades.command_runner import CommandRunner
from code_assistant_manager.upgrades.pip_upgrade import PipUpgrade


class DummyExecutor:
    def __init__(self, responses=None, fail_on=None):
        self.responses = responses or {}
        self.fail_on = fail_on or set()
        self.commands = []

    def run(self, cmd: str, check: bool = True) -> str:
        self.commands.append(cmd)
        for key in self.fail_on:
            if key in cmd:
                raise RuntimeError("simulated failure")
        return self.responses.get(cmd, "ok")


def test_pip_upgrade_success(tmp_path, caplog):
    exec = DummyExecutor(
        responses={
            "pip install --upgrade foo==1.2.3": "installed",
            'python -c "import foo; print(foo.__version__)"': "1.2.3\n",
        }
    )
    up = PipUpgrade(name="foo", target_version="1.2.3", dry_run=False, executor=exec)

    res = up.run()

    assert res["status"] == "success"
    assert "pip install --upgrade foo==1.2.3" in exec.commands


def test_pip_upgrade_dry_run(tmp_path):
    exec = DummyExecutor()
    up = PipUpgrade(name="foo", target_version="1.2.3", dry_run=True, executor=exec)

    res = up.run()
    assert res["status"] == "success"
    assert exec.commands == []


def test_pip_upgrade_failure_triggers_rollback(tmp_path):
    exec = DummyExecutor(fail_on={"pip install"})
    up = PipUpgrade(name="foo", target_version="1.2.3", dry_run=False, executor=exec)

    with pytest.raises(UpgradeError):
        up.run()
