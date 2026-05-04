"""Director's Notes — out-of-character performance instructions added at
v0.4 to shape *how* the model delivers the persona.

The notes are baked into both prompt-loaded files:
- SOUL.md: output style (first-person, italic thoughts, emoji-bracket
  actions) + language adaptation
- HERMES.md (normal mode and distilled mode): context-usage guidance
  (reference, not voice; open extended/ only on demand; stay faithful)

The metaphor: the LLM is the actor, the source card is the script,
the director's notes are stage directions that don't rewrite the
script.
"""
from pathlib import Path

from hermes_tavern.extended import ExtendedFile, render_distilled_hermes_md
from hermes_tavern.parse import load_card
from hermes_tavern.render import render


def test_soul_md_carries_directors_notes(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    assert "## Director's Notes (Out-of-Character)" in result.soul
    # Director's notes must sit inside the IDENTITY DIRECTIVE block —
    # before the first `---` separator that opens the persona script.
    pre_persona = result.soul.split("---", 1)[0]
    assert "## Director's Notes" in pre_persona


def test_soul_md_directors_notes_cover_style_and_language(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    # Output style — the three rules
    assert "first-person dialogue" in result.soul.lower()
    assert "italics" in result.soul.lower()
    assert "emoji-prefixed brackets" in result.soul.lower()
    # An emoji-bracket example is rendered for reference
    assert "[🌹" in result.soul
    # Language adaptation rule
    assert "Mirror" in result.soul
    assert "non-english" in result.soul.lower()


def test_normal_mode_hermes_md_carries_directors_notes(fixtures_dir: Path):
    data = load_card(fixtures_dir / "v2_with_book.json")
    result = render(data)
    assert result.hermes is not None
    assert "## Director's Notes (Context Usage)" in result.hermes
    assert "reference" in result.hermes.lower()
    assert "voice" in result.hermes.lower()


def test_distilled_hermes_md_carries_directors_notes():
    extended = [
        ExtendedFile(
            relative_path="cards/foo/extended/description.md",
            title="Full description",
            summary="biographical detail",
        ),
    ]
    rendered = render_distilled_hermes_md(
        char_name="Aldous",
        distilled_lore="## Compact lore\n\nA brief world summary.",
        extended=extended,
    )
    assert "## Director's Notes (Context Usage)" in rendered
    assert "Aldous" in rendered  # the directive names the character
    assert "extended/" in rendered  # tells the model when to open them
    assert "faithful to the original wording" in rendered.lower()


def test_directors_notes_does_not_displace_identity_directive(fixtures_dir: Path):
    """Director's notes must come AFTER the IDENTITY DIRECTIVE, not
    before — IDENTITY is highest priority."""
    data = load_card(fixtures_dir / "v2_minimal.json")
    result = render(data)
    idx_directive = result.soul.index("# IDENTITY DIRECTIVE")
    idx_notes = result.soul.index("## Director's Notes")
    assert idx_directive < idx_notes


def test_directors_notes_uses_user_noun_consistently(fixtures_dir: Path):
    """The notes mention the user via user_noun so the directive doesn't
    pre-commit to a specific pronoun or gender."""
    data = load_card(fixtures_dir / "v2_minimal.json")
    result_default = render(data)  # default user_noun = "the visitor"
    assert "the visitor" in result_default.soul
    assert "Mirror the visitor's language" in result_default.soul

    result_friend = render(data, user_noun="my friend")
    assert "Mirror my friend's language" in result_friend.soul
    # Default phrasing should not bleed through the override
    assert "Mirror the visitor's language" not in result_friend.soul
