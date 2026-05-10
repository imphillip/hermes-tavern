#!/usr/bin/env python3
"""SoulTavern 'list' subcommand. See `python3 list.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["list", *sys.argv[1:]]))
