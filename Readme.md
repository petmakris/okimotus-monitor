# Okimotus Monitor

Okimotus Monitor is a lightweight Python helper for streaming MCU telemetry from one or more serial ports and rendering your own computed observables in a shared terminal UI. You stay in full control of the parsing/math; the library simply handles robust serial reads and a curses-based dashboard you can update from any loop.

## Features
- **Tiny API surface:** `port = monitor.get_port('/dev/ttyUSB0')` and `port.readline()` return parsed CSV lines as dictionaries.
- **Bring-your-own logic:** compute any values you need and push them to the dashboard via `monitor.out([...])`.
- **Multi-port ready:** open as many ports as you like; each reader runs in its own background thread and exposes blocking `readline()` calls.
- **Zero config:** defaults to 115200 baud, newline-delimited CSV, and a minimal TUI (falls back to simple stdout when curses is unavailable).

## Installation
```bash
git clone https://github.com/okimotus/okimotus-monitor.git
cd okimotus-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Quick Start
Use `monitor.run(...)` when you want the library to own the life-cycle (Ctrl+C,
pressing `q`, shutting down ports, etc.). Provide a `render()` function that
receives the latest line from every configured device and returns the rows the
dashboard should display:

```python
from monitor import run

def render(lines):
    encoder = lines.get("encoder")
    command = lines.get("command")

    rows = [
        {"label": "Motor Revs (Encoder)", "value": "--"},
        {"label": "Radial Degrees (Encoder)", "value": "--"},
        {"label": "Units", "value": "--"},
        {"label": "Radial Degrees (Cmd)", "value": "--"},
    ]

    if encoder:
        counts = float(encoder.get(1, 0))
        rows[0]["value"] = f"{counts / 1600.0:.3f} rev"
        rows[1]["value"] = f"{(counts / 1600.0) * 10.0:.3f} deg"

    if command:
        units = int(command.get(1, 0))
        scale = float(command.get(5, 10.0) or 10.0)
        rows[2]["value"] = {1: "mm", 2: "in", 3: "deg"}.get(units, "--")
        rows[3]["value"] = f"{(float(command.get(2, 0)) / 1600.0) * scale:.3f} deg"

    return rows


run(
    {
        "encoder": {"device": "/dev/ttyUSB0", "baudrate": 115200},
        "command": ("/dev/ttyUSB1", 115200),
    },
    render=render,
    poll_interval=0.5,
)
```

If you prefer to handle the control flow yourself you still can:

```python
from monitor import get_port, out, shutdown

port1 = get_port('/dev/ttyUSB0')          # defaults to 115200 baud
device = get_port('/dev/ttyUSB1', baudrate=921600)

try:
    while True:
        line1 = port1.readline(timeout=0.5)
        line2 = device.readline(timeout=0.5)
        if not line1 or not line2:
            continue

        rpm = float(line1.get(2, 0))
        phase_error = float(line2.get(4, 0)) / 1600 * 360

        out([
            {"label": "Motor RPM", "value": f"{rpm:,.0f}"},
            {"label": "Phase Error", "value": f"{phase_error:.2f} deg"},
        ])
finally:
    shutdown()   # stop the TUI thread (optional but recommended)
    port1.close()
    device.close()
