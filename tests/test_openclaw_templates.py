"""Render-only tests for the OpenClaw target's Jinja templates.

These verify the templates produce sensible output in isolation —
before library integration plumbs them into apply_card / finalize.
The templates render via the same env as the Hermes side
(``render._env``), so substitution / sanitization filters apply
identically.
"""

from __future__ import annotations

from soultavern.classify import Classification
from soultavern.render import _env
from soultavern.targets import OPENCLAW


# ---------- SOUL.md.openclaw.j2 ----------


def test_openclaw_soul_renders_persona_body_without_identity_directive():
    """The IDENTITY DIRECTIVE belongs in AGENTS.md for OpenClaw,
    NOT in SOUL.md. The SOUL template should be persona-body only."""
    data = {
        "name": "Aldous",
        "description": "A bookish wandering scholar.",
        "personality": "Curious, patient.",
        "scenario": "On the road to {{user}}.",
    }
    env = _env(data["name"], "the visitor")
    out = env.get_template(OPENCLAW.soul_template).render(
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
    # Substitution applied to source content (the literal `{{user}}` in
    # the footer is intentional, teaching the model the convention)
    assert "On the road to the visitor." in out


def test_openclaw_soul_points_at_agents_md_as_authority():
    """The footer should signal that AGENTS.md is the override
    authority — clarifies precedence to the model."""
    data = {"name": "Aldous", "description": "..."}
    env = _env(data["name"], "the visitor")
    out = env.get_template(OPENCLAW.soul_template).render(
        data=data, metadata=None, user_noun="the visitor",
        trust_system_prompt=False,
    )
    assert "AGENTS.md" in out
    assert "highest priority" in out.lower() or "AGENTS.md wins" in out


def test_openclaw_soul_renders_trust_banner():
    data = {"name": "X", "description": "..."}
    env = _env("X", "the visitor")
    out = env.get_template(OPENCLAW.soul_template).render(
        data=data, metadata=None, user_noun="the visitor",
        trust_system_prompt=False,
    )
    assert "Persona content boundary" in out


# ---------- AGENTS.md.openclaw.j2 ----------


def test_openclaw_agents_renders_identity_directive():
    """The IDENTITY DIRECTIVE partial must be included — that's the
    whole point of the AGENTS.md managed section."""
    env = _env("Aldous", "the visitor")
    out = env.get_template(OPENCLAW.companion_template).render(
        char_name="Aldous",
        user_noun="the visitor",
        extended_files=[],
    )
    assert "Active character: Aldous" in out
    assert "You are **Aldous**" in out
    # Operator-safety-above-character section
    assert "Operator safety" in out
    # Substitution: char_name and user_noun should both appear
    assert "Aldous" in out
    assert "the visitor" in out


def test_openclaw_agents_renders_lore_index_when_files_present():
    from soultavern.extended import ExtendedFile

    files = [
        ExtendedFile("cards/x/extended/identity.md", "Identity",
                     "name, age, ethnicity, height, basic biographical facts"),
        ExtendedFile("cards/x/extended/lore/forest.md", "Forest",
                     "world detail"),
    ]
    env = _env("Aldous", "the visitor")
    out = env.get_template(OPENCLAW.companion_template).render(
        char_name="Aldous", user_noun="the visitor",
        extended_files=files,
    )
    assert "Lore index" in out
    assert "cards/x/extended/identity.md" in out
    assert "cards/x/extended/lore/forest.md" in out


def test_openclaw_agents_skips_lore_section_when_no_files():
    env = _env("Aldous", "the visitor")
    out = env.get_template(OPENCLAW.companion_template).render(
        char_name="Aldous", user_noun="the visitor", extended_files=[],
    )
    assert "Lore index" not in out


# ---------- IDENTITY.md.openclaw.j2 ----------


def test_openclaw_identity_renders_metadata():
    data = {"name": "Aldous", "tags": ["scholar", "introvert"]}
    env = _env("Aldous", "the visitor")
    out = env.get_template("IDENTITY.md.openclaw.j2").render(
        data=data, avatar_path="",
    )
    assert "Aldous" in out
    assert "roleplay character" in out
    assert "scholar" in out
    assert "introvert" in out
    # Falls back when avatar empty
    assert "see source card backup" in out


def test_openclaw_identity_uses_avatar_path_when_provided():
    data = {"name": "Aldous"}
    env = _env("Aldous", "the visitor")
    out = env.get_template("IDENTITY.md.openclaw.j2").render(
        data=data, avatar_path="avatars/aldous.png",
    )
    assert "avatars/aldous.png" in out
    assert "see source card backup" not in out


# ---------- SOUL.md.curated.openclaw.j2 ----------


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
    env = _env("Aldous", "the visitor")
    picks = {
        "identity": classification.categories["identity"],
        "personality": classification.categories["personality"],
        "roleplay_guides": classification.categories["roleplay_guides"],
    }
    out = env.get_template(OPENCLAW.curated_soul_template).render(
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
    """Output style still belongs in SOUL.md regardless of curated vs
    full render — these guide voice, not framing."""
    env = _env("X", "the visitor")
    out = env.get_template(OPENCLAW.curated_soul_template).render(
        data={"name": "X"}, user_noun="the visitor",
        picks={"identity": "X", "personality": "", "roleplay_guides": ""},
    )
    assert "Director's Notes" in out
    assert "first-person dialogue" in out


def test_openclaw_curated_soul_points_to_extended_files():
    """The footer hints that extended/ files exist and live behind
    AGENTS.md's index — same pattern as Hermes curated SOUL but the
    file authority differs."""
    env = _env("X", "the visitor")
    out = env.get_template(OPENCLAW.curated_soul_template).render(
        data={"name": "X"}, user_noun="the visitor",
        picks={"identity": "X.", "personality": "", "roleplay_guides": ""},
    )
    assert "extended/" in out
    assert "AGENTS.md" in out


# ---------- partial: _identity_directive.openclaw.j2 ----------


def test_identity_directive_partial_substitutes_char_and_user():
    env = _env("Aldous", "the visitor")
    out = env.get_template("_identity_directive.openclaw.j2").render(
        char_name="Aldous", user_noun="the visitor",
    )
    assert "Aldous" in out
    assert "the visitor" in out
    # Three required pieces
    assert "Operator safety" in out
    assert "MEMORY.md" in out
    assert "break character" in out
