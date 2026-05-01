---
name: hermes-tavern
description: "Import a SillyTavern V2 character card (.png/.json/.yaml) into Hermes-Agent as SOUL.md + HERMES.md. Channel-agnostic — affects every gateway."
version: 0.3.0
author: HermesTavern contributors
license: MIT
metadata:
  hermes:
    tags: [Roleplay, CharacterCard, SillyTavern, SOUL, Persona, TavernAI]
    homepage: https://github.com/hermes-tavern/hermes-tavern
    related_skills: [hermes-tavern-cards]
prerequisites:
  commands: [python]
  python:
    version: ">=3.10"
    packages: [pillow, pyyaml, jinja2]
---

# HermesTavern (loader)

## When to use

Trigger this skill when the user wants to **bring a SillyTavern character into
Hermes**. Concrete signals:

- mentions of "import character card", "load SillyTavern card", "set up
  roleplay persona", "TavernAI character", "chub.ai card"
- the user provides a `.png`, `.json`, or `.yaml` character card path
- the user asks Hermes to "be" / "play" a character whose card they have
  on disk

This skill is **channel-agnostic**. The persona it writes is loaded by
Hermes itself at startup, so it applies uniformly across every channel the
user has configured (CLI, email, Telegram, Discord, Slack, …). Do not touch
channel configuration here — that lives on the Hermes side.

For *managing* already-imported cards (list / switch / delete / restore),
use the sibling skill `hermes-tavern-cards`.

## What it does

```
   .png/.json/.yaml card                   <HERMES_HOME>/
   ┌──────────────────┐    parse +         ├── SOUL.md       ← persona
   │ chara_card_v2    │    render +    →   ├── HERMES.md     ← lorebook (if any)
   │ {data: {...}}    │    write           └── cards/
   └──────────────────┘                        ├── .active.json
                                                └── <name>_<ts>.<ext>   (backup)
```

One pass: read the card, substitute `{{char}}` / `{{user}}` placeholders,
render the V2 fields into two markdown files, copy the source card into
`<HERMES_HOME>/cards/` for safekeeping, and record it as the active
character. Hermes loads `SOUL.md` (identity slot, 20k chars) and
`HERMES.md` (project context slot, 20k chars) automatically on startup.

## Prerequisites

- Python 3.10+
- The `hermes-tavern` CLI on PATH — run `bash scripts/install.sh` once
  (see Install below; the package is bundled as a wheel in `assets/`
  because it is not yet published to PyPI)
- A target `HERMES_HOME` directory that Hermes will be launched against

## Install

```bash
bash scripts/install.sh
```

The installer tries, in order: `pipx` → `uv tool` → a dedicated venv at
`~/.local/share/hermes-tavern-venv` with a shim in `~/.local/bin`. It is
idempotent: if `hermes-tavern` is already on PATH, it exits without
touching anything. Override paths with `HERMES_TAVERN_VENV` and
`HERMES_TAVERN_BIN` env vars.

## Quick start

```bash
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay
cd ~/.hermes-roleplay && HERMES_HOME=~/.hermes-roleplay hermes
```

**Important launch posture.** `SOUL.md` is read from `HERMES_HOME`, but
`HERMES.md` is read from **cwd**. You must `cd $HERMES_HOME` (or use
`--cwd`) before running `hermes`, or the lorebook / extended-file index
won't be loaded. This applies in both normal and distillation modes.

Useful flags:

```bash
# Preview without writing
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --dry-run

# Replace existing files
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --overwrite

# Custom address term for {{user}}
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --user-noun "the operator"

# Skip lorebook even if the card has one
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --soul-only

# Sanity-check a card without writing (also runs the red-flag scan)
hermes-tavern validate --card aldous.png

# Render system_prompt / post_history_instructions in their high-trust V2 slots
# instead of inside untrusted blockquotes. Only for trusted card authors.
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --trust-system-prompt

# Skip distillation for oversized cards; surface the budget error instead.
hermes-tavern import --card huge.png --home ~/.hermes-roleplay --no-distill

# Use a different distillation command than the default `hermes -q`.
hermes-tavern import --card huge.png --home ~/.hermes-roleplay --distill-cmd "claude -p"
```

