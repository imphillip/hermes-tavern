"""End-to-end tests for the v0.4.5 oversized-card flow:

1. Stage with apply_card / import_card → NeedsAgentCategorizationError + on-disk source.md
2. Simulate the agent writing extended/<cat>.md
3. finalize_card assembles curated SOUL.md + indexed HERMES.md
4. Switching back to a finalized oversized card reuses extended/ — no re-staging
5. Delete / restore round-trip preserves source.md + extended/
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_tavern import library
from hermes_tavern.staging import NeedsAgentCategorizationError


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


def _write_card(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), "utf-8")


def _agent_phase(extended_dir: Path,
                 *,
                 identity: str = "Bloat is a stoic monolith.",
                 personality: str = "Reserved.",
                 roleplay_guides: str = "Stay faithful to source.",
                 appearance: str | None = None) -> None:
    """Simulate the agent writing V2 category files. The agent has its
    own discretion on which to write; mirror that by only touching the
    requested categories."""
    extended_dir.mkdir(parents=True, exist_ok=True)
    (extended_dir / "identity.md").write_text(
        f"# Identity\n\n{identity}\n", "utf-8")
    (extended_dir / "personality.md").write_text(
        f"# Personality\n\n{personality}\n", "utf-8")
    (extended_dir / "roleplay_guides.md").write_text(
        f"# Roleplay Guidelines\n\n{roleplay_guides}\n", "utf-8")
    if appearance is not None:
        (extended_dir / "appearance.md").write_text(
            f"# Appearance\n\n{appearance}\n", "utf-8")


def test_oversized_import_stages_then_finalize_assembles(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload())
    # Phase 1: staging
    with pytest.raises(NeedsAgentCategorizationError) as exc_info:
        library.import_card(home, src)
    source_md = exc_info.value.source_md_path
    assert source_md.is_file()
    extended_dir = source_md.parent / "extended"
    # The CLI also wrote per-entry payloads (none for this card → no greetings/lore subdirs)
    assert extended_dir.is_dir()

    # Phase 2: agent writes V2 category files. Route the bulk of the
    # source content into appearance.md (extended-only), keeping the
    # curated SOUL.md picks compact.
    _agent_phase(extended_dir, appearance="x" * 16_000)

    # Phase 3: finalize
    outcome = library.finalize_card(home, "Bloat")
    assert outcome.finalized is True
    assert outcome.extended_files >= 4  # identity, personality, roleplay_guides, appearance

    soul = (home / "SOUL.md").read_text()
    # Curated picks
    assert "Bloat is a stoic monolith." in soul
    assert "Reserved." in soul
    assert "Stay faithful to source." in soul

    hermes = (home / "HERMES.md").read_text()
    assert "Extended material on disk" in hermes
    assert "extended/identity.md" in hermes
    assert "extended/appearance.md" in hermes
    # AGENTS.md must never be written
    assert not (home / "AGENTS.md").exists()

    active = library.read_active(home)
    assert active is not None
    assert active.finalized is True
    assert active.extended_dir is not None


def test_finalize_without_agent_work_raises(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload())
    with pytest.raises(NeedsAgentCategorizationError):
        library.import_card(home, src)
    # Don't write any extended/<cat>.md — finalize should refuse.
    with pytest.raises(library.LibraryError) as exc_info:
        library.finalize_card(home, "Bloat")
    assert "no agent categorization" in str(exc_info.value)


def test_switch_to_finalized_card_reuses_extended(home: Path, tmp_path: Path,
                                                  fixtures_dir: Path):
    # Set up: a small card and a finalized oversized card.
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload(name="Bloat"))
    with pytest.raises(NeedsAgentCategorizationError) as exc:
        library.import_card(home, src, overwrite=True)
    extended_dir = exc.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)
    library.finalize_card(home, "Bloat")
    assert (home / "SOUL.md").read_text().count("monolith") == 1

    # Switch back to the small card.
    library.switch_to(home, "Echo")
    assert "Echo" in (home / "SOUL.md").read_text()

    # Switch back to Bloat. Should reuse extended/ — no re-staging needed.
    target, outcome = library.switch_to(home, "Bloat")
    assert outcome.finalized is True
    assert "monolith" in (home / "SOUL.md").read_text()


def test_switch_to_unfinalized_oversize_raises(home: Path, tmp_path: Path,
                                               fixtures_dir: Path):
    """If extended/ is missing the V2 categories (e.g. user deleted them),
    switch_to falls back to the staging path and raises."""
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload(name="Bloat"))
    with pytest.raises(NeedsAgentCategorizationError) as exc:
        library.import_card(home, src, overwrite=True)
    extended_dir = exc.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)
    library.finalize_card(home, "Bloat")

    # User wipes the agent's work
    import shutil
    shutil.rmtree(extended_dir)
    # Now switching back triggers staging again
    with pytest.raises(NeedsAgentCategorizationError):
        library.switch_to(home, "Bloat")


def test_delete_moves_per_card_dir_to_trash(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload())
    with pytest.raises(NeedsAgentCategorizationError) as exc:
        library.import_card(home, src)
    extended_dir = exc.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)
    library.finalize_card(home, "Bloat")

    bloat_stem = next(p for p in (home / "cards").iterdir()
                      if p.is_dir() and p.name.startswith("Bloat")).name
    library.delete_card(home, "Bloat")
    assert not (home / "cards" / bloat_stem).exists()
    trash_stem = library.trash_dir(home) / bloat_stem
    assert (trash_stem / "extended" / "identity.md").is_file()
    assert (trash_stem / "source.md").is_file()


def test_restore_brings_per_card_dir_back(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload())
    with pytest.raises(NeedsAgentCategorizationError) as exc:
        library.import_card(home, src)
    extended_dir = exc.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)
    library.finalize_card(home, "Bloat")

    library.delete_card(home, "Bloat")
    library.restore_card(home, "Bloat")
    bloat_stem = next(p for p in (home / "cards").iterdir()
                      if p.is_dir() and p.name.startswith("Bloat")).name
    assert (home / "cards" / bloat_stem / "extended" / "identity.md").is_file()


def test_apply_card_with_existing_extended_finalizes_in_place(home: Path,
                                                              tmp_path: Path):
    """If an oversized card is re-applied (e.g. via switch) and extended/
    already has agent work, apply_card behaves like finalize without
    re-raising."""
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_payload())
    with pytest.raises(NeedsAgentCategorizationError) as exc:
        library.import_card(home, src)
    extended_dir = exc.value.source_md_path.parent / "extended"
    _agent_phase(extended_dir)

    # Calling apply_card directly on the library copy now succeeds.
    library_path = next(p for p in (home / "cards").iterdir()
                        if p.is_file() and p.name.startswith("Bloat"))
    outcome = library.apply_card(home, library_path, overwrite=True)
    assert outcome.finalized is True
    assert (home / "SOUL.md").exists()
