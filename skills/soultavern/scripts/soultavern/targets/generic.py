"""``GENERIC`` — skeleton generic / unknown-runtime fallback target.

For agent runtimes we haven't built specific support for, the generic
target outputs a single ``SOUL.md`` plus an ``index.md`` that lists any
extended files. The intent: any runtime that loads markdown system
prompts at startup can pick these up by symlinking or copying.

This target is registered for CLI discovery but the renderers raise
``NotImplementedError`` — ``implemented=False`` means the CLI surfaces
a friendly "not yet implemented" message before invoking them.
"""

from __future__ import annotations

from .base import Target, _not_implemented

GENERIC = Target(
    name="generic",
    soul_filename="SOUL.md",
    companion_filename="index.md",
    soul_renderer=_not_implemented,
    companion_renderer=_not_implemented,
    curated_soul_renderer=_not_implemented,
    soul_budget=19_000,
    companion_budget=19_000,
    oversize_threshold=15_000,
    implemented=False,
)
