# List Ports Command Added

## Summary

Added a new `--list` command-line option to easily view available serial ports without starting the GUI.

## Usage

### Basic Usage
```bash
monitor --list
```

**Output:**
```
Available serial ports:
------------------------------------------------------------
  /dev/ttyACM0         STM32 STLink - ST-Link VCP Ctrl
  /dev/ttyUSB0         FT232R USB UART - FT232R USB UART
  /dev/ttyUSB1         FT232R USB UART - FT232R USB UART
------------------------------------------------------------
Found 3 port(s)
```

### Verbose Mode
```bash
monitor --list --verbose
```

**Output with Hardware IDs:**
```
Available serial ports:
------------------------------------------------------------
  /dev/ttyACM0         STM32 STLink - ST-Link VCP Ctrl
    Hardware ID: USB VID:PID=0483:3752 SER=066FFF485753667187152419 LOCATION=3-4.1.2:1.1
  /dev/ttyUSB0         FT232R USB UART - FT232R USB UART
    Hardware ID: USB VID:PID=0403:6001 SER=A50285BI LOCATION=3-4.1.1
  /dev/ttyUSB1         FT232R USB UART - FT232R USB UART
    Hardware ID: USB VID:PID=0403:6001 SER=A50285BI LOCATION=3-4.1.3
------------------------------------------------------------
Found 3 port(s)
```

## Benefits

1. **Quick Port Discovery** - See available ports without opening config files
2. **No GUI Required** - Works in headless/SSH environments
3. **Helpful for Setup** - Identify correct ports before creating config
4. **Verbose Details** - Get hardware IDs with `-v` flag for troubleshooting
5. **Clean Output** - Filtered list (excludes generic/meaningless ports)

## Common Workflow

```bash
# 1. List available ports
monitor --list

# 2. Create config template
monitor --create-config

# 3. Edit config with the correct port names
nano monitor_config.json

# 4. Run the monitor
monitor -c monitor_config.json
```

## Implementation Details

### Files Modified
- ✅ `src/monitor/monitor.py` - Added `--list` argument and handler

### Code Changes
- Imported `list_serial_ports` from `serial_reader` module
- Added `--list` argument to argument parser
- Added handler that displays ports in formatted table
- Exits after displaying ports (doesn't start GUI)
- Supports verbose mode for detailed hardware information

### Port Filtering
The list automatically filters out:
- Ports with meaningless descriptions (n/a, unknown)
- Generic entries that aren't useful

Falls back to showing all ports if filtering results in empty list.

## Help Integration

The new option appears in help:

```bash
monitor --help
```

Shows:
```
Information:
  --list                List available serial ports and exit
  -v, --verbose         Enable verbose logging
```

And in examples:
```
Examples:
  monitor --create-config               # Create example configuration file
  monitor --list                        # List available serial ports
  monitor -c config.json                # Use config file
```
