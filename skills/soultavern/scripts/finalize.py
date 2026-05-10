#!/usr/bin/env python3
"""SoulTavern 'finalize' subcommand. See `python3 finalize.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["finalize", *sys.argv[1:]]))
