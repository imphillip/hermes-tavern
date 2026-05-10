"""Per-runtime adapter targets.

The Tavern format (parse / sanitize / substitute / scan / library /
snapshots / agent staging) is target-agnostic. The differences between
agent runtimes — which filenames hermes / openclaw / generic write,
which loader-priority quirks they have, which Python render functions
produce their persona files — live here.

Usage::

    from soultavern.targets import TARGETS, DEFAULT_TARGET
    target = TARGETS["hermes"]
    soul_filename = target.soul_filename       # "SOUL.md"
    soul_text = target.soul_renderer(...)      # callable, returns str

Consumers that don't plumb a ``target`` argument fall back to
``DEFAULT_TARGET`` (the Hermes target).
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
