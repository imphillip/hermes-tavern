# OpenClaw target — design baseline

This document captures the v0.6 spike that validated the
**openclaw** target. The design described here landed in v1.0 and is
the current production behavior — this is the source of truth for
budget constants, file-by-file write strategy, and design rationale.

Source-of-truth references throughout point at the [OpenClaw
repository](https://github.com/openclaw/openclaw) (paths shown are
relative to its root).

## Loader order

OpenClaw's workspace loader registers eight bootstrap files in this
exact order — first listed is loaded first, which the user has
confirmed is the priority order in the assembled system prompt
(see `src/agents/workspace.ts:609-641`):

| # | File | Purpose | Touched by SoulTavern |
|---|---|---|---|
| 1 | `AGENTS.md` | Operating instructions; highest priority | ✅ append managed-section |
| 2 | `SOUL.md` | Persona, tone, boundaries | ✅ replace |
| 3 | `TOOLS.md` | Local tool conventions | ❌ never |
| 4 | `IDENTITY.md` | Name / vibe / emoji / avatar | ✅ replace |
| 5 | `USER.md` | User profile (the human's data) | ❌ never; optionally read |
| 6 | `HEARTBEAT.md` | Periodic-check checklist | ❌ never |
| 7 | `BOOTSTRAP.md` | First-run ritual; agent self-deletes after | ❌ never |
| 8 | `MEMORY.md` | Curated long-term memory; main session only | ❌ never |

`AGENTS.md` carries the **highest authority** — placing the
character's IDENTITY DIRECTIVE there is what gives it priority over
the default agent framing in `SOUL.md` template.

## Real budget constants

From `src/agents/pi-embedded-helpers/bootstrap.ts:87-88`:

```typescript
DEFAULT_BOOTSTRAP_MAX_CHARS = 12_000        // per file
DEFAULT_BOOTSTRAP_TOTAL_MAX_CHARS = 60_000  // across all bootstrap files
```

User-configurable via `agents.defaults.bootstrapMaxChars` /
`bootstrapTotalMaxChars` in `~/.openclaw/openclaw.json`.

Per-file truncation runs at OpenClaw's load time. SoulTavern's job is
to write within these caps so content isn't mid-sentence-truncated
when the agent boots.

Default OpenClaw templates use roughly 10k of the 60k total cap
(AGENTS.md ≈ 7k + SOUL.md ≈ 1k + TOOLS / IDENTITY / USER / HEARTBEAT
≈ 2k combined), leaving **~50k headroom** for character-specific
content — generous in aggregate, but each individual file still has
to fit in 12k.

## Default-template framing analysis

Worth noting because it shapes the IDENTITY DIRECTIVE design: OpenClaw's
default templates are **soul-loader-friendly**, not adversarial.

- `SOUL.md` template: *"You're not a chatbot. You're becoming someone."*
- `AGENTS.md` template: framed as "be the assistant you'd actually
  want to talk to" — emphasis on memory, red lines, group-chat
  etiquette; not "you are a work agent"
- `BOOTSTRAP.md` template: *"What kind of creature are you? (AI
  assistant is fine, but maybe you're something weirder)"*

Compared to Hermes's hard-coded "you are an AI assistant on
\<channel\>" framing (which the hermes-target IDENTITY DIRECTIVE has
to explicitly override), OpenClaw's templates are largely cooperative.
The OpenClaw IDENTITY DIRECTIVE can be **shorter and softer** —
mainly affirming the character override rather than fighting hostile
framing.

This invalidates the openclaw-tavern memo's concern about needing a
`--suppress-workspace-bootstrap` flag. **The stub-and-restore
mechanism for TOOLS / BOOTSTRAP / HEARTBEAT / USER is not required.**
v1.0 confirmed this: the openclaw target ships without that mechanism
and the IDENTITY DIRECTIVE alone is sufficient.

## File-by-file write strategy

### `AGENTS.md` — append managed-section

**Why not full replacement**: AGENTS.md is documented as
user-customizable (the template explicitly says *"Make It Yours / Add
your own conventions"*) and the OpenClaw docs recommend committing
the workspace to a private git repo. Wholesale replacement would
destroy user customizations.

**Marker design**:

```markdown
<!-- BEGIN soultavern:character -->
<!-- managed by soultavern; safe to delete the markers + content
     between them, or run SoulTavern's delete.py against this workspace -->

# Active character: {{ character_name }}

## IDENTITY DIRECTIVE
... (overrides default agent framing for this character)

## Lore index
- [Mirror Lake](lore/mirror_lake.md) — ...
- [Old Council](lore/old_council.md) — ...

<!-- END soultavern:character -->
```

**Insertion position**: top of `AGENTS.md` (highest weight within the
file).

**Operations**:

- `import` / `switch`: read existing → if markers exist, replace
  content between them; otherwise prepend the block at the top
- `delete` / `revert`: strip the entire block (markers and contents);
  if the resulting file is empty/whitespace-only, remove it

**Budget**: managed section ≤ 6k chars
(`OPENCLAW.companion_budget`). Leaves ~6k for the user's existing
AGENTS.md content under the 12k per-file cap.

### `SOUL.md` — full replace

The character's persona body (description / personality / scenario /
first_mes / mes_example) goes here. SoulTavern owns this file by
convention — that's the loading point for "this is who you are".

