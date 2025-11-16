# Okimotus Monitor – AI Operator Guidelines

This guide is printed via `python -c "import monitor, json; print('See CHEATSHEET_AI.md')"` (no console script). It summarizes how to embed Okimotus Monitor without inspecting the entire repository.

## Mission Overview
- **Goal:** Provide a tiny API for reading newline-separated CSV from serial ports and updating a curses dashboard from your own logic loop.
- **Entry point:** import `monitor` inside your Python script; there is no standalone executable.
- **Runtime requirements:** CPython ≥ 3.7, `pyserial`, and a curses backend (`windows-curses` on Windows).

## Primary API
| Task | Call |
| --- | --- |
| Acquire a port | `port = monitor.get_port('/dev/ttyUSB0', baudrate=115200)` |
| Read next CSV line | `line = port.readline(timeout=None)` (returns `SerialLine` or `None`) |
| Show observables | `monitor.out([{"label": "RPM", "value": 3200}, ...])` |
| Hide dashboard | `monitor.shutdown()` |

`SerialLine` implements `Mapping[int, str]` and exposes `.raw`, `.timestamp`, `.line_number`, and `.values` (a copy). Treat it like a dict: `line.get(2)` for column 2, etc.

## Usage Pattern (pseudo)
```
from monitor import get_port, out

motor = get_port('/dev/ttyUSB0')
with get_port('/dev/ttyUSB1', baudrate=921600) as phase:
    while True:
        a = motor.readline(timeout=0.5)
        b = phase.readline(timeout=0.5)
        if not a or not b:
            continue
        rpm = float(a.get(2, 0))
        phase_error = float(b.get(4, 0)) / 1600 * 360
        out([
            {"label": "RPM", "value": f"{rpm:,.0f}"},
            {"label": "Phase", "value": f"{phase_error:.2f} deg"},
        ])
```

## Data Flow Recap
1. `SerialReader` (in `serial_reader.py`) spawns a background thread per port, reading bytes, splitting on `\n`, and parsing comma-separated values into `SerialLine` objects.
2. `SerialPort.readline()` pops the next `SerialLine` from an internal queue (blocking until data is available or the optional timeout expires).
3. `monitor.out()` stores the caller-provided observables, starting a curses loop (thread) on the first update.
4. The curses loop continuously redraws the latest label/value pairs; pressing `q` hides it. When stdout is not a TTY, `monitor.out()` simply prints the observables.

## Assumptions
- Incoming telemetry must be newline-terminated ASCII/UTF-8 CSV with comma separators; no quoting or escaping.
- There is no flow control or per-port throttling; the MCU must respect host throughput.
- Background threads stop when `port.close()` or `monitor.shutdown()` is called (also triggered automatically at interpreter exit).

## Validation Checklist
1. Confirm serial permissions (e.g., Linux `dialout` group) before running automation.
2. Treat `SerialPort` as a context manager or call `.close()` explicitly; otherwise background threads linger.
3. Avoid extremely small dashboard refresh intervals (<50 ms) when patching the library—`_DisplayManager` enforces a floor of 0.05 s.
4. When unit testing, you can skip `monitor.out()` or mock it; headless environments fall back to stdout printing.
5. If you need structured data beyond the dict view, use `SerialLine.raw` or `.timestamp` for diagnostics.

## Troubleshooting Notes
- **`readline()` always returns `None`** – check cabling/baud rate; ensure the MCU emits lines terminated by `\n`.
- **Garbled text** – UART mismatch or binary data; fix firmware serial settings.
- **Dashboard never appears** – script may run without a TTY (Docker, CI); `monitor.out()` will print to stdout instead of using curses.
- **"RuntimeError: SerialPort is closed"** – calling `readline()` after `.close()`; reopen with `get_port()`.
- **Permission denied** – add user to platform-specific serial group and reconnect.
