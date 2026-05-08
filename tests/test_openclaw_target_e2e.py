"""End-to-end tests for the OpenClaw target.

Covers the small-card flow (rendered SOUL fits, no agent
categorization), the oversized flow (stage → simulate agent →
finalize), the managed-section append/strip behavior on a real
AGENTS.md with user content, switch between targets, and delete /
revert cleanup.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soultavern import library
from soultavern.staging import NeedsAgentCategorizationError


# ---------- helpers ----------


def _bloated_payload(name: str = "Bloat") -> dict:
    return {
        "spec": "chara_card_v2",
        "data": {
            "name": name,
            "description": "x" * 12_000,  # over OpenClaw's 11k soul_budget
            "personality": "patient",
            "first_mes": "hi",
        },
    }


def _agent_phase(extended_dir: Path) -> None:
    """Simulate the agent's phase-2 work for an oversized card."""
    extended_dir.mkdir(parents=True, exist_ok=True)
    (extended_dir / "identity.md").write_text(
        "# Identity\n\nBloat is a stoic monolith.\n", "utf-8")
    (extended_dir / "personality.md").write_text(
        "# Personality\n\nReserved.\n", "utf-8")
    (extended_dir / "roleplay_guides.md").write_text(
        "# Roleplay Guidelines\n\nStay faithful.\n", "utf-8")


# ---------- small-card flow ----------


def test_openclaw_small_card_writes_three_files(home: Path, fixtures_dir: Path):
    """Small-card path on OpenClaw target: SOUL.md replace, AGENTS.md
    managed-section, IDENTITY.md replace."""
    from soultavern.targets import OPENCLAW

    outcome, lib_path = library.import_card(
        home, fixtures_dir / "v2_minimal.json", target=OPENCLAW,
    )
    assert outcome.finalized is False
    assert outcome.wrote_hermes_md is True

    assert (home / "SOUL.md").is_file()
    assert (home / "AGENTS.md").is_file()
    assert (home / "IDENTITY.md").is_file()
    # HERMES.md must NOT be written by OpenClaw target
    assert not (home / "HERMES.md").exists()

    record = library.read_active(home)
    assert record is not None
    assert record.target == "openclaw"


def test_openclaw_soul_md_has_no_identity_directive(home: Path, fixtures_dir: Path):
    """Verify SOUL.md is persona-body only — IDENTITY DIRECTIVE lives
    in AGENTS.md for OpenClaw."""
    from soultavern.targets import OPENCLAW

    library.import_card(home, fixtures_dir / "v2_minimal.json", target=OPENCLAW)
    soul = (home / "SOUL.md").read_text()
    assert "IDENTITY DIRECTIVE" not in soul
    assert "HIGHEST PRIORITY" not in soul


def test_openclaw_agents_md_has_identity_directive_in_managed_section(
    home: Path, fixtures_dir: Path,
):
    """The IDENTITY DIRECTIVE belongs in AGENTS.md, wrapped by the
    managed-section markers."""
    from soultavern.targets import OPENCLAW

    library.import_card(home, fixtures_dir / "v2_minimal.json", target=OPENCLAW)
    agents = (home / "AGENTS.md").read_text()
    assert "<!-- BEGIN soultavern:character -->" in agents
    assert "<!-- END soultavern:character -->" in agents
    # Active character header from _identity_directive.openclaw.j2
    assert "Active character: Echo" in agents
    assert "You are **Echo**" in agents
    # Operator-safety guarantee
    assert "Operator safety" in agents


def test_openclaw_identity_md_has_character_metadata(
    home: Path, fixtures_dir: Path,
):
    from soultavern.targets import OPENCLAW

    library.import_card(home, fixtures_dir / "v2_minimal.json", target=OPENCLAW)
    identity = (home / "IDENTITY.md").read_text()
    assert "Echo" in identity
    assert "roleplay character" in identity


# ---------- preserves user content in AGENTS.md ----------


def test_openclaw_preserves_user_agents_md_content(
    home: Path, fixtures_dir: Path,
):
    """If the user has existing AGENTS.md content (their own project
    setup), import must NOT destroy it. The managed section is added
    in addition; user content stays."""
    from soultavern.targets import OPENCLAW

    home.mkdir(parents=True, exist_ok=True)
    user_agents_md = (
        "# My personal AGENTS.md\n"
        "\n"
        "## My rules\n"
        "\n"
        "Always check the dev branch first.\n"
        "Never commit without tests.\n"
    )
    (home / "AGENTS.md").write_text(user_agents_md, "utf-8")

    library.import_card(
        home, fixtures_dir / "v2_minimal.json",
        target=OPENCLAW, overwrite=True,
    )

    agents = (home / "AGENTS.md").read_text()
    # User content survives
    assert "My personal AGENTS.md" in agents
    assert "Always check the dev branch first." in agents
    assert "Never commit without tests." in agents
    # Managed section also present
    assert "<!-- BEGIN soultavern:character -->" in agents
    assert "Active character: Echo" in agents


def test_openclaw_replaces_managed_section_on_reimport(
    home: Path, fixtures_dir: Path,
):
    """Importing a different card should replace the managed section,
    not duplicate it."""
    from soultavern.targets import OPENCLAW

    library.import_card(
        home, fixtures_dir / "v2_minimal.json", target=OPENCLAW,
    )
    library.import_card(
        home, fixtures_dir / "v2_full.json",
        target=OPENCLAW, overwrite=True,
    )

    agents = (home / "AGENTS.md").read_text()
    # Only one managed block (Marcellus replaced Echo)
    assert agents.count("<!-- BEGIN soultavern:character -->") == 1
    assert "Active character: Marcellus" in agents
    assert "Active character: Echo" not in agents


# ---------- delete cleans up ----------


def test_openclaw_delete_strips_managed_section_and_removes_extras(
    home: Path, fixtures_dir: Path,
):
    """Deleting the active OpenClaw card strips just the managed
    section from AGENTS.md, removes IDENTITY.md, and unlinks SOUL.md.
    User content in AGENTS.md outside the markers is preserved."""
    from soultavern.targets import OPENCLAW

    home.mkdir(parents=True, exist_ok=True)
    (home / "AGENTS.md").write_text(
        "# My AGENTS.md\n\nMy rules go here.\n", "utf-8",
    )

    library.import_card(
        home, fixtures_dir / "v2_minimal.json",
        target=OPENCLAW, overwrite=True,
    )
    assert (home / "SOUL.md").exists()
    assert (home / "IDENTITY.md").exists()

    library.delete_card(home, "Echo")

    # SOUL.md unlinked (target-owned)
    assert not (home / "SOUL.md").exists()
    # IDENTITY.md unlinked (target-owned extra)
    assert not (home / "IDENTITY.md").exists()
    # AGENTS.md still exists with just user content
    agents = (home / "AGENTS.md").read_text()
    assert "<!-- BEGIN soultavern:character -->" not in agents
    assert "Active character" not in agents
    assert "My AGENTS.md" in agents
    assert "My rules go here." in agents


def test_openclaw_delete_removes_agents_md_when_no_user_content(
    home: Path, tmp_path: Path,
):
    """When AGENTS.md was created entirely by SoulTavern (no user
    content), stripping the managed block leaves nothing — the file
    should be removed rather than leaving an empty file behind."""
    from soultavern.targets import OPENCLAW

    src = tmp_path / "card.json"
    src.write_text(json.dumps({
        "spec": "chara_card_v2",
        "data": {"name": "Solo", "description": "alone."},
    }), "utf-8")

    library.import_card(home, src, target=OPENCLAW)
    assert (home / "AGENTS.md").exists()

    library.delete_card(home, "Solo")
    assert not (home / "AGENTS.md").exists()


# ---------- oversized-card flow ----------


