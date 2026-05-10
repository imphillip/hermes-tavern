#!/usr/bin/env python3
"""SoulTavern 'restore' subcommand. See `python3 restore.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["restore", *sys.argv[1:]]))
