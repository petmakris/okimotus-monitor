"""Terminal UI that renders user-provided observables.

By default the dashboard is powered by the `textual` library which provides a
more discoverable and interactive interface than the previous curses-only
implementation. The legacy curses dashboard is still available as a fallback
when `textual` is not installed or when callers provide a custom renderer via
`set_renderer`.
"""

from __future__ import annotations

import atexit
import contextlib
import curses
import os
import queue
import signal
import sys
import threading
import time
from typing import Callable, Iterable, Iterator, List, Mapping, Optional

try:  # textual is optional and only used when available
    from textual.app import App, ComposeResult
    from textual.widgets import DataTable, Footer, Header, Static

    _TEXTUAL_AVAILABLE = True
except Exception:  # pragma: no cover - textual might not be installed
    App = object  # type: ignore
    ComposeResult = object  # type: ignore
    _TEXTUAL_AVAILABLE = False



DisplayItems = List[Mapping[str, object]]
Renderer = Callable[[object, DisplayItems], None]
HeadlessRenderer = Callable[[DisplayItems], None]


@contextlib.contextmanager
def _suppress_signal_errors() -> Iterator[None]:
    """
    Textual installs a number of SIG* handlers which fail when run outside the
    main thread. When we run the dashboard on a worker thread we silently skip
    these registrations to avoid crashing the whole program.
    """

    original = signal.signal

    def safe_signal(signum, handler):
        try:
            return original(signum, handler)
        except ValueError:
            return handler

    signal.signal = safe_signal  # type: ignore[assignment]
    try:
        yield
    finally:
        signal.signal = original  # type: ignore[assignment]


