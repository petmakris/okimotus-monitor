"""Lightweight curses display that renders user-provided observables."""

from __future__ import annotations

import atexit
import curses
import sys
import threading
import time
from typing import Callable, Iterable, List, Mapping, Optional


def to_int(line, index: int) -> int:
    raw = line.get(index)
    if raw is None:
        return None
    try:
        return int(str(raw).strip() or 0)
    except ValueError:
        return None


def to_float(line, index: int) -> float:
    raw = line.get(index)
    if raw is None:
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        try:
            return float(int(str(raw).strip(), 10))
        except ValueError:
            return None


class _DisplayManager:
    def __init__(self, refresh_interval: float = 0.2):
        self.refresh_interval = max(0.05, refresh_interval)
        self._items: List[Mapping[str, object]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._headless = not sys.stdout.isatty()
        self._quit_callbacks: List[Callable[[], None]] = []

    def start(self):
        if self._headless:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._thread = None

    def update(self, items: Iterable[Mapping[str, object]]):
        with self._lock:
            self._items = list(items)
        if self._headless:
            self._print_headless()
        else:
            self.start()

    def register_quit_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._quit_callbacks.append(callback)

        def _remove():
            try:
                self._quit_callbacks.remove(callback)
            except ValueError:
                pass

        return _remove

    def _emit_quit(self):
        for callback in list(self._quit_callbacks):
            try:
                callback()
            except Exception:
                pass

    def _print_headless(self):
        snapshot = self._snapshot()
        lines = [f"{entry.get('label', '--')}: {entry.get('value', '')}" for entry in snapshot]
        if not lines:
            lines = ["(no data)"]
        print("\n".join(lines))

    def _snapshot(self):
        with self._lock:
            return list(self._items)

    def _run(self):
        try:
            curses.wrapper(self._loop)
        except curses.error:
            self._headless = True
            self._print_headless()

    def _loop(self, stdscr):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(True)
        stdscr.timeout(0)

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

        while not self._stop_event.is_set():
            items = self._snapshot()
            self._render(stdscr, items)
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q')):
                self._stop_event.set()
                self._emit_quit()
                break
            time.sleep(self.refresh_interval)
        self._stop_event.set()

    def _render(self, stdscr, items: List[Mapping[str, object]]):
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        max_width = max(1, width - 1)

        title = " Okimotus Monitor "
        header = f"{title:-^{max_width}}"
        stdscr.addnstr(0, 0, header[:max_width], max_width, curses.color_pair(1) | curses.A_BOLD)

        if not items:
            stdscr.addnstr(2, 0, "Waiting for monitor.out(...) updates...", max_width, curses.color_pair(3))
        else:
            row = 2
            label_width = min(32, max(16, max((len(str(e.get('label', ''))) for e in items), default=16)))
            for idx, entry in enumerate(items):
                label = str(entry.get('label', '')).replace('\x00', ' ').strip() or 'observable'
                value = entry.get('value', '')
                unit = entry.get('unit', '')
                value_str = str(value).replace('\x00', ' ')
                unit_str = f" {unit}" if unit else ""
                line = f"{label:<{label_width}} {value_str}{unit_str}".replace('\x00', ' ')
                if row >= height - 1:
                    break
                color = curses.color_pair(2 if idx % 2 == 0 else 3)
                stdscr.addnstr(row, 0, line.ljust(max_width), max_width, color)
                row += 1
        stdscr.refresh()


_display = _DisplayManager()
atexit.register(lambda: _display.stop())


def out(items: Iterable[Mapping[str, object]]):
    """Update the on-screen display with a new set of label/value pairs."""
    _display.update(items)


def shutdown():
    """Stop the terminal UI thread (useful for clean exits)."""
    _display.stop()


def on_quit(callback: Callable[[], None]) -> Callable[[], None]:
    """Register a callback that fires when the user presses 'q'."""
    return _display.register_quit_callback(callback)
