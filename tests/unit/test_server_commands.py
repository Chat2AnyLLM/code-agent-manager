from types import SimpleNamespace

import pytest

from code_assistant_manager.mcp import server_commands


class DummyManager:
    def __init__(self, available):
        self._available = available

    def get_client(self, name):
        return name if name in self._available else None

    def get_available_tools(self):
        return list(self._available)


class DummyInstaller:
    def __init__(self):
        self.calls = []

    def install_server(
        self,
        server_name,
        client_name,
        installation_method=None,
        force=False,
        scope="user",
    ):
        self.calls.append((server_name, client_name, installation_method, force, scope))
        return True


def test_add_handles_comma_separated_clients(monkeypatch):
    dummy_manager = DummyManager({"claude", "codex"})
    monkeypatch.setattr(
        server_commands,
        "MCPManagerFactory",
        lambda: SimpleNamespace(
            get_client=dummy_manager.get_client,
            get_available_tools=dummy_manager.get_available_tools,
        ),
    )

    dummy_installer = DummyInstaller()
    monkeypatch.setattr(server_commands, "installation_manager", dummy_installer)
    # ensure registry has the server schema
    monkeypatch.setattr(
        server_commands,
        "registry_manager",
        SimpleNamespace(get_server_schema=lambda name: object()),
        raising=False,
    )

    # Call add with two clients
    server_commands.add(
        "test-server",
        client="claude,codex",
        method="auto",
        force=True,
        interactive=False,
        scope="user",
    )

    assert ("test-server", "claude", "auto", True, "user") in dummy_installer.calls
    assert ("test-server", "codex", "auto", True, "user") in dummy_installer.calls


def test_add_handles_all_keyword(monkeypatch):
    dummy_manager = DummyManager({"claude", "codex"})
    monkeypatch.setattr(
        server_commands,
        "MCPManagerFactory",
        lambda: SimpleNamespace(
            get_client=dummy_manager.get_client,
            get_available_tools=dummy_manager.get_available_tools,
        ),
    )

    dummy_installer = DummyInstaller()
    monkeypatch.setattr(server_commands, "installation_manager", dummy_installer)
    # ensure registry has the server schema
    monkeypatch.setattr(
        server_commands,
        "registry_manager",
        SimpleNamespace(get_server_schema=lambda name: object()),
        raising=False,
    )

    server_commands.add(
        "test-server",
        client="all",
        method=None,
        force=False,
        interactive=False,
        scope="user",
    )

    assert ("test-server", "claude", None, False, "user") in dummy_installer.calls
    assert ("test-server", "codex", None, False, "user") in dummy_installer.calls


def test_remove_handles_comma_separated_clients(monkeypatch):
    dummy_manager = DummyManager({"claude", "codex"})
    monkeypatch.setattr(
        server_commands,
        "MCPManagerFactory",
        lambda: SimpleNamespace(
            get_client=dummy_manager.get_client,
            get_available_tools=dummy_manager.get_available_tools,
        ),
    )

    # monkeypatch client remove_server behavior via manager.get_client returning object with remove_server
    class ClientObj:
        def __init__(self, name, record):
            self.name = name
            self.record = record

        def remove_server(self, server_name, scope):
            self.record.append((self.name, server_name, scope))
            return True

    record = []
    monkeypatch.setattr(
        "code_assistant_manager.mcp.manager.MCPManager",
        lambda: SimpleNamespace(
            get_client=lambda n: (
                ClientObj(n, record) if n in {"claude", "codex"} else None
            ),
            get_available_tools=dummy_manager.get_available_tools,
        ),
    )

    server_commands.remove(
        "test-server", client="claude,codex", interactive=False, scope="user"
    )

    assert ("claude", "test-server", "user") in record
    assert ("codex", "test-server", "user") in record


def test_update_handles_comma_separated_clients(monkeypatch):
    dummy_manager = DummyManager({"claude", "codex"})

    class ClientObj:
        def __init__(self, name, record):
            self.name = name
            self.record = record

        def remove_server(self, server_name, scope):
            self.record.append((self.name, "removed", server_name, scope))
            return True

        def add_server(self, server_name, scope):
            self.record.append((self.name, "added", server_name, scope))
            return True

    record = []
    monkeypatch.setattr(
        "code_assistant_manager.mcp.manager.MCPManager",
        lambda: SimpleNamespace(
            get_client=lambda n: (
                ClientObj(n, record) if n in {"claude", "codex"} else None
            ),
            get_available_tools=dummy_manager.get_available_tools,
        ),
    )

    # need registry check for existing server schema, monkeypatch registry_manager
    class Schema:
        def __init__(self):
            self.name = "test-server"
            self.display_name = "Test Server"
            self.description = "dummy"
            self.categories = []
            self.installations = {}

    monkeypatch.setattr(
        server_commands,
        "registry_manager",
        SimpleNamespace(
            get_server_schema=lambda name: Schema(),
            list_server_schemas=lambda: {"test-server": Schema()},
        ),
    )

    # Mock installation_manager to track install_server calls
    class DummyInstallationManager:
        def install_server(self, server_name, client_name, scope="user"):
            record.append((client_name, "added", server_name, scope))
            return True

    monkeypatch.setattr(
        server_commands, "installation_manager", DummyInstallationManager()
    )

    server_commands.update(
        "test-server", client="claude,codex", interactive=False, scope="user"
    )

    # ensure both remove and add recorded for each client
    assert ("claude", "removed", "test-server", "user") in record
    assert ("claude", "added", "test-server", "user") in record
    assert ("codex", "removed", "test-server", "user") in record
    assert ("codex", "added", "test-server", "user") in record
