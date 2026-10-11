"""
Dione AI — Interactive Terminal MCQ & Arrow-Key Selection Engine
================================================================
Cross-platform arrow-key selection menu for Windows & Unix terminals.
Allows users to navigate options with Up/Down arrows and select with Enter.
Falls back seamlessly to numeric prompt if not in an interactive terminal.
"""

import sys
import os
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def select_mcq(
    title: str,
    options: List[str],
    default_index: int = 0,
    border_style: str = "cyan",
    subtitle: str = "(Use ↑ / ↓ arrow keys to navigate, Enter to select)",
) -> int:
    """
    Render an interactive menu where user navigates options using arrow keys
    and selects using Enter.

    Returns the integer index (0-based) of the selected option.
    """
    if not options:
        return -1

    # Check if interactive TTY is available
    if not sys.stdin.isatty():
        return _fallback_numeric_select(title, options, default_index)

    # Windows interactive selector using msvcrt
    if os.name == "nt":
        return _windows_arrow_select(title, options, default_index, border_style, subtitle)
    else:
        return _unix_arrow_select(title, options, default_index, border_style, subtitle)


def _render_menu(title: str, options: List[str], selected_idx: int, border_style: str, subtitle: str) -> Panel:
    text = Text()
    text.append(f"{title}\n\n", style="bold white")

    for i, opt in enumerate(options):
        if i == selected_idx:
            text.append(f"  ❯ ", style="bold green")
            text.append(f"[{i + 1}] {opt}\n", style="bold cyan underline")
        else:
            text.append(f"    ", style="dim")
            text.append(f"[{i + 1}] {opt}\n", style="white")

    text.append(f"\n{subtitle}", style="dim italic")

    return Panel(
        text,
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _windows_arrow_select(
    title: str,
    options: List[str],
    default_index: int,
    border_style: str,
    subtitle: str,
) -> int:
    import msvcrt

    current = max(0, min(default_index, len(options) - 1))
    
    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    total_lines = len(options) + 6

    def redraw():
        panel = _render_menu(title, options, current, border_style, subtitle)
        # Move up and overwrite
        console.print(panel)

    try:
        redraw()
        while True:
            key = msvcrt.getch()

            if key in (b"\r", b"\n"):
                # Enter key pressed
                break

            elif key in (b"\x00", b"\xe0"):
                # Special key prefix on Windows
                ext = msvcrt.getch()
                if ext == b"H":  # Up arrow
                    current = (current - 1) % len(options)
                elif ext == b"P":  # Down arrow
                    current = (current + 1) % len(options)
                
                # Move cursor back up and redraw
                sys.stdout.write(f"\033[{total_lines}A\r")
                sys.stdout.flush()
                redraw()

            elif key.isdigit():
                num = int(key.decode("ascii", errors="ignore"))
                if 1 <= num <= len(options):
                    current = num - 1
                    sys.stdout.write(f"\033[{total_lines}A\r")
                    sys.stdout.flush()
                    redraw()

            elif key in (b"\x03", b"\x1b", b"q", b"Q"):  # Ctrl+C or Escape or Q
                current = -1
                break

    finally:
        # Show cursor again
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        print()

    return current


def _unix_arrow_select(
    title: str,
    options: List[str],
    default_index: int,
    border_style: str,
    subtitle: str,
) -> int:
    import termios
    import tty

    current = max(0, min(default_index, len(options) - 1))
    total_lines = len(options) + 6

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def redraw():
        panel = _render_menu(title, options, current, border_style, subtitle)
        console.print(panel)

    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        redraw()

        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                break
            elif ch == "\033":
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                if next1 == "[":
                    if next2 == "A":  # Up
                        current = (current - 1) % len(options)
                    elif next2 == "B":  # Down
                        current = (current + 1) % len(options)
                sys.stdout.write(f"\033[{total_lines}A\r")
                sys.stdout.flush()
                redraw()
            elif ch.isdigit():
                num = int(ch)
                if 1 <= num <= len(options):
                    current = num - 1
                    sys.stdout.write(f"\033[{total_lines}A\r")
                    sys.stdout.flush()
                    redraw()
            elif ch in ("q", "Q", "\x03"):
                current = -1
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        print()

    return current


def _fallback_numeric_select(title: str, options: List[str], default_index: int) -> int:
    """Fallback if not running in an interactive terminal."""
    console.print(f"\n[bold]{title}[/bold]")
    for i, opt in enumerate(options):
        console.print(f"  [{i + 1}] {opt}")
    try:
        val = input(f"Choose option (1-{len(options)}) [{default_index + 1}]: ").strip()
        if not val:
            return default_index
        idx = int(val) - 1
        if 0 <= idx < len(options):
            return idx
    except Exception:
        pass
    return default_index
