"""Snapshot history: pristine capture, post-mutation snapshots, and
revert (incl. the critical case of reverting to a pristine state where
no SOUL.md / HERMES.md existed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soultavern import library, snapshots


def test_first_import_creates_pristine_then_snapshot(home: Path, fixtures_dir: Path):
    """Importing into an empty HERMES_HOME captures pristine (no files)
    and a post-import snapshot."""
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    history = library.list_history(home)
    assert len(history) == 2
    assert history[0].action == "pristine"
    assert history[0].has_soul_md is False
    assert history[0].has_hermes_md is False
    assert history[1].action == "import"
    assert history[1].has_soul_md is True
    # v2_minimal has no character_book
    assert history[1].has_hermes_md is False


def test_pristine_captures_pre_existing_files(home: Path, fixtures_dir: Path):
    """If SOUL.md / HERMES.md exist before HermesTavern's first write,
    pristine snapshot must preserve them."""
    (home / "SOUL.md").write_text("# Pre-existing custom SOUL\n")
    (home / "HERMES.md").write_text("# Pre-existing custom HERMES\n")
    library.import_card(home, fixtures_dir / "v2_with_book.json", overwrite=True)
    history = library.list_history(home)
    assert history[0].action == "pristine"
    assert history[0].has_soul_md is True
    assert history[0].has_hermes_md is True
    # Pristine snapshot directory contains the original files
    pristine_dir = snapshots.snapshots_dir(home) / history[0].dir_name
    assert "Pre-existing custom SOUL" in (pristine_dir / "SOUL.md").read_text()


def test_revert_to_pristine_removes_live_files_when_pristine_was_empty(
    home: Path, fixtures_dir: Path
):
    """Critical: reverting to an empty pristine snapshot must DELETE the
    live SOUL.md / HERMES.md, not write empty content."""
    library.import_card(home, fixtures_dir / "v2_with_book.json")
    assert (home / "SOUL.md").exists()
    assert (home / "HERMES.md").exists()
    library.revert_to(home, "pristine")
    assert not (home / "SOUL.md").exists()
    assert not (home / "HERMES.md").exists()
    # Active record cleared
    assert library.read_active(home) is None


def test_revert_to_pristine_restores_pre_existing_content(
    home: Path, fixtures_dir: Path
):
    """Pristine that captured pre-existing files must restore them on revert."""
    (home / "SOUL.md").write_text("# Original\n")
    library.import_card(home, fixtures_dir / "v2_minimal.json", overwrite=True)
    library.revert_to(home, "pristine")
    assert (home / "SOUL.md").read_text() == "# Original\n"
    assert not (home / "HERMES.md").exists()


def test_revert_previous_jumps_one_back(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    # 0001 pristine, 0002 Echo, 0003 Marcellus  → previous = 0002 (Echo)
    target = library.revert_to(home, "previous")
    assert target.name == "Echo"
    assert "Echo" in (home / "SOUL.md").read_text()
    active = library.read_active(home)
    assert active is not None and active.name == "Echo"


def test_revert_by_id(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    library.revert_to(home, "0002")
    assert "Echo" in (home / "SOUL.md").read_text()


def test_revert_by_name_prefix(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    library.revert_to(home, "Marc")  # prefix of "Marcellus"
    assert "Marcellus" in (home / "SOUL.md").read_text()


def test_revert_records_itself_as_a_snapshot(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    history_before = library.list_history(home)
    library.revert_to(home, "Echo")
    history_after = library.list_history(home)
    assert len(history_after) == len(history_before) + 1
    assert history_after[-1].action == "revert"


def test_history_grows_chronologically(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_with_book.json", overwrite=True)
    snaps = library.list_history(home)
    ids = [s.id for s in snaps]
    assert ids == sorted(ids)
    actions = [s.action for s in snaps]
    assert actions[0] == "pristine"
    assert actions[1] == "import"
    assert actions[2] == "import"


def test_switch_records_switch_action(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    library.switch_to(home, "Echo")
    history = library.list_history(home)
    assert history[-1].action == "switch"
    assert history[-1].name == "Echo"


def test_revert_pristine_when_only_pristine_exists_is_noop(home: Path):
    """Synthesise a pristine-only history (e.g. after `revert --to pristine`
    plus some manual cleanup), ensure revert to pristine still works."""
    snapshots.ensure_pristine(home, soul=home / "SOUL.md", hermes=home / "HERMES.md")
    target = library.revert_to(home, "pristine")
    assert target.action == "pristine"
    # Now there's pristine + revert in history
    assert len(library.list_history(home)) == 2


def test_revert_unknown_id_raises(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    with pytest.raises(snapshots.SnapshotError):
        library.revert_to(home, "9999")


def test_previous_with_only_pristine_raises(home: Path):
    snapshots.ensure_pristine(home, soul=home / "SOUL.md", hermes=home / "HERMES.md")
    with pytest.raises(snapshots.SnapshotError):
        library.revert_to(home, "previous")


def test_snapshot_manifest_round_trip(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    snaps = library.list_history(home)
    manifest_path = snapshots.snapshots_dir(home) / snaps[1].dir_name / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    assert payload["action"] == "import"
    assert payload["name"] == "Echo"
    assert payload["active_record"]["name"] == "Echo"


def test_finalize_path_also_snapshots(home: Path, tmp_path: Path):
    """Snapshots fire for the agent-driven oversized-card pipeline too:
    one snapshot at finalize time, capturing curated SOUL.md + indexed
    HERMES.md."""
    import pytest as _pytest

    from soultavern.staging import NeedsAgentCategorizationError

    big = tmp_path / "big.json"
    big.write_text(
        '{"spec": "chara_card_v2", "data": {"name": "Big", "description": "'
        + "x" * 16_000 + '"}}'
    )

    # Phase 1 stages source.md and raises (no snapshot yet — nothing was
    # written into the home root).
    with _pytest.raises(NeedsAgentCategorizationError) as exc_info:
        library.import_card(home, big)
    extended_dir = exc_info.value.source_md_path.parent / "extended"

    # Phase 2: simulate the agent
    extended_dir.mkdir(parents=True, exist_ok=True)
    (extended_dir / "identity.md").write_text("# Identity\n\nBig.\n", "utf-8")

    # Phase 3: finalize — this is the snapshotting moment
    library.finalize_card(home, "Big")

    history = library.list_history(home)
    assert len(history) == 2
    assert history[0].action == "pristine"
    assert history[1].action == "finalize"
    assert history[1].has_soul_md is True
    assert history[1].has_hermes_md is True  # finalize always writes HERMES.md
