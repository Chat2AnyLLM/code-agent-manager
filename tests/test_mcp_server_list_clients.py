import pytest
from typer.testing import CliRunner

from code_assistant_manager.mcp import server_commands

# We'll monkeypatch MCPManagerFactory on the server_commands module to return
# a fake manager with predictable behavior.


class FakeClient:
    def __init__(self, name):
        self.name = name
        self.list_called = False

    def list_servers(self):
        self.list_called = True
        print(f"listing for {self.name}")
        return True


class FakeManager:
    def __init__(self, clients):
        # clients: dict name -> FakeClient
        self._clients = clients

    def get_client(self, name):
        return self._clients.get(name.lower())

    def get_available_tools(self):
        return list(self._clients.keys())


@pytest.fixture(autouse=True)
def patch_manager(monkeypatch):
    # Create fake clients for claude and codex
    clients = {
        "claude": FakeClient("claude"),
        "codex": FakeClient("codex"),
    }
    fake_mgr = FakeManager(clients)

    monkeypatch.setattr(server_commands, "MCPManagerFactory", lambda: fake_mgr)
    yield


def test_list_single_client(tmp_path):
    runner = CliRunner()
    result = runner.invoke(server_commands.app, ["list", "--client", "claude"])
    assert result.exit_code == 0
    output = result.output
    assert "MCP Servers installed for claude" in output
    assert "listing for claude" in output


def test_list_comma_separated_clients(tmp_path):
    runner = CliRunner()
    result = runner.invoke(server_commands.app, ["list", "--client", "claude,codex"])
    assert result.exit_code == 0
    output = result.output
    # Both clients should appear
    assert "MCP Servers installed for claude" in output
    assert "MCP Servers installed for codex" in output
    assert "listing for claude" in output
    assert "listing for codex" in output


def test_list_all_special_value(tmp_path):
    runner = CliRunner()
    result = runner.invoke(server_commands.app, ["list", "--client", "all"])
    assert result.exit_code == 0
    output = result.output
    # Because get_available_tools returns keys 'claude' and 'codex', both should be listed
    assert "MCP Servers installed for claude" in output
    assert "MCP Servers installed for codex" in output


def test_list_unknown_client(tmp_path):
    runner = CliRunner()
    result = runner.invoke(server_commands.app, ["list", "--client", "doesnotexist"])
    # Should exit cleanly but print error about unsupported client
    assert result.exit_code == 0
    output = result.output
    assert "is not supported" in output
