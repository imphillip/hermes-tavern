"""Tests for staging.py — the deterministic CLI step that writes
source.md (and the per-entry payloads) when an oversized card is
detected, then raises NeedsAgentCategorizationError for the agent to
pick up.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_tavern import library
from hermes_tavern.staging import (
    NeedsAgentCategorizationError,
    format_source_for_agent,
    write_source_md,
)


def _bloated_payload(name: str = "Bloat") -> dict:
    return {
        "spec": "chara_card_v2",
        "data": {
            "name": name,
            "description": "x" * 16_000,
            "personality": "patient",
            "first_mes": "hi",
        },
    }


def test_format_source_for_agent_emits_per_field_blocks():
    data = {
        "name": "Echo",
        "description": "long prose",
        "personality": "quiet",
        "scenario": "café at dusk",
        "first_mes": "hi",
        "mes_example": "<Echo> hello",
    }
    out = format_source_for_agent(data, char_name="Echo", user_noun="the visitor")
    assert "Echo — source material" in out
    assert "## description" in out
    assert "long prose" in out
    assert "## personality" in out
    assert "## scenario" in out
    assert "## first_mes" in out
    assert "## mes_example" in out
    assert "Oversized card procedure" in out  # SKILL.md pointer in the header


def test_format_source_flags_subheaders_in_description():
    """Veranna-class cards (description with `Header: value` lines) get
    pre-flagged as ### Header blocks so the agent doesn't have to discover
    them itself."""
    description = (
        "Full Name: Echo\n"
        "Age: 22\n"
        "Height: 181 cm\n"
        "Appearance: tall and dark-haired.\n"
    )
    out = format_source_for_agent(
        {"name": "Echo", "description": description},
        char_name="Echo",
        user_noun="the visitor",
    )
    assert "already structured by subheaders" in out
    assert "### Full Name" in out
    assert "### Appearance" in out


def test_format_source_passes_through_unstructured_description():
    description = "Just a long paragraph of prose with no labels."
    out = format_source_for_agent(
        {"name": "X", "description": description},
        char_name="X",
        user_noun="the visitor",
    )
    assert "already structured by subheaders" not in out
    assert description in out


def test_format_source_includes_alternate_greetings_and_lore():
    data = {
        "name": "Echo",
        "alternate_greetings": ["alt one", "alt two"],
        "character_book": {
            "entries": [
                {"comment": "Mirror Lake", "keys": ["lake"], "content": "still water"},
            ],
        },
    }
    out = format_source_for_agent(data, char_name="Echo", user_noun="the visitor")
    assert "## alternate_greeting #1" in out
    assert "alt one" in out
    assert "## alternate_greeting #2" in out
    assert "## character_book" in out
    assert "### Mirror Lake" in out
    assert "<!-- keys: lake -->" in out


def test_write_source_md_also_writes_lorebook_payloads(tmp_path: Path):
    """Phase 1 of the oversized-card flow writes both source.md (for the
    agent to read) and the per-entry payloads (which the CLI handles
    deterministically — they're already structured per-entry)."""
    extended_dir = tmp_path / "cards" / "Echo_x" / "extended"
    data = {
        "name": "Echo",
        "description": "long prose",
        "alternate_greetings": ["alt one"],
        "character_book": {
            "entries": [
                {"comment": "Mirror Lake", "keys": ["lake"], "content": "still water"},
            ],
        },
    }
    target = write_source_md(extended_dir, data,
                             char_name="Echo", user_noun="the visitor")
    # source.md lives in the per-card dir, parent of extended/
    assert target == extended_dir.parent / "source.md"
    assert target.is_file()
    body = target.read_text()
    assert "## description" in body
    # Per-entry payloads were also written under extended/
    assert (extended_dir / "alternate_greetings" / "01.md").is_file()
    assert (extended_dir / "lore" / "Mirror_Lake.md").is_file()


def test_apply_card_raises_needs_agent_for_oversize(home: Path, tmp_path: Path):
    """library.apply_card propagates NeedsAgentCategorizationError when
    rendering would overflow the threshold and no agent work is yet on
    disk."""
    src = tmp_path / "bloat.json"
    src.write_text(json.dumps(_bloated_payload()))
    with pytest.raises(NeedsAgentCategorizationError) as exc_info:
        library.import_card(home, src)
    err = exc_info.value
    assert err.char_name == "Bloat"
    assert err.threshold == library.OVERSIZE_THRESHOLD
    assert err.rendered_size > err.threshold
    assert err.source_md_path.is_file()
    # The card was still copied into the library and the staging artifacts
    # are on disk, ready for the agent.
    card_dirs = [p for p in (home / "cards").iterdir() if p.is_dir()
                 and not p.name.startswith(".")]
    assert len(card_dirs) == 1
    assert (card_dirs[0] / "source.md").is_file()
    # SOUL.md / HERMES.md not written — those wait for finalize.
    assert not (home / "SOUL.md").exists()
    assert not (home / "HERMES.md").exists()


def test_soul_only_skips_agent_flow(home: Path, tmp_path: Path):
    """--soul-only is an explicit "skip the second file"; the oversize
    routing must not engage. As long as the rendered SOUL still fits
    under the hard cap, the import succeeds without staging anything
    for the agent. (When it doesn't fit, BudgetExceededError surfaces;
    that path is covered in test_render.)"""
    src = tmp_path / "bloat.json"
    src.write_text(json.dumps(_bloated_payload()))
    outcome, _ = library.import_card(home, src, soul_only=True)
    assert outcome.finalized is False
    assert (home / "SOUL.md").is_file()
    assert not (home / "HERMES.md").exists()
    # No source.md / extended/ side-effects from the agent flow.
    card_dirs = [p for p in (home / "cards").iterdir() if p.is_dir()
                 and not p.name.startswith(".")]
    for d in card_dirs:
        assert not (d / "source.md").exists()
        assert not (d / "extended").exists()
