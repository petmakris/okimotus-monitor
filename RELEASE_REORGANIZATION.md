# Release Files Reorganization

All files related to building and distributing binary releases have been moved to the `releases/` folder.

## What Changed

### Files Moved to `releases/` Folder:
- ✅ `build_executable.py` - PyInstaller build script
- ✅ `okimotus-monitor.spec` - PyInstaller spec file  
- ✅ `setup_cxfreeze.py` - cx_Freeze build script
- ✅ `Makefile` - Build automation
- ✅ `BUILD.md` - Build documentation
- ✅ `DISTRIBUTION_SUMMARY.md` - Distribution overview

### New Files Created:
- ✅ `releases/README.md` - Documentation for the releases folder
- ✅ `build_release.py` - Convenience wrapper script (in project root)

### Updated Files:
- ✅ `.gitignore` - Updated to keep spec files in releases folder
- ✅ `Readme.md` - Updated installation instructions
- ✅ `releases/build_executable.py` - Updated to work from releases folder
- ✅ `releases/Makefile` - Updated paths to work from releases folder

## Project Structure

```
okimotus-monitor/
├── src/                      # Source code
├── releases/                 # All release/build files
│   ├── README.md
│   ├── build_executable.py
│   ├── okimotus-monitor.spec
│   ├── setup_cxfreeze.py
│   ├── Makefile
│   ├── BUILD.md
│   └── DISTRIBUTION_SUMMARY.md
├── build_release.py          # Convenience wrapper
├── dist/                     # Built executables (created during build)
├── build/                    # Temporary build files (created during build)
└── Readme.md                 # Main documentation
```

## How to Build Releases

### From Project Root (Recommended):
```bash
python build_release.py
```

### From Releases Folder:
```bash
cd releases
python build_executable.py
```

### Using Make:
```bash
cd releases
make build
```

## Benefits

1. **Cleaner Root Directory** - Main project folder is no longer cluttered with build files
2. **Better Organization** - All release-related files are in one place
3. **Clear Separation** - Development code vs. release/distribution concerns
4. **Easy to Ignore** - Can easily exclude entire `releases/` folder if needed
5. **Backwards Compatible** - Convenience wrapper in root for easy access

## Output Location

Build artifacts are still created in the project root:
- `dist/` - Final executables
- `build/` - Temporary build files

This keeps the output in a familiar location while organizing the input files.