class _DisplayManager:
    def __init__(self, refresh_interval: float = 0.2):
        self.refresh_interval = max(0.05, refresh_interval)
        self._items: List[Mapping[str, object]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._headless = not sys.stdout.isatty()
        self._quit_callbacks: List[Callable[[], None]] = []
        self._renderer: Optional[Renderer] = None
        self._headless_renderer: Optional[HeadlessRenderer] = None
        textual_flag = (os.environ.get("OKIMOTUS_MONITOR_TEXTUAL") or "").strip().lower()
        self._textual_disabled = textual_flag in {"0", "false", "no", "off"}
        self._textual_queue: "queue.SimpleQueue" = queue.SimpleQueue()
        self._textual_app: Optional["_MonitorDashboardApp"] = None

    def start(self):
        if self._headless:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        target = self._run_textual if self._should_use_textual() else self._run_curses
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        app = self._textual_app
        if app is not None:
            try:
                app.call_from_thread(app.exit)
            except Exception:
                pass
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._thread = None

    def update(self, items: Iterable[Mapping[str, object]]):
        snapshot = list(items)
        with self._lock:
            self._items = snapshot
        if self._headless:
            self._print_headless()
            return
        if self._should_use_textual():
            self._textual_queue.put(snapshot)
        self.start()

    def set_renderer(self, renderer: Optional[Renderer]):
        with self._lock:
            self._renderer = renderer
        # Restart the UI so the change takes effect.
        self.stop()

    def set_headless_renderer(self, renderer: Optional[HeadlessRenderer]):
        with self._lock:
            self._headless_renderer = renderer

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
        renderer = self._headless_renderer
        if renderer is not None:
            try:
                renderer(snapshot)
            except Exception:
                pass
            return
        lines = [f"{entry.get('label', '--')}: {entry.get('value', '')}" for entry in snapshot]
        if not lines:
            lines = ["(no data)"]
        print("\n".join(lines))

    def _snapshot(self):
        with self._lock:
            return list(self._items)

    def _should_use_textual(self) -> bool:
        if not _TEXTUAL_AVAILABLE:
            return False
        if self._textual_disabled:
            return False
        with self._lock:
            has_custom_renderer = self._renderer is not None
        return not has_custom_renderer

    def _run_textual(self):
        if not _TEXTUAL_AVAILABLE:
            self._run_curses()
            return
        try:
            with _suppress_signal_errors():
                app = _MonitorDashboardApp(self)
                self._textual_app = app
                app.run()
        except Exception:
            self._headless = True
            self._print_headless()
        finally:
            self._textual_app = None
            self._stop_event.set()

    def _run_curses(self):
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
        renderer = None
        with self._lock:
            renderer = self._renderer
        if renderer is None:
            renderer = self._default_renderer
        try:
            renderer(stdscr, items)
        except Exception:
            if renderer is not self._default_renderer:
                self._default_renderer(stdscr, items)

    def _default_renderer(self, stdscr, items: List[Mapping[str, object]]):
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


if _TEXTUAL_AVAILABLE:

    class _MonitorDashboardApp(App):
        """Textual dashboard that renders the latest monitor rows."""

        CSS = """
        Screen {
            background: #101010;
        }

        #status {
            padding: 0 1;
            color: $text-muted;
        }

        #table {
            height: 1fr;
            margin: 1 1 0 1;
        }

        #help-panel {
            margin: 1;
            border: round #09c;
            padding: 1;
        }

        .hidden {
            display: none;
        }
        """

        BINDINGS = [
            ("q", "quit_app", "Quit"),
            ("p", "toggle_pause", "Pause/resume"),
            ("s", "toggle_sort", "Toggle sort"),
            ("?", "toggle_help", "Help"),
        ]

        def __init__(self, manager: _DisplayManager):
            super().__init__()
            self._manager = manager
            self._paused = False
            self._sort_alpha = False
            self._latest: DisplayItems = []
            self._last_update: float = 0.0
            self._status_widget: Optional[Static] = None
            self._help_widget: Optional[Static] = None
            self._table: Optional[DataTable] = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)

            status = Static("", id="status")
            self._status_widget = status
            yield status

            table = DataTable(id="table")
            table.cursor_type = "row"
            try:
                table.zebra_stripes = True
            except Exception:
                pass
            self._table = table
            yield table

            help_panel = Static(self._help_text(), id="help-panel")
            help_panel.display = False
            self._help_widget = help_panel
            yield help_panel

            yield Footer()

        def on_mount(self):
            if self._table is None:
                return
            self._table.add_columns("Label", "Value", "Unit")
            self._table.focus()
            self.set_interval(0.1, self._pull_updates)
            self._refresh_status()

        def _pull_updates(self):
            changed = False
            while True:
                try:
                    rows = self._manager._textual_queue.get_nowait()
                except queue.Empty:
                    break
                else:
                    self._latest = list(rows)
                    self._last_update = time.time()
                    changed = True
            if changed and not self._paused:
                self._render_items()
            elif changed:
                self._refresh_status()

        def _render_items(self):
            if self._table is None:
                return
            self._table.clear()
            for entry in self._sorted_items():
                label = str(entry.get("label", "")).replace("\x00", " ").strip() or "observable"
                value = str(entry.get("value", "")).replace("\x00", " ")
                unit = str(entry.get("unit", "") or "").replace("\x00", " ")
                self._table.add_row(label, value, unit)
            self._refresh_status()

        def _sorted_items(self) -> DisplayItems:
            if not self._sort_alpha:
                return list(self._latest)
            return sorted(self._latest, key=lambda row: str(row.get("label", "")).lower())

        def _refresh_status(self):
            if not self._status_widget:
                return
            parts = ["PAUSED" if self._paused else "LIVE"]
            parts.append("Sort: A→Z" if self._sort_alpha else "Sort: Monitor order")
            parts.append(f"Rows: {len(self._latest)}")
            if self._last_update:
                age = max(0.0, time.time() - self._last_update)
                parts.append(f"Updated {age:.1f}s ago")
            self._status_widget.update(" | ".join(parts))

        def action_toggle_pause(self):
            self._paused = not self._paused
            if not self._paused:
                self._render_items()
            else:
                self._refresh_status()

        def action_toggle_sort(self):
            self._sort_alpha = not self._sort_alpha
            if not self._paused:
                self._render_items()
            else:
                self._refresh_status()

        def action_toggle_help(self):
            if not self._help_widget:
                return
            self._help_widget.display = not self._help_widget.display

        def action_quit_app(self):
            self._manager._stop_event.set()
            self._manager._emit_quit()
            self.exit()

        @staticmethod
        def _help_text() -> str:
            return (
                "Controls\n"
                "--------\n"
                "q : Quit the monitor\n"
                "p : Pause/resume automatic updates\n"
                "s : Toggle between original and alphabetical ordering\n"
                "? : Toggle this help panel\n"
            )


else:

    class _MonitorDashboardApp:  # pragma: no cover - textual optional fallback
        """Placeholder used when textual isn't available."""

        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("textual is not available")


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


def set_renderer(renderer: Optional[Renderer]):
    """
    Override the curses renderer used to draw the dashboard.

    Pass None to restore the built-in renderer. The callable receives the active
    curses window and the latest items list.
    """
    _display.set_renderer(renderer)


def set_headless_renderer(renderer: Optional[HeadlessRenderer]):
    """
    Override the fallback renderer used when stdout is not a TTY.

    Pass None to restore the simple text output. The callable receives the
    latest items list.
    """
    _display.set_headless_renderer(renderer)
