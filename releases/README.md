# Release Build Files

This folder contains all files related to building and distributing binary releases of the Okimotus Monitor application.

## Files in this folder:

- **`build_executable.py`** - Simple build script for creating executables
- **`okimotus-monitor.spec`** - PyInstaller spec file for advanced configuration
- **`setup_cxfreeze.py`** - Alternative build script using cx_Freeze
- **`Makefile`** - Convenient make commands for building releases
- **`BUILD.md`** - Comprehensive build documentation
- **`DISTRIBUTION_SUMMARY.md`** - Summary of distribution options

## Quick Start

To build a standalone executable:

```bash
# From this folder
python build_executable.py

# Or use make
make build

# The executable will be created in ../dist/
```

## Documentation

For detailed build instructions, see [BUILD.md](BUILD.md).
For distribution options overview, see [DISTRIBUTION_SUMMARY.md](DISTRIBUTION_SUMMARY.md).

## Output

Built executables and build artifacts are placed in:
- `../dist/` - Final executables ready for distribution
- `../build/` - Temporary build files (can be deleted)
