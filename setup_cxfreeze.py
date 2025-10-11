#!/usr/bin/env python3
"""
Build script using cx_Freeze
"""

import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need help with some packages.
build_options = {
    'packages': ['serial', 'tkinter'],
    'excludes': ['test', 'unittest'],
    'include_files': [
        'monitor_config.json',
        'phase_tracker_config.json'
    ],
    'zip_include_packages': ['encodings', 'PySide6'],
}

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'  # Hide console on Windows

executables = [
    Executable(
        'src/monitor/monitor.py',
        base=base,
        target_name='okimotus-monitor'
    )
]

setup(
    name='okimotus-monitor',
    version='0.1.0',
    description='Okimotus Monitor Application',
    options={'build_exe': build_options},
    executables=executables
)