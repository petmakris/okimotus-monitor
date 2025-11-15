# 🚀 Okimotus Monitor Quick Start Cheatsheet


### The Big Picture

```
┌─────────────────────────────────────────────────────────┐
│  CONFIG FILE (YAML)                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│     title          ← Window title                       │
│     window         ← Size (width × height)              │
│     ports          ← Where the magic happens!           │
│     └─ /dev/tty*                                        │
│         ├─ baudrate    ← Communication speed            │
│         ├─ 0           ← First value from MCU           │
│         ├─ 1           ← Second value                   │
│         └─ 2           ← Third value...                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Minimal Example

```yaml
title: My Monitor
ports:
  /dev/ttyUSB0:
    baudrate: 115200
    0:
      label: Temperature
      type: float
      unit: °C
```

---

## 🎨 Common Use Cases

### 1️⃣ Single Sensor (Simplest)

**Your MCU sends:** `23.5\n`

```yaml
title: Temperature Monitor
ports:
  /dev/ttyUSB0:
    baudrate: 9600
    0:
      label: Temperature
      type: float
      format: "{:.1f}"
      unit: °C
      color: red
```

**Result:** Shows `23.5 °C` in red

---

### 2️⃣ Multiple Sensors

**Your MCU sends:** `23.5,1024,98.2\n`
```
      ↓     ↓    ↓
      0     1    2
```

```yaml
title: Multi-Sensor Board
ports:
  /dev/ttyUSB0:
    baudrate: 115200
    0:
      label: Temperature
      type: float
      unit: °C
    1:
      label: Light Level
      type: int
      unit: ADC
    2:
      label: Humidity
      type: float
      unit: "%"
```

---

### 3️⃣ Multiple Ports (Advanced)

**Two devices connected simultaneously:**

```yaml
title: Dual Device Monitor
ports:
  /dev/ttyUSB0:        # First device
    baudrate: 115200
    0: {label: "Motor Speed", type: int, unit: "RPM"}
    
  /dev/ttyUSB1:        # Second device
    baudrate: 9600
    0: {label: "Battery", type: float, unit: "V"}
```

---

## 📊 Field Types & Formatting

### Type Reference

| Type | Use For | Example Input | Display |
|------|---------|---------------|---------|
| `int` | Whole numbers | `1234` | `1,234` |
| `float` | Decimals | `3.14159` | `3.14` |
| `string` | Text | `OK` | `OK` |

### Format Strings Cheatsheet

```yaml
# Integers
format: "{}"         # 1234 → 1234
format: "{:,}"       # 1234567 → 1,234,567  ✨ (thousands separator)
format: "{:08d}"     # 42 → 00000042        (zero-padded)
format: "{:#x}"      # 255 → 0xff           (hexadecimal)

# Floats
format: "{:.1f}"     # 3.14159 → 3.1        ✨ (1 decimal)
format: "{:.3f}"     # 3.14159 → 3.142      ✨ (3 decimals)
format: "{:,.2f}"    # 1234.5 → 1,234.50    (thousands + decimals)
format: "{:+.1f}"    # 3.1 → +3.1           (show sign)
```

> 💡 **Most Common:** `"{:,}"` for integers, `"{:.2f}"` for floats

### Color Options

```
red  green  blue  orange  purple  pink  cyan  yellow  gray  brown  magenta  black
 🔴   🟢     🔵    🟠      🟣      🩷    🩵    🟡      ⚫    🟤     🌸       ⚫
```

Use colors to quickly identify critical values:
- **Red:** Errors, warnings, limits
- **Green:** Normal operation
- **Blue:** Time, status info

---

## 🎪 Transformations (Magic!)

Transform raw MCU values into useful units!

### Formula Flow

```
RAW VALUE  →  [Transform 1]  →  [Transform 2]  →  FINAL RESULT
  1600          ÷ 1600            × 360             360°
(counts)      (rotations)        (degrees)
```

### Common Transformations

#### Encoder → Rotations
```yaml
transformations:
  - label: Rotations
    operation: divide
    value: 1600          # counts per revolution
    format: "{:.3f}"
    unit: rev
```

#### Encoder → Degrees
```yaml
transformations:
  - label: Degrees
    operation: multiply
    value: 0.225         # 360 / 1600 = 0.225
    format: "{:.1f}"
    unit: °
```

#### ADC → Voltage
```yaml
transformations:
  - label: Voltage
    operation: multiply
    value: 0.000805      # 3.3V / 4096 steps
    format: "{:.3f}"
    unit: V
```

#### Milliseconds → Seconds
```yaml
transformations:
  - label: Seconds
    operation: divide
    value: 1000
    format: "{:.3f}"
    unit: s
```

#### Temperature Offset
```yaml
transformations:
  - label: Calibrated
    operation: subtract
    value: 2.5           # Remove offset
    format: "{:.1f}"
    unit: °C
```

### Operations Reference

| Operation | Formula | Example |
|-----------|---------|---------|
| `divide` | raw ÷ N | 1600 ÷ 1600 = 1 rev |
| `multiply` | raw × N | 1 × 360 = 360° |
| `add` | raw + N | 20 + 273 = 293 K |
| `subtract` | raw - N | 25 - 2.5 = 22.5°C |
| `power` | raw ^ N | 2 ^ 3 = 8 |

### Chaining Transformations

**You can apply multiple transforms in sequence!**

```yaml
1:
  label: Encoder
  type: int
  format: "{:,}"
  unit: counts
  transformations:
    - label: Rotations        # Step 1
      operation: divide
      value: 1600
      format: "{:.3f}"
      unit: rev
      
    - label: Degrees          # Step 2 (uses result from Step 1)
      operation: multiply
      value: 360
      format: "{:.1f}"
      unit: °
```
