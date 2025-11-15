# 🤖 Okimotus Monitor Configuration Guide for AI Agents

Purpose: help language-model copilots generate or edit monitor configuration files (YAML/JSON) with zero guesswork. Focus on deterministic schemas, defaults, and validation rules so responses stay executable.

---

## 1. Canonical Schema (YAML shown)

```yaml
title: <string, optional, default "MCU Monitor">
window:
  width: <int, default 800>
  height: <int, default 600>
ports:
  <port_path>:
    baudrate: <int, default 115200>
    <position_index>:
      label: <string, default "Field <index>">
      type: <int|float|string, default string>
      format: <python format string, default "{}">
      unit: <string, optional>
      color: <named color, default "black">
      transformations:
        - label: <string>
          operation: <multiply|divide|add|subtract|power>
          value: <numeric>
          format: <python format string, default "{:.3f}">
          unit: <string, optional>
      # experimental metadata accepted but unused: min, max
```

Notes for agents:
- `ports` is a mapping; keys must match actual serial device names (e.g., `/dev/ttyUSB0`).
- Field keys are zero-based indices correlating to the comma-separated values emitted by the MCU.
- YAML allows bare integers for field keys; JSON requires them as strings (`"0"`, `"1"`, ...). The parser converts automatically.
- Empty fields or strings containing `\x00` resolve to `'---'` placeholders; avoid generating such values.

---

## 2. Field Attributes (How the GUI uses them)

| Attribute | Required | Effect |
|-----------|----------|--------|
| `label` | ✔️ | Tree column header for the field row. |
| `type` | ✔️ (defaults to `string`) | Casts raw MCU text to `int`, `float`, or leaves string. Non‐numeric types skip transformations. |
| `format` | optional | Python `str.format` string applied after type conversion. Examples: `"{:,}"`, `"{:.2f}"`, `"{:08d}"`. |
| `unit` | optional | Appended with a leading space (`"3.14 rad"`). |
| `color` | optional | Tree label color. Allowed names: `red, green, blue, orange, purple, pink, cyan, yellow, gray, brown, magenta, black`. |
| `transformations` | optional list | Enables the Transform dropdown. Each entry creates both a selectable step and participates in the “All Transforms (Final)” pipeline. |
| `min`/`max` | optional | Currently parsed but unused in UI; keep only if future validation is desired. |

Formatting behaviour:
- Integers/floats support signs, padding, and thousands separators because `str.format` is used verbatim.
- Strings bypass formatting and units. They appear exactly as received.

---

## 3. Transformation Semantics

Applied only when `type` is `int` or `float`.

| Operation | Formula | Typical Use |
|-----------|---------|-------------|
| `multiply` | `result = value * transform_value` | convert revolutions to degrees |
| `divide` | `result = value / transform_value` (safe guard against divide-by-zero) | counts → volts/time |
| `add` | `result = value + transform_value` | offsets |
| `subtract` | `result = value - transform_value` | invert offset |
| `power` | `result = value ** transform_value` | exponent conversions |

- Steps execute sequentially; the GUI’s “All Transforms (Final)” selection returns the formatted output of the last step.
- Each step may define its own `label`, `format`, and `unit`. If omitted, defaults `label=Transform N`, `format="{:.3f}"`, `unit=""`.
- `get_transformation_steps` exposes intermediate results to the Transform dropdown, so descriptive labels matter.

---

## 4. Agent Workflow Checklist

1. **Collect constraints** from the user: port path(s), baudrate, data order, engineering units, visualization hints.
2. **Derive field indices** from the MCU payload order (0-based). If the user shares a CSV string, map each comma-separated segment to an index.
3. **Decide types and formats**:
   - `int` for counts, IDs, booleans (use `{}` or `{:d}`).
   - `float` for fractional data (`"{:.2f}"`, `"{:,.3f}"`).
   - `string` for textual statuses; skip `format`.
4. **Add units and colors** to improve readability. Use colors sparingly; align with semantics (e.g., red for warnings).
5. **Encode transformations** when the user needs derived units. Work left-to-right exactly as described (never reorder).
6. **Validate defaults**:
   - Always set `baudrate` when user mentions it; otherwise leave default (`115200`).
   - Make sure every configured index has a `label`.
   - Omit columns entirely if the user wants fewer values; gaps are allowed (e.g., indices `0` and `2` defined while `1` is absent).
7. **Respond with fenced YAML** (unless the user explicitly wants JSON) and include a brief explanation for humans.

---

## 5. Templates for Responses

### Introduce a fresh config
```yaml
title: <title from user or default>
window:
  width: 1200
  height: 500
ports:
  /dev/ttyUSB0:
    baudrate: 115200
    0:
      label: <Field 0>
      type: <int|float|string>
      format: "{:,}"
      unit: <unit>
      color: <color>
      transformations:
        - label: <Short label>
          operation: divide
          value: 1000
          format: "{:.3f}"
          unit: s
```

### Append/modify a single field
```yaml
  /dev/ttyUSB0:
    <existing entries>...
    3:
      label: Battery Voltage
      type: float
      format: "{:.2f}"
      unit: V
      color: green
      transformations:
        - label: Percentage
          operation: multiply
          value: 20
          format: "{:.0f}"
          unit: "%"
```

### Multiple ports (share baudrate or not)
```yaml
ports:
  /dev/ttyUSB0:
    baudrate: 230400
    0: {...}
  /dev/ttyUSB1:
    baudrate: 57600
    0: {...}
    1: {...}
```

---

## 6. Troubleshooting Tips for Agents

- If the user references “column order” or “position”, confirm the 0-based index explicitly before editing.
- When adding transforms, reflect the exact units/labels the user states; these drive drop-down text.
- Unsupported requests (e.g., new operations) should be acknowledged; stick to the five allowed operations unless the codebase evolves.
- Encourage reusable snippets by pointing to `sample.yaml` if the user needs a starter file.
- Mention when optional values are inferred (e.g., “Using default baudrate 115200 because none specified”).

Armed with this cheat sheet, an AI agent can confidently translate natural-language monitoring requirements into valid Okimotus Monitor configs. Happy automating!
