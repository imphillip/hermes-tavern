"""Tests for the (now LLM-call-free) classify module.

v0.4.5 moved the actual semantic categorization out of this module — the
agent does it in its own context and writes ``extended/<category>.md``
files. What classify still owns:

- The canonical V2 categories + display titles + summaries
- The Classification dataclass that render and finalize consume
- The deterministic subheader preprocessor used at staging time
- The reader that loads agent-written category files back into a
  Classification for finalize to render from
"""
from __future__ import annotations

from pathlib import Path

from hermes_tavern.classify import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    CATEGORY_TITLES,
    SOUL_PICKS,
    Classification,
    _detect_subheaders,
    _strip_h1,
    load_classification_from_extended,
)


def test_categories_are_the_eight_v2_aligned_buckets():
    assert CATEGORIES == (
        "identity", "appearance", "personality", "backstory",
        "scenario", "kinks", "roleplay_guides", "examples",
    )


def test_soul_picks_are_a_strict_subset_of_categories():
    assert set(SOUL_PICKS).issubset(set(CATEGORIES))
    # The "always-on core" picks: who the character is + how to play them.
    # appearance / backstory / scenario / kinks / examples live in extended/.
    assert SOUL_PICKS == ("identity", "personality", "roleplay_guides")


def test_titles_and_descriptions_cover_every_category():
    for cat in CATEGORIES:
        assert cat in CATEGORY_TITLES
        assert cat in CATEGORY_DESCRIPTIONS
        assert CATEGORY_TITLES[cat]
        assert CATEGORY_DESCRIPTIONS[cat]


def test_detect_subheaders_finds_veranna_style_labels():
    text = (
        "Full Name: Veranna Li\n"
        "Age: 22 years old\n"
        "Ethnicity: Chinese\n"
        "Height: 181 cm\n"
        "Appearance: long dark hair, hazel eyes\n"
    )
    parts = _detect_subheaders(text)
    assert parts is not None
    assert len(parts) == 5
    headers = [h for h, _ in parts]
    assert headers == ["Full Name", "Age", "Ethnicity", "Height", "Appearance"]


def test_detect_subheaders_returns_none_when_no_structure():
    text = "Just a regular paragraph of prose. She said: 'Hi.'"
    assert _detect_subheaders(text) is None


def test_detect_subheaders_preserves_multiline_body():
    text = (
        "Appearance: long dark hair.\n"
        "Eyes are hazel.\n"
        "Height is tall.\n"
        "\n"
        "Personality: reserved.\n"
        "Speaks softly.\n"
        "Listens well.\n"
    )
    parts = _detect_subheaders(text, min_count=2)
    assert parts is not None
    assert len(parts) == 2
    assert parts[0][0] == "Appearance"
    assert "Eyes are hazel" in parts[0][1]
    assert "Height is tall" in parts[0][1]
    assert parts[1][0] == "Personality"
    assert "Speaks softly" in parts[1][1]


def test_classification_non_empty_filters_blanks():
    """Convenience accessor for downstream consumers."""
    c = Classification(categories={
        "identity": "Echo",
        "appearance": "",
        "personality": "Quiet.",
        "backstory": "",
        "scenario": "",
        "kinks": "",
        "roleplay_guides": "",
        "examples": "",
    })
    non_empty = c.non_empty()
    assert set(non_empty.keys()) == {"identity", "personality"}


def test_strip_h1_removes_leading_heading_and_blanks():
    body = "# Identity\n\nBody line one.\nBody line two.\n"
    out = _strip_h1(body)
    assert out == "Body line one.\nBody line two.\n"


def test_strip_h1_no_op_when_no_h1():
    body = "Body line one.\nBody line two.\n"
    assert _strip_h1(body) == "Body line one.\nBody line two.\n"


def test_strip_h1_handles_empty():
    assert _strip_h1("") == ""


def test_load_classification_from_extended(tmp_path: Path):
    extended = tmp_path / "extended"
    extended.mkdir()
    (extended / "identity.md").write_text(
        "# Identity\n\nEcho, 22.\n", "utf-8")
    (extended / "personality.md").write_text(
        "Quiet observer.\n", "utf-8")  # no H1 — finalize tolerates it
    # Skip writing the others; they should come back as empty strings.

    c = load_classification_from_extended(extended)
    assert isinstance(c, Classification)
    assert set(c.categories.keys()) == set(CATEGORIES)
    assert c.categories["identity"] == "Echo, 22.\n"
    assert c.categories["personality"] == "Quiet observer.\n"
    for cat in CATEGORIES:
        if cat not in {"identity", "personality"}:
            assert c.categories[cat] == ""

    # non_empty() reflects the LLM-tolerance signal
    assert set(c.non_empty().keys()) == {"identity", "personality"}


def test_load_classification_from_missing_dir_is_all_empty(tmp_path: Path):
    """If the extended/ dir doesn't exist yet, every category is empty —
    the typical state right after staging, before the agent has done its
    work."""
    missing = tmp_path / "no_such_dir"
    c = load_classification_from_extended(missing)
    assert all(v == "" for v in c.categories.values())
