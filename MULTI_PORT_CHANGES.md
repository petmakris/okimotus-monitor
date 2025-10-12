# Multi-Port Support - Change Summary

## Overview

The application has been successfully refactored to support monitoring multiple serial ports simultaneously. This is a significant architectural change that affects the configuration format, internal logic, and user interface.

## Key Changes

### 1. Configuration Format (Breaking Change)

**Old Format (Single Port):**
```json
{
  "title": "Phase Tracker",
  "fields": {
    "0": {
      "label": "Time",
      "type": "int",
      ...
    }
  }
}
```

**New Format (Multi-Port):**
```json
{
  "title": "Phase Tracker",
  "ports": {
    "/dev/ttyUSB0": {
      "0": {
        "label": "Time",
        "type": "int",
        ...
      }
    },
    "/dev/ttyUSB1": {
      "0": {
        "label": "Another Field",
        "type": "float",
        ...
      }
    }
  }
}
```

### 2. Code Changes

#### `src/monitor/config.py`
- Changed `self.fields` to `self.ports` (dict of port -> fields mapping)
- Updated all methods to accept `port` parameter:
  - `get_field_config(port, position)`
  - `get_all_positions(port)`
  - `format_value(port, position, raw_value)`
  - `apply_all_transformations(port, position, raw_value)`
  - `get_transformation_steps(port, position, raw_value)`
- Added `get_ports()` method to list all configured ports
- Updated `create_example_config()` to use new format

#### `src/monitor/serial_reader.py`
- Added new `MultiPortSerialReader` class that:
  - Manages multiple `SerialReader` instances (one per port)
  - Aggregates callbacks from all ports
  - Provides unified interface for start/stop/stats
  - Callbacks now include port name: `callback(port, data)` and `callback(port, error)`

#### `src/monitor/gui.py`
- Updated to use `MultiPortSerialReader` instead of single `SerialReader`
- Removed port selection UI:
  - Removed "Select Port" button
  - Removed port selection dialog (`select_port()` method)
- Updated data structures to track port + position:
  - `self.tree_items: Dict[tuple, str]` - now uses `(port, position)` as key
  - `self.field_data: Dict[tuple, Dict]` - now uses `(port, position)` as key
  - `self.transform_vars: Dict[tuple, tk.StringVar]` - now uses `(port, position)` as key
- Added "Port" column to the data table
- Updated callbacks to handle port parameter
- Modified statistics aggregation to combine stats from all ports
- Auto-connects to all configured ports on startup

#### `src/monitor/monitor.py`
- Removed command-line arguments:
  - `--port` / `-p`
  - `--ask-port`
  - `--list-ports`
- Removed `ask_for_port()` function
- Updated GUI initialization to not require port parameter
- Auto-connects to all configured ports after GUI initialization
- Updated help text and examples to reflect new configuration format

### 3. User Interface Changes

**Before:**
- Single port connection
- "Select Port" button to choose port from dropdown
- Port specified via command line or GUI

**After:**
- Multiple simultaneous port connections
- All ports configured in JSON file
- Auto-connect to all configured ports on startup
- "Port" column in data table shows which port each field comes from
- "Connect/Disconnect" button controls all ports together

### 4. Migration Guide

To migrate existing configurations:

1. Wrap your `fields` section inside a `ports` object
2. Use the port name (e.g., `/dev/ttyUSB0`) as the key
3. Move the fields under that port key

**Example:**
```bash
# Old config:
{
  "fields": {
    "0": {...}
  }
}

# New config:
{
  "ports": {
    "/dev/ttyUSB0": {
      "0": {...}
    }
  }
}
```

### 5. Example Multi-Port Configuration

```json
{
  "title": "Multi-Sensor Monitor",
  "refresh_rate": 100,
  "window": {
    "width": 1200,
    "height": 600
  },
  "ports": {
    "/dev/ttyUSB0": {
      "0": {
        "label": "Time",
        "type": "int",
        "format": "{:,}",
        "unit": "counts"
      },
      "1": {
        "label": "Encoder 1",
        "type": "int",
        "format": "{:,}",
        "unit": "counts"
      }
    },
    "/dev/ttyUSB1": {
      "0": {
        "label": "Temperature",
        "type": "float",
        "format": "{:.2f}",
        "unit": "°C"
      },
      "1": {
        "label": "Humidity",
        "type": "float",
        "format": "{:.1f}",
        "unit": "%"
      }
    }
  }
}
```

## Usage

### Command Line
```bash
# Create example config (already updated to new format)
monitor --create-config

# Edit the config file to add your ports and fields
nano monitor_config.json

# Run the monitor (will auto-connect to all configured ports)
monitor -c monitor_config.json

# Use custom baudrate
monitor -c monitor_config.json -b 9600
```

### What Happens on Startup
1. Application reads configuration file
2. Creates GUI with all fields from all ports
3. Creates serial readers for each configured port
4. Auto-connects to all ports simultaneously
5. Data from each port updates its corresponding fields in the table

## Benefits

1. **Multi-Device Monitoring**: Monitor multiple microcontrollers simultaneously
2. **Simplified Workflow**: No manual port selection needed
3. **Configuration-Driven**: All settings in one JSON file
4. **Better Organization**: Clear separation of which fields come from which port
5. **Parallel Data Collection**: All ports read simultaneously in separate threads

## Breaking Changes

⚠️ **Important**: This is a breaking change that requires config file updates.

1. Configuration file format changed (see Migration Guide above)
2. Command-line arguments removed: `--port`, `--ask-port`, `--list-ports`
3. GUI no longer has port selection button
4. All existing config files must be updated

## Files Updated

- ✅ `src/monitor/config.py` - Multi-port configuration parsing
- ✅ `src/monitor/serial_reader.py` - MultiPortSerialReader class
- ✅ `src/monitor/gui.py` - Multi-port UI and data handling
- ✅ `src/monitor/monitor.py` - Removed port arguments
- ✅ `monitor_config.json` - Updated to new format
- ✅ `phase_tracker_config.json` - Updated to new format

## Testing Recommendations

1. Test with single port configuration
2. Test with multiple ports simultaneously
3. Verify all transformations work correctly
4. Test connection/disconnection behavior
5. Verify stats aggregation from multiple ports
6. Test error handling when a port fails

## Notes

- All ports share the same baudrate (specified via `-b` argument)
- Ports are connected/disconnected together as a group
- Statistics are aggregated across all ports
- Each port maintains its own serial reader thread
- The GUI table shows which port each field belongs to
