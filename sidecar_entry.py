#!/usr/bin/env python3
"""Standalone entry point for PyInstaller sidecar build."""

import sys
import os

# Add the src directory to path for imports
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

from deck_link.main import main

if __name__ == "__main__":
    main()
