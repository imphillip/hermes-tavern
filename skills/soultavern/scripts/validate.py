#!/usr/bin/env python3
"""SoulTavern 'validate' subcommand. See `python3 validate.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["validate", *sys.argv[1:]]))
