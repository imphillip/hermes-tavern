#!/usr/bin/env python3
"""SoulTavern 'switch' subcommand. See `python3 switch.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["switch", *sys.argv[1:]]))
