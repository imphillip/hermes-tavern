from pathlib import Path

import pytest

from soultavern import library


def test_import_creates_layout(home: Path, fixtures_dir: Path):
    outcome, lib_path = library.import_card(
        home, fixtures_dir / "v2_with_book.json"
    )
    assert (home / "SOUL.md").exists()
    assert (home / "HERMES.md").exists()
    assert outcome.wrote_hermes_md is True
    assert lib_path.parent == library.cards_dir(home)
    active = library.read_active(home)
    assert active is not None
    assert active.name == "Lyra"
    assert active.has_hermes_md is True
    assert active.finalized is False


def test_import_minimal_no_hermes(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    assert (home / "SOUL.md").exists()
    assert not (home / "HERMES.md").exists()


def test_overwrite_required(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    with pytest.raises(library.AlreadyExistsError):
        library.import_card(home, fixtures_dir / "v2_full.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    assert "Marcellus" in (home / "SOUL.md").read_text()


def test_list_marks_active(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    cards = library.list_cards(home)
    assert len(cards) == 2
    actives = [c for c in cards if c.active]
    assert len(actives) == 1
    assert actives[0].name == "Marcellus"


def test_switch_by_name(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_full.json", overwrite=True)
    target, _outcome = library.switch_to(home, "Echo")
    assert "Echo" in target.name
    assert "Echo" in (home / "SOUL.md").read_text()
    active = library.read_active(home)
    assert active.name == "Echo"


def test_overwrite_drops_stale_hermes_md(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_with_book.json")
    assert (home / "HERMES.md").exists()
    library.import_card(home, fixtures_dir / "v2_minimal.json", overwrite=True)
    assert not (home / "HERMES.md").exists()


def test_switch_drops_stale_hermes_md(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.import_card(home, fixtures_dir / "v2_with_book.json", overwrite=True)
    assert (home / "HERMES.md").exists()
    library.switch_to(home, "Echo")
    assert not (home / "HERMES.md").exists()


def test_delete_moves_to_trash(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    dest = library.delete_card(home, "Echo")
    assert dest.parent == library.trash_dir(home)
    # Active record cleared because deleted card was active
    assert library.read_active(home) is None
    # SOUL.md left in place per spec
    assert (home / "SOUL.md").exists()


def test_restore_brings_card_back(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.delete_card(home, "Echo")
    restored = library.restore_card(home, "Echo")
    assert restored.parent == library.cards_dir(home)
    assert restored.exists()


def test_restore_refuses_overwrite(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    library.delete_card(home, "Echo")
    # Re-import a different card with same eventual name
    library.import_card(home, fixtures_dir / "v2_minimal.json", overwrite=True)
    # Now restoring would clash with the live one — same filename only if timestamps collide
    # Synthesise the collision by copying the live card name into trash
    live = next(library.cards_dir(home).glob("Echo_*.json"))
    fake_trash = library.trash_dir(home) / live.name
    import shutil
    shutil.copy(live, fake_trash)
    with pytest.raises(library.AlreadyExistsError):
        library.restore_card(home, fake_trash.name)


def test_find_card_ambiguous(home: Path, fixtures_dir: Path):
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    # Force a second card whose name also starts with "E"
    import shutil
    src = next(library.cards_dir(home).glob("Echo_*.json"))
    twin = src.with_name(src.name.replace("Echo", "Echobis"))
    shutil.copy(src, twin)
    with pytest.raises(library.AmbiguousCardError):
        library.find_card(home, "Echo")
