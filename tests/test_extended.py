"""Tests for the extended-files writer and AGENTS.md index renderer."""

from __future__ import annotations

from pathlib import Path

from hermes_tavern.extended import (
    ExtendedFile,
    render_distilled_hermes_md,
    slug,
    write_extended,
)


def test_slug_normalises_safely():
    assert slug("Mirror Lake") == "Mirror_Lake"
    assert slug("  spaced  ") == "spaced"
    assert slug("!!!") == "entry"
    assert slug("a/b\\c") == "a_b_c"


def test_write_extended_creates_per_field_files(tmp_path: Path):
    home = tmp_path / "home"
    extended_dir = home / "cards" / "test_card" / "extended"
    data = {
        "name": "Aldous",
        "description": "long description with {{user}} reference",
        "personality": "patient",
        "first_mes": "first opening",
        "alternate_greetings": ["alt one", "alt two"],
        "mes_example": "example dialogue",
        "character_book": {
            "entries": [
                {"comment": "Mirror Lake", "keys": ["lake"], "content": "still water"},
                {"comment": "", "keys": ["trees"], "content": "tall pines"},
            ],
        },
    }
    files = write_extended(home, extended_dir, data, user_noun="the visitor")

    paths = {f.relative_path for f in files}
    assert any(p.endswith("extended/description.md") for p in paths)
    assert any(p.endswith("extended/personality.md") for p in paths)
    assert any(p.endswith("extended/mes_example.md") for p in paths)
    assert any(p.endswith("extended/alternate_greetings/01.md") for p in paths)
    assert any(p.endswith("extended/alternate_greetings/02.md") for p in paths)
    assert any(p.endswith("extended/lore/Mirror_Lake.md") for p in paths)
    assert any(p.endswith("extended/lore/trees.md") for p in paths)

    # File contents include placeholder substitution
    desc = (extended_dir / "description.md").read_text()
    assert "the visitor" in desc
    assert "{{user}}" not in desc


def test_write_extended_skips_empty_fields(tmp_path: Path):
    home = tmp_path / "home"
    extended_dir = home / "cards" / "min" / "extended"
    data = {"name": "Echo", "description": "only this"}
    files = write_extended(home, extended_dir, data, user_noun="the visitor")
    paths = {f.relative_path for f in files}
    assert any(p.endswith("description.md") for p in paths)
    assert not any("personality" in p for p in paths)
    assert not any("first_mes" in p for p in paths)


def test_render_distilled_hermes_md_with_lore_and_index():
    files = [
        ExtendedFile("cards/x/extended/description.md", "Full description", "biographical"),
        ExtendedFile("cards/x/extended/lore/forest.md", "Forest", "world detail"),
    ]
    out = render_distilled_hermes_md("Aldous", "## World\n\nbrief lore", files)
    assert "Aldous" in out
    assert "Lore content boundary" in out
    assert "## World" in out
    assert "## Extended material on disk" in out
    assert "cards/x/extended/description.md" in out
    assert "Full description" in out


def test_render_distilled_hermes_md_with_no_lore_is_index_only():
    files = [ExtendedFile("cards/x/extended/description.md", "Full description", "biographical")]
    out = render_distilled_hermes_md("Aldous", None, files)
    assert "Lore content boundary" in out
    assert "## Extended material on disk" in out
    assert "## World" not in out


def test_render_distilled_hermes_md_with_nothing_is_minimal():
    out = render_distilled_hermes_md("Echo", None, [])
    assert "Echo" in out
    assert "## Extended material on disk" not in out
