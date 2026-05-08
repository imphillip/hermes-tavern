"""Sanity tests for the targets/ registry.

Step 1 of the SoulTavern migration: confirm the Hermes target is the
canonical source of truth for filenames / template names / budgets,
and that the legacy module-level constants (kept as backward-compat
aliases) match.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soultavern import library
from soultavern.cli import main
from soultavern.render import HERMES_BUDGET, SOUL_BUDGET
from soultavern.targets import (
    DEFAULT_TARGET,
    GENERIC,
    HERMES,
    OPENCLAW,
    TARGETS,
    Target,
)


def test_registry_resolves_hermes_by_name():
    assert "hermes" in TARGETS
    assert TARGETS["hermes"] is HERMES
    assert isinstance(TARGETS["hermes"], Target)


def test_registry_includes_all_targets():
    """All three targets registered. Hermes + OpenClaw functional in
    v1.0; generic still skeleton."""
    assert TARGETS["openclaw"] is OPENCLAW
    assert TARGETS["generic"] is GENERIC
    assert HERMES.implemented is True
    assert OPENCLAW.implemented is True
    assert GENERIC.implemented is False  # skeleton — lands later


def test_openclaw_target_uses_agents_md_as_companion():
    """OpenClaw's loader treats AGENTS.md as the primary project-context
    slot — opposite of Hermes which intentionally never writes it."""
    assert OPENCLAW.companion_filename == "AGENTS.md"
    assert OPENCLAW.soul_filename == "SOUL.md"


def test_generic_target_uses_index_md_as_companion():
    assert GENERIC.companion_filename == "index.md"
    assert GENERIC.soul_filename == "SOUL.md"


def test_default_target_is_hermes():
    """For step 1 the default target stays Hermes — the v0.5.x behavior
    is preserved when callers don't pass ``target=`` explicitly."""
    assert DEFAULT_TARGET is HERMES
    assert DEFAULT_TARGET.name == "hermes"


def test_hermes_target_preserves_v05x_constants():
    """The values folded into the Target dataclass must match what
    library / render exported as module-level constants in v0.5.x."""
    assert HERMES.soul_filename == "SOUL.md"
    assert HERMES.companion_filename == "HERMES.md"
    assert HERMES.soul_template == "SOUL.md.j2"
    assert HERMES.companion_template == "HERMES.md.j2"
    assert HERMES.curated_soul_template == "SOUL.md.curated.j2"
    assert HERMES.soul_budget == 19_000
    assert HERMES.companion_budget == 19_000
    assert HERMES.oversize_threshold == 15_000


def test_legacy_aliases_match_default_target():
    """Backward-compat aliases on render and library re-export the
    default target's values. Existing imports keep working."""
    assert SOUL_BUDGET == DEFAULT_TARGET.soul_budget
    assert HERMES_BUDGET == DEFAULT_TARGET.companion_budget
    assert library.OVERSIZE_THRESHOLD == DEFAULT_TARGET.oversize_threshold


def test_path_helpers_route_through_target(tmp_path):
    """``soul_path`` and ``hermes_path`` accept a target and produce
    target-specific paths. Default arg = HERMES (preserves v0.5.x)."""
    home = tmp_path
    assert library.soul_path(home) == home / "SOUL.md"
    assert library.hermes_path(home) == home / "HERMES.md"
    # Explicit target works too — same default for now.
    assert library.soul_path(home, HERMES) == home / "SOUL.md"
    assert library.hermes_path(home, HERMES) == home / "HERMES.md"


def test_target_is_frozen():
    """Targets are intended to be immutable singletons; the dataclass
    is frozen so accidental mutation raises."""
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        HERMES.name = "evil"  # type: ignore[misc]


# ---------- CLI --target routing ----------


def test_cli_default_target_is_hermes(
    tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str],
):
    """No --target flag → hermes target → write SOUL.md + HERMES.md as before."""
    home = tmp_path / "home"
    rc = main([
        "import",
        "--card", str(fixtures_dir / "v2_with_book.json"),
        "--home", str(home),
    ])
    assert rc == 0
    assert (home / "SOUL.md").exists()
    assert (home / "HERMES.md").exists()


def test_cli_explicit_hermes_target_works(
    tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str],
):
    home = tmp_path / "home"
    rc = main([
        "import",
        "--card", str(fixtures_dir / "v2_minimal.json"),
        "--home", str(home),
        "--target", "hermes",
    ])
    assert rc == 0
    assert (home / "SOUL.md").exists()


def test_cli_generic_target_rejected(tmp_path: Path, fixtures_dir: Path):
    """Generic is still a skeleton in v1.0 — must reject before doing
    any filesystem work."""
    home = tmp_path / "home"
    with pytest.raises(SystemExit) as exc:
        main([
            "import",
            "--card", str(fixtures_dir / "v2_minimal.json"),
            "--home", str(home),
            "--target", "generic",
        ])
    assert "generic" in str(exc.value)
    assert "not yet implemented" in str(exc.value)


def test_cli_unknown_target_rejected_by_argparse(
    tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str],
):
    """argparse handles `choices=` enforcement; the unknown name never
    reaches our handler."""
    home = tmp_path / "home"
    with pytest.raises(SystemExit) as exc:
        main([
            "import",
            "--card", str(fixtures_dir / "v2_minimal.json"),
            "--home", str(home),
            "--target", "doesnotexist",
        ])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice" in err
    assert "doesnotexist" in err


# ---------- ActiveRecord target round-trip + backward compat ----------


def test_active_record_persists_target(tmp_path: Path, fixtures_dir: Path):
    home = tmp_path / "home"
    library.import_card(home, fixtures_dir / "v2_minimal.json")
    record = library.read_active(home)
    assert record is not None
    assert record.target == "hermes"


def test_active_record_legacy_json_defaults_to_hermes(tmp_path: Path):
    """Records written by pre-v0.6.0 have no `target` key. Loading them
    must default to "hermes" rather than raising — that's what every
    existing user has on disk."""
    legacy = json.dumps({
        "name": "Aldous",
        "card_file": "Aldous_20260501T120000.json",
        "imported_at": "2026-05-01T12:00:00+00:00",
        "user_noun": "the visitor",
        "soul_only": False,
        "has_hermes_md": True,
        "trust_system_prompt": False,
        "finalized": False,
        "extended_dir": None,
        # NO "target" key — this is the legacy shape
    })
    record = library.ActiveRecord.from_json(legacy)
    assert record.target == "hermes"
    assert record.name == "Aldous"


def test_active_record_to_json_round_trip_preserves_target():
    record = library.ActiveRecord(
        name="X",
        card_file="X_20260101T000000.json",
        imported_at="2026-01-01T00:00:00+00:00",
        target="openclaw",  # deliberately non-default to confirm it survives
    )
    round_tripped = library.ActiveRecord.from_json(record.to_json())
    assert round_tripped.target == "openclaw"
