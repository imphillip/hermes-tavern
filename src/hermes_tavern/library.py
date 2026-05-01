"""Card library inside ``<HERMES_HOME>/cards/``.

Layout (normal mode)::

    <HERMES_HOME>/
    ├── SOUL.md                 # active persona (rendered)
    ├── HERMES.md               # active world (rendered, optional)
    └── cards/
        ├── .active.json        # pointer to currently active card
        ├── .trash/             # soft-deleted cards
        └── <name>_<ts>.<ext>   # imported card payloads

Layout (distillation mode — triggered when SOUL or HERMES would exceed
75% of the Hermes 20k slot)::

    <HERMES_HOME>/
    ├── SOUL.md                 # LLM-distilled persona (compact)
    ├── HERMES.md               # distilled lore + index pointing to extended/
    └── cards/
        ├── .active.json
        ├── <name>_<ts>.<ext>
        └── <name>_<ts>/extended/
            ├── description.md
            ├── alternate_greetings/01.md ...
            ├── mes_example.md
            └── lore/<entry>.md

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

from . import distill as distill_mod
from . import extended as extended_mod
from .parse import load_card
from .render import SOUL_BUDGET, BudgetExceededError, RenderResult, render

DEFAULT_USER_NOUN = "the visitor"
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
    distilled: bool = False
    extended_dir: str | None = None  # relative to home

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
            distilled=payload.get("distilled", False),
            extended_dir=payload.get("extended_dir"),
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


def soul_path(home: Path) -> Path:
    return home / "SOUL.md"


def hermes_path(home: Path) -> Path:
    return home / "HERMES.md"


def _extended_dir_for(card_file: str, home: Path) -> Path:
    return cards_dir(home) / Path(card_file).stem / "extended"


def _stem_dir_for(card_file: str, home: Path) -> Path:
    """Parent of the extended/ dir — the per-card directory inside cards/."""
    return cards_dir(home) / Path(card_file).stem


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
    """Returned by :func:`apply_card`. Captures what was actually written so
    the CLI can render an accurate one-screen summary."""

    rendered: RenderResult
    wrote_hermes_md: bool
    distilled: bool = False
    distilled_soul_size: int | None = None
    distilled_lore_size: int | None = None
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
) -> bool:
    """Normal-mode write: SOUL.md + optional HERMES.md."""
    soul = soul_path(home)
    hermes = hermes_path(home)
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
) -> bool:
    return _write_outputs_normal(home, rendered, overwrite=overwrite, write_hermes=write_hermes)


def _write_outputs_distilled(
    home: Path,
    *,
    soul: str,
    hermes: str,
    overwrite: bool,
) -> None:
    """Distilled-mode write: SOUL.md + HERMES.md (with distilled lore + index).

    AGENTS.md is intentionally never written — Hermes shadows it with
    HERMES.md, so the references must live inside HERMES.md to reach the
    model.
    """
    soul_p = soul_path(home)
    hermes_p = hermes_path(home)
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
    allow_distill: bool = True,
    distill_command: str = distill_mod.DEFAULT_DISTILL_CMD,
    distill_runner: object | None = None,
) -> ApplyOutcome:
    """Render and write SOUL/HERMES (and AGENTS+extended in distilled mode)."""
    data = load_card(card_path)
    # Render without budget enforcement so oversized output can still flow
    # into the distillation pipeline; we re-impose the hard cap manually
    # below for the non-distilled path.
    rendered = render(
        data,
        user_noun=user_noun,
        include_hermes_md=not soul_only,
        trust_system_prompt=trust_system_prompt,
        enforce_budget=False,
    )
    char_name = (data.get("name") or card_path.stem).strip()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    should_distill = (
        allow_distill
        and not soul_only  # --soul-only opts out of the agents/extended layout
        and distill_mod.needs_distillation(rendered.soul, rendered.hermes)
    )

    if not should_distill:
        # Hard cap still applies on the non-distilled path: refuse to write
        # something Hermes can't load.
        if len(rendered.soul) > SOUL_BUDGET:
            raise BudgetExceededError("SOUL.md", len(rendered.soul), SOUL_BUDGET)
        if rendered.hermes is not None and len(rendered.hermes) > SOUL_BUDGET:
            raise BudgetExceededError("HERMES.md", len(rendered.hermes), SOUL_BUDGET)
        wrote_hermes = _write_outputs_normal(
            home, rendered, overwrite=overwrite, write_hermes=not soul_only
        )
        record = ActiveRecord(
            name=char_name,
            card_file=card_path.name,
            imported_at=now,
            user_noun=user_noun,
            soul_only=soul_only,
            has_hermes_md=wrote_hermes,
            trust_system_prompt=trust_system_prompt,
            distilled=False,
        )
        write_active(home, record)
        return ApplyOutcome(rendered=rendered, wrote_hermes_md=wrote_hermes, distilled=False)

    # Distillation path.
    distilled = distill_mod.distill(
        rendered.soul,
        rendered.hermes,
        char_name=char_name,
        command=distill_command,
        runner=distill_runner,
    )

    extended_dir = _extended_dir_for(card_path.name, home)
    # Replace any prior extended/ dir for this same card.
    if extended_dir.exists():
        shutil.rmtree(extended_dir)
    files = extended_mod.write_extended(home, extended_dir, data, user_noun=user_noun)
    hermes_md = extended_mod.render_distilled_hermes_md(char_name, distilled.lore, files)

    _write_outputs_distilled(home, soul=distilled.soul, hermes=hermes_md, overwrite=overwrite)

    record = ActiveRecord(
        name=char_name,
        card_file=card_path.name,
        imported_at=now,
        user_noun=user_noun,
        soul_only=False,
        has_hermes_md=True,
        trust_system_prompt=trust_system_prompt,
        distilled=True,
        extended_dir=str(extended_dir.relative_to(home)),
    )
    write_active(home, record)
    return ApplyOutcome(
        rendered=rendered,
        wrote_hermes_md=True,
        distilled=True,
        distilled_soul_size=len(distilled.soul),
        distilled_lore_size=len(distilled.lore) if distilled.lore else None,
        extended_files=len(files),
    )


def import_card(
    home: Path,
    src: Path,
    *,
    user_noun: str = DEFAULT_USER_NOUN,
    soul_only: bool = False,
    overwrite: bool = False,
    trust_system_prompt: bool = False,
    allow_distill: bool = True,
    distill_command: str = distill_mod.DEFAULT_DISTILL_CMD,
    distill_runner: object | None = None,
) -> tuple[ApplyOutcome, Path]:
    """Copy ``src`` into the library and apply it as the active persona."""
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
        allow_distill=allow_distill,
        distill_command=distill_command,
        distill_runner=distill_runner,
    )
    return outcome, library_path


def delete_card(home: Path, query: str) -> Path:
    """Soft-delete a card by moving it to ``cards/.trash/``.

    The card's per-card directory (``cards/<stem>/``, holding ``extended/``)
    is moved alongside the card payload so restore brings everything back.
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
    allow_distill: bool = True,
    distill_command: str = distill_mod.DEFAULT_DISTILL_CMD,
    distill_runner: object | None = None,
) -> tuple[Path, ApplyOutcome]:
    """Switch the active persona to a card already in the library.

    Switching always overwrites SOUL.md / HERMES.md (that is its whole point).
    If ``user_noun`` / ``soul_only`` / ``trust_system_prompt`` are omitted,
    reuse the previous active record's values when available, otherwise fall
    back to defaults.
    """
    target = find_card(home, query)
    previous = read_active(home)
    chosen_user = user_noun or (previous.user_noun if previous else DEFAULT_USER_NOUN)
    chosen_soul_only = soul_only if soul_only is not None else (
        previous.soul_only if previous else False
    )
    chosen_trust = trust_system_prompt if trust_system_prompt is not None else (
        previous.trust_system_prompt if previous else False
    )
    outcome = apply_card(
        home,
        target,
        user_noun=chosen_user,
        soul_only=chosen_soul_only,
        overwrite=True,
        trust_system_prompt=chosen_trust,
        allow_distill=allow_distill,
        distill_command=distill_command,
        distill_runner=distill_runner,
    )
    return target, outcome


def get_meta(card_path: Path) -> dict[str, Any]:
    """Best-effort parse for status display; never raises."""
    try:
        return load_card(card_path)
    except Exception:
        return {}
