#!/usr/bin/env python3
"""
Standalone entry point: render a diagram from an existing coordinates.txt.

This is a thin wrapper around generate_code.py for when you already
have a blueprint and just want to (re-)render it.

Usage:
    python3 render_geometry.py --coordinates coordinates.txt --output output/diagram.png --format png
"""

import subprocess
import sys
from pathlib import Path


def main():
    # Forward all arguments to generate_code.py
    script = Path(__file__).parent / "generate_code.py"
    result = subprocess.run(
        [sys.executable, str(script)] + sys.argv[1:],
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
