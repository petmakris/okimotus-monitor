#!/usr/bin/env python3
"""
Build script for creating standalone executables using PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    """Build the executable using PyInstaller"""
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Entry point script
    entry_point = "src/monitor/monitor.py"
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Create a single executable file
        "--windowed",  # Hide console on Windows (remove if you want console)
        "--name", "okimotus-monitor",
        "--icon", "icon.ico",  # Add this if you have an icon file
        "--add-data", "monitor_config.json:.",
        "--add-data", "phase_tracker_config.json:.",
        "--hidden-import", "serial",
        "--hidden-import", "serial.tools.list_ports",
        entry_point
    ]
    
    # Remove --icon line if no icon exists
    if not Path("icon.ico").exists():
        cmd = [arg for arg in cmd if not arg.startswith("--icon") and arg != "icon.ico"]
    
    print("Building executable with PyInstaller...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(f"Executable created in: {project_root}/dist/")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("PyInstaller not found. Install it with: pip install pyinstaller")
        return False

if __name__ == "__main__":
    build_executable()