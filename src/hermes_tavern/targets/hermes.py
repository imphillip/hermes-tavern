"""``HERMES`` — the Hermes-Agent adapter target.

This is the historical default (and only) target through v0.5.x.
Hermes loads ``SOUL.md`` from ``HERMES_HOME`` and ``HERMES.md`` from
**cwd** at startup; ``AGENTS.md`` is shadowed by ``HERMES.md`` and
intentionally never written.

Slot is 20k chars per file. We render to 19k hard cap and route through
the agent oversized-card flow at 15k (75% threshold) so there's room
for the trust banner / headings / IDENTITY DIRECTIVE that the templates
emit on top of the source content.
"""

from __future__ import annotations

from .base import Target

HERMES = Target(
    name="hermes",
    soul_filename="SOUL.md",
    companion_filename="HERMES.md",
    soul_template="SOUL.md.j2",
    companion_template="HERMES.md.j2",
    curated_soul_template="SOUL.md.curated.j2",
    soul_budget=19_000,
    companion_budget=19_000,
    oversize_threshold=15_000,
)
