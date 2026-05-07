"""Card library inside ``<HERMES_HOME>/cards/``.

Layout (small cards — fits in always-on context as-is)::

    <HERMES_HOME>/
    ├── SOUL.md                 # active persona (rendered)
    ├── HERMES.md               # active world (rendered, optional)
    └── cards/
        ├── .active.json        # pointer to currently active card
        ├── .trash/             # soft-deleted cards
        └── <name>_<ts>.<ext>   # imported card payload

Layout (oversized cards — requires agent V2 categorization)::

    <HERMES_HOME>/
    ├── SOUL.md                 # curated persona (identity + personality + roleplay_guides)
    ├── HERMES.md               # index pointing into extended/
    └── cards/
        ├── .active.json
        ├── <name>_<ts>.<ext>   # source card
        └── <name>_<ts>/
            ├── source.md       # CLI-staged input for the agent
            └── extended/
                ├── identity.md ... examples.md   # agent-written V2 categories
                ├── alternate_greetings/01.md ... # CLI-staged at import time
                └── lore/<entry>.md ...           # CLI-staged at import time

The flow on oversize is:

1. ``import_card`` copies the card into the library and calls ``apply_card``.
2. ``apply_card`` detects that the rendered SOUL.md / HERMES.md would
   exceed the always-on budget. It writes ``source.md`` plus the
   per-entry payloads, then raises :class:`NeedsAgentCategorizationError`.
3. The agent (working from the SKILL.md procedure) reads ``source.md``
   and writes one ``extended/<category>.md`` per V2 category.
4. The user runs ``hermes-tavern finalize``, which calls
   :func:`finalize_card` here to assemble the curated SOUL.md and the
   indexed HERMES.md from the on-disk material.

HermesTavern intentionally **never writes AGENTS.md, MEMORY.md, or
USER.md**. AGENTS.md is shadowed by HERMES.md per Hermes's loader
priority; MEMORY.md and USER.md are owned by the agent itself.

Note: SOUL.md is read relative to HERMES_HOME, but HERMES.md is read
relative to **cwd** at hermes startup. Users must launch hermes from
inside HERMES_HOME (``cd $HERMES_HOME && hermes``) for HERMES.md to be
picked up. This is documented prominently in the README and SKILL.md.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import classify as classify_mod
from . import extended as extended_mod
from . import render as render_mod
from . import snapshots as snap_mod
from . import staging as staging_mod
from .parse import load_card
from .render import BudgetExceededError, RenderResult, render
from .snapshots import Snapshot
from .staging import NeedsAgentCategorizationError
from .targets import DEFAULT_TARGET, Target

# Re-export so callers don't need to reach into staging.
__all__ = [
    "ActiveRecord",
    "AlreadyExistsError",
    "AmbiguousCardError",
    "ApplyOutcome",
    "CardEntry",
    "CardNotFoundError",
    "DEFAULT_USER_NOUN",
    "LibraryError",
    "NeedsAgentCategorizationError",
    "apply_card",
    "cards_dir",
    "clear_active",
    "copy_into_library",
    "delete_card",
    "ensure_layout",
    "find_card",
    "finalize_card",
    "get_meta",
    "hermes_path",
    "import_card",
    "list_cards",
    "list_history",
    "read_active",
    "restore_card",
    "revert_to",
    "soul_path",
    "switch_to",
    "trash_dir",
    "write_active",
    "write_outputs",
]

DEFAULT_USER_NOUN = "the visitor"
# Backwards-compatible alias — internal code paths consult a Target
# (currently always DEFAULT_TARGET / Hermes), but tests and external
# callers may still import this directly.
OVERSIZE_THRESHOLD = DEFAULT_TARGET.oversize_threshold

_ACTIVE_FILE = ".active.json"
_TRASH_DIR = ".trash"
_CARD_SUFFIXES = {".json", ".png", ".yaml", ".yml"}
_NAME_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


class LibraryError(Exception):
    """Raised when a library operation cannot be completed."""


class CardNotFoundError(LibraryError):
    pass


class AmbiguousCardError(LibraryError):
    pass


class AlreadyExistsError(LibraryError):
    pass


@dataclass
class ActiveRecord:
    name: str
    card_file: str
    imported_at: str
    user_noun: str = DEFAULT_USER_NOUN
    soul_only: bool = False
    has_hermes_md: bool = False
    trust_system_prompt: bool = False
    finalized: bool = False  # True iff this card went through the agent categorization flow
    extended_dir: str | None = None  # relative to home
    target: str = "hermes"  # which runtime target wrote SOUL/companion files

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> ActiveRecord:
        payload = json.loads(text)
        return cls(
            name=payload["name"],
            card_file=payload["card_file"],
            imported_at=payload["imported_at"],
            user_noun=payload.get("user_noun", DEFAULT_USER_NOUN),
            soul_only=payload.get("soul_only", False),
            has_hermes_md=payload.get("has_hermes_md", False),
            trust_system_prompt=payload.get("trust_system_prompt", False),
            # accept legacy `distilled` key as the same signal
            finalized=payload.get("finalized", payload.get("distilled", False)),
            extended_dir=payload.get("extended_dir"),
            # legacy active records without a target field were all hermes
            target=payload.get("target", "hermes"),
        )


@dataclass
class CardEntry:
    file: str
    name: str
    imported_at: str | None
    active: bool
    trashed: bool


def cards_dir(home: Path) -> Path:
    return home / "cards"


def trash_dir(home: Path) -> Path:
    return cards_dir(home) / _TRASH_DIR


def soul_path(home: Path, target: Target = DEFAULT_TARGET) -> Path:
    return home / target.soul_filename


def hermes_path(home: Path, target: Target = DEFAULT_TARGET) -> Path:
    """Path to the rendered companion file (lorebook + index).

    Name kept as ``hermes_path`` for backward compat; conceptually this
    is the companion file, named per ``target.companion_filename``. The
    function will be renamed to ``companion_path`` when the package
    itself is renamed in step 4 of the SoulTavern migration.
    """
    return home / target.companion_filename


def _target_for(name: str) -> Target:
    """Look up a target by name with a default fallback to Hermes.

    Used internally when reading legacy ActiveRecord values that may
    have been written before the ``target`` field existed.
    """
    from .targets import TARGETS  # local to avoid module-cycle nag
    return TARGETS.get(name, DEFAULT_TARGET)


def _extended_dir_for(card_file: str, home: Path) -> Path:
    return cards_dir(home) / Path(card_file).stem / "extended"


def _stem_dir_for(card_file: str, home: Path) -> Path:
    """Parent of the extended/ dir — the per-card directory inside cards/."""
    return cards_dir(home) / Path(card_file).stem


def _has_agent_categorization(extended_dir: Path) -> bool:
    """True iff at least one V2 category file exists in extended/. Used
    to distinguish ``apply_card`` re-runs after the agent has populated
    extended/ from cold imports that still need the agent."""
    if not extended_dir.is_dir():
        return False
    return any(
        (extended_dir / f"{cat}.md").is_file()
        for cat in classify_mod.CATEGORIES
    )


def _active_path(home: Path) -> Path:
    return cards_dir(home) / _ACTIVE_FILE


def ensure_layout(home: Path) -> None:
    cards_dir(home).mkdir(parents=True, exist_ok=True)
    trash_dir(home).mkdir(parents=True, exist_ok=True)


def read_active(home: Path) -> ActiveRecord | None:
    path = _active_path(home)
    if not path.exists():
        return None
    try:
        return ActiveRecord.from_json(path.read_text("utf-8"))
    except (OSError, ValueError, KeyError):
        return None


def write_active(home: Path, record: ActiveRecord) -> None:
    ensure_layout(home)
    _active_path(home).write_text(record.to_json(), "utf-8")


def clear_active(home: Path) -> None:
    path = _active_path(home)
    if path.exists():
        path.unlink()


def _safe_filename(name: str, suffix: str, when: datetime) -> str:
    base = _NAME_SAFE.sub("_", name.strip()) or "card"
    stamp = when.strftime("%Y%m%dT%H%M%S")
    return f"{base}_{stamp}{suffix.lower()}"


def list_cards(home: Path, *, include_trash: bool = False) -> list[CardEntry]:
    """List all cards in the library, sorted by filename."""
    ensure_layout(home)
    active = read_active(home)
    active_file = active.card_file if active else None
    entries: list[CardEntry] = []
    for path in sorted(cards_dir(home).iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in _CARD_SUFFIXES:
            continue
        entries.append(_describe(path, active_file=active_file, trashed=False))
    if include_trash and trash_dir(home).exists():
        for path in sorted(trash_dir(home).iterdir()):
            if path.suffix.lower() not in _CARD_SUFFIXES:
                continue
            entries.append(_describe(path, active_file=None, trashed=True))
    return entries


def _describe(path: Path, *, active_file: str | None, trashed: bool) -> CardEntry:
    name = ""
    imported_at: str | None = None
    try:
        data = load_card(path)
        name = (data.get("name") or "").strip()
    except Exception:
        pass
    match = re.search(r"_(\d{8}T\d{6})", path.stem)
    if match:
        imported_at = match.group(1)
    return CardEntry(
        file=path.name,
        name=name or path.stem,
        imported_at=imported_at,
        active=(not trashed) and (active_file == path.name),
        trashed=trashed,
    )


def find_card(home: Path, query: str, *, in_trash: bool = False) -> Path:
    """Locate a card by exact filename or by case-insensitive name/stem match."""
    base = trash_dir(home) if in_trash else cards_dir(home)
    if not base.exists():
        raise CardNotFoundError(f"no library at {base}")
    direct = base / query
    if direct.is_file():
        return direct
    q = query.casefold()
    matches: list[Path] = []
    for path in base.iterdir():
        if path.is_dir() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in _CARD_SUFFIXES:
            continue
        if path.name.casefold() == q or path.stem.casefold() == q:
            return path
        try:
            data = load_card(path)
            name = (data.get("name") or "").strip().casefold()
        except Exception:
            name = ""
        if name == q or path.stem.casefold().startswith(q) or (name and name.startswith(q)):
            matches.append(path)
    if not matches:
        where = "trash" if in_trash else "library"
        raise CardNotFoundError(f"no card matching {query!r} in {where}")
    if len(matches) > 1:
        joined = ", ".join(p.name for p in matches)
        raise AmbiguousCardError(f"{query!r} matches multiple cards: {joined}")
    return matches[0]


def copy_into_library(home: Path, src: Path, *, name: str) -> Path:
    """Copy ``src`` into the cards/ directory, returning the destination path."""
    ensure_layout(home)
    dest_name = _safe_filename(name, src.suffix, datetime.now(timezone.utc))
    dest = cards_dir(home) / dest_name
    shutil.copy2(src, dest)
    return dest


@dataclass
class ApplyOutcome:
    """Returned by :func:`apply_card` and :func:`finalize_card`. Captures
    what was actually written so the CLI can render an accurate one-screen
    summary."""

    rendered: RenderResult
    wrote_hermes_md: bool
    finalized: bool = False
    curated_soul_size: int | None = None
    extended_files: int = 0


def _check_no_existing(home: Path, *paths: Path) -> None:
    existing = [p.name for p in paths if p.exists()]
    if existing:
        raise AlreadyExistsError(
            f"{', '.join(existing)} already exist; pass --overwrite to replace"
        )


def _write_outputs_normal(
    home: Path,
    rendered: RenderResult,
    *,
    overwrite: bool,
    write_hermes: bool,
    target: Target = DEFAULT_TARGET,
) -> bool:
    """Normal-mode write: SOUL.md + optional companion file."""
    soul = soul_path(home, target)
    hermes = hermes_path(home, target)
    if not overwrite:
        _check_no_existing(home, soul, hermes)
    home.mkdir(parents=True, exist_ok=True)
    soul.write_text(rendered.soul, "utf-8")
    wrote_hermes = False
    if write_hermes and rendered.hermes is not None:
        hermes.write_text(rendered.hermes, "utf-8")
        wrote_hermes = True
    elif hermes.exists() and overwrite and (not write_hermes or rendered.hermes is None):
        hermes.unlink()
    return wrote_hermes


# Public alias kept for the existing test that imports it directly.
def write_outputs(
    home: Path,
    rendered: RenderResult,
    *,
    overwrite: bool,
    write_hermes: bool,
    target: Target = DEFAULT_TARGET,
) -> bool:
    return _write_outputs_normal(
        home, rendered, overwrite=overwrite, write_hermes=write_hermes, target=target,
    )


def _write_outputs_finalized(
    home: Path,
    *,
    soul: str,
    hermes: str,
    overwrite: bool,
    target: Target = DEFAULT_TARGET,
) -> None:
    """Finalize-mode write: curated SOUL.md + indexed companion file."""
    soul_p = soul_path(home, target)
    hermes_p = hermes_path(home, target)
    if not overwrite:
        _check_no_existing(home, soul_p, hermes_p)
    home.mkdir(parents=True, exist_ok=True)
    soul_p.write_text(soul, "utf-8")
    hermes_p.write_text(hermes, "utf-8")


def apply_card(
    home: Path,
    card_path: Path,
    *,
    user_noun: str = DEFAULT_USER_NOUN,
    soul_only: bool = False,
    overwrite: bool = False,
    trust_system_prompt: bool = False,
    action: str = "apply",
    target: Target = DEFAULT_TARGET,
) -> ApplyOutcome:
    """Render and write SOUL.md / HERMES.md for ``card_path``.

    Three exit paths:

    1. **Fits in always-on context** (≤ target.oversize_threshold per
       slot) → render directly, write SOUL + companion file, return
       ``ApplyOutcome``.
    2. **Oversized but extended/ already populated by the agent** →
       behave like ``finalize_card`` (assemble from on-disk material).
       This is what ``switch_to`` hits when re-activating an already-
       finalized oversized card.
    3. **Oversized, no agent work yet** → write ``source.md`` and the
       per-entry payloads to ``cards/<stem>/``, then raise
       :class:`NeedsAgentCategorizationError`. The CLI converts that to
       exit code 2 plus a message pointing at the SKILL.md procedure.

    Captures a pristine snapshot on first invocation, then a snapshot
    after the mutation completes — allowing later ``revert`` operations.
    """
    snap_mod.ensure_pristine(
        home, soul=soul_path(home, target), hermes=hermes_path(home, target),
    )

    data = load_card(card_path)
    rendered = render(
        data,
        user_noun=user_noun,
        include_hermes_md=not soul_only,
        trust_system_prompt=trust_system_prompt,
        enforce_budget=False,
        target=target,
    )
    char_name = (data.get("name") or card_path.stem).strip()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    is_oversized = (
        not soul_only and (
            len(rendered.soul) > target.oversize_threshold
            or (rendered.hermes is not None and len(rendered.hermes) > target.oversize_threshold)
        )
    )

    if not is_oversized:
        if len(rendered.soul) > target.soul_budget:
            raise BudgetExceededError(
                target.soul_filename, len(rendered.soul), target.soul_budget,
            )
        if rendered.hermes is not None and len(rendered.hermes) > target.companion_budget:
            raise BudgetExceededError(
                target.companion_filename,
                len(rendered.hermes),
                target.companion_budget,
            )
        wrote_hermes = _write_outputs_normal(
            home, rendered, overwrite=overwrite, write_hermes=not soul_only,
            target=target,
        )
        record = ActiveRecord(
            name=char_name,
            card_file=card_path.name,
            imported_at=now,
            user_noun=user_noun,
            soul_only=soul_only,
            has_hermes_md=wrote_hermes,
            trust_system_prompt=trust_system_prompt,
            finalized=False,
            target=target.name,
        )
        write_active(home, record)
        snap_mod.take_snapshot(
            home,
            action=action,
            name=char_name,
            card_file=card_path.name,
            soul=soul_path(home, target),
            hermes=hermes_path(home, target),
            active_record=asdict(record),
        )
        return ApplyOutcome(rendered=rendered, wrote_hermes_md=wrote_hermes, finalized=False)

    # Oversized. If the agent has already written V2 categories, finalize
    # straight from disk (this is the switch_to-an-already-finalized path).
    extended_dir = _extended_dir_for(card_path.name, home)
    if _has_agent_categorization(extended_dir):
        return _finalize_in_place(
            home,
            card_path=card_path,
            data=data,
            rendered=rendered,
            user_noun=user_noun,
            trust_system_prompt=trust_system_prompt,
            overwrite=overwrite,
            action=action,
            now=now,
            target=target,
        )

    # Cold oversize: stage source.md + per-entry payloads, raise.
    source_md = staging_mod.write_source_md(
        extended_dir, data,
        char_name=char_name, user_noun=user_noun,
    )
    rendered_size = max(
        len(rendered.soul),
        len(rendered.hermes) if rendered.hermes is not None else 0,
    )
    raise NeedsAgentCategorizationError(
        char_name=char_name,
        source_md_path=source_md,
        rendered_size=rendered_size,
        threshold=target.oversize_threshold,
    )


def _finalize_in_place(
    home: Path,
    *,
    card_path: Path,
    data: dict[str, Any],
    rendered: RenderResult,
    user_noun: str,
    trust_system_prompt: bool,
    overwrite: bool,
    action: str,
    now: str,
    target: Target = DEFAULT_TARGET,
) -> ApplyOutcome:
    """Shared assembly step for ``apply_card`` (re-run after agent work)
    and ``finalize_card`` (explicit finalize invocation)."""
    char_name = (data.get("name") or card_path.stem).strip()
    extended_dir = _extended_dir_for(card_path.name, home)

    classification = classify_mod.load_classification_from_extended(extended_dir)
    soul_md = render_mod.render_curated_soul(
        char_name, classification, user_noun=user_noun, target=target,
    )
    extended_files = extended_mod.collect_extended_files(home, extended_dir, char_name)
    hermes_md = extended_mod.render_indexed_hermes_md(char_name, extended_files)

    _write_outputs_finalized(
        home, soul=soul_md, hermes=hermes_md, overwrite=overwrite, target=target,
    )

    record = ActiveRecord(
        name=char_name,
        card_file=card_path.name,
        imported_at=now,
        user_noun=user_noun,
        soul_only=False,
        has_hermes_md=True,
        trust_system_prompt=trust_system_prompt,
        finalized=True,
        extended_dir=str(extended_dir.relative_to(home)),
        target=target.name,
    )
    write_active(home, record)
    snap_mod.take_snapshot(
        home,
        action=action,
        name=char_name,
        card_file=card_path.name,
        soul=soul_path(home, target),
        hermes=hermes_path(home, target),
        active_record=asdict(record),
    )
    return ApplyOutcome(
        rendered=rendered,
        wrote_hermes_md=True,
        finalized=True,
        curated_soul_size=len(soul_md),
        extended_files=len(extended_files),
    )


def finalize_card(
    home: Path,
    query: str,
    *,
    user_noun: str = DEFAULT_USER_NOUN,
    trust_system_prompt: bool = False,
    overwrite: bool = True,
    action: str = "finalize",
    target: Target = DEFAULT_TARGET,
) -> ApplyOutcome:
    """Assemble curated SOUL.md + indexed companion file from
    agent-written ``extended/<category>.md`` files. Default
    ``overwrite=True`` because finalize is the natural completion of an
    oversize import that already placed staging artifacts on disk.

    Raises :class:`LibraryError` if the agent hasn't written any V2
    category files yet — the operator probably skipped the agent step.
    """
    snap_mod.ensure_pristine(
        home, soul=soul_path(home, target), hermes=hermes_path(home, target),
    )

    card_path = find_card(home, query)
    extended_dir = _extended_dir_for(card_path.name, home)
    if not _has_agent_categorization(extended_dir):
        raise LibraryError(
            f"no agent categorization found in {extended_dir}; expected at "
            "least one of identity.md/personality.md/etc. — see SKILL.md "
            "'Oversized card procedure'."
        )

    data = load_card(card_path)
    rendered = render(
        data, user_noun=user_noun, include_hermes_md=True,
        trust_system_prompt=trust_system_prompt, enforce_budget=False,
        target=target,
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return _finalize_in_place(
        home,
        card_path=card_path,
        data=data,
        rendered=rendered,
        user_noun=user_noun,
        trust_system_prompt=trust_system_prompt,
        overwrite=overwrite,
        action=action,
        now=now,
        target=target,
    )


def import_card(
    home: Path,
    src: Path,
    *,
    user_noun: str = DEFAULT_USER_NOUN,
    soul_only: bool = False,
    overwrite: bool = False,
    trust_system_prompt: bool = False,
    target: Target = DEFAULT_TARGET,
) -> tuple[ApplyOutcome, Path]:
    """Copy ``src`` into the library and apply it as the active persona.

    For oversized cards this propagates :class:`NeedsAgentCategorizationError`
    after staging — the source card is left in the library, the staging
    artifacts (source.md, lorebook payloads) are written, and the CLI
    surfaces the agent procedure to the user.
    """
    data = load_card(src)
    name = (data.get("name") or src.stem).strip()
    library_path = copy_into_library(home, src, name=name)
    outcome = apply_card(
        home,
        library_path,
        user_noun=user_noun,
        soul_only=soul_only,
        overwrite=overwrite,
        trust_system_prompt=trust_system_prompt,
        action="import",
        target=target,
    )
    return outcome, library_path


def delete_card(home: Path, query: str) -> Path:
    """Soft-delete a card by moving it to ``cards/.trash/``.

    The card's per-card directory (``cards/<stem>/``, holding ``extended/``
    + ``source.md``) is moved alongside the card payload so restore brings
    everything back.
    """
    ensure_layout(home)
    src = find_card(home, query)
    dest = trash_dir(home) / src.name
    if dest.exists():
        dest.unlink()
    shutil.move(str(src), str(dest))
    stem_dir = _stem_dir_for(src.name, home)
    if stem_dir.is_dir():
        trash_stem = trash_dir(home) / stem_dir.name
        if trash_stem.exists():
            shutil.rmtree(trash_stem)
        shutil.move(str(stem_dir), str(trash_stem))
    active = read_active(home)
    if active and active.card_file == src.name:
        clear_active(home)
    return dest


def restore_card(home: Path, query: str) -> Path:
    """Move a card from ``cards/.trash/`` back into the library."""
    ensure_layout(home)
    src = find_card(home, query, in_trash=True)
    dest = cards_dir(home) / src.name
    if dest.exists():
        raise AlreadyExistsError(
            f"{dest.name} already exists in the library; remove it first"
        )
    shutil.move(str(src), str(dest))
    trash_stem = trash_dir(home) / Path(src.name).stem
    if trash_stem.is_dir():
        live_stem = _stem_dir_for(src.name, home)
        if live_stem.exists():
            shutil.rmtree(live_stem)
        shutil.move(str(trash_stem), str(live_stem))
    return dest


def switch_to(
    home: Path,
    query: str,
    *,
    user_noun: str | None = None,
    soul_only: bool | None = None,
    trust_system_prompt: bool | None = None,
    target: Target | None = None,
) -> tuple[Path, ApplyOutcome]:
    """Switch the active persona to a card already in the library.

    Switching always overwrites SOUL.md / companion. If the card is
    oversized but its ``extended/`` is already populated (from a prior
    finalize), the switch reuses those files. If it's oversized and not
    yet finalized, :class:`NeedsAgentCategorizationError` propagates.

    ``target`` defaults to the previously-active record's target, or to
    :data:`DEFAULT_TARGET` if no prior record exists. Pass an explicit
    target to override.
    """
    card_path = find_card(home, query)
    previous = read_active(home)
    chosen_user = user_noun or (previous.user_noun if previous else DEFAULT_USER_NOUN)
    chosen_soul_only = soul_only if soul_only is not None else (
        previous.soul_only if previous else False
    )
    chosen_trust = trust_system_prompt if trust_system_prompt is not None else (
        previous.trust_system_prompt if previous else False
    )
    chosen_target = target if target is not None else (
        _target_for(previous.target) if previous else DEFAULT_TARGET
    )
    outcome = apply_card(
        home,
        card_path,
        user_noun=chosen_user,
        soul_only=chosen_soul_only,
        overwrite=True,
        trust_system_prompt=chosen_trust,
        action="switch",
        target=chosen_target,
    )
    return card_path, outcome


def get_meta(card_path: Path) -> dict[str, Any]:
    """Best-effort parse for status display; never raises."""
    try:
        return load_card(card_path)
    except Exception:
        return {}


def list_history(home: Path) -> list[Snapshot]:
    """Chronological list of SOUL.md / HERMES.md snapshots."""
    return snap_mod.list_snapshots(home)


def revert_to(home: Path, query: str) -> Snapshot:
    """Restore SOUL.md / HERMES.md from a snapshot named by ``query``.

    ``query`` may be ``"pristine"``, ``"previous"``, a numeric snapshot
    id, or a case-insensitive name prefix. The current state is replaced
    in-place — including correctly removing live files when the target
    snapshot didn't have them. The active record is restored from the
    snapshot's manifest, or cleared if the target had none. The revert
    itself is recorded as a new snapshot for history continuity.
    """
    target = snap_mod.find_snapshot(home, query)
    snap_mod.restore_files(target, home, soul=soul_path(home), hermes=hermes_path(home))

    if target.active_record:
        record = ActiveRecord(
            **{
                k: target.active_record.get(k)
                for k in ActiveRecord.__dataclass_fields__
            }
        )
        write_active(home, record)
    else:
        clear_active(home)

    snap_mod.take_snapshot(
        home,
        action="revert",
        name=f"revert→{target.id}/{target.name}",
        card_file=target.card_file,
        soul=soul_path(home),
        hermes=hermes_path(home),
        active_record=target.active_record,
    )
    return target
