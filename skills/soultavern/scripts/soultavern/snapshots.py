"""Per-mutation snapshot history of every agent file SoulTavern touches.

Every ``import`` / ``switch`` captures the resulting on-disk state into
``<home>/cards/.snapshots/<NNNN>_<ts>_<name>/``. Before the very
first mutation, a special ``pristine`` snapshot records the
pre-SoulTavern state — which may legitimately mean "no agent files
existed".

``revert`` restores any of these snapshots, correctly removing live
files when the target snapshot didn't have them.

Coverage (v2.0+): every file any registered target might write is
captured on every snapshot — currently SOUL.md, HERMES.md, AGENTS.md,
IDENTITY.md. This makes cross-target reverts predictable: if the user
ran openclaw then switched to hermes then reverted to pristine, the
pre-SoulTavern AGENTS.md / IDENTITY.md content (or absence) is fully
restored along with SOUL.md / HERMES.md.

Layout::

    <home>/cards/.snapshots/
    ├── 0001_pristine/
    │   ├── manifest.json
    │   ├── SOUL.md          (if it existed pre-SoulTavern)
    │   ├── HERMES.md        (ditto, hermes target)
    │   ├── AGENTS.md        (ditto, openclaw target — full file)
    │   └── IDENTITY.md      (ditto, openclaw target)
    ├── 0002_20260502T130000_Aldous/
    │   ├── manifest.json
    │   └── (whichever managed files existed at snap time)
    └── ...

Backward compatibility: legacy manifests written by pre-v2.0 versions
captured only SOUL.md + HERMES.md and lacked the ``target`` /
``captured`` fields. ``Snapshot.from_json`` upgrades them on read —
``target`` defaults to ``"hermes"``, ``captured`` is derived from
``has_soul_md`` / ``has_hermes_md``. The legacy snap-dir layout is
read unchanged.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SNAPSHOTS_DIR_NAME = ".snapshots"
PRISTINE = "pristine"
_SLUG_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_DIR_RE = re.compile(r"^(\d{4})_")


class SnapshotError(Exception):
    pass


@dataclass
class Snapshot:
    id: str               # zero-padded 4-digit sequence number
    created_at: str       # ISO UTC, second precision
    action: str           # "pristine" | "import" | "switch" | "revert"
    name: str             # character name, or "pristine"
    card_file: str | None
    has_soul_md: bool     # legacy field; mirrors captured["SOUL.md"]
    has_hermes_md: bool   # legacy field; mirrors captured["HERMES.md"]
    active_record: dict[str, Any] | None = None
    # v2.0 additions:
    target: str = "hermes"
    # `captured` keys are filenames (relative to home), values mark
    # whether the file existed on disk at snap time. Restore uses this
    # dict — files marked True are copied from snap_dir; files marked
    # False are unlinked from live position. Files not in the dict are
    # left untouched.
    captured: dict[str, bool] = field(default_factory=dict)

    @property
    def dir_name(self) -> str:
        if self.action == "pristine":
            return f"{self.id}_pristine"
        slug = _SLUG_RE.sub("_", self.name).strip("_") or "snap"
        ts_short = self.created_at.replace(":", "").replace("-", "").split("+")[0]
        return f"{self.id}_{ts_short}_{slug}"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Snapshot:
        payload = json.loads(text)
        # Back-compat: legacy manifests pre-v2.0 lack `target` and
        # `captured`. Derive them from the has_* flags so the rest of
        # the code can treat all snapshots uniformly.
        if "target" not in payload:
            payload["target"] = "hermes"
        if "captured" not in payload:
            payload["captured"] = {
                "SOUL.md": bool(payload.get("has_soul_md")),
                "HERMES.md": bool(payload.get("has_hermes_md")),
            }
        fields = {k: payload.get(k) for k in cls.__dataclass_fields__}
        return cls(**fields)  # type: ignore[arg-type]


def snapshots_dir(home: Path) -> Path:
    return home / "cards" / SNAPSHOTS_DIR_NAME


def _next_id(home: Path) -> str:
    sd = snapshots_dir(home)
    if not sd.exists():
        return "0001"
    nums: list[int] = []
    for child in sd.iterdir():
        m = _DIR_RE.match(child.name)
        if m:
            nums.append(int(m.group(1)))
    return f"{(max(nums) if nums else 0) + 1:04d}"


def _capture(snap_dir: Path, home: Path, filenames: Iterable[str]) -> dict[str, bool]:
    """Copy each named file from ``home`` into ``snap_dir`` if it exists.

    Returns a presence dict ``{filename: existed?}``. The dict always
    contains every filename in ``filenames``, even ones that didn't
    exist — the False entries are what makes restore correctly unlink
    files that were absent at snap time.
    """
    snap_dir.mkdir(parents=True, exist_ok=True)
    captured: dict[str, bool] = {}
    for fn in filenames:
        src = home / fn
        if src.exists() and src.is_file():
            shutil.copy2(src, snap_dir / fn)
            captured[fn] = True
        else:
            captured[fn] = False
    return captured


def ensure_pristine(
    home: Path,
    *,
    filenames: Iterable[str],
    target: str,
) -> Snapshot | None:
    """Capture the pre-SoulTavern state if no snapshots exist yet.

    Idempotent — returns None if any snapshot already exists. The
    pristine snapshot legitimately captures "no files" when none of
    the managed files were present before SoulTavern's first write.

    ``filenames`` is the union of every managed filename across all
    registered targets (passed in by the caller — library.py — to keep
    snapshots.py target-agnostic). ``target`` is recorded as the
    target of the upcoming first import; informational only.
    """
    sd = snapshots_dir(home)
    if sd.exists() and any(p for p in sd.iterdir() if _DIR_RE.match(p.name)):
        return None
    filenames_list = list(filenames)
    snap = Snapshot(
        id=_next_id(home),
        created_at=_now(),
        action="pristine",
        name="pristine",
        card_file=None,
        has_soul_md=False,
        has_hermes_md=False,
        active_record=None,
        target=target,
        captured={},
    )
    snap_dir = sd / snap.dir_name
    captured = _capture(snap_dir, home, filenames_list)
    snap.captured = captured
    snap.has_soul_md = captured.get("SOUL.md", False)
    snap.has_hermes_md = captured.get("HERMES.md", False)
    (snap_dir / "manifest.json").write_text(snap.to_json(), "utf-8")
    return snap


def take_snapshot(
    home: Path,
    *,
    action: str,
    name: str,
    card_file: str | None,
    filenames: Iterable[str],
    target: str,
    active_record: dict[str, Any] | None,
) -> Snapshot:
    """Capture the current state of every managed file as a new snapshot.

    ``filenames`` should be the union of every managed filename across
    all registered targets, same as ``ensure_pristine``. Snapshotting
    the union (rather than only the active target's file set) makes
    cross-target reverts predictable.
    """
    filenames_list = list(filenames)
    snap = Snapshot(
        id=_next_id(home),
        created_at=_now(),
        action=action,
        name=name,
        card_file=card_file,
        has_soul_md=False,
        has_hermes_md=False,
        active_record=active_record,
        target=target,
        captured={},
    )
    snap_dir = snapshots_dir(home) / snap.dir_name
    captured = _capture(snap_dir, home, filenames_list)
    snap.captured = captured
    snap.has_soul_md = captured.get("SOUL.md", False)
    snap.has_hermes_md = captured.get("HERMES.md", False)
    (snap_dir / "manifest.json").write_text(snap.to_json(), "utf-8")
    return snap


def list_snapshots(home: Path) -> list[Snapshot]:
    sd = snapshots_dir(home)
    if not sd.exists():
        return []
    snaps: list[Snapshot] = []
    for child in sorted(sd.iterdir()):
        manifest = child / "manifest.json"
        if not manifest.exists() or not _DIR_RE.match(child.name):
            continue
        try:
            snaps.append(Snapshot.from_json(manifest.read_text("utf-8")))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue  # skip corrupted snapshot, don't crash history
    return snaps


def find_snapshot(home: Path, query: str) -> Snapshot:
    """Resolve ``query`` to one Snapshot.

    Accepts: ``"pristine"``, ``"previous"`` (one back from latest), a
    4-digit id (or any-digit form padded to 4), or a case-insensitive
    name prefix.
    """
    snaps = list_snapshots(home)
    if not snaps:
        raise SnapshotError(f"no snapshots in {home}")

    q = query.strip()
    qlow = q.lower()

    if qlow == "pristine":
        for s in snaps:
            if s.action == "pristine":
                return s
        raise SnapshotError("no pristine snapshot in history")

    if qlow == "previous":
        if len(snaps) < 2:
            raise SnapshotError(
                "no previous snapshot — only one entry in history"
            )
        return snaps[-2]

    if q.isdigit():
        target_id = q.zfill(4)
        for s in snaps:
            if s.id == target_id:
                return s
        raise SnapshotError(f"no snapshot with id {target_id}")

    matches = [s for s in snaps if s.name.casefold().startswith(qlow)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(f"{s.id}/{s.name}" for s in matches)
        raise SnapshotError(f"{q!r} matches multiple snapshots: {joined}")
    raise SnapshotError(f"no snapshot matching {q!r}")


def restore_files(snap: Snapshot, home: Path) -> None:
    """Apply ``snap`` to the live file positions.

    Walks ``snap.captured``: for each filename, if the snapshot has the
    file (presence == True), copy from snap_dir into home. If the
    snapshot recorded the file as absent (presence == False), unlink
    the live file. Files not mentioned in ``captured`` are left alone.

    This is what makes "revert to pristine when nothing existed" work
    — the unlink branch removes the live SOUL.md / companion / extras
    rather than leaving them in place.
    """
    snap_dir = snapshots_dir(home) / snap.dir_name
    for fn, was_present in snap.captured.items():
        live = home / fn
        snap_src = snap_dir / fn
        if was_present and snap_src.exists():
            shutil.copy2(snap_src, live)
        elif not was_present and live.exists():
            live.unlink()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
