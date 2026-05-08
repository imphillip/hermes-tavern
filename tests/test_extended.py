"""Tests for extended.py: per-entry payload writes, the post-agent
extended-files walker, and the indexed HERMES.md renderer."""

from __future__ import annotations

from pathlib import Path

from soultavern.extended import (
    ExtendedFile,
    collect_extended_files,
    render_indexed_hermes_md,
    slug,
    write_lorebook_payloads,
)


def test_slug_normalises_safely():
    assert slug("Mirror Lake") == "Mirror_Lake"
    assert slug("  spaced  ") == "spaced"
    assert slug("!!!") == "entry"
    assert slug("a/b\\c") == "a_b_c"


def test_write_lorebook_payloads_writes_greetings_and_lore(tmp_path: Path):
    extended_dir = tmp_path / "cards" / "test_card" / "extended"
    data = {
        "name": "Aldous",
        "alternate_greetings": ["alt one with {{user}}", "alt two"],
        "character_book": {
            "entries": [
                {"comment": "Mirror Lake", "keys": ["lake"], "content": "still water"},
                {"comment": "", "keys": ["trees"], "content": "tall pines"},
            ],
        },
    }
    write_lorebook_payloads(extended_dir, data, user_noun="the visitor")

    g1 = extended_dir / "alternate_greetings" / "01.md"
    g2 = extended_dir / "alternate_greetings" / "02.md"
    assert g1.is_file()
    assert g2.is_file()
    assert "the visitor" in g1.read_text()
    assert "{{user}}" not in g1.read_text()

    lore_lake = extended_dir / "lore" / "Mirror_Lake.md"
    lore_trees = extended_dir / "lore" / "trees.md"
    assert lore_lake.is_file()
    assert lore_trees.is_file()
    assert "still water" in lore_lake.read_text()
    assert "<!-- keys: lake -->" in lore_lake.read_text()


def test_write_lorebook_payloads_skips_empty_entries(tmp_path: Path):
    extended_dir = tmp_path / "extended"
    data = {
        "name": "Echo",
        "alternate_greetings": ["", "real one"],
        "character_book": {
            "entries": [
                {"comment": "Empty", "keys": [], "content": "   "},
                {"comment": "Real", "keys": ["k"], "content": "kept"},
            ],
        },
    }
    write_lorebook_payloads(extended_dir, data, user_noun="the visitor")
    # First greeting is empty → no 01.md; second writes as 02.md
    assert not (extended_dir / "alternate_greetings" / "01.md").exists()
    assert (extended_dir / "alternate_greetings" / "02.md").exists()
    assert not (extended_dir / "lore" / "Empty.md").exists()
    assert (extended_dir / "lore" / "Real.md").exists()


def test_write_lorebook_payloads_no_op_with_no_greetings_or_book(tmp_path: Path):
    extended_dir = tmp_path / "extended"
    write_lorebook_payloads(extended_dir, {"name": "Echo"}, user_noun="the visitor")
    # Dir is created but empty (no greetings/lore subdirs)
    assert extended_dir.is_dir()
    assert not (extended_dir / "alternate_greetings").exists()
    assert not (extended_dir / "lore").exists()


def test_collect_extended_files_indexes_v2_categories(tmp_path: Path):
    home = tmp_path / "home"
    extended_dir = home / "cards" / "x" / "extended"
    extended_dir.mkdir(parents=True)
    (extended_dir / "identity.md").write_text("# Identity\n\nbody\n", "utf-8")
    (extended_dir / "personality.md").write_text("# Personality\n\nbody\n", "utf-8")
    # Empty file should be skipped — same signal as a missing one
    (extended_dir / "kinks.md").write_text("", "utf-8")

    files = collect_extended_files(home, extended_dir, char_name="X")
    paths = [f.relative_path for f in files]
    assert any(p.endswith("extended/identity.md") for p in paths)
    assert any(p.endswith("extended/personality.md") for p in paths)
    assert not any(p.endswith("extended/kinks.md") for p in paths)
    # Title comes from CATEGORY_TITLES
    identity = next(f for f in files if f.relative_path.endswith("identity.md"))
    assert identity.title == "Identity"


def test_collect_extended_files_includes_greetings_and_lore(tmp_path: Path):
    home = tmp_path / "home"
    extended_dir = home / "cards" / "x" / "extended"
    extended_dir.mkdir(parents=True)
    (extended_dir / "identity.md").write_text("# Identity\n\nbody\n", "utf-8")
    write_lorebook_payloads(extended_dir, {
        "name": "X",
        "alternate_greetings": ["one"],
        "character_book": {"entries": [
            {"comment": "Mirror Lake", "keys": ["lake"], "content": "still water"},
        ]},
    }, user_noun="the visitor")

    files = collect_extended_files(home, extended_dir, char_name="X")
    paths = [f.relative_path for f in files]
    assert any(p.endswith("alternate_greetings/01.md") for p in paths)
    assert any(p.endswith("lore/Mirror_Lake.md") for p in paths)
    # Lore entry's title comes from the H1 (preserves the original label)
    lore = next(f for f in files if f.relative_path.endswith("Mirror_Lake.md"))
    assert lore.title == "Mirror Lake"


def test_render_indexed_hermes_md_emits_director_notes_and_index():
    files = [
        ExtendedFile("cards/x/extended/identity.md", "Identity", "name, age, etc."),
        ExtendedFile("cards/x/extended/lore/forest.md", "Forest", "world detail"),
    ]
    out = render_indexed_hermes_md("Aldous", files)
    assert "Aldous" in out
    assert "Director's Notes (Context Usage)" in out
    assert "Lore content boundary" in out
    assert "## Extended material on disk" in out
    assert "cards/x/extended/identity.md" in out
    assert "Identity" in out


def test_render_indexed_hermes_md_with_no_files_is_minimal():
    out = render_indexed_hermes_md("Echo", [])
    assert "Echo" in out
    assert "## Extended material on disk" not in out
