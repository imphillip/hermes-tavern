#!/usr/bin/env python3
"""SoulTavern 'revert' subcommand. See `python3 revert.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["revert", *sys.argv[1:]]))
