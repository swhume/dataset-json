"""
Main entry point for running dsjconvert as a module.

This allows the package to be run with:
    python -m dsjconvert [arguments]
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())
