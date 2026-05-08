"""Per-runtime adapter targets.

The Tavern format (parse / sanitize / substitute / scan / library /
snapshots / agent staging) is target-agnostic. The differences between
agent runtimes — which filenames hermes / openclaw / generic write,
which loader-priority quirks they have, which Jinja templates produce
their persona files — live here.

This module is the seam future SoulTavern multi-target work expands.
For now (v0.6 alpha) only ``hermes`` is implemented; ``openclaw`` and
``generic`` join in step 2 of the migration.

Usage::

    from soultavern.targets import TARGETS, DEFAULT_TARGET
    target = TARGETS["hermes"]
    soul_filename = target.soul_filename       # "SOUL.md"
    template = target.soul_template            # "SOUL.md.j2"

Consumers that don't yet plumb a `target` argument fall back to
``DEFAULT_TARGET`` (currently the Hermes target — that's the v0.5.x
behavior unchanged).
"""

from __future__ import annotations

from .base import Target
from .generic import GENERIC
from .hermes import HERMES
from .openclaw import OPENCLAW

TARGETS: dict[str, Target] = {
    "hermes": HERMES,
    "openclaw": OPENCLAW,
    "generic": GENERIC,
}
DEFAULT_TARGET: Target = HERMES

__all__ = [
    "DEFAULT_TARGET",
    "GENERIC",
    "HERMES",
    "OPENCLAW",
    "TARGETS",
    "Target",
]
