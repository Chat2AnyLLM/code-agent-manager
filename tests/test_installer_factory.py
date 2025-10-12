from code_assistant_manager.upgrades.installer_factory import pick_installer
from code_assistant_manager.upgrades.npm_upgrade import NpmUpgrade
from code_assistant_manager.upgrades.shell_upgrade import ShellUpgrade


def test_pick_npm():
    inst = pick_installer(
        name="foo", install_cmd="npm install -g @org/foo@latest", command_name="foo"
    )
    assert isinstance(inst, NpmUpgrade)


def test_pick_shell_for_curl():
    inst = pick_installer(
        name="zed",
        install_cmd="curl -f https://zed.dev/install.sh | sh",
        command_name="zed",
    )
    assert isinstance(inst, ShellUpgrade)


def test_pick_default_shell():
    inst = pick_installer(
        name="custom",
        install_cmd="/usr/local/bin/install-custom",
        command_name="custom",
    )
    assert isinstance(inst, ShellUpgrade)