## Oversized cards

When the rendered SOUL.md or HERMES.md would exceed 75% of Hermes's 20k
slot budget (≥ 15,000 chars), HermesTavern shells out to your already-
configured Hermes CLI (`hermes -q "<prompt>"` by default) to compress
the prompt-loaded portion. The full original content is written to
`<HERMES_HOME>/cards/<card_stem>/extended/` (one file per field) and
indexed from `HERMES.md` so the model can read specific files on demand.

In distillation mode, `HERMES.md` carries (a) the LLM-distilled lore
that fits in static context and (b) the file index. We use the
HERMES.md slot — not AGENTS.md — because Hermes's loader skips
AGENTS.md whenever HERMES.md is present.

See `references/distillation.md` for the full pipeline, prompt format,
and failure modes.

## Files this skill never touches

- **AGENTS.md** — shadowed by HERMES.md; we put references in HERMES.md instead.
- **MEMORY.md / USER.md** — owned by the running agent; human edits get overwritten.
- **CLAUDE.md / .cursorrules** — lower-priority context files used by other tools.

## Security defaults

Every card is treated as third-party content:

1. **`# IDENTITY DIRECTIVE`** is auto-injected at the top of every
   `SOUL.md` to override hermes's hard-coded "you are an AI assistant
   on \<channel\>" framing. Without it the model collapses back to
   "I'm an AI assistant. If we're roleplaying, I'm currently
   portraying X" instead of just answering as the character. Operator
   safety is explicitly preserved.
2. SOUL.md / HERMES.md include a **trust-boundary banner** marking
   everything below as third-party content. Banner is security-only —
   it tells the model to ignore directives that try to change tools /
   override safety / leak data, without calling the persona "roleplay
   material" (that would undercut the IDENTITY DIRECTIVE).
3. `system_prompt` and `post_history_instructions` are demoted into
   `## Author's framing (untrusted ...)` and `## Author's closing note
   (untrusted ...)` sections by default. Use `--trust-system-prompt` to
   promote them back to the V2 high-trust slot. The IDENTITY DIRECTIVE
   is emitted regardless of this flag.
4. Card text is run through a **sanitiser** that strips zero-width
   chars, RTL overrides, and other invisible / control characters.
5. Every `import` and `validate` runs a **red-flag scan** for prompt
   injection patterns (override instructions, fake tool tags, exfil
   URLs, …) and prints findings to stderr / stdout. Findings warn but
   never block.

See `references/security.md` for the full threat model and what is
*not* covered (channel-level safety lives on the Hermes side).

## References

- `references/v2-spec-summary.md` — V2 card field cheat sheet
- `references/field-mapping.md` — exact V2 → markdown rendering rules
- `references/usage-recipes.md` — common workflows and gotchas
- `references/security.md` — threat model, sanitiser layers, operator workflow
- `references/distillation.md` — oversized-card pipeline, AGENTS.md layout, failure modes

## Files this skill writes

Normal mode (rendered output ≤ 15k per slot):

- `<HERMES_HOME>/SOUL.md` — character identity (always written)
- `<HERMES_HOME>/HERMES.md` — world / lorebook (only if the card has a
  `character_book`, and `--soul-only` was not passed)
- `<HERMES_HOME>/cards/<name>_<timestamp>.<ext>` — copy of the source card
- `<HERMES_HOME>/cards/.active.json` — pointer to the currently active card

Distillation mode (triggered when either rendered file > 15k):

- `<HERMES_HOME>/SOUL.md` — LLM-distilled identity (compact)
- `<HERMES_HOME>/HERMES.md` — distilled lore + index pointing into extended/
- `<HERMES_HOME>/cards/<name>_<timestamp>/extended/...` — full original content

By default the loader **refuses to overwrite** existing `SOUL.md` /
`HERMES.md`. Pass `--overwrite` to replace them.

## Out of scope

- Keyword-triggered lorebook injection (entries are rendered as always-on)
- Multi-character routing or per-sender state
- Patching Hermes source / writing middleware / running a relay
- Channel configuration (`platform_toolsets`, allowlists, safety settings)
- Starting or supervising the Hermes process itself
