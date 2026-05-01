"""Smoke-test ``hermes-tavern validate`` against real third-party cards.

Drop V2 cards under ``examples/.local/`` (or anywhere else inside
``examples/``) and ``pytest`` will discover them automatically. Each
card runs the full parse + render + scan pipeline; the test asserts a
clean exit. When no real cards are present, the test is skipped so CI
without bundled cards stays green.

This replaces the standalone ``scripts/smoke-real-cards.sh``: same
intent, runs through the same test runner, fewer top-level entry
points to maintain.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
_SUFFIXES = (".json", ".png", ".yaml", ".yml")


def _discover_real_cards() -> list[Path]:
    if not EXAMPLES_DIR.is_dir():
        return []
    return sorted(
        path
        for path in EXAMPLES_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in _SUFFIXES
    )


_CARDS = _discover_real_cards()


@pytest.mark.skipif(
    not _CARDS,
    reason="no real cards under examples/ — drop some into examples/.local/ to enable",
)
@pytest.mark.parametrize("card", _CARDS, ids=lambda p: p.relative_to(EXAMPLES_DIR).as_posix())
def test_real_card_validates(card: Path) -> None:
    result = subprocess.run(
        ["hermes-tavern", "validate", "--card", str(card)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"hermes-tavern validate {card.name} exited {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
