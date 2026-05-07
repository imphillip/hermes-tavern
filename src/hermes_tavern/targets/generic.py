"""``GENERIC`` — skeleton generic / unknown-runtime fallback target
(v0.6.0 placeholder).

For agent runtimes we haven't built specific support for, the generic
target outputs a single ``SOUL.md`` plus a ``index.md`` that lists any
extended files. The intent: any runtime that loads markdown system
prompts at startup can pick these up by symlinking or copying.

Step 2 of the SoulTavern migration only registers this target so the
CLI's ``--target`` flag can discover it. Real templates land in step 3
or later — the design question is whether ``GENERIC`` should mirror
Hermes's two-file output (SOUL.md + companion) or compress to a
one-file SOUL.md with the index inlined as a section.

Provisional values mirror Hermes; calibrate when we ship real templates.
"""

from __future__ import annotations

from .base import Target

GENERIC = Target(
    name="generic",
    soul_filename="SOUL.md",
    companion_filename="index.md",
    soul_template="SOUL.md.generic.j2",
    companion_template="index.md.generic.j2",
    curated_soul_template="SOUL.md.curated.generic.j2",
    soul_budget=19_000,
    companion_budget=19_000,
    oversize_threshold=15_000,
    implemented=False,
)
