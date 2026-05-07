"""``Target`` — the per-runtime adapter dataclass.

For step 1 of the SoulTavern migration this is data-only: filenames,
template names, budget numbers. Methods stay in ``render`` / ``library``
/ ``extended`` and consult the target for which constants to use.

If a future target needs behaviour that varies beyond template choice
(e.g. OpenClaw's workspace-stub mechanism), we'll either subclass this
or add method hooks. Step 1 doesn't pre-design that surface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    """An agent-runtime adapter target.

    Attributes:
        name: short identifier used by the CLI (``--target <name>``)
            and the registry. Lowercase, hyphen-separated if needed.
        soul_filename: the always-on identity file the runtime loads
            from its home dir. ``SOUL.md`` for Hermes; same name for
            most targets.
        companion_filename: the project-context / lorebook file. The
            "companion" of SOUL.md in the runtime's loader. ``HERMES.md``
            for Hermes; ``AGENTS.md`` for OpenClaw.
        soul_template: Jinja template for the always-on rendered soul
            (small-card path).
        companion_template: Jinja template for the lorebook-rendered
            companion file (small-card path with a character_book).
        curated_soul_template: Jinja template for the post-finalize
            curated SOUL.md assembled from V2 category picks
            (oversized-card path).
        soul_budget: hard char cap before render refuses (target's slot
            limit minus headroom).
        companion_budget: same for the companion file.
        oversize_threshold: rendered-output size at or above which
            ``apply_card`` routes through the agent-driven oversized
            flow instead of writing the rendered output as-is. Usually
            75% of the runtime slot.
    """

    name: str
    soul_filename: str
    companion_filename: str
    soul_template: str
    companion_template: str
    curated_soul_template: str
    soul_budget: int
    companion_budget: int
    oversize_threshold: int
