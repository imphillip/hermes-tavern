"""Per-mutation snapshot history of SOUL.md and HERMES.md.

Every ``import`` / ``switch`` captures the resulting on-disk state into
``<HERMES_HOME>/cards/.snapshots/<NNNN>_<ts>_<name>/``. Before the very
first mutation, a special ``pristine`` snapshot records the
pre-HermesTavern state — which may legitimately mean "no SOUL.md or
HERMES.md existed". ``revert`` restores any of these snapshots,
correctly removing live files when the target snapshot didn't have
them.

Layout::

    <HERMES_HOME>/cards/.snapshots/
    ├── 0001_pristine/
    │   ├── manifest.json
    │   └── (SOUL.md / HERMES.md if they existed pre-HermesTavern)
    ├── 0002_20260502T130000_Aldous/
    │   ├── manifest.json
    │   ├── SOUL.md
    │   └── HERMES.md
    └── ...
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    has_soul_md: bool
    has_hermes_md: bool
    active_record: dict[str, Any] | None = None

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


def _capture_files(snap_dir: Path, soul: Path, hermes: Path) -> tuple[bool, bool]:
    snap_dir.mkdir(parents=True, exist_ok=True)
    has_soul = soul.exists()
    has_hermes = hermes.exists()
    if has_soul:
        shutil.copy2(soul, snap_dir / "SOUL.md")
    if has_hermes:
        shutil.copy2(hermes, snap_dir / "HERMES.md")
    return has_soul, has_hermes


def ensure_pristine(
    home: Path,
    *,
    soul: Path,
    hermes: Path,
) -> Snapshot | None:
    """Capture the pre-HermesTavern state if no snapshots exist yet.

    Idempotent — returns None if any snapshot already exists. The
    pristine snapshot legitimately captures "no files" when SOUL.md /
    HERMES.md were absent before HermesTavern's first write.
    """
    sd = snapshots_dir(home)
    if sd.exists() and any(p for p in sd.iterdir() if _DIR_RE.match(p.name)):
        return None
    snap = Snapshot(
        id=_next_id(home),
        created_at=_now(),
        action="pristine",
        name="pristine",
        card_file=None,
        has_soul_md=False,
        has_hermes_md=False,
        active_record=None,
    )
    snap_dir = sd / snap.dir_name
    has_soul, has_hermes = _capture_files(snap_dir, soul, hermes)
    snap.has_soul_md = has_soul
    snap.has_hermes_md = has_hermes
    (snap_dir / "manifest.json").write_text(snap.to_json(), "utf-8")
    return snap


def take_snapshot(
    home: Path,
    *,
    action: str,
    name: str,
    card_file: str | None,
    soul: Path,
    hermes: Path,
    active_record: dict[str, Any] | None,
) -> Snapshot:
    """Capture current SOUL.md + HERMES.md as a new snapshot."""
    snap = Snapshot(
        id=_next_id(home),
        created_at=_now(),
        action=action,
        name=name,
        card_file=card_file,
        has_soul_md=False,
        has_hermes_md=False,
        active_record=active_record,
    )
    snap_dir = snapshots_dir(home) / snap.dir_name
    has_soul, has_hermes = _capture_files(snap_dir, soul, hermes)
    snap.has_soul_md = has_soul
    snap.has_hermes_md = has_hermes
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


def restore_files(
    snap: Snapshot,
    home: Path,
    *,
    soul: Path,
    hermes: Path,
) -> None:
    """Apply ``snap``'s SOUL.md / HERMES.md to the live positions.

    Crucially, when the snapshot did NOT have a file, the live file is
    **removed** rather than overwritten with empty content. This is
    what makes "revert to pristine when nothing existed" work.
    """
    snap_dir = snapshots_dir(home) / snap.dir_name
    soul_src = snap_dir / "SOUL.md"
    hermes_src = snap_dir / "HERMES.md"

    if soul_src.exists():
        shutil.copy2(soul_src, soul)
    elif soul.exists():
        soul.unlink()

    if hermes_src.exists():
        shutil.copy2(hermes_src, hermes)
    elif hermes.exists():
        hermes.unlink()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
