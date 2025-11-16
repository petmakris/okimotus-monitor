# Okimotus Monitor

Okimotus Monitor is a desktop tool for viewing MCU telemetry in real time. It opens one or more serial ports, parses newline-separated comma values, and renders them in a Tkinter GUI with optional conversions performed via inline Python snippets. The application helps quickly validate firmware output, compare raw vs. scaled data, and keep a clear log of when values last changed.

## Features
- **Multi-port streaming:** attach any number of serial ports, each with its own baudrate.
- **Config-driven fields:** define every displayed row in YAML, including label, units, and formatting.
- **Inline math:** derive engineering units with short Python expressions (`python:` blocks in config).
- **Visibility tools:** toggle between converted and raw values, clear the table, and monitor last-received/change times.
- **Portable CLI:** bundled as `monitor` console script with helpers for listing ports and generating sample configs.

## Requirements
- Python 3.7 or newer.
- Tkinter (bundled with most Python installs; on Linux install `python3-tk`).
- Serial access via [pyserial](https://pyserial.readthedocs.io/) and YAML parsing via [PyYAML](https://pyyaml.org/).

## Installation
```bash
git clone https://github.com/okimotus/okimotus-monitor.git
cd okimotus-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

The editable install registers the `monitor` entrypoint that lives in `src/monitor/monitor.py`.

## Quick Start
1. **Find available ports**
   ```bash
   monitor --list
   ```
   Add `-v` to print hardware IDs, which helps differentiate similar adapters.

2. **Generate a starter config**
   ```bash
   monitor --create-config > monitor.yaml
   ```

3. **Edit `monitor.yaml`**
   - Choose a descriptive `title`.
   - Add each serial port under `ports`.
   - For every CSV column, add a `values` entry describing its label, type, and formatting.

4. **Launch the GUI**
   ```bash
   monitor --config monitor.yaml
   ```
   Connect/disconnect using the button inside the window; use **Clear Values** while debugging firmware.

## Configuration Reference
The application only reads a single YAML file per run. The format is parsed by `MonitorConfig` (`src/monitor/config.py`) and supports the following keys:

```yaml
title: Phase Tracker            # Optional window title (default: "MCU Monitor")
window:
  width: 1200                   # Optional, default 800
  height: 700                   # Optional, default 600
ports:
  /dev/ttyUSB0:                 # Serial port path or COM number
    baudrate: 921600            # Default 115200 if omitted
    values:                     # Required: describes each CSV column
      - label: Timestamp        # Row label used in GUI
        index: 0                # Zero-based CSV column index
        type: int               # string, int, or float (defaults to string)
        format: "{:.3f}"        # Python format string applied to converted value
        unit: s                 # Optional suffix appended with a space
        color: blue             # One of the color tags defined in GUI
        python: value / 1000    # Inline Python (expression or multi-line block)
      - label: Phase Error (deg)
        index: 4
        type: float
        format: "{:.1f}"
        python: "(value / 1600) * 360"
        unit: deg
  /dev/ttyUSB1:
    baudrate: 115200
    values:
      - label: Motor Temp
        index: 2
        type: float
        format: "{:.1f}"
        unit: °C
        enabled: true           # Toggle visibility without removing the row
```

### Python Conversion Blocks
- Expressions (`"value / 1000"`) are evaluated with access to `value`, `raw_value`, `field`, `line`, and `line_values`.
- For multi-line logic, use YAML’s `|` block syntax and assign `result`:
  ```yaml
  python: |
    volts = line_values.get(3, 0)
    amps = value / 1000
    result = volts * amps
  ```
- Import access is restricted to basic math helpers (`abs`, `min`, `max`, `round`, `sum`, `pow`, and the `math` module).

### Legacy Format Support
If you encounter historical configs that use a mapping of `index: { ... }` rather than a `values` list, they will still load. Newly generated configs always use the list structure for clarity.

## Serial Data Expectations
- Every line must end with `\n`.
- Fields are separated by `,` (no quoting rules). Whitespace is stripped.
- Missing or short lines are skipped silently; parsing errors are logged.

## GUI Walkthrough
- **Rows:** Pre-created according to the YAML; disconnected rows show `---`.
- **Columns:** `Port`, `Field`, `Raw Value` (optional via checkbox), `Value`, and `Status`.
- **Status:** Displays two timestamps—`rx` for last receive time, `ch` for last change.
- **Status bar:** Shows consolidated connection state plus aggregated line counters for all ports.
- **Dialogs:** Serial errors and failures to set up ports produce Tk popups and console logs.

## Development Notes
- `setup.py` declares the `monitor` entrypoint and dependencies (`pyserial`, `pyyaml`). Install optional extras with `pip install -e .[dev]` to grab pytest, coverage, PyInstaller, and cx_Freeze.
- The GUI lives in `src/monitor/gui.py`; serial backends are in `src/monitor/serial_reader.py`.
- Run unit tests (if added) via `pytest`.

## Troubleshooting
- **"Configuration file is required"** – the CLI was invoked without `--config`.
- **GUI shows “No ports configured”** – your YAML `ports` map was empty or mis-indented.
- **Rows never update** – confirm the MCU is emitting newline-terminated CSV and that every `index` exists in the stream.
- **Incorrect math** – check for typos inside the `python` snippet; exceptions are logged to stdout and fall back to raw values.
- **Serial permissions on Linux** – ensure your user belongs to the `dialout` (or equivalent) group.
