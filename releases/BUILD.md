# Okimotus Monitor - Building Standalone Executables

This document explains how to create self-contained executable files for the Okimotus Monitor application.

## Option 1: PyInstaller (Recommended)

PyInstaller is the most reliable option for creating standalone executables from Python applications with GUI components.

### Installation

```bash
# Install PyInstaller
pip install pyinstaller

# Or install with build dependencies
pip install -e .[build]
```

### Build Methods

#### Method 1: Using the build script (Recommended)

```bash
python build_executable.py
```

#### Method 2: Using the spec file

```bash
pyinstaller okimotus-monitor.spec
```

#### Method 3: Direct command line

```bash
pyinstaller --onefile --name okimotus-monitor \
    --add-data "monitor_config.json:." \
    --add-data "phase_tracker_config.json:." \
    --hidden-import serial \
    --hidden-import serial.tools.list_ports \
    src/monitor/monitor.py
```

### Output

The executable will be created in the `dist/` directory:
- **Linux**: `dist/okimotus-monitor`
- **Windows**: `dist/okimotus-monitor.exe`
- **macOS**: `dist/okimotus-monitor`

## Option 2: cx_Freeze (Alternative)

### Installation

```bash
pip install cx_Freeze
```

### Build

```bash
python setup_cxfreeze.py build
```

The executable will be in the `build/` directory.

## Distribution

### Single File Executable

The PyInstaller `--onefile` option creates a single executable file that contains everything needed to run the application. This is the most convenient for distribution.

### Directory Distribution

Without `--onefile`, PyInstaller creates a directory with the executable and all dependencies. This starts faster but requires distributing the entire directory.

## Platform-Specific Notes

### Linux

- The executable will only run on the same architecture (x86_64, ARM, etc.)
- May need to be built on the oldest supported distribution for compatibility
- Consider using AppImage for better Linux distribution compatibility

### Windows

- Add `--windowed` flag to hide the console window for GUI-only operation
- Consider adding an icon with `--icon=icon.ico`
- The executable will work on Windows 7+ (depending on Python version used)

### macOS

- Code signing may be required for distribution
- Consider creating a `.app` bundle or DMG for proper macOS distribution

## Troubleshooting

### Common Issues

1. **Missing modules**: Add `--hidden-import module_name` for any missing imports
2. **Large file size**: Use `--exclude-module` to remove unnecessary modules
3. **Slow startup**: Consider using directory mode instead of `--onefile`
4. **Permission errors**: Ensure the executable has proper permissions after building

### Optimization

To reduce executable size:

```bash
pyinstaller --onefile --strip --upx-dir=/path/to/upx \
    --exclude-module matplotlib \
    --exclude-module numpy \
    okimotus-monitor.spec
```

## Testing

Always test the executable on a clean system without Python installed to ensure it's truly self-contained.

## CI/CD Integration

For automated builds, consider using GitHub Actions or similar CI/CD systems to build executables for multiple platforms:

```yaml
# Example GitHub Actions workflow
name: Build Executables
on: [push, pull_request]
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - run: pip install -e .[build]
    - run: python build_executable.py
    - uses: actions/upload-artifact@v2
      with:
        name: okimotus-monitor-${{ matrix.os }}
        path: dist/
```