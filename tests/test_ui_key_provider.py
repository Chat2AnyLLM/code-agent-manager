from code_assistant_manager.menu.menus import display_centered_menu


def make_provider(seq):
    it = iter(seq)
    return lambda: next(it, None)


def test_key_provider_arrow_navigation():
    # Build a provider that simulates Down Arrow then Enter
    # Arrow sequences: '\x1b', '[', 'B'
    provider = make_provider(["\x1b", "[", "B", "\r"])

    success, idx = display_centered_menu("Pick", ["a", "b", "c"], key_provider=provider)
    assert success is True
    # After one down arrow, highlight moves to index 1 (original index 1)
    assert idx == 1
