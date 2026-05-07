"""Sanity tests for the targets/ registry.

Step 1 of the SoulTavern migration: confirm the Hermes target is the
canonical source of truth for filenames / template names / budgets,
and that the legacy module-level constants (kept as backward-compat
aliases) match.
"""

from __future__ import annotations

from hermes_tavern import library
from hermes_tavern.render import HERMES_BUDGET, SOUL_BUDGET
from hermes_tavern.targets import DEFAULT_TARGET, HERMES, TARGETS, Target


def test_registry_resolves_hermes_by_name():
    assert "hermes" in TARGETS
    assert TARGETS["hermes"] is HERMES
    assert isinstance(TARGETS["hermes"], Target)


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
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        HERMES.name = "evil"  # type: ignore[misc]
