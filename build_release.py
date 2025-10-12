#!/usr/bin/env python3
"""
Convenience wrapper to build from project root.
This script just calls the actual build script in the releases folder.
"""

import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Get the releases folder path
    project_root = Path(__file__).parent
    build_script = project_root / "releases" / "build_executable.py"
    
    print("Building release executable...")
    print(f"Using build script: {build_script}")
    print("-" * 60)
    
    # Run the actual build script
    result = subprocess.run([sys.executable, str(build_script)])
    sys.exit(result.returncode)
