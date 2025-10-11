# Monitor Tool - Complete Guide

**Real-time GUI for Microcontroller Data Visualization**

> 💡 **Quick Start:** `monitor --create-config` → edit config → `monitor -c config.json -p /dev/ttyUSB0`

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Command Reference](#command-reference)
5. [Configuration](#configuration)
6. [Data Format & MCU Code](#data-format--mcu-code)
7. [Transformations](#transformations)
8. [Format Strings](#format-strings)
9. [Complete Examples](#complete-examples)
10. [Troubleshooting](#troubleshooting)
11. [Tips & Best Practices](#tips--best-practices)

---

## Overview

**Monitor** displays real-time comma-separated data from microcontrollers via serial communication, with automatic value transformations and grid-aligned visualization.

### Features

- ✅ Real-time serial visualization
- ✅ Mathematical transformations (divide, multiply, add, subtract, power)
- ✅ Grid-aligned layout with color coding
- ✅ Change tracking with timestamps
- ✅ Visual feedback on updates
- ✅ JSON configuration system

### Use Cases

- Encoder monitoring (counts → rotations → degrees)
- Sensor readings (ADC → voltage, temperature conversions)
- Motor control (PWM → percentage, speed monitoring)
- Multi-sensor dashboards

---

## Quick Start

### 3-Step Setup

```bash
# 1. Create template
monitor --create-config

# 2. Edit monitor_config.json

# 3. Run
monitor -c monitor_config.json -p /dev/ttyUSB0
```

### Minimal Configuration

```json
{
  "title": "My Monitor",
  "fields": {
    "0": "Temperature",
    "1": "Encoder"
  }
}
```

### MCU Code

```c
Serial.println("23.5,1234");  // That's it!
```

---

## Installation

```bash
# Install Okimotus toolkit
pip install -e .

# Verify
monitor --help
```

**Dependencies:** Python 3.7+, tkinter, pyserial, pyyaml, tabulate, pygments

---

## Command Reference

### Common Commands

| Command | Description |
|---------|-------------|
| `monitor --create-config` | Generate template |
| `monitor --list-ports` | Show serial ports |
| `monitor -c FILE -p PORT` | Run with config |
| `monitor -c FILE -p PORT -b 9600` | Custom baudrate |
| `monitor -v` | Verbose mode |

### All Options

**Connection:**
- `-p PORT` - Serial port (/dev/ttyUSB0, COM3)
- `-b RATE` - Baudrate (default: 115200)
- `--ask-port` - Interactive port selection

**Configuration:**
- `-c FILE` - Config file (JSON)
- `--create-config` - Generate example

**Information:**
- `--list-ports` - List ports
- `-v` - Verbose logging
- `-h` - Help

### Examples

```bash
monitor --create-config                    # Create template
monitor --list-ports                       # See ports
monitor -c config.json -p /dev/ttyUSB0     # Basic run
monitor -c config.json -p COM3 -b 9600     # Windows
monitor -c config.json --ask-port          # Interactive
monitor -c config.json -p /dev/ttyUSB0 -v  # Debug mode
```

### GUI Controls

| Control | Function |
|---------|----------|
| **Connect/Disconnect** | Toggle connection |
| **Clear Values** | Reset to `---` |
| **Scrollbar** | Navigate fields |
| **Status Bar** | Shows stats & time |

**Visual Indicators:**
- Light blue flash = Value changed
- Light green flash = Transform updated
- `rx: now` (blue) = Data received
- `ch: 5s ago` (green) = Value changed

---

## Configuration

### File Structure

```json
{
  "title": "Monitor Title",
  "refresh_rate": 100,
  "window": {"width": 1400, "height": 500},
  "fields": {
    "0": { /* field config */ },
    "1": { /* field config */ }
  }
}
```

### Global Settings

| Property | Default | Description |
|----------|---------|-------------|
| `title` | "MCU Monitor" | Window title |
| `refresh_rate` | 100 | Update interval (ms) |
| `window.width` | 800 | Window width (px) |
| `window.height` | 600 | Window height (px) |

### Field Configuration

**Simple (string only):**
```json
"0": "Temperature"
```

**Full configuration:**
```json
"0": {
  "label": "Encoder 1",
  "type": "int",
  "format": "{:,}",
  "unit": "counts",
  "color": "green",
  "transformations": [ /* see below */ ]
}
```

### Field Options

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `label` | string | "Field N" | Display name |
| `type` | string | "string" | int, float, string |
| `format` | string | "{}" | Format string |
| `unit` | string | "" | Unit label |
| `color` | string | "black" | red, blue, green, etc. |
| `transformations` | array | [] | Calculations |

### Window Sizing

| Fields | Transforms | Size (W × H) |
|--------|-----------|--------------|
| 1-3 | 0 | 800 × 400 |
| 1-5 | 1 | 1000 × 450 |
| 1-5 | 2 | 1200 × 500 |
| 3-6 | 2-3 | 1400 × 600 |

---

## Data Format & MCU Code

### Protocol

Send **comma-separated values** with newline:
```
value0,value1,value2,...\n
```

### Position Mapping

```
"1234,5678,98.6\n"
  ↓    ↓    ↓
  0    1    2
```

Configuration maps by position:
```json
{
  "fields": {
    "0": "Encoder 1",
    "1": "Encoder 2", 
    "2": "Temperature"
  }
}
```

### MCU Examples

**Arduino:**
```cpp
void loop() {
  Serial.print(encoder1);
  Serial.print(",");
  Serial.print(encoder2);
  Serial.print(",");
  Serial.println(temp);  // \n added
  delay(100);
}
```

**STM32 HAL:**
```c
char buf[128];
snprintf(buf, sizeof(buf), "%ld,%ld,%.2f\r\n", 
         enc1, enc2, temp);
HAL_UART_Transmit(&huart1, (uint8_t*)buf, strlen(buf), 100);
```

**ESP32:**
```cpp
Serial.printf("%d,%.3f\n", adc, voltage);
```

**Python Simulator:**
```python
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200)
while True:
    ser.write(f"{1234},{5678},{98.6}\n".encode())
    time.sleep(0.1)
```

### Best Practices

✅ **Do:**
- Use commas (no spaces)
- End with `\n` or `\r\n`
- Keep consistent field count
- Update at 10-100 Hz

❌ **Don't:**
- Add extra commas
- Use spaces between values
- Send incomplete lines
- Flood at >1000 Hz

---

## Transformations

Apply mathematical operations to raw values. Each field can have multiple transformations.

### Operations

| Operation | Formula | Use Case |
|-----------|---------|----------|
| `divide` | raw / N | Encoder → Rotations |
| `multiply` | raw × N | ADC → Voltage |
| `add` | raw + N | Offset correction |
| `subtract` | raw - N | Remove bias |
| `power` | raw ^ N | Square/cube |

### Configuration

```json
{
  "label": "Transform Name",
  "operation": "divide",
  "value": 1600,
  "format": "{:.3f}",
  "unit": "rev"
}
```

### Common Formulas

#### Encoder → Rotations
```
Counts/rev = PPR × 4 (quadrature)
Operation: divide, Value: counts/rev
```

```json
{
  "label": "Rotations",
  "operation": "divide",
  "value": 1600,
  "format": "{:.3f}",
  "unit": "rev"
}
```

#### Encoder → Degrees
```
Degrees/count = 360 / counts/rev
Operation: multiply, Value: deg/count
```

```json
{
  "label": "Degrees",
  "operation": "multiply",
  "value": 0.225,
  "format": "{:.1f}",
  "unit": "°"
}
```

#### ADC → Voltage
```
V/count = Vref / resolution
Operation: multiply, Value: V/count
```

```json
{
  "label": "Voltage",
  "operation": "multiply",
  "value": 0.000805,
  "format": "{:.3f}",
  "unit": "V"
}
```

#### Time → Seconds
```json
{
  "label": "Seconds",
  "operation": "divide",
  "value": 1000,
  "format": "{:.3f}",
  "unit": "s"
}
```

#### PWM → Percentage
```json
{
  "label": "Duty Cycle",
  "operation": "divide",
  "value": 10.23,
  "format": "{:.1f}",
  "unit": "%"
}
```

### Multiple Transformations

```json
{
  "label": "Encoder",
  "type": "int",
  "format": "{:,}",
  "unit": "counts",
  "transformations": [
    {
      "label": "Rotations",
      "operation": "divide",
      "value": 1600,
      "format": "{:.3f}",
      "unit": "rev"
    },
    {
      "label": "Degrees",
      "operation": "multiply",
      "value": 0.225,
      "format": "{:.1f}",
      "unit": "°"
    }
  ]
}
```

**Display:**
```
Encoder | 3200 counts | Rotations: 2.000 rev | Degrees: 720.0°
```

---

## Format Strings

Python format strings control display formatting. Use in `"format"` fields.

### Integer Formatting

| Format | Input | Output | Description |
|--------|-------|--------|-------------|
| `"{}"` | 1234 | 1234 | Default |
| `"{:,}"` | 1234567 | 1,234,567 | Thousands |
| `"{:08d}"` | 123 | 00000123 | Zero-pad |
| `"{:6d}"` | 42 | "    42" | Right-align |
| `"{:x}"` | 255 | ff | Hexadecimal |
| `"{:#x}"` | 255 | 0xff | Hex with prefix |
| `"{:b}"` | 42 | 101010 | Binary |

**Common:**
```json
"format": "{:,}"      // Large numbers: 1,234,567
"format": "{:08d}"    // IDs: 00000123
"format": "{:#04x}"   // Registers: 0xff
```

### Float Formatting

| Format | Input | Output | Description |
|--------|-------|--------|-------------|
| `"{:.2f}"` | 3.14159 | 3.14 | 2 decimals |
| `"{:.3f}"` | 0.123456 | 0.123 | 3 decimals |
| `"{:.1f}"` | 98.76 | 98.8 | 1 decimal |
| `"{:,.2f}"` | 1234.56 | 1,234.56 | Thousands |
| `"{:+.2f}"` | 3.14 | +3.14 | Show sign |
| `"{:.1%}"` | 0.856 | 85.6% | Percentage |

**Common:**
```json
"format": "{:.1f}"    // Temperature: 23.5
"format": "{:.3f}"    // Voltage: 3.142
"format": "{:,.2f}"   // Currency: 1,234.50
"format": "{:.1%}"    // Percent: 85.6%
```

### Width & Alignment

| Format | Input | Output | Description |
|--------|-------|--------|-------------|
| `"{:10}"` | "Hi" | "Hi        " | Width 10 |
| `"{:<10}"` | "Hi" | "Hi        " | Left |
| `"{:>10}"` | "Hi" | "        Hi" | Right |
| `"{:^10}"` | "Hi" | "    Hi    " | Center |
| `"{:0>10}"` | 42 | 0000000042 | Zero-pad |

### Complete Examples

**Encoder Values:**
```json
{"format": "{:,}"}         // 123456 → "123,456"
{"format": "{:10,}"}       // 123 → "       123"
{"format": "{:08d}"}       // 42 → "00000042"
```

**Temperature:**
```json
{"format": "{:.1f}"}       // 23.456 → "23.5"
{"format": "{:.3f}"}       // 23.456789 → "23.457"
{"format": "{:+.1f}"}      // 23.5 → "+23.5"
```

**Voltage:**
```json
{"format": "{:.3f}"}       // 3.14159 → "3.142"
{"format": "{:.4f}"}       // 1.234567 → "1.2346"
```

**ADC:**
```json
{"format": "{:5d}"}        // 42 → "   42"
{"format": "{:#06x}"}      // 255 → "0x00ff"
```

**Time:**
```json
{"format": "{:.3f}"}       // 1.234 s
{"format": "{:,}"}         // 123,456 ms
{"format": "{:.2f}"}       // 1.08 min
```

**Percentages:**
```json
{"format": "{:.1f}"}       // 85.7 %
{"format": "{:.1%}"}       // 85.6% (from 0.856)
{"format": "{:.0f}"}       // 50 %
```

### Syntax Reference

```
{:[fill][align][sign][#][0][width][,][.precision][type]}
```

- `fill`: Padding character
- `align`: `<` left, `>` right, `^` center
- `sign`: `+` always, `-` negative only, ` ` space
- `#`: Prefix (0x, 0b)
- `0`: Zero-pad
- `width`: Minimum width
- `,`: Thousands separator
- `.precision`: Decimal places
- `type`: `d` int, `f` float, `e` scientific, `x` hex, `b` binary

### Common Mistakes

| Wrong | Right | Issue |
|-------|-------|-------|
| `"{:2f}"` | `"{:.2f}"` | Missing dot |
| `"{.2f}"` | `"{:.2f}"` | Missing colon |
| `"%.2f"` | `"{:.2f}"` | C-style |

---

## Complete Examples

### Example 1: Phase Tracker (Dual Encoders)

**phase_tracker.json:**
```json
{
  "title": "Phase Tracker",
  "window": {"width": 1400, "height": 500},
  "fields": {
    "0": {
      "label": "Time",
      "type": "int",
      "format": "{:,}",
      "unit": "ms",
      "transformations": [{
        "label": "Seconds",
        "operation": "divide",
        "value": 1000,
        "format": "{:.3f}",
        "unit": "s"
      }]
    },
    "1": {
      "label": "Encoder 1",
      "type": "int",
      "format": "{:,}",
      "unit": "counts",
      "color": "green",
      "transformations": [
        {
          "label": "Rotations",
          "operation": "divide",
          "value": 1600,
          "format": "{:.3f}",
          "unit": "rev"
        },
        {
          "label": "Degrees",
          "operation": "multiply",
          "value": 0.225,
          "format": "{:.1f}",
          "unit": "°"
        }
      ]
    },
    "2": {
      "label": "Encoder 2",
      "type": "int",
      "format": "{:,}",
      "unit": "counts",
      "color": "red",
      "transformations": [{
        "label": "Rotations",
        "operation": "divide",
        "value": 4096,
        "format": "{:.3f}",
        "unit": "rev"
      }]
    }
  }
}
```

**MCU Code (STM32):**
```c
uint32_t timestamp = HAL_GetTick();
int32_t enc1 = __HAL_TIM_GET_COUNTER(&htim2);
int32_t enc2 = __HAL_TIM_GET_COUNTER(&htim3);

char buf[128];
snprintf(buf, sizeof(buf), "%lu,%ld,%ld\r\n", 
         timestamp, enc1, enc2);
HAL_UART_Transmit(&huart1, (uint8_t*)buf, strlen(buf), 100);
```

**Run:**
```bash
monitor -c phase_tracker.json -p /dev/ttyACM0
```

### Example 2: Power Supply Monitor

**power_monitor.json:**
```json
{
  "title": "Power Supply Monitor",
  "window": {"width": 1200, "height": 400},
  "fields": {
    "0": {
      "label": "Voltage ADC",
      "type": "int",
      "format": "{}",
      "unit": "ADC",
      "transformations": [{
        "label": "Voltage",
        "operation": "multiply",
        "value": 0.00322,
        "format": "{:.3f}",
        "unit": "V"
      }]
    },
    "1": {
      "label": "Current ADC",
      "type": "int",
      "format": "{}",
      "unit": "ADC",
      "transformations": [{
        "label": "Current",
        "operation": "multiply",
        "value": 0.00161,
        "format": "{:.3f}",
        "unit": "A"
      }]
    },
    "2": {
      "label": "Temperature",
      "type": "float",
      "format": "{:.1f}",
      "unit": "°C",
      "color": "red"
    },
    "3": "Status"
  }
}
```

**MCU Code:**
```c
uint16_t v_adc = ADC_Read(VOLTAGE_CH);
uint16_t i_adc = ADC_Read(CURRENT_CH);
float temp = Read_Temperature();
const char* status = is_fault ? "FAULT" : "OK";

printf("%u,%u,%.1f,%s\n", v_adc, i_adc, temp, status);
```

### Example 3: IMU Monitor

**imu.json:**
```json
{
  "title": "IMU Monitor",
  "fields": {
    "0": {"label": "Accel X", "type": "float", "format": "{:.3f}", "unit": "g"},
    "1": {"label": "Accel Y", "type": "float", "format": "{:.3f}", "unit": "g"},
    "2": {"label": "Accel Z", "type": "float", "format": "{:.3f}", "unit": "g"},
    "3": {"label": "Gyro X", "type": "float", "format": "{:.1f}", "unit": "°/s"},
    "4": {"label": "Gyro Y", "type": "float", "format": "{:.1f}", "unit": "°/s"},
    "5": {"label": "Gyro Z", "type": "float", "format": "{:.1f}", "unit": "°/s"}
  }
}
```

---

## Troubleshooting

### No Ports Found

**Symptoms:** `monitor --list-ports` shows nothing

**Solutions:**
```bash
# Linux: Add to dialout group
sudo usermod -a -G dialout $USER
# Logout/login required

# Check devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Try different USB port
# Update drivers (Windows)
```

### Values Not Updating

**Symptoms:** GUI shows `---` or frozen values

**Solutions:**
```bash
# Test MCU output
cat /dev/ttyUSB0
# Should see: 1234,5678,98.6

# Check baudrate matches
# Verify cable quality
# Check field positions in config
```

### Data Parsing Errors

**Symptoms:** Some fields show `---`, others work

**Solutions:**
- Check data type matches (int/float)
- Verify position numbers
- Look for extra/missing commas
- Check for special characters

### Wrong Transformation Values

**Symptoms:** Calculated values incorrect

**Solutions:**
- Verify formula and value
- Check operation type
- Ensure raw value is numeric
- Double-check math

### Permission Denied (Linux)

```bash
# Add to dialout group
sudo usermod -a -G dialout $USER

# Or run with sudo (not recommended)
sudo monitor -c config.json -p /dev/ttyUSB0
```

### GUI Performance Issues

**Solutions:**
- Reduce MCU update rate
- Increase `refresh_rate` in config
- Reduce transformations
- Use simpler format strings

### Configuration Errors

**Symptoms:** `Failed to load configuration`

**Solutions:**
- Validate JSON syntax (online validator)
- Use double quotes (`"`)
- No trailing commas
- Check file path

### Debug Mode

```bash
monitor -c config.json -p /dev/ttyUSB0 -v
```

Shows:
- Connection details
- Data parsing
- Transformation calculations
- Error stack traces

---

## Tips & Best Practices

### 1. Start Simple

Begin basic, add complexity:
```json
{
  "title": "Test",
  "fields": {
    "0": "Value 1",
    "1": "Value 2"
  }
}
```

### 2. Test Data Stream First

```bash
cat /dev/ttyUSB0
# Should show: 1234,5678,98.6
```

### 3. Document Your Calculations

Keep notes (separate from JSON):
```
Encoder 1: 400 PPR × 4 = 1600 counts/rev
Degrees: 360 / 1600 = 0.225 °/count
```

### 4. Use Meaningful Colors

- Red: Warnings, critical
- Green: Normal, encoders
- Blue: Time, status

### 5. Backup Configs

```
configs/
├── encoder_test.json
├── production.json
├── calibration.json
└── debug.json
```

### 6. Format String Tips

- Start with `"{}"`, add formatting later
- Test in Python: `print(f"{123.456:.2f}")`
- Common: `"{:width.precision type}"`
- `.2f` for money, `.3f` for measurements

### 7. Transformation Calculations

**Encoder to rotations:**
```
counts/rev = PPR × quadrature_factor
```

**ADC to voltage:**
```
V/count = Vref / resolution
```

**Counts to degrees:**
```
deg/count = 360 / counts_per_rev
```

### 8. Update Rates

- **10-50 Hz:** Most applications
- **100 Hz:** Fast control loops
- **<10 Hz:** Slow sensors (temperature)
- **>200 Hz:** GUI struggles

### 9. Window Sizing

Adjust based on content:
- More fields → taller
- More transforms → wider

### 10. Common Patterns

**Simple monitoring:**
```json
{"label": "Temp", "type": "float", "format": "{:.1f}", "unit": "°C"}
```

**With transformation:**
```json
{
  "label": "ADC",
  "type": "int",
  "transformations": [{
    "label": "Voltage",
    "operation": "multiply",
    "value": 0.000805,
    "format": "{:.3f}",
    "unit": "V"
  }]
}
```

---

## Quick Reference Card

### Essential Commands
```bash
monitor --create-config              # Template
monitor --list-ports                 # Ports
monitor -c config.json -p PORT       # Run
```

### Data Format
```
value0,value1,value2\n
```

### Operations
- divide, multiply, add, subtract, power

### Format Patterns
```
"{:,}"        Thousands
"{:.2f}"      2 decimals
"{:08d}"      Zero-pad
"{:.1%}"      Percentage
```

---

## Support

**Documentation:** This file!

**Debug:** `monitor -v`

**Test stream:** `cat /dev/ttyUSB0`

**Repo:** [okimotus](https://github.com/petmakris/okimotus)

---

**End of Guide** - Happy Monitoring! 🎉