```

## API Highlights
- `monitor.run(port_configs, render, poll_interval=0.05)` → opens every configured device, feeds lines into your `render()` callback, updates the UI, and shuts everything down on exit.
- `monitor.get_port(path, baudrate=115200, **serial_kwargs)` → returns a `SerialPort` object.
- `SerialPort.readline(timeout=None)` → blocking call that yields a `SerialLine` mapping (`{index: 'value'}`) or `None` on timeout.
- `SerialPort.close()` (or use it as a context manager) → stops the background thread and closes the device.
- `monitor.out([{"label": str, "value": Any}, ...])` → updates the curses dashboard with your latest observables.
- `monitor.shutdown()` → hides the dashboard and joins its thread (called automatically at process exit, but explicit calls help during tests).

### Notes
- `SerialLine` behaves like a dictionary, has `.raw` (the original CSV text), `.timestamp`, `.line_number`, and `.values` (a copy of the parsed mapping).
- The dashboard starts the first time you call `monitor.out()`. Press `q` inside the terminal to hide it; calling `monitor.out()` later will show it again.
- When stdout is not attached to a real TTY, `monitor.out()` simply prints the observables to standard output.
- `monitor.run(...)` hands a dictionary of the latest `SerialLine` objects (or `None` if a port has not produced data yet) to your `render()` callback; return rows or raise `StopIteration` when you want to quit.

## Customizing the Dashboard
The default dashboard renders a single two-column list, but you can take over the
entire curses surface if you need separators, multi-column layouts, or custom
styling. Register a renderer once and every subsequent `monitor.out(...)` call
will feed data into your function:

```python
import curses
from itertools import zip_longest

from collections import OrderedDict
from monitor import run, set_renderer


def dashboard_renderer(stdscr, items):
    def format_entry(entry: dict) -> str:
        label = str(entry.get("label", "")).strip()
        value = str(entry.get("value", "")).strip()
        unit = entry.get("unit")
        suffix = f" {unit}" if unit else ""
        return f"{label:<18} {value}{suffix}"

    stdscr.erase()
    height, width = stdscr.getmaxyx()

    title = " Okimotus Monitor "
    stdscr.addnstr(0, 0, f"{title:=^{width-1}}", width-1, curses.color_pair(1) | curses.A_BOLD)

    row = 2
    col_gap = 2
    col_width = max(20, (width - col_gap) // 2)

    sections: "OrderedDict[str, list]" = OrderedDict()
    for entry in items:
        section = str(entry.get("section") or "Observables")
        sections.setdefault(section, []).append(entry)

    for section, section_items in sections.items():
        if row >= height - 1:
            break
        stdscr.addnstr(row, 0, f"[ {section} ]", width-1, curses.color_pair(3) | curses.A_BOLD)
        row += 1
        stdscr.hline(row, 0, curses.ACS_HLINE, width-1)
        row += 1

        for left, right in zip_longest(section_items[::2], section_items[1::2]):
            if row >= height - 1:
                break
            if left:
                stdscr.addnstr(row, 0, format_entry(left)[:col_width], col_width, curses.color_pair(2))
            if right:
                stdscr.addnstr(row, col_width + col_gap, format_entry(right)[:col_width], col_width, curses.color_pair(2))
            row += 1
        row += 1

    stdscr.refresh()


set_renderer(dashboard_renderer)
run({...}, render=render)  # your existing render() function
```

Pass `None` to `set_renderer(None)` to restore the built-in layout. When stdout
is not attached to a TTY you can also override the headless output via
`monitor.set_headless_renderer(...)`.

## Serial Data Expectations
- Each MCU line must end with `\n` and use `,` to separate values (no quoting rules, whitespace is stripped automatically).
- Missing fields are ignored; parsing failures skip the faulty line without crashing your script.
- Pick a baud rate that matches your firmware—mismatches manifest as garbled CSV strings.

## Troubleshooting
- **"No data"** – ensure the firmware is transmitting newline-delimited CSV and that USB permissions (e.g., Linux `dialout` group) allow access.
- **Garbled characters** – baud mismatch or binary framing. Double-check firmware UART settings.
- **Terminal UI does not appear** – verify you are running inside a true terminal; otherwise `monitor.out()` will fall back to simple stdout logging.
- **Need to cleanly exit** – call `monitor.shutdown()` and `.close()` ports when your loop finishes to stop background threads.

## Development Notes
- Serial helpers live in `src/monitor/serial_reader.py`; the high-level API is in `src/monitor/sdk.py` and the TUI in `src/monitor/tui.py`.
- Run tests (if added) via `pytest`. The project intentionally has no console entrypoint; import the package inside your own scripts.
