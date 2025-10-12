#!/usr/bin/env python3
"""Example of creating custom menu classes by inheriting from Menu base class."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Optional, Tuple

from code_assistant_manager.menu import Colors, Menu


class ColoredMenu(Menu):
    """A custom menu that displays items with different colors."""

    def _calculate_menu_height(self) -> int:
        """Calculate menu height."""
        return len(self.items) + 5  # items + title + borders + prompt

    def _draw_menu_items(self, highlighted_idx: int = -1):
        """Draw menu items with alternating colors."""
        colors = [Colors.YELLOW, Colors.GREEN, Colors.CYAN, Colors.BLUE]

        for i, item in enumerate(self.items):
            num = i + 1
            # Truncate item if too long
            available_width = self.max_item_len - 8
            display_item = item
            if len(item) > available_width:
                display_item = item[: available_width - 3] + "..."

            # Choose color based on index
            item_color = colors[i % len(colors)]

            print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET}", end="")
            print(f" {Colors.GREEN}{num:2d}{Colors.RESET}) ", end="")

            if i == highlighted_idx:
                print(
                    f"{Colors.REVERSE}{item_color}{display_item:<{available_width}}{Colors.RESET}{Colors.REVERSE_OFF}",
                    end="",
                )
            else:
                print(
                    f"{item_color}{display_item:<{available_width}}{Colors.RESET}",
                    end="",
                )

            print(f" {Colors.CYAN}║{Colors.RESET}")

    def _get_prompt_text(self) -> str:
        """Get prompt text."""
        return "Use ↑/↓ to navigate, Enter to select: "

    def display(self) -> Tuple[bool, Optional[int]]:
        """Display menu and get user selection."""
        # Initial draw
        self._draw_menu(0)

        # Prompt for selection
        print()
        self._redraw_with_prompt()

        attempt = 0

        try:
            # Try arrow key navigation
            choice = None
            while attempt < self.max_attempts:
                try:
                    char = self._get_key()

                    if char is None:
                        # Fallback to regular input
                        choice = input()
                        break

                    if self._handle_navigation_key(char):
                        continue
                    elif char == "\r" or char == "\n":  # Enter
                        return self._handle_selection()
                except (OSError, AttributeError):
                    # Fall back to regular input
                    choice = input()
                    break

            if choice is None:
                return self._handle_selection()

        except (ImportError, KeyboardInterrupt, EOFError):
            # Fall back to regular input without arrow keys
            print()
            try:
                choice = input(
                    " " * self.left_margin
                    + f"{Colors.BOLD}Enter selection [1-{len(self.items) + 1}]: {Colors.RESET}"
                )
            except (KeyboardInterrupt, EOFError):
                print()
                print(
                    " " * self.left_margin
                    + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
                )
                return False, None

        # Process the selection (fallback path for numeric input)
        while attempt < self.max_attempts:
            continue_loop, result, attempt = self._process_numeric_input(
                choice, attempt
            )
            if not continue_loop:
                if result is not None:
                    return True, result
                return False, None
            try:
                choice = input()
            except (KeyboardInterrupt, EOFError):
                print()
                print(
                    " " * self.left_margin
                    + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
                )
                return False, None

        # Max attempts exceeded
        print()
        print(
            " " * self.left_margin
            + f"{Colors.RED}Maximum attempts exceeded. Selection cancelled.{Colors.RESET}",
            file=sys.stderr,
        )
        return False, None


class NumberedPrefixMenu(Menu):
    """A custom menu that adds item numbers to the display."""

    def _calculate_menu_height(self) -> int:
        """Calculate menu height."""
        return len(self.items) + 5

    def _draw_menu_items(self, highlighted_idx: int = -1):
        """Draw menu items with numbered prefixes."""
        for i, item in enumerate(self.items):
            num = i + 1
            # Add number prefix to item text
            prefixed_item = f"[{num}] {item}"

            # Truncate if too long
            available_width = self.max_item_len - 8
            display_item = prefixed_item
            if len(prefixed_item) > available_width:
                display_item = prefixed_item[: available_width - 3] + "..."

            print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET}", end="")
            print(f" {Colors.GREEN}{num:2d}{Colors.RESET}) ", end="")

            if i == highlighted_idx:
                print(
                    f"{Colors.REVERSE}{Colors.YELLOW}{display_item:<{available_width}}{Colors.RESET}{Colors.REVERSE_OFF}",
                    end="",
                )
            else:
                print(
                    f"{Colors.YELLOW}{display_item:<{available_width}}{Colors.RESET}",
                    end="",
                )

            print(f" {Colors.CYAN}║{Colors.RESET}")

    def _get_prompt_text(self) -> str:
        """Get prompt text."""
        return "Use ↑/↓ to navigate, Enter to select: "

    def display(self) -> Tuple[bool, Optional[int]]:
        """Display menu and get user selection - reuse parent's SimpleMenu logic."""
        from code_assistant_manager.menu import SimpleMenu

        # We can delegate to SimpleMenu's display implementation
        # since we only changed rendering
        return SimpleMenu.display(self)


def main():
    """Demonstrate custom menu classes."""

    print(f"{Colors.BOLD}=== Custom Menu Examples ==={Colors.RESET}\n")

    # Example 1: Colored Menu
    print(f"{Colors.CYAN}Example 1: ColoredMenu with alternating colors{Colors.RESET}")
    items1 = ["Python", "JavaScript", "Go", "Rust", "TypeScript"]
    menu1 = ColoredMenu("Select Programming Language", items1)
    success, idx = menu1.display()

    if success and idx is not None:
        print(f"\n{Colors.GREEN}You selected: {items1[idx]}{Colors.RESET}\n")
    else:
        print(f"\n{Colors.YELLOW}Selection cancelled{Colors.RESET}\n")

    # Give user a moment to see result
    import time

    time.sleep(2)

    # Example 2: Numbered Prefix Menu
    print(
        f"\n{Colors.CYAN}Example 2: NumberedPrefixMenu with item numbers in display{Colors.RESET}"
    )
    items2 = ["Create new project", "Open existing project", "Settings", "Help"]
    menu2 = NumberedPrefixMenu("Main Menu", items2)
    success, idx = menu2.display()

    if success and idx is not None:
        print(f"\n{Colors.GREEN}You selected: {items2[idx]}{Colors.RESET}\n")
    else:
        print(f"\n{Colors.YELLOW}Selection cancelled{Colors.RESET}\n")


if __name__ == "__main__":
    main()
