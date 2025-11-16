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
- `monitor.get_port(path, baudrate=115200, **serial_kwargs)` → returns a `SerialPort` object.
- `SerialPort.readline(timeout=None)` → blocking call that yields a `SerialLine` mapping (`{index: 'value'}`) or `None` on timeout.
- `SerialPort.close()` (or use it as a context manager) → stops the background thread and closes the device.
- `monitor.out([{"label": str, "value": Any}, ...])` → updates the curses dashboard with your latest observables.
- `monitor.shutdown()` → hides the dashboard and joins its thread (called automatically at process exit, but explicit calls help during tests).

### Notes
- `SerialLine` behaves like a dictionary, has `.raw` (the original CSV text), `.timestamp`, `.line_number`, and `.values` (a copy of the parsed mapping).
- The dashboard starts the first time you call `monitor.out()`. Press `q` inside the terminal to hide it; calling `monitor.out()` later will show it again.
- When stdout is not attached to a real TTY, `monitor.out()` simply prints the observables to standard output.

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
