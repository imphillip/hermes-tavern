"""``OPENCLAW`` — skeleton OpenClaw adapter target (v0.6.0 placeholder).

OpenClaw's loader reads three workspace files at session start:

- ``AGENTS.md`` — **highest priority**, governs the whole agent's
  behavior. Functionally equivalent to Hermes's ``HERMES.md`` slot but
  with override-level authority over ``SOUL.md``. This is where the
  ``IDENTITY DIRECTIVE`` MUST live for OpenClaw — placing it in
  ``SOUL.md`` won't suppress OpenClaw's "you are a work agent"
  framing because ``AGENTS.md`` outranks ``SOUL.md`` in the loader.
- ``SOUL.md`` — identity / persona body (description, personality,
  scenario, first_mes, mes_example). Lower priority than AGENTS.md.
- ``IDENTITY.md`` — name / avatar / metadata.

Lorebook entries land in ``lore/<slug>.md``, indexed from ``AGENTS.md``.

Step 2 of the SoulTavern migration only registers this target so the
CLI's ``--target`` flag can list it and reject it gracefully. Real
templates and the IDENTITY DIRECTIVE measurement spike happen in step 3.

Provisional values (copied from Hermes — to be calibrated after the
spike measures actual workspace prompt-budget headroom):

- soul_budget / companion_budget: 19_000
- oversize_threshold: 15_000

## Critical design constraints (must inform step 3)

**1. AGENTS.md uses managed-section append, NOT full replacement.**
Unlike Hermes's HERMES.md (which is HermesTavern's exclusive
territory), OpenClaw's AGENTS.md is potentially shared with the
user's existing project setup. Full replacement would destroy their
work configuration. The OpenClaw target must:

- Read existing AGENTS.md (if present)
- Find ``<!-- BEGIN soultavern:character -->`` … ``<!-- END soultavern:character -->`` markers
- Replace just the section between them; preserve everything outside
- If no markers exist, append the managed block at the end
- On ``delete`` / ``revert``, strip the managed block (markers and all);
  if the file ends up empty, remove it

**2. IDENTITY DIRECTIVE belongs in AGENTS.md, not SOUL.md.**
Because AGENTS.md outranks SOUL.md in OpenClaw's loader, the override
that suppresses the "I am a work agent" framing has to live there.
SOUL.md carries persona body only.

## Open questions for step 3

1. Even with IDENTITY DIRECTIVE in the AGENTS.md managed section, can
   it actually outweigh ``BOOTSTRAP.md`` / ``TOOLS.md`` / ``HEARTBEAT.md``
   contributions? If not, we need the workspace-stub mechanism described
   in the openclaw-tavern memo (``--suppress-workspace-bootstrap`` flag,
   reversibly).
2. What's the real prompt-budget ceiling for an OpenClaw workspace?
   The hard-coded 2 MB ``MAX_WORKSPACE_BOOTSTRAP_FILE_BYTES`` is not
   the practical limit — we need the model context window minus
   generation budget minus the bootstrap-files overhead.
3. Extending the ``Target`` dataclass: needs ``companion_write_mode``
   ("replace" vs "managed-section"), ``companion_section_marker``
   (e.g. "soultavern:character"), and an ``extra_files`` field for
   OpenClaw's third file (``IDENTITY.md``). Lock the shape after the
   spike validates the design works at all.
"""

from __future__ import annotations

from .base import Target

OPENCLAW = Target(
    name="openclaw",
    soul_filename="SOUL.md",
    companion_filename="AGENTS.md",
    soul_template="SOUL.md.openclaw.j2",
    companion_template="AGENTS.md.openclaw.j2",
    curated_soul_template="SOUL.md.curated.openclaw.j2",
    soul_budget=19_000,
    companion_budget=19_000,
    oversize_threshold=15_000,
    implemented=False,
)
