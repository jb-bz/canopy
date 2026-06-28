"""canopy CLI entry point.

Mirrors `python -m canopy` → calls into `canopy.cli.main`.
"""
from __future__ import annotations

import sys

from canopy.cli import main


if __name__ == "__main__":
    sys.exit(main())