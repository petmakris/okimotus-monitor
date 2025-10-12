# README.md Cleanup Summary

## Overview
Cleaned up README.md to remove all references to obsolete features and update documentation to reflect the current multi-port configuration system.

## Removed Obsolete Features

### 1. Command-Line Port Selection
**Removed:**
- `-p PORT, --port PORT` - Serial port selection via CLI
- `--ask-port` - Interactive port selection dialog
- Port selection button in GUI
- Port selection popup dialog

**Reason:** Ports are now configured in the JSON config file, not via command-line arguments.

### 2. Command-Line Baudrate
**Removed:**
- `-b RATE, --baudrate RATE` - Baudrate via CLI argument

**Reason:** Baudrate is now specified per-port in the configuration file, allowing different speeds for different devices.

### 3. Old Command Names
**Changed:**
- `--list-ports` → `--list` (updated throughout)
- `--create-config` now prints to stdout instead of creating a file

### 4. Old Configuration Format
**Removed references to:**
```json
{
  "fields": {
    "0": "Field Name"
  }
}
```

**Updated to:**
```json
{
  "ports": {
    "/dev/ttyUSB0": {
      "baudrate": 115200,
      "0": {"label": "Field Name", "type": "int"}
    }
  }
}
```

### 5. Obsolete GUI Features
**Removed mentions of:**
- Port selection dialog/button
- Single-port limitation
- Generic port filtering dialog

**Replaced with:**
- Multi-port simultaneous monitoring
- Port column in table view
- Configuration-based port management

### 6. Demo Mode
**Removed:** All references to running without config file or demo mode

**Current behavior:** Configuration file is required; shows help if not provided.

## Updated Sections

### Command Reference
- ✅ Removed `-p`, `-b`, `--ask-port` options
- ✅ Changed `--list-ports` to `--list`
- ✅ Updated all example commands
- ✅ Clarified that `-c config.json` is required

### Configuration Section
- ✅ Updated to show `ports` structure instead of `fields`
- ✅ Added per-port baudrate examples
- ✅ Added multi-port configuration examples
- ✅ Documented port naming conventions (Linux, Windows, macOS)
- ✅ Added note about using `--list` to discover ports

### Quick Start
- ✅ Updated minimal config to use `ports` format
- ✅ Changed `--create-config` to redirect output
- ✅ Removed port argument from run command

### GUI Controls
- ✅ Removed "Select Port" button documentation
- ✅ Added "Port" column to table description
- ✅ Updated controls to reflect multi-port operation

### Examples
- ✅ Updated Phase Tracker example to new format
- ✅ Updated Power Supply Monitor example
- ✅ Removed port arguments from all run commands
- ✅ All examples now use `ports` configuration

### Troubleshooting
- ✅ Changed `--list-ports` to `--list`
- ✅ Removed port selection dialog issues
- ✅ Updated debug command to remove `-p` argument

### Tips & Best Practices
- ✅ Updated simple config example to `ports` format
- ✅ Updated common patterns to show multi-port setup
- ✅ Removed references to port selection workflow

## Benefits of Cleanup

1. **Accuracy** - Documentation matches actual implementation
2. **Clarity** - No confusion about obsolete features
3. **Multi-port Focus** - Highlights the key advantage
4. **Simplified Commands** - Fewer options to remember
5. **Configuration-Driven** - Emphasizes declarative approach
