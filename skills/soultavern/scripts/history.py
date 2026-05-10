#!/usr/bin/env python3
"""SoulTavern 'history' subcommand. See `python3 history.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["history", *sys.argv[1:]]))
