# Okimotus Monitor – AI Operator Guidelines

This document is printed by `monitor --ai`. It is optimized for automated agents that need to reason about Okimotus Monitor without reading the full repository.

## Mission Overview
- **Goal:** Display MCU telemetry streamed over serial ports (CSV rows) inside a Tkinter GUI with derived metrics.
- **Entry point:** `monitor.monitor:main` (installed console script `monitor`).
- **Runtime requirements:** CPython ≥ 3.7, Tk (bundled with python3-tk on Linux), `pyserial`, `pyyaml`.

## Canonical Commands
| Purpose | Command |
| --- | --- |
| List attached serial ports | `monitor --list` (add `-v` for hardware IDs) |
| Emit sample config | `monitor --create-config > monitor.yaml` |
| Launch GUI | `monitor --config monitor.yaml` |
| Print this guide | `monitor --ai` |

The CLI refuses to run without `--config`. Use absolute or relative paths; no search heuristics exist.

## Configuration Schema (YAML)

Root keys handled in `MonitorConfig` (`src/monitor/config.py`):
- `title` *(string, optional)* – window title and banner text.
- `window.width`, `window.height` *(ints)* – Tk geometry. Defaults: `800x600`.
- `ports` *(mapping)* – **required**. Each key is a serial device (`/dev/ttyUSB0`, `COM4`, etc.).

Per-port settings:
- `baudrate` *(int, default 115200)*.
- `values` *(list)* – entries describing CSV columns. Legacy dict form `index: {…}` is still supported, but prefer the list form because it makes ordering explicit.

Each value entry allows:
- `index` *(int)* – zero-based column index. Mandatory.
- `label` *(string)* – row label. Defaults to `Field {index}`.
- `type` *(string)* – `string`, `int`, or `float`; drives type conversion before formatting.
- `format` *(string)* – Python format string applied to the converted value (default `{}`).
- `unit` *(string)* – appended to the formatted value (with a space).
- `color` *(string)* – must match one of `['red','green','blue','orange','purple','brown','pink','cyan','magenta','yellow','gray','black']` to affect the UI.
- `python` *(string)* – evaluated expression or block. You may reference:
  - `value` – the type‑converted value for the current column.
  - `raw_value` – the original string.
  - `field` – dictionary describing this field.
  - `line` – `{column_index: raw_string}` for the current packet.
  - `line_values` – same as `line`, but every element is auto-converted to `int`/`float` when possible.
- `enabled` *(bool)* – include/exclude the field without removing it.

`MonitorConfig.format_value` auto-applies type conversion, Python logic (if present), formatting, and unit concatenation. If conversion fails, the UI prints `'---'` and logs a warning.

## Data Flow Recap
1. `MultiPortSerialReader` (in `serial_reader.py`) spawns a `SerialReader` per configured port.
2. Each reader:
   - opens the port with the configured `baudrate`,
   - reads arbitrarily sized chunks, splits them at `\n`, and parses comma-separated fields (`SerialDataParser`).
3. Parsed dictionaries (`{index: "value"}`) are pushed to the GUI via `SimpleMonitorGUI.on_serial_data`.
4. GUI rows are pre-created from the YAML. Every incoming `(port, index)` pair updates the rows with the same `index`.

**Important assumptions for agents:**
- Incoming lines must be newline-terminated, comma-delimited ASCII/UTF-8 strings.
- There is no flow control logic; the MCU must send at or below the host’s ability to parse.
- The GUI is not headless; you can still work with config files and CLI output, but actual rendering requires a display.

## Validation Checklist
When editing configs programmatically:
1. Ensure every port listed really exists during runtime (use `monitor --list` for discovery in scripts/tests).
2. Guarantee each `values` entry includes `index` and that indexes match the CSV layout provided by firmware docs.
3. For computed fields, prefer short expressions (e.g., `"value / 1000"`). If you need multi-line logic, set `python` to a multi-line string and assign the result to `result`.
4. After writing a config, run `python -m yaml`/`yamllint` (optional) or at least `monitor --config your.yaml --list` to catch syntax problems before connecting hardware.
5. Watch stdout: the CLI prints connection, port, and baudrate info plus warnings coming from Tk or pyserial.

## Troubleshooting Notes
- If the GUI reports “No ports configured,” it means your YAML `ports` map was empty or missing.
- If all values show `---`, confirm the firmware sends more columns than referenced indexes, and check for stray `\r` or `\0` characters.
- Exceptions in `python` snippets are caught; the system logs a warning and falls back to the unmodified value. Look at terminal output to debug.
- The project does not bundle any firmware-specific scaling constants. All conversions must be encoded inside the YAML you control.
