#!/usr/bin/env python3
"""SoulTavern 'delete' subcommand. See `python3 delete.py --help`."""

from __future__ import annotations

import sys

from soultavern.cli import main


if __name__ == "__main__":
    sys.exit(main(["delete", *sys.argv[1:]]))
