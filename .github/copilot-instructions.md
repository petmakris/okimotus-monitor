# Okimotus Development Tools - AI Agent Instructions

## Project Overview

Okimotus is a Python toolkit for AVR microcontroller development providing three main CLI tools:
- **`avr`**: AVR programming interface wrapping avrdude for firmware, EEPROM, and fuse management
- **`terminal`**: Enhanced serial terminal (miniterm) for embedded development communication
- **`monitor`**: Real-time GUI dashboard for visualizing comma-separated MCU data streams

## Architecture & Core Components

### Entry Points & CLI Structure
- Console scripts defined in `setup.py`: `avr`, `terminal`, and `monitor` commands
- Both tools use argparse with nested subcommands for complex CLI hierarchies
- Command delegation pattern: CLI parsers set `func` lambdas that call toolkit methods

### AVR Toolkit (`src/okimotus/avr/`)
- **`AvrToolkit`** class: Core abstraction wrapping avrdude commands
- **Configuration-driven**: Expects `config.yaml` with MCU settings (mcu, programmer, port, signature, fuses, firmware path, eeprom_size, eeprom_parts)
- **Hardware validation**: Automatic signature verification on initialization with retries
- **Operations**: Production workflows, EEPROM/firmware/fuse read/write/verify, colorized EEPROM dumps

### Terminal System (`src/okimotus/terminal/`)
- **`Miniterm`** class: Main serial terminal with threading (rx/tx threads)
- **Transform pipeline**: Pluggable text transformations for EOL conversion, control character handling
- **Interactive menus**: CTRL+T menu system for runtime configuration (baudrate, parity, flow control)
- **Platform-specific**: `console_linux.py` handles terminal raw mode with termios

### Monitor System (`src/okimotus/monitor/`)
- **`MonitorGUI`** class: Tkinter-based real-time data visualization
- **JSON configuration**: Field mapping system for CSV data interpretation
- **Serial integration**: Background threading for non-blocking data reception
- **Live updates**: Real-time field updates with visual feedback and timestamps

### Utility Modules
- **`exec_command.py`**: Subprocess wrapper with real-time stderr display and cleanup (erases stderr lines after completion)
- **`utils.py`**: ANSI color functions (`pr_red`, `pr_green`, etc.), JSON formatting, file operations
- **`hexutils.py`**: Intel HEX file parsing/generation with checksum validation

## Development Patterns & Conventions

### Error Handling
- **Fail-fast philosophy**: `sys.exit(1)` on configuration/hardware errors
- **Colorized logging**: Use `pr_red()` for errors, `pr_yellow()` for warnings, `pr_green()` for success
- **Retry logic**: Hardware operations (signature verification) include automatic retries with delays

### Command Execution
- **Always use `exec_command()`** instead of raw subprocess for external tools
- Provides consistent error handling, colored output, and stderr management
- Example: `self.run_avrdude_command(['-U', 'signature:r:-:h'])`

### Configuration Management
- **YAML-based config** (AVR): Hardware specifications with retry and validation patterns
- **JSON-based config** (Monitor): Field mappings with type conversion and formatting
- **No config validation yet**: TODO comments indicate validation needs implementation
- **Example monitor config structure**:
  ```json
  {
    "title": "MCU Monitor",
    "fields": {
      "0": {"label": "Encoder 1", "type": "int", "format": "{:,}", "unit": "counts"},
      "1": "Simple Label",
      "2": {"label": "Temperature", "type": "float", "format": "{:.2f}", "unit": "°C"}
    }
  }
  ```

### GUI Development Patterns
- **Tkinter with threading**: Main GUI thread + background serial reader thread
- **Callback-based updates**: Serial data callbacks update GUI via `root.after()`
- **Widget composition**: Reusable field widgets with automatic formatting
- **Cross-platform compatibility**: Pure Python/Tkinter for maximum portability

