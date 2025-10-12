#!/usr/bin/env python3


import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Get the releases folder path
    project_root = Path(__file__).parent
    build_script = project_root / "releases" / "build_executable.py"
    
    print("Building release executable...")
    print(f"Using build script: {build_script}")
    
    # Run the actual build script
    result = subprocess.run([sys.executable, str(build_script)])
    sys.exit(result.returncode)
