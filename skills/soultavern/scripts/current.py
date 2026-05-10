#!/usr/bin/env python3
"""SoulTavern 'current' subcommand. See `python3 current.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["current", *sys.argv[1:]]))
