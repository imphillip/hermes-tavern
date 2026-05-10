"""Smoke-test SoulTavern's validate flow against real third-party cards.

Drop V2 cards under ``examples/.local/`` (or anywhere else inside
``examples/``) and ``pytest`` will discover them automatically. Each
card runs the full parse + render + scan pipeline; the test asserts a
clean exit. When no real cards are present, the test is skipped so CI
without bundled cards stays green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from soultavern.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
_SUFFIXES = (".json", ".png")  # v2.0 dropped YAML support


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
    rc = main(["validate", "--card", str(card)])
    assert rc == 0, f"soultavern validate {card.name} exited {rc}"
