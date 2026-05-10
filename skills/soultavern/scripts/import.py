#!/usr/bin/env python3
"""SoulTavern 'import' subcommand. See `python3 import.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["import", *sys.argv[1:]]))
