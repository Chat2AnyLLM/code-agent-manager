"""Menu classes for Code Assistant Manager."""

import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple


class Colors:
    """ANSI color codes."""

    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    REVERSE = "\033[7m"
    REVERSE_OFF = "\033[27m"


class Menu(ABC):
    """Base class for terminal menu display."""

    def __init__(
        self,
        title: str,
        items: List[str],
        cancel_text: str = "Cancel",
        max_attempts: int = 3,
        key_provider: Optional[Callable[[], Optional[str]]] = None,
    ):
        """
        Initialize menu.

        Args:
            title: Menu title
            items: List of menu items
            cancel_text: Text for cancel option
            max_attempts: Maximum input attempts
            key_provider: Optional function to provide keyboard input (for testing)
        """
        self.title: str = title
        self.items: List[str] = items
        self.cancel_text: str = cancel_text
        self.max_attempts: int = max_attempts
        self.key_provider: Optional[Callable[[], Optional[str]]] = key_provider
        self.selected_idx: int = 0
        self.term_width: int
        self.term_height: int
        self.term_width, self.term_height = self._get_terminal_size()
        self.max_item_len: int = self._calculate_menu_width()
        self.left_margin: int = max(0, (self.term_width - self.max_item_len) // 2)

    @staticmethod
    def _get_terminal_size() -> Tuple[int, int]:
        """Get terminal width and height."""
        try:
            cols, rows = shutil.get_terminal_size((80, 24))
            return cols, rows
        except Exception:
            return 80, 24

    @staticmethod
    def _clear_screen():
        """Clear the terminal screen."""
        subprocess.run(["clear"] if os.name == "posix" else ["cls"], check=False)

    def _calculate_menu_width(self) -> int:
        """Calculate menu width based on content with smarter sizing for long titles."""
        max_content_len = len(self.title)
        for item in self.items:
            if len(item) > max_content_len:
                max_content_len = len(item)

        if len(self.cancel_text) > max_content_len:
            max_content_len = len(self.cancel_text)

        # Total width = content + formatting overhead (8 chars: "║ NN) " and " ║")
        max_item_len = max_content_len + 8

        # For very long titles, allow menu to be wider (up to 80% of terminal)
        if len(self.title) > 60:
            return min(max_item_len, int(self.term_width * 0.8))

        # For normal titles, ensure minimum and maximum width
        return max(50, min(max_item_len, self.term_width - 10))

    def _draw_border_top(self):
        """Draw top border."""
        print(" " * self.left_margin + f"{Colors.CYAN}╔", end="")
        print("═" * (self.max_item_len - 2), end="")
        print(f"╗{Colors.RESET}")

    def _draw_border_bottom(self):
        """Draw bottom border."""
        print(" " * self.left_margin + f"{Colors.CYAN}╚", end="")
        print("═" * (self.max_item_len - 2), end="")
        print(f"╝{Colors.RESET}")

    def _draw_separator(self):
        """Draw horizontal separator."""
        print(" " * self.left_margin + f"{Colors.CYAN}╠", end="")
        print("═" * (self.max_item_len - 2), end="")
        print(f"╣{Colors.RESET}")

    def _draw_title(self):
        """Draw menu title."""
        title_padding = (self.max_item_len - len(self.title) - 2) // 2
        print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET}", end="")
        print(" " * title_padding, end="")
        print(f"{Colors.BOLD}{Colors.BLUE}{self.title}{Colors.RESET}", end="")
        print(" " * (self.max_item_len - len(self.title) - title_padding - 2), end="")
        print(f"{Colors.CYAN}║{Colors.RESET}")

    def _draw_item(self, num: int, item: str, is_highlighted: bool = False):
        """
        Draw a menu item.

        Args:
            num: Item number (1-based)
            item: Item text
            is_highlighted: Whether to highlight this item
        """
        available_width = self.max_item_len - 8
        display_item = item
        if len(item) > available_width:
            display_item = item[: available_width - 3] + "..."

        print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET}", end="")
        print(f" {Colors.GREEN}{num:2d}{Colors.RESET}) ", end="")

        if is_highlighted:
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

    def _draw_cancel_option(self, is_highlighted: bool = False):
        """Draw cancel option."""
        cancel_num = len(self.items) + 1
        available_width = self.max_item_len - 8

        print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET}", end="")
        print(f" {Colors.GREEN}{cancel_num:2d}{Colors.RESET}) ", end="")

        if is_highlighted:
            print(
                f"{Colors.REVERSE}{self.cancel_text:<{available_width}}{Colors.RESET}{Colors.REVERSE_OFF}",
                end="",
            )
        else:
            print(f"{self.cancel_text:<{available_width}}", end="")

        print(f" {Colors.CYAN}║{Colors.RESET}")

    @abstractmethod
    def _draw_menu_items(self, highlighted_idx: int = -1):
        """
        Draw menu items. To be implemented by subclasses.

        Args:
            highlighted_idx: Index to highlight
        """

    @abstractmethod
    def _get_prompt_text(self) -> str:
        """Get prompt text for user input. To be implemented by subclasses."""

    def _draw_menu(self, highlighted_idx: int = -1):
        """
        Draw the complete menu.

        Args:
            highlighted_idx: Index to highlight
        """
        menu_height = self._calculate_menu_height()
        top_margin = max(1, (self.term_height - menu_height) // 2)

        # Clear screen and move to top position
        self._clear_screen()
        if top_margin > 0:
            print("\n" * top_margin, end="", flush=True)

        # Draw menu structure
        self._draw_border_top()
        self._draw_title()
        self._draw_separator()
        self._draw_menu_items(highlighted_idx)
        self._draw_cancel_option(highlighted_idx == len(self.items))
        self._draw_border_bottom()

    @abstractmethod
    def _calculate_menu_height(self) -> int:
        """Calculate menu height. To be implemented by subclasses."""

    def _get_key(self):
        """Get a single key from stdin or from the provided key_provider."""
        # If a test-provided key provider exists, use it first
        if self.key_provider is not None:
            try:
                return self.key_provider()
            except Exception:
                return None

        try:
            import termios
            import tty

            # Set terminal to raw mode
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch
        except (ImportError, OSError, AttributeError):
            # Fallback if raw mode not available
            return None

    def _handle_navigation_key(self, char: str) -> bool:
        """
        Handle navigation keys (arrow keys, etc.).

        Args:
            char: Character received

        Returns:
            True if navigation was handled, False otherwise
        """
        return self._handle_common_navigation(char)

    def _handle_common_navigation(
        self, char: str, max_items: Optional[int] = None
    ) -> bool:
        """
        Handle common navigation keys (arrow keys).

        Args:
            char: Character received
            max_items: Maximum number of items (defaults to len(self.items))

        Returns:
            True if navigation was handled, False otherwise
        """
        if max_items is None:
            max_items = len(self.items)

        if char == "\x1b":  # Escape sequence
            next1 = self._get_key()
            if next1 == "[":
                next2 = self._get_key()
                if next2 == "A":  # Up arrow
                    if self.selected_idx > 0:
                        self.selected_idx -= 1
                        self._redraw_with_prompt()
                    return True
                elif next2 == "B":  # Down arrow
                    if self.selected_idx < max_items:
                        self.selected_idx += 1
                        self._redraw_with_prompt()
                    return True
        return False

    def _redraw_with_prompt(self):
        """Redraw menu with prompt."""
        self._draw_menu(self.selected_idx)
        print()
        print(
            " " * self.left_margin
            + f"{Colors.BOLD}{self._get_prompt_text()}{Colors.RESET}",
            end="",
            flush=True,
        )

    def _handle_selection(self) -> Tuple[bool, Optional[int]]:
        """
        Handle item selection.

        Returns:
            Tuple of (success, selected_index)
        """
        if self.selected_idx < len(self.items):
            print()
            print(
                " " * self.left_margin
                + f"{Colors.GREEN}✓ Selected: {Colors.BOLD}{self.items[self.selected_idx]}{Colors.RESET}"
            )
            return True, self.selected_idx
        elif self.selected_idx == len(self.items):
            print()
            print(
                " " * self.left_margin
                + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
            )
            return False, None
        return False, None

    def _handle_input_validation_attempt(
        self, error_msg: str, attempt: int
    ) -> Tuple[bool, Optional[int], int]:
        """
        Handle a validation error during input processing.

        Args:
            error_msg: Error message to display
            attempt: Current attempt number

        Returns:
            Tuple of (continue_loop, result_index, new_attempt)
        """
        attempt += 1
        if attempt < self.max_attempts:
            print(
                " " * self.left_margin
                + f"{Colors.YELLOW}{error_msg} (attempt {attempt + 1}/{self.max_attempts}): {Colors.RESET}",
                end="",
                flush=True,
            )
            try:
                return True, None, attempt
            except (KeyboardInterrupt, EOFError):
                print()
                print(
                    " " * self.left_margin
                    + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
                )
                return False, None, attempt
        return False, None, attempt

    def _process_numeric_input(
        self, choice: str, attempt: int
    ) -> Tuple[bool, Optional[int], int]:
        """
        Process numeric input from user.

        Args:
            choice: User input string
            attempt: Current attempt number

        Returns:
            Tuple of (continue_loop, result_index, new_attempt)
        """
        choice = choice.strip()

        # Check for empty input
        if not choice:
            return self._handle_input_validation_attempt(
                f"Please enter a number between 1 and {len(self.items) + 1}", attempt
            )

        # Check if input is a valid number
        if not choice.isdigit():
            return self._handle_input_validation_attempt(
                f"Invalid input: Please enter a number between 1 and {len(self.items) + 1}",
                attempt,
            )

        # Check if number is in valid range
        choice_num = int(choice)
        if choice_num < 1 or choice_num > len(self.items) + 1:
            return self._handle_input_validation_attempt(
                f"Number out of range: Please enter a number between 1 and {len(self.items) + 1}",
                attempt,
            )

        # Valid input received
        if choice_num == len(self.items) + 1:
            print()
            print(
                " " * self.left_margin
                + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
            )
            return False, None, attempt

        selected_idx = choice_num - 1
        print()
        print(
            " " * self.left_margin
            + f"{Colors.GREEN}✓ Selected: {Colors.BOLD}{self.items[selected_idx]}{Colors.RESET}"
        )
        return False, selected_idx, attempt

    @abstractmethod
    def display(self) -> Tuple[bool, Optional[int]]:
        """
        Display menu and get user selection.

        Returns:
            Tuple of (success, selected_index)
        """


class SimpleMenu(Menu):
    """Simple menu without filtering."""

    def _calculate_menu_height(self) -> int:
        """Calculate menu height."""
        return len(self.items) + 5  # items + title + borders + prompt

    def _draw_menu_items(self, highlighted_idx: int = -1):
        """Draw menu items."""
        for i, item in enumerate(self.items):
            self._draw_item(i + 1, item, i == highlighted_idx)

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


class FilterableMenu(Menu):
    """Menu with dynamic filtering capability."""

    def __init__(self, *args, **kwargs):
        """Initialize filterable menu."""
        super().__init__(*args, **kwargs)
        self.filter_text = ""
        self.original_items = self.items.copy()
        self.filtered_items = [(i, item) for i, item in enumerate(self.original_items)]

    def _calculate_menu_height(self) -> int:
        """Calculate menu height."""
        num_items = len(self.filtered_items) if self.filtered_items else 1
        return num_items + 6  # items + title + borders + prompt + filter line

    def _filter_items(self) -> List[Tuple[int, str]]:
        """Filter items based on filter text (case-insensitive)."""
        if not self.filter_text:
            return [(i, item) for i, item in enumerate(self.original_items)]

        filter_lower = self.filter_text.lower()
        return [
            (i, item)
            for i, item in enumerate(self.original_items)
            if filter_lower in item.lower()
        ]

    def _draw_filter_line(self):
        """Draw filter input line."""
        filter_display = (
            f"Filter: {self.filter_text}"
            if self.filter_text
            else "Filter: (type to filter)"
        )
        available_width = self.max_item_len - 4
        print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET} ", end="")
        print(
            f"{Colors.BOLD}{filter_display:<{available_width}}{Colors.RESET} ", end=""
        )
        print(f"{Colors.CYAN}║{Colors.RESET}")

    def _draw_menu_items(self, highlighted_idx: int = -1):
        """Draw filtered menu items."""
        if not self.filtered_items:
            # No matching items
            available_width = self.max_item_len - 4
            no_match_text = "No matching items"
            padding = (available_width - len(no_match_text)) // 2
            print(" " * self.left_margin + f"{Colors.CYAN}║{Colors.RESET} ", end="")
            print(" " * padding + f"{Colors.RED}{no_match_text}{Colors.RESET}", end="")
            print(
                " " * (available_width - len(no_match_text) - padding)
                + f" {Colors.CYAN}║{Colors.RESET}"
            )
        else:
            for i, (original_idx, item) in enumerate(self.filtered_items):
                self._draw_item(i + 1, item, i == highlighted_idx)

    def _draw_menu(self, highlighted_idx: int = -1):
        """Draw the complete menu with filter line."""
        menu_height = self._calculate_menu_height()
        top_margin = max(1, (self.term_height - menu_height) // 2)

        # Clear screen and move to top position
        self._clear_screen()
        if top_margin > 0:
            print("\n" * top_margin, end="", flush=True)

        # Draw menu structure
        self._draw_border_top()
        self._draw_title()
        self._draw_separator()
        self._draw_filter_line()
        self._draw_separator()
        self._draw_menu_items(highlighted_idx)
        self._draw_cancel_option(highlighted_idx == len(self.filtered_items))
        self._draw_border_bottom()

    def _get_prompt_text(self) -> str:
        """Get prompt text."""
        return "Use ↑/↓ to navigate, type to filter, Enter to select, Esc to clear filter: "

    def _handle_navigation_key(self, char: str) -> bool:
        """Handle navigation keys with filter support."""
        # Check for filter-specific keys first (escape to clear filter)
        if char == "\x1b":  # Escape sequence
            next1 = self._get_key()
            if next1 == "[":
                # This is an arrow key sequence, not filter clearing
                # Put back the '[' so _handle_common_navigation can process it
                # But we can't put it back. Instead, handle arrow keys here.
                next2 = self._get_key()
                if next2 == "A":  # Up arrow
                    if self.selected_idx > 0:
                        self.selected_idx -= 1
                        self._redraw_with_prompt()
                    return True
                elif next2 == "B":  # Down arrow
                    if self.selected_idx < len(self.filtered_items):
                        self.selected_idx += 1
                        self._redraw_with_prompt()
                    return True
                # Not an arrow key, ignore
                return True
            elif (
                next1 == "\x1b" or next1 is None
            ):  # Double escape or single escape - clear filter
                if self.filter_text:
                    self.filter_text = ""
                    self.filtered_items = self._filter_items()
                    self.selected_idx = 0
                    self._redraw_with_prompt()
                return True

        # No special handling, return False so other handlers can process
        return False

    def _handle_filter_input(self, char: str) -> bool:
        """
        Handle filter text input.

        Args:
            char: Character received

        Returns:
            True if filter was updated
        """
        if char == "\x7f" or char == "\x08":  # Backspace
            if self.filter_text:
                self.filter_text = self.filter_text[:-1]
                self.filtered_items = self._filter_items()
                self.selected_idx = 0
                self._redraw_with_prompt()
            return True
        elif char.isprintable():
            # Add to filter text
            self.filter_text += char
            self.filtered_items = self._filter_items()
            self.selected_idx = 0
            self._redraw_with_prompt()
            return True
        return False

    def _handle_selection(self) -> Tuple[bool, Optional[int]]:
        """Handle item selection from filtered list."""
        if self.selected_idx < len(self.filtered_items):
            # Return the original index
            original_idx = self.filtered_items[self.selected_idx][0]
            print()
            print(
                " " * self.left_margin
                + f"{Colors.GREEN}✓ Selected: {Colors.BOLD}{self.original_items[original_idx]}{Colors.RESET}"
            )
            return True, original_idx
        elif self.selected_idx == len(self.filtered_items):
            # Cancel option
            print()
            print(
                " " * self.left_margin
                + f"{Colors.YELLOW}Selection cancelled{Colors.RESET}"
            )
            return False, None
        return False, None

    def display(self) -> Tuple[bool, Optional[int]]:
        """Display menu with filtering and get user selection."""
        # Initial draw
        self._draw_menu(0)

        # Prompt for selection
        print()
        self._redraw_with_prompt()

        attempt = 0

        try:
            # Try arrow key navigation with filtering
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
                    elif self._handle_filter_input(char):
                        continue
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
                    + f"{Colors.BOLD}Enter selection [1-{len(self.original_items) + 1}]: {Colors.RESET}"
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
