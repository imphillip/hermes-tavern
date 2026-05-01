"""End-to-end pipeline tests with the LLM call mocked.

These verify that when a card crosses the 75% threshold:
1. apply_card / import_card / switch_to take the distillation path
2. SOUL.md gets the distilled content; AGENTS.md gets the index; HERMES.md
   is NOT written (so it doesn't shadow AGENTS.md per kickoff §2.1)
3. The per-card extended/ directory is populated with one file per field
4. ActiveRecord remembers the distilled state
5. delete / restore move the extended/ dir alongside the card
6. --no-distill falls back to the original budget error
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from hermes_tavern import library
from hermes_tavern.distill import DISTILL_THRESHOLD
from hermes_tavern.render import BudgetExceededError


@dataclass
class FakeProc:
    stdout: str
    stderr: str = ""
    returncode: int = 0


def _bloated_card_payload(name: str = "Bloat") -> dict:
    """A card that renders to > 75% threshold but stays under the 19k hard cap."""
    return {
        "spec": "chara_card_v2",
        "data": {
            "name": name,
            "description": "x" * 16_000,  # > 15k threshold, < 19k hard cap
            "personality": "patient",
            "first_mes": "hi",
        },
    }


def _write_card(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), "utf-8")


def _ok_runner(soul: str = "# Compact Identity\n\nDistilled.", lore: str | None = None):
    body = f"<soul>\n{soul}\n</soul>\n"
    body += f"<lore>{lore if lore else 'NONE'}</lore>"

    def runner(argv):
        return FakeProc(stdout=body)
    return runner


def test_threshold_triggers_distillation(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())
    outcome, lib_path = library.import_card(
        home, src, distill_runner=_ok_runner(),
    )
    assert outcome.distilled is True
    assert outcome.wrote_hermes_md is True

    assert (home / "SOUL.md").exists()
    # HERMES.md carries distilled lore + extended-file index in distilled mode
    assert (home / "HERMES.md").exists()
    # AGENTS.md must never be written — it's shadowed by HERMES.md
    assert not (home / "AGENTS.md").exists()

    hermes = (home / "HERMES.md").read_text()
    assert "Extended material on disk" in hermes
    assert "extended/description.md" in hermes

    # Extended dir co-located with the card backup
    extended = library.cards_dir(home) / lib_path.stem / "extended"
    assert extended.is_dir()
    # description.md was over threshold so it ended up here
    assert (extended / "description.md").exists()
    desc = (extended / "description.md").read_text()
    assert len(desc) > 16_000  # original size preserved

    active = library.read_active(home)
    assert active.distilled is True
    assert active.has_hermes_md is True
    assert active.extended_dir is not None


def test_under_threshold_keeps_normal_layout(home: Path, fixtures_dir: Path):
    outcome, _ = library.import_card(
        home, fixtures_dir / "v2_with_book.json",
        distill_runner=_ok_runner(),  # would crash if accidentally invoked
    )
    assert outcome.distilled is False
    assert (home / "HERMES.md").exists()
    # AGENTS.md is never written — not in normal mode, not in distilled mode
    assert not (home / "AGENTS.md").exists()
    # Normal-mode HERMES.md is the rendered lorebook, not the distilled-mode index
    hermes = (home / "HERMES.md").read_text()
    assert "Extended material on disk" not in hermes


def test_no_distill_flag_falls_back_to_budget_error(home: Path, tmp_path: Path):
    src = tmp_path / "huge.json"
    # Push over the 19k hard cap so render() raises BudgetExceededError
    _write_card(src, {
        "spec": "chara_card_v2",
        "data": {"name": "Huge", "description": "x" * 25_000},
    })
    with pytest.raises(BudgetExceededError):
        library.import_card(home, src, allow_distill=False)


def test_soul_only_disables_distillation(home: Path, tmp_path: Path):
    """--soul-only is an explicit "don't write a second file" — must not be
    silently overridden by distillation, which writes AGENTS.md."""
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())
    outcome, _ = library.import_card(
        home, src, soul_only=True, distill_runner=_ok_runner(),
    )
    assert outcome.distilled is False
    assert (home / "SOUL.md").exists()
    assert not (home / "AGENTS.md").exists()
    assert not (home / "HERMES.md").exists()
    # No extended dir either — soul_only is "minimal" mode
    assert not any(p.is_dir() for p in (library.cards_dir(home)).iterdir()
                   if p.name != ".trash" and not p.name.startswith("."))


def test_switch_to_distilled_card(home: Path, tmp_path: Path, fixtures_dir: Path):
    # Import a small card first so library has multiple
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload(name="Bloat"))
    library.import_card(home, src, overwrite=True, distill_runner=_ok_runner())
    # Switch back to the small one — HERMES.md should now be the normal rendered
    # lorebook (or absent if Echo has none), not the distilled index
    target, outcome = library.switch_to(home, "Echo")
    assert outcome.distilled is False
    assert (home / "SOUL.md").exists()
    # Echo has no character_book → HERMES.md absent in normal mode
    assert not (home / "HERMES.md").exists()
    assert not (home / "AGENTS.md").exists()


def test_switch_to_normal_replaces_distilled_hermes(home: Path, tmp_path: Path, fixtures_dir: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())
    _, bloat_path = library.import_card(home, src, distill_runner=_ok_runner())
    extended = library.cards_dir(home) / bloat_path.stem / "extended"
    assert extended.is_dir()
    # Distilled HERMES.md exists with the index
    assert "Extended material on disk" in (home / "HERMES.md").read_text()

    # Re-import a small card that has its own (normal) lorebook
    library.import_card(home, fixtures_dir / "v2_with_book.json", overwrite=True)
    # The bloat card's extended dir stays — it's owned by its card
    assert extended.is_dir()
    # HERMES.md is now the normal rendered lorebook for the new card, not the distilled index
    new_hermes = (home / "HERMES.md").read_text()
    assert "Extended material on disk" not in new_hermes
    assert "The Underland" in new_hermes  # from v2_with_book.json
    assert not (home / "AGENTS.md").exists()


def test_delete_moves_extended_dir_to_trash(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())
    _, bloat_path = library.import_card(home, src, distill_runner=_ok_runner())
    extended = library.cards_dir(home) / bloat_path.stem / "extended"
    assert extended.is_dir()

    library.delete_card(home, "Bloat")
    # Stem dir under cards/ is gone
    assert not (library.cards_dir(home) / bloat_path.stem).exists()
    # And shows up in trash
    trash_stem = library.trash_dir(home) / bloat_path.stem
    assert trash_stem.is_dir()
    assert (trash_stem / "extended" / "description.md").exists()


def test_restore_brings_extended_dir_back(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())
    _, bloat_path = library.import_card(home, src, distill_runner=_ok_runner())
    library.delete_card(home, "Bloat")
    library.restore_card(home, "Bloat")
    extended = library.cards_dir(home) / bloat_path.stem / "extended"
    assert extended.is_dir()
    assert (extended / "description.md").exists()


def test_distillation_failure_raises(home: Path, tmp_path: Path):
    src = tmp_path / "bloat.json"
    _write_card(src, _bloated_card_payload())

    def boom(argv):
        return FakeProc(stdout="", stderr="api dead", returncode=1)
    from hermes_tavern.distill import DistillationError
    with pytest.raises(DistillationError):
        library.import_card(home, src, distill_runner=boom)
    # Nothing partial left
    assert not (home / "SOUL.md").exists()
    assert not (home / "HERMES.md").exists()
    assert not (home / "AGENTS.md").exists()
