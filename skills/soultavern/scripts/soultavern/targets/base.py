"""``Target`` — the per-runtime adapter dataclass.

Data + callables: filenames, render functions, budget numbers. The
render functions live next to each target's instance (in
``targets/hermes.py`` / ``targets/openclaw.py``) so target-specific
rendering stays self-contained — no shared template directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal


@dataclass(frozen=True)
class ExtraFile:
    """An additional file the target writes alongside soul/companion.

    OpenClaw needs ``IDENTITY.md`` (name / vibe / emoji metadata) at
    workspace root; that's an extra file beyond the soul + companion
    pair. Hermes has no extras.

    Attributes:
        filename: file name relative to ``home``.
        renderer: callable producing the file body. Signature varies
            per target; the call site in ``render.render_extra_file``
            forwards ``data``, ``char_name``, ``user_noun``,
            ``avatar_path``.
        budget: hard char cap (warning above, error if templates can't
            shrink). Defaults match OpenClaw's per-file 12k cap.
        description: short label used in operator-facing reports.
    """

    filename: str
    renderer: Callable[..., str]
    budget: int = 12_000
    description: str = ""


@dataclass(frozen=True)
class Target:
    """An agent-runtime adapter target.

    Attributes:
        name: short identifier used by the CLI (``--target <name>``)
            and the registry. Lowercase, hyphen-separated if needed.
        soul_filename: the always-on identity file the runtime loads
            from its home dir. ``SOUL.md`` for Hermes and OpenClaw.
        companion_filename: the project-context / lorebook file. The
            "companion" of SOUL.md in the runtime's loader. ``HERMES.md``
            for Hermes; ``AGENTS.md`` for OpenClaw.
        soul_renderer: callable that produces the always-on rendered
            soul (small-card path).
        companion_renderer: callable that produces the lorebook /
            managed-section content.
        curated_soul_renderer: callable for the post-finalize curated
            SOUL.md assembled from V2 category picks (oversized-card path).
        soul_budget: hard char cap before render refuses (target's slot
            limit minus headroom).
        companion_budget: same for the companion file.
        oversize_threshold: rendered-output size at or above which
            ``apply_card`` routes through the agent-driven oversized
            flow instead of writing the rendered output as-is. Usually
            75% of the runtime slot.
        implemented: True iff the target's renderers and pipeline are
            real and tested. Skeleton targets (registered for CLI
            discovery but not yet functional) have this set to False.
        companion_write_mode: ``"replace"`` (Hermes — the file is
            target-owned, full overwrite) or ``"managed-section"``
            (OpenClaw — the file is shared with user content; only the
            section between markers is touched).
        companion_section_marker: short identifier inside the markers
            (e.g. ``"soultavern:character"``). Empty string for replace
            mode.
        extra_files: tuple of additional files the target writes
            alongside soul/companion (each in replace mode). OpenClaw
            uses this for ``IDENTITY.md``.
    """

    name: str
    soul_filename: str
    companion_filename: str
    soul_renderer: Callable[..., str]
    companion_renderer: Callable[..., str]
    curated_soul_renderer: Callable[..., str]
    soul_budget: int
    companion_budget: int
    oversize_threshold: int
    implemented: bool = True
    companion_write_mode: Literal["replace", "managed-section"] = "replace"
    companion_section_marker: str = ""
    extra_files: tuple[ExtraFile, ...] = field(default_factory=tuple)


def _not_implemented(*_: Any, **__: Any) -> str:
    raise NotImplementedError("This target is a skeleton; renderer is not implemented.")
