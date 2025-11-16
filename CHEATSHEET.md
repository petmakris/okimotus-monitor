# Okimotus Monitor – Quick Reference

Okimotus Monitor is a Tkinter GUI that subscribes to one or more MCU serial ports, parses comma‑separated values (CSV), and renders them as labeled rows with optional engineering conversions.

## Common CLI Tasks
- `monitor --list` &nbsp;→ show available serial ports (add `-v` to also print hardware IDs).
- `monitor --create-config > monitor.yaml` &nbsp;→ print an example YAML configuration.
- `monitor --config monitor.yaml` &nbsp;→ launch the GUI using the provided config (required).
- `monitor --ai` &nbsp;→ output the AI cheatsheet (same file you are reading on automation agents).
- `monitor -v --config monitor.yaml` &nbsp;→ enable verbose logging for troubleshooting.

## Speedrun Workflow
1. `monitor --list` to determine which `/dev/tty…` or `COM…` ports are attached.
2. Copy the default config (`monitor --create-config > monitor.yaml`) and edit it.
3. For each port, set its `baudrate` and add the fields you expect to receive in CSV order.
4. Launch `monitor --config monitor.yaml`. Use the **Disconnect** button to stop streaming.
5. Toggle **Show Raw Value** if you need to compare converted vs. unparsed values; use **Clear Values** while debugging firmware.

## Configuration Cheatsheet
The configuration file is YAML and must contain a `ports` map. Every port in that map may define:

| Key | Description |
| --- | --- |
| `baudrate` | Serial speed for that port (default `115200`). |
| `values` | Ordered list describing each CSV column (see below). |

Each entry inside `values` accepts:

| Field | Purpose |
| --- | --- |
| `label` | Friendly name displayed in the table header. |
| `index` | Zero-based CSV column index for this value (required). |
| `type` | `string`, `int`, or `float` – controls parsing. |
| `format` | Python format string applied after parsing (default `{}`). |
| `unit` | Optional suffix such as `ms`, `°`, or `rpm`. |
| `color` | Row color tag (one of: red, green, blue, orange, purple, brown, pink, cyan, magenta, yellow, gray, black). |
| `python` | Inline Python expression executed with `value`, `raw_value`, `field`, `line`, `line_values`. |
| `enabled` | `true`/`false` toggle; disabled fields stay hidden. |

> `line` exposes the raw values for the current packet indexed by column, while `line_values` exposes the same values auto-converted to numbers when possible. Use those dictionaries to compute combined metrics.

### Minimal Example
```yaml
title: Bench Monitor
window:
  width: 1200
  height: 700
ports:
  /dev/ttyUSB0:
    baudrate: 921600
    values:
      - label: Timestamp
        index: 0
        type: int
        format: "{:.3f}"
        unit: s
        python: value / 1000
      - label: Motor Temp
        index: 4
        type: float
        format: "{:.1f}"
        unit: °C
      - label: Duty Cycle
        index: 6
        type: float
        format: "{:.1%}"
        python: value / 100
  /dev/ttyUSB1:
    baudrate: 115200
    values:
      - label: Encoder Position
        index: 1
        type: int
        python: "(value / 1600) * 360"
        format: "{:.1f}"
        unit: deg
```

## GUI Reminders
- Rows are statically created from the YAML – if a CSV column stops reporting you still see the row with `---`.
- Status column shows `rx:` and `ch:` timestamps (“received” and “changed”).
- The application aggregates statistics for all configured ports in the status bar and prints serial errors via popups plus stdout.

## Troubleshooting
- Missing file errors usually mean the YAML path is wrong. The tool does not auto-search.
- If no rows update, ensure the firmware emits newline-terminated CSV and the indices match.
- Use `enabled: false` to hide experimental fields without deleting their conversion logic.
- Very large Python expressions are possible but keep them pure; exceptions are logged and the raw value is left untouched.
