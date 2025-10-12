import builtins
import termios

from code_assistant_manager.menu.menus import display_centered_menu


def test_numeric_fallback_selection(monkeypatch):
    # Force raw-mode path to fail so code falls back to input()
    def _raise(fd):
        raise termios.error

    monkeypatch.setattr(termios, "tcgetattr", _raise)

    # Simulate the user entering '2' to select the second item
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")

    success, idx = display_centered_menu(
        "Choose", ["one", "two", "three"], max_attempts=1
    )
    assert success is True
    assert idx == 1
