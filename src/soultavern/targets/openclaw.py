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
templates land in step 3.

Budget values calibrated from OpenClaw source
(``src/agents/pi-embedded-helpers/bootstrap.ts:87-88``):

- ``DEFAULT_BOOTSTRAP_MAX_CHARS = 12_000`` per file
- ``DEFAULT_BOOTSTRAP_TOTAL_MAX_CHARS = 60_000`` across all bootstrap
  files combined

Both are user-configurable via ``agents.defaults.bootstrapMaxChars`` /
``bootstrapTotalMaxChars`` in ``~/.openclaw/openclaw.json``. Per-file
truncation runs at OpenClaw's load time — soultavern's job is to
write within these caps to avoid mid-content truncation.

OPENCLAW values:

- ``soul_budget = 11_000`` (1k headroom under the 12k per-file cap)
- ``companion_budget = 6_000`` (managed-section soft target; the
  remaining ~6k of AGENTS.md is reserved for the user's existing
  content. See "managed-section append" in
  ``references/openclaw-target.md``.)
- ``oversize_threshold = 9_000`` (~75% of soul_budget; matches the
  Hermes ratio for routing through the agent categorization flow)

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

1. Workspace-stub mechanism (``--suppress-workspace-bootstrap`` flag)
   from the openclaw-tavern memo: spike findings suggest this is **NOT
   needed** — OpenClaw's default templates (BOOTSTRAP / TOOLS /
   HEARTBEAT / USER) carry agent-philosophy framing rather than
   work-agent framing, and SOUL.md template explicitly invites
   character identities ("you're not a chatbot, you're becoming
   someone"). Re-evaluate only if step 3 implementation hits actual
   conflicts.
2. Extending the ``Target`` dataclass: step 3 will need
   ``companion_write_mode`` ("replace" vs "managed-section"),
   ``companion_section_marker`` (e.g. "soultavern:character"), and an
   ``extra_files`` tuple for OpenClaw's third file (``IDENTITY.md``).
   Shape locks after the first real OpenClaw template render.
3. ``user_noun`` source: should soultavern parse OpenClaw's
   ``USER.md`` for "What to call them" and use that as the
   ``{{user}}`` substitution, or stick with the Hermes-style
   ``--user-noun`` flag default ("the visitor")? Defer to step 3.

See ``skills/hermes-tavern/references/openclaw-target.md`` for the
full spike findings, design rationale, and what's locked vs open.
"""

from __future__ import annotations

from .base import ExtraFile, Target

OPENCLAW = Target(
    name="openclaw",
    soul_filename="SOUL.md",
    companion_filename="AGENTS.md",
    soul_template="SOUL.md.openclaw.j2",
    companion_template="AGENTS.md.openclaw.j2",
    curated_soul_template="SOUL.md.curated.openclaw.j2",
    soul_budget=11_000,
    companion_budget=6_000,
    oversize_threshold=9_000,
    implemented=True,
    companion_write_mode="managed-section",
    companion_section_marker="soultavern:character",
    extra_files=(
        ExtraFile(
            filename="IDENTITY.md",
            template="IDENTITY.md.openclaw.j2",
            budget=2_000,
            description="character metadata (name / vibe / avatar)",
        ),
    ),
)
