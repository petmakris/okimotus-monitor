# Okimotus Monitor – Quick Reference

Okimotus Monitor is a minimal Python helper that reads newline-delimited CSV from serial ports and lets you draw your own observables inside a curses dashboard.

## Core API
- `from monitor import get_port, out, shutdown`
- `port = get_port('/dev/ttyUSB0', baudrate=115200)` → returns a `SerialPort` with `.readline(timeout=None)` and `.close()`.
- `line = port.readline()` → yields a `SerialLine` mapping (`line[0]`, `line.get(4)`, `line.raw`, `line.timestamp`, etc.).
- `out([{"label": "RPM", "value": 3200}, ...])` → refreshes the dashboard (starts automatically on first call).
- `shutdown()` → hides the dashboard and joins its thread.

## Speedrun Workflow
```python
from monitor import get_port, out

port = get_port('/dev/ttyUSB0', baudrate=921600)
while True:
    line = port.readline(timeout=0.5)
    if not line:
        continue
    rpm = float(line.get(2, 0))
    duty = float(line.get(5, 0)) / 255 * 100
    out([
        {"label": "RPM", "value": f"{rpm:,.0f}"},
        {"label": "Duty", "value": f"{duty:.1f}%"},
    ])
```

## Display Tips
- Runs in a background thread; press `q` inside the terminal to hide it.
- When stdout is not a real TTY (CI, logging-only scripts), `out()` simply prints the observables.
- Call `shutdown()` at exit to avoid leaving the curses screen hanging.

## Serial Notes
- CSV lines must end with `\n`; fields are split on `,` and stripped.
- Baud rate defaults to 115200; override per port if your firmware differs.
- Parsing errors skip the bad line and continue with the next one.

## Troubleshooting
- **No data** – check port path, permissions (`dialout` on Linux), and firmware output format.
- **Garbled strings** – UART settings mismatch.
- **Dashboard missing** – make sure you’re running in a TTY; otherwise expect stdout logging only.
- **Need cleanup** – always `.close()` ports and call `shutdown()` after your loop.