def test_openclaw_oversized_import_stages_then_finalize_assembles(
    home: Path, tmp_path: Path,
):
    """Same three-phase pattern as Hermes oversize, but finalize
    produces curated SOUL + AGENTS managed section + IDENTITY.md."""
    from soultavern.targets import OPENCLAW

    src = tmp_path / "bloat.json"
    src.write_text(json.dumps(_bloated_payload()), "utf-8")

    # Phase 1: staging
    with pytest.raises(NeedsAgentCategorizationError) as exc_info:
        library.import_card(home, src, target=OPENCLAW)
    extended_dir = exc_info.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)

    # Phase 3: finalize (target sticks via active record? actually no
    # — finalize_card needs explicit target since import didn't get
    # to write the active record)
    outcome = library.finalize_card(home, "Bloat", target=OPENCLAW)
    assert outcome.finalized is True

    # Three files written
    assert (home / "SOUL.md").is_file()
    assert (home / "AGENTS.md").is_file()
    assert (home / "IDENTITY.md").is_file()
    assert not (home / "HERMES.md").exists()

    # Curated SOUL has picks
    soul = (home / "SOUL.md").read_text()
    assert "Bloat is a stoic monolith." in soul
    assert "Reserved." in soul
    assert "Stay faithful." in soul
    # No IDENTITY DIRECTIVE in SOUL.md (it's in AGENTS.md)
    assert "IDENTITY DIRECTIVE" not in soul

    # AGENTS.md managed section has IDENTITY DIRECTIVE + index
    agents = (home / "AGENTS.md").read_text()
    assert "<!-- BEGIN soultavern:character -->" in agents
    assert "Active character: Bloat" in agents
    assert "Lore index" in agents
    # Lore index points at the agent's category files
    assert "extended/identity.md" in agents
    assert "extended/personality.md" in agents


# ---------- switch between targets ----------


def test_openclaw_switch_between_cards(home: Path, fixtures_dir: Path):
    """Switching cards on OpenClaw target replaces the managed section,
    preserves the rest of AGENTS.md, and rewrites SOUL.md + IDENTITY.md."""
    from soultavern.targets import OPENCLAW

    home.mkdir(parents=True, exist_ok=True)
    (home / "AGENTS.md").write_text(
        "# My setup\n\nUser rules here.\n", "utf-8",
    )

    library.import_card(
        home, fixtures_dir / "v2_minimal.json", target=OPENCLAW,
    )
    assert "Active character: Echo" in (home / "AGENTS.md").read_text()
    library.import_card(
        home, fixtures_dir / "v2_full.json",
        target=OPENCLAW, overwrite=True,
    )

    # Switch back to Echo via switch_to (target inherited from active record)
    library.switch_to(home, "Echo")

    agents = (home / "AGENTS.md").read_text()
    assert "Active character: Echo" in agents
    assert "Active character: Marcellus" not in agents
    # User rules survive every switch
    assert "User rules here." in agents


# ---------- CLI integration ----------


def test_cli_openclaw_target_writes_three_files(
    tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str],
):
    """`hermes-tavern import --target openclaw` produces SOUL +
    AGENTS managed section + IDENTITY.md."""
    from soultavern.cli import main

    home = tmp_path / "home"
    rc = main([
        "import",
        "--card", str(fixtures_dir / "v2_minimal.json"),
        "--home", str(home),
        "--target", "openclaw",
    ])
    assert rc == 0
    assert (home / "SOUL.md").exists()
    assert (home / "AGENTS.md").exists()
    assert (home / "IDENTITY.md").exists()
    # No HERMES.md
    assert not (home / "HERMES.md").exists()


def test_cli_current_shows_target_and_extras(
    tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str],
):
    from soultavern.cli import main

    home = tmp_path / "home"
    main([
        "import",
        "--card", str(fixtures_dir / "v2_minimal.json"),
        "--home", str(home),
        "--target", "openclaw",
    ])
    capsys.readouterr()
    main(["current", "--home", str(home)])
    out = capsys.readouterr().out
    assert "target:              openclaw" in out
    assert "SOUL.md:" in out
    assert "AGENTS.md:" in out
    assert "IDENTITY.md:" in out