### File Management
- **Temporary file pattern**: Use `get_random_hex()` for temp files, always clean up in try/finally
- **`delete_file()` utility**: Handles FileNotFoundError gracefully with warnings
- **Intel HEX operations**: Use `intelhex` library for EEPROM/firmware processing

### Threading & Terminal Handling
- **Daemon threads**: Reader/writer threads marked as daemon for clean shutdown
- **Thread lifecycle**: Explicit start/stop/join methods for controlled threading
- **Context managers**: Console class supports context manager for temporary terminal mode switching

## Build & Development Workflow

### Package Structure
```
src/okimotus/                 # Source root
├── avr/                      # AVR programming toolkit
├── terminal/                 # Serial terminal implementation
├── monitor/                  # GUI data visualization system
│   ├── config.py            # JSON configuration parser
│   ├── gui.py               # Tkinter GUI application
│   ├── monitor.py           # CLI entry point
│   └── serial_reader.py     # Background serial data reader
├── utils.py                  # Shared utilities
├── exec_command.py           # Command execution wrapper
└── hexutils.py               # Intel HEX processing
```

### Dependencies
- **Hardware tools**: Requires `avrdude` installed for AVR operations
- **Key packages**: `pyserial`, `intelhex`, `pyyaml`, `tabulate`, `pygments`
- **GUI**: `tkinter` (included with Python) for cross-platform GUI support
- **Testing**: pytest, mock, coverage (defined but no tests found)

### Installation & Usage
```bash
pip install -e .                        # Development install
avr --help                              # AVR toolkit commands
terminal /dev/ttyUSB0 115200            # Serial terminal
monitor                                 # GUI data monitor (demo mode)
monitor -p /dev/ttyUSB0 -c config.json # Monitor with custom config
monitor --create-config                 # Generate example config file
```

## Integration Points & External Dependencies

### Hardware Dependencies
- **avrdude**: Critical external dependency for all AVR operations
- **Serial ports**: Direct hardware communication via pyserial for terminal and monitor
- **USB programmers**: Supports USBasp and other avrdude-compatible programmers

### Cross-Component Communication
- **Shared utilities**: Common logging, coloring, and file operations across modules
- **Configuration coupling**: AVR toolkit hardcodes `config.yaml` filename
- **Independent tools**: AVR, terminal, and monitor tools operate independently
- **Serial data format**: Monitor expects CSV format: "value1,value2,value3,..."

## Development Guidelines

### Adding New AVR Operations
1. Add method to `AvrToolkit` class
2. Create CLI parser in appropriate `create_menu_section_*` function
3. Use `run_avrdude_command()` for hardware communication
4. Follow temporary file cleanup patterns

### Terminal Enhancements
1. Add transform classes inheriting from `Transform` in `transform.py`
2. Register in `TRANSFORMATIONS` dict
3. Update menu system in `handle_menu_key()` if needed

### Monitor Extensions
1. **Field types**: Add new data types in `MonitorConfig.format_value()`
2. **Widgets**: Create custom field widgets inheriting from `FieldWidget`
3. **Protocols**: Extend `SerialDataParser` for different data formats
4. **Visualizations**: Add plotting/graphing widgets for trend analysis

### Code Style
- **Lambda patterns**: CLI uses `set_defaults(func=lambda args: method())` 
- **Color coding**: Consistent use of color functions for different message types
- **Threading safety**: Use `root.after()` for GUI updates from background threads
- **Descriptive exceptions**: Include hardware state and expected values in error messages

## Common Pitfalls
- Missing `config.yaml` will cause immediate AVR toolkit startup failure
- Hardware signature mismatches require physical hardware debugging
- Terminal raw mode changes persist if cleanup fails - always use try/finally
- Temporary hex files must be cleaned up to prevent disk space issues
- GUI updates from background threads must use `root.after()` to avoid crashes
- Monitor config field positions must be numeric strings in JSON ("0", "1", not 0, 1)