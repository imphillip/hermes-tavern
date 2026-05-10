"""Render-only tests for the OpenClaw target's renderers.

v2.0: templates are Python functions on the Target object, not Jinja
files. These tests call the renderers directly and assert on the
output. Coverage matches the v1.x test file — same intents, new wiring.
"""

from __future__ import annotations

from soultavern.classify import Classification
from soultavern.targets import OPENCLAW
from soultavern.targets.openclaw import (
    _identity_directive,
    render_agents_managed_section,
    render_curated_soul,
    render_identity,
    render_soul,
)


# ---------- SOUL.md (openclaw) ----------


def test_openclaw_soul_renders_persona_body_without_identity_directive():
    """The IDENTITY DIRECTIVE belongs in AGENTS.md for OpenClaw,
    NOT in SOUL.md. The SOUL renderer should be persona-body only."""
    data = {
        "name": "Aldous",
        "description": "A bookish wandering scholar.",
        "personality": "Curious, patient.",
        "scenario": "On the road to {{user}}.",
    }
    out = render_soul(
        data=data,
        metadata=None,
        user_noun="the visitor",
        trust_system_prompt=False,
    )
    # Persona body present
    assert "Aldous" in out
    assert "bookish wandering scholar" in out
    assert "Curious, patient." in out
    # IDENTITY DIRECTIVE must NOT be in SOUL.md (it's in AGENTS.md)
    assert "IDENTITY DIRECTIVE" not in out
    assert "HIGHEST PRIORITY" not in out
    # Director's Notes (output style) should still be present
    assert "Director's Notes" in out
    # Substitution applied to source content
    assert "On the road to the visitor." in out


def test_openclaw_soul_points_at_agents_md_as_authority():
    """The footer should signal that AGENTS.md is the override
    authority — clarifies precedence to the model."""
    data = {"name": "Aldous", "description": "..."}
    out = render_soul(
        data=data, metadata=None, user_noun="the visitor",
        trust_system_prompt=False,
    )
    assert "AGENTS.md" in out
    assert "highest priority" in out.lower() or "AGENTS.md wins" in out


def test_openclaw_soul_renders_trust_banner():
    out = render_soul(
        data={"name": "X", "description": "..."},
        metadata=None, user_noun="the visitor",
        trust_system_prompt=False,
    )
    assert "Persona content boundary" in out


# ---------- AGENTS.md (openclaw, managed section) ----------


def test_openclaw_agents_renders_identity_directive():
    """The IDENTITY DIRECTIVE block must be included — that's the
    whole point of the AGENTS.md managed section."""
    out = render_agents_managed_section(
        char_name="Aldous",
        user_noun="the visitor",
        extended_files=[],
    )
    assert "Active character: Aldous" in out
    assert "You are **Aldous**" in out
    # Operator-safety-above-character section
    assert "Operator safety" in out
    assert "the visitor" in out


def test_openclaw_agents_renders_lore_index_when_files_present():
    from soultavern.extended import ExtendedFile

    files = [
        ExtendedFile("cards/x/extended/identity.md", "Identity",
                     "name, age, ethnicity, height, basic biographical facts"),
        ExtendedFile("cards/x/extended/lore/forest.md", "Forest",
                     "world detail"),
    ]
    out = render_agents_managed_section(
        char_name="Aldous", user_noun="the visitor",
        extended_files=files,
    )
    assert "Lore index" in out
    assert "cards/x/extended/identity.md" in out
    assert "cards/x/extended/lore/forest.md" in out


def test_openclaw_agents_skips_lore_section_when_no_files():
    out = render_agents_managed_section(
        char_name="Aldous", user_noun="the visitor", extended_files=[],
    )
    assert "Lore index" not in out


# ---------- IDENTITY.md (openclaw) ----------


def test_openclaw_identity_renders_metadata():
    out = render_identity(
        data={"name": "Aldous", "tags": ["scholar", "introvert"]},
        char_name="Aldous", user_noun="the visitor", avatar_path="",
    )
    assert "Aldous" in out
    assert "roleplay character" in out
    assert "scholar" in out
    assert "introvert" in out
    # Falls back when avatar empty
    assert "see source card backup" in out


def test_openclaw_identity_uses_avatar_path_when_provided():
    out = render_identity(
        data={"name": "Aldous"},
        char_name="Aldous", user_noun="the visitor",
        avatar_path="avatars/aldous.png",
    )
    assert "avatars/aldous.png" in out
    assert "see source card backup" not in out


# ---------- SOUL.md curated (openclaw) ----------


def test_openclaw_curated_soul_renders_picks_only():
    classification = Classification(categories={
        "identity": "Aldous, 42, scholar.",
        "appearance": "tall, gaunt",  # NOT picked — should not appear
        "personality": "patient, curious",
        "backstory": "studied at the university",  # NOT picked
        "scenario": "",
        "kinks": "",
        "roleplay_guides": "stay scholarly",
        "examples": "",
    })
    picks = {
        "identity": classification.categories["identity"],
        "personality": classification.categories["personality"],
        "roleplay_guides": classification.categories["roleplay_guides"],
    }
    out = render_curated_soul(
        data={"name": "Aldous"}, user_noun="the visitor", picks=picks,
    )
    # Picked categories appear
    assert "Aldous, 42, scholar." in out
    assert "patient, curious" in out
    assert "stay scholarly" in out
    # Non-picked categories DON'T appear
    assert "tall, gaunt" not in out
    assert "studied at the university" not in out
    # No IDENTITY DIRECTIVE (lives in AGENTS.md for OpenClaw)
    assert "IDENTITY DIRECTIVE" not in out


def test_openclaw_curated_soul_includes_directors_notes():
    out = render_curated_soul(
        data={"name": "X"}, user_noun="the visitor",
        picks={"identity": "X", "personality": "", "roleplay_guides": ""},
    )
    assert "Director's Notes" in out
    assert "first-person dialogue" in out


def test_openclaw_curated_soul_points_to_extended_files():
    """The footer hints that extended/ files exist and live behind
    AGENTS.md's index."""
    out = render_curated_soul(
        data={"name": "X"}, user_noun="the visitor",
        picks={"identity": "X.", "personality": "", "roleplay_guides": ""},
    )
    assert "extended/" in out
    assert "AGENTS.md" in out


# ---------- IDENTITY DIRECTIVE block ----------


def test_identity_directive_substitutes_char_and_user():
    out = _identity_directive("Aldous", "the visitor")
    assert "Aldous" in out
    assert "the visitor" in out
    assert "Operator safety" in out
    assert "MEMORY.md" in out
    assert "break character" in out