**Budget**: ≤ 11k chars (`OPENCLAW.soul_budget`). Leaves 1k headroom
under the 12k per-file cap.

### `IDENTITY.md` — full replace

Tiny file, character metadata only:

```markdown
- Name: {{ character_name }}
- Creature: roleplay character (imported from SillyTavern V2 card)
- Vibe: {{ character_vibe }}
- Emoji: {{ character_emoji }}
- Avatar: {{ avatar_path }}
```

Falls well under the 12k cap; full replace is safe.

### `lore/<slug>.md` — directory replace

One file per `character_book` entry, indexed from the AGENTS.md
managed section. Loaded on demand by the agent, not eagerly.

`import` / `switch`: clear the `lore/` directory and rewrite from
the card's character_book. `delete` / `revert`: remove the directory.

### `USER.md` — read-only (optional)

SoulTavern must NOT write USER.md — that's OpenClaw's user-profile
slot, the agent itself maintains it. Implications:

1. The Hermes-style `{{user}}` substitution defaults to "the
   visitor" via `--user-noun`.
2. **Optional enhancement (still open)**: parse USER.md for "What to
   call them" and use that as the substitution source, falling back
   to `--user-noun` if not set. Not implemented in v1.0/v2.0.

## Target dataclass extensions (landed in v1.0 / refined in v2.0)

The pre-spike `Target` dataclass modeled a single companion file with
replace semantics. The OpenClaw target needed three new fields:

```python
@dataclass(frozen=True)
class Target:
    # existing fields...
    companion_write_mode: Literal["replace", "managed-section"] = "replace"
    companion_section_marker: str = ""  # e.g. "soultavern:character"
    extra_files: tuple[ExtraFile, ...] = ()  # IDENTITY.md, etc.
```

These shipped in v1.0. v2.0 additionally replaced the
`soul_template: str` / `companion_template: str` / etc. fields with
callable `*_renderer` fields when the jinja2 dependency was removed.

## What the original memo got wrong

The pre-spike `openclaw-tavern-memo.md` made a few assumptions that
spike findings invalidate:

| Memo claim | Reality |
|---|---|
| "阈值取实测 prompt 预算的 75%——不是 2MB 那个文件硬限。预算 = 模型 context window 减生成预算,需先量。" | Real budgets are source constants: 12k per file, 60k total. No measurement needed; the 2 MB figure was a different (file-system) cap. |
| "TOOLS.md / BOOTSTRAP.md / HEARTBEAT.md / USER.md 仍在 workspace 加载——携带 OpenClaw 的 work agent 框架,模型可能因为 prompt 里看见工具就破角色去调用。" | Templates carry **agent-philosophy framing**, not work-agent framing. SOUL.md template even invites character identities. The stub-and-restore mechanism is not needed in v0.7. |
| "蒸馏命令默认 openclaw -q '<prompt>'(若有等价 one-shot)" | v0.4.5+ shifted to agent-driven categorization; no shell-out is in scope for any target. |

The memo correctly identified: AGENTS.md as the override authority,
managed-section append as the write strategy, USER.md as off-limits,
multi-character routing as out of scope, no plugin / no patches.

## Open questions (still open after v1.0/v2.0)

1. ~~Exact IDENTITY DIRECTIVE wording for OpenClaw~~ — landed in v1.0;
   see `openclaw-identity-directive.md` for the wording and iteration
   playbook.
2. Whether to also read `IDENTITY.md` to detect existing emoji /
   vibe before character import (so user's existing self-identity is
   preserved through `revert`). Not implemented.
3. Whether `user_noun` should opportunistically read USER.md (see
   §USER.md above). Not implemented; current default is the
   `--user-noun` flag with fallback "the visitor".
4. Prompt-budget surveillance: should `validate.py --target openclaw`
   warn when the **post-import total** would exceed
   `bootstrapTotalMaxChars`? (The 60k cap is a session-level signal.)
   Not implemented.

These are refinements, not blockers — the target is production
without them.
