from pathlib import Path

import pytest

from hermes_tavern.parse import load_card
from hermes_tavern.render import BudgetExceededError, render


def test_render_minimal(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data, user_noun="friend")
    assert "# Echo" in result.soul
    assert "## Identity" in result.soul
    assert "friend" in result.soul
    # Minimal card has no character_book
    assert result.hermes is None


def test_render_full_substitutes_user_noun(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data, user_noun="the operator")
    body, _, _ = result.soul.partition("\n---\n")  # strip trailing model-notes block
    assert "the operator" in body
    assert "{{user}}" not in body
    assert "{{char}}" not in body
    assert "Marcellus" in result.soul
    # Field-mapping headings present (default = system_prompt / post_history untrusted)
    for heading in ("## Identity", "## Personality", "## Scenario",
                    "## Opening line", "## Example dialogues",
                    "## Author's framing",
                    "## Author's closing note"):
        assert heading in result.soul


def test_render_trusts_system_prompt_when_flagged(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data, trust_system_prompt=True)
    # In trust mode the system_prompt is rendered before the H1 (high-trust slot)
    body_before_h1 = result.soul.split("# Marcellus", 1)[0]
    assert "Stay in character as Marcellus" in body_before_h1
    # And post_history_instructions becomes "## Final reminders" again
    assert "## Final reminders" in result.soul
    assert "Author's framing" not in result.soul
    assert "Author's closing note" not in result.soul


def test_render_v1_legacy_tokens(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v1_legacy.json")
    result = render(data, user_noun="traveller")
    body, _, _ = result.soul.partition("\n---\n")
    # <BOT> and <USER> from V1 should be replaced too
    assert "<BOT>" not in body
    assert "<USER>" not in body
    assert "Old Tom" in result.soul
    assert "traveller" in result.soul


def test_render_with_book(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_with_book.json")
    result = render(data)
    assert result.hermes is not None
    assert "# The Underland" in result.hermes
    # Disabled entry must not appear
    assert "Disabled entry" not in result.hermes
    # Entries sorted by insertion_order ascending: Greythorn (10) before Mirror (20)
    greythorn_idx = result.hermes.index("Greythorn entrance")
    mirror_idx = result.hermes.index("Mirror Lake")
    assert greythorn_idx < mirror_idx


def test_render_soul_only(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_with_book.json")
    result = render(data, include_hermes_md=False)
    assert result.hermes is None


def test_render_budget_exceeded():
    data = {"name": "Bloated", "description": "x" * 25_000}
    with pytest.raises(BudgetExceededError) as exc:
        render(data)
    assert exc.value.kind == "SOUL.md"


def test_render_includes_metadata_comment(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data)
    assert "<!--" in result.soul
    assert "creator: test" in result.soul


def test_render_alternate_greetings_block(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_full.json")
    result = render(data)
    assert "## Alternate openings" in result.soul


def test_render_hermes_truncation_when_oversized(fixtures_dir: Path):
    # Build a synthetic book that overflows
    big_entries = [
        {"comment": f"entry-{i}", "content": "z" * 4000, "insertion_order": i, "enabled": True}
        for i in range(10)
    ]
    data = {
        "name": "Truncatable",
        "description": "short",
        "character_book": {"name": "Big", "entries": big_entries},
    }
    result = render(data)
    assert result.hermes is not None
    assert result.truncated_entries > 0
    # Higher insertion_order should be dropped first
    assert "entry-9" not in result.hermes
    assert "entry-0" in result.hermes
