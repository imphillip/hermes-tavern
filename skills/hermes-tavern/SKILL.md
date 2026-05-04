---
name: hermes-tavern
description: "Import and manage SillyTavern V2 character cards (.png/.json/.yaml) for Hermes-Agent. Imports write SOUL.md + HERMES.md; the same skill also handles list / current / switch / delete / restore / history / revert. Channel-agnostic — affects every gateway."
version: 0.5.0
author: HermesTavern contributors
license: MIT
metadata:
  hermes:
    tags: [Roleplay, CharacterCard, SillyTavern, SOUL, Persona, Library, TavernAI]
    homepage: https://github.com/imphillip/hermes-tavern
prerequisites:
  commands: [python]
  python:
    version: ">=3.10"
    packages: [pillow, pyyaml, jinja2]
---

# HermesTavern

## When to use

Trigger this skill whenever the user wants to **bring a SillyTavern character
into Hermes** *or* **manage characters already imported**. Concrete signals:

**Import / load:**
- "import character card", "load SillyTavern card", "set up roleplay persona",
  "TavernAI character", "chub.ai card"
- the user provides a `.png`, `.json`, or `.yaml` character card path
- the user asks Hermes to "be" / "play" a character whose card they have on disk

**Library management:**
- "switch character to X", "play X instead", "be Alice now"
- "what character am I running right now?", "who is loaded?"
- "list my characters", "show all imported cards"
- "delete the X card", "remove the Bob persona"
- "bring back the card I deleted", "undelete X", "restore the previous one"
- "go back to before I loaded any card", "revert to the previous SOUL",
  "show me the snapshot history"

This skill is **channel-agnostic**. The persona it writes is loaded by
Hermes itself at startup, so it applies uniformly across every channel the
user has configured (CLI, email, Telegram, Discord, Slack, …). Do not touch
channel configuration here — that lives on the Hermes side.

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
won't be loaded. This applies to small cards and oversized ones alike.

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
```

## Library management

Once cards are imported, the same CLI handles list / current / switch /
delete / restore over `<HERMES_HOME>/cards/`. None of these reach outside
that directory; switching writes a fresh SOUL.md + HERMES.md from a card
already in the library.

```bash
# What's loaded right now?
hermes-tavern current --home ~/.hermes-roleplay

# What cards do I have?
hermes-tavern list --home ~/.hermes-roleplay
hermes-tavern list --home ~/.hermes-roleplay --all     # include trash

# Switch active persona
hermes-tavern switch --card alice --home ~/.hermes-roleplay

# Soft-delete a card (moves to cards/.trash/)
hermes-tavern delete --card bob --home ~/.hermes-roleplay

# Bring it back
hermes-tavern restore --card bob --home ~/.hermes-roleplay

# SOUL.md / HERMES.md snapshot history (every import/switch is captured)
hermes-tavern history --home ~/.hermes-roleplay

# Revert SOUL.md / HERMES.md to a snapshot
hermes-tavern revert --home ~/.hermes-roleplay --to pristine    # back to before any card
hermes-tavern revert --home ~/.hermes-roleplay --to alice       # back to when alice was active
hermes-tavern revert --home ~/.hermes-roleplay --to 0003        # back to snapshot 0003
hermes-tavern revert --home ~/.hermes-roleplay --previous       # one snapshot back
```

For `switch` / `delete` / `restore`, the `--card` argument is matched in
this order: exact filename → case-insensitive filename stem →
case-insensitive parsed `data.name` → case-insensitive prefix on either.
Ambiguous queries refuse and list the candidates.

`switch` always overwrites `SOUL.md` / `HERMES.md` (that is its whole
point). `delete` never touches `SOUL.md` itself — if the user deletes the
active card and wants the persona gone too, they should `switch` to a
different card or `revert` to a snapshot.

`switch` to an oversized card whose `extended/` is already populated from
a prior `finalize` reuses those files — no agent re-engagement needed.
If `extended/` was deleted, `switch` falls back to the staging path and
prompts for the agent procedure again.

Full library layout (`.active.json` schema, snapshot directory, trash
behavior, `--card` resolution rules) is in
`references/library-layout.md`.

## Oversized card procedure

When the rendered SOUL.md or HERMES.md would exceed 75% of Hermes's
20k slot budget (≥ 15,000 chars), `hermes-tavern import` does **not**
shell out to any LLM. Instead it stages the source material on disk and
asks the agent (you) to redistribute it into V2 categories. The flow:

### Step 1 — `import` runs and exits with code 2

```text
hermes-tavern: Veranna is oversized (16842 chars over the 15000-char threshold).

Source material has been staged for the agent at:
  /Users/me/.hermes-roleplay/cards/Veranna_20260502T010101/source.md

Next step: read that file, redistribute its content into per-category
files under the sibling extended/ directory ...
```

The CLI has already written:

- `cards/<stem>/source.md` — the parsed, sanitized, placeholder-substituted
  source. Description fields with `Header:` style sub-headers are
  pre-flagged as `### Header` blocks.
- `cards/<stem>/extended/alternate_greetings/01.md, 02.md, ...` — one per
  alternate opening (CLI-written; no agent work needed on these).
- `cards/<stem>/extended/lore/<entry>.md` — one per lorebook entry
  (CLI-written; no agent work needed on these either).

### Step 2 — agent reads `source.md` and writes V2 category files

Open `cards/<stem>/source.md` and redistribute its content into up to
**eight** files under `cards/<stem>/extended/`:

| filename | what goes here |
|---|---|
| `identity.md` | name, age, ethnicity, height, basic biographical facts |
| `appearance.md` | physical description, body, voice, distinctive features |
| `personality.md` | traits, archetype, mannerisms, speech style, quirks |
| `backstory.md` | past events, history, relationships, formative context |
| `scenario.md` | the situation the conversation opens in |
| `kinks.md` | sexual preferences, fetishes, taboos *(only if present in source)* |
| `roleplay_guides.md` | explicit instructions about how to portray the character |
| `examples.md` | sample dialogue or interaction patterns |

**Rules of the road for this step:**

- **Faithful to source wording.** Reuse sentences from `source.md`
  verbatim wherever you can. Don't paraphrase into a smoother version,
  don't invent new framing, don't rewrite for tone. The character voice
  belongs to the source; your job is choosing what goes where.
- **Skip categories that have no source material.** If the card has no
  kinks content, don't write `kinks.md` — leave it absent. Empty/missing
  files are an observable signal in the index.
- **Decline gracefully.** If part of the source material conflicts with
  your operating policy, leave that category file out and proceed with
  the rest. Do not silently rewrite content. The user will see the
  absence in the HERMES.md index.
- **One H1 per file.** Open each file with `# <Category title>` (e.g.
  `# Identity`, `# Roleplay Guidelines`) — `finalize` strips the H1 when
  re-rendering and uses it for the index title.
- **Don't touch `alternate_greetings/` or `lore/`.** Those are already
  written by the CLI and have their own structure.

### Step 3 — run `finalize`

```bash
hermes-tavern finalize --card <name> --home <home>
```

This:

1. Loads `cards/<stem>/extended/<cat>.md` for each V2 category.
2. Renders the **curated SOUL.md** from a small subset (identity +
   personality + roleplay_guides) — these are the always-on essentials.
3. Walks `extended/` and renders an **indexed HERMES.md** pointing at
   every category file, every alternate greeting, and every lorebook
   entry, with one-line "read me when …" hints.
4. Writes both files into `<HERMES_HOME>/`, updates `.active.json`, and
   takes a snapshot for `revert`.

After this, the card behaves exactly like a small card from the user's
perspective: `cd $HERMES_HOME && hermes` and the persona loads.

See `references/oversized-cards.md` for the design rationale, full file
layout, security considerations, and failure modes.

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
6. The **oversized-card flow stays in your context** — there is no
   subprocess shell-out to a separate LLM. Source material is staged
   on disk; you (the agent) categorize it with the same trust posture
   you apply to any third-party file you read.

See `references/security.md` for the full threat model and what is
*not* covered (channel-level safety lives on the Hermes side).

## References

- `references/v2-spec-summary.md` — V2 card field cheat sheet
- `references/field-mapping.md` — exact V2 → markdown rendering rules
- `references/usage-recipes.md` — common workflows and gotchas
- `references/security.md` — threat model, sanitiser layers, operator workflow
- `references/oversized-cards.md` — agent-driven categorization flow, file layout, failure modes
- `references/library-layout.md` — `<HERMES_HOME>/cards/` schema, snapshots, `--card` resolution

## Files this skill writes

Small cards (rendered output ≤ 15k per slot):

- `<HERMES_HOME>/SOUL.md` — character identity (always written)
- `<HERMES_HOME>/HERMES.md` — world / lorebook (only if the card has a
  `character_book`, and `--soul-only` was not passed)
- `<HERMES_HOME>/cards/<name>_<timestamp>.<ext>` — copy of the source card
- `<HERMES_HOME>/cards/.active.json` — pointer to the currently active card

Oversized cards (after the agent flow + `finalize`):

- `<HERMES_HOME>/SOUL.md` — curated identity (identity + personality +
  roleplay_guides picks)
- `<HERMES_HOME>/HERMES.md` — index over the extended/ files
- `<HERMES_HOME>/cards/<name>_<timestamp>/source.md` — staging input
- `<HERMES_HOME>/cards/<name>_<timestamp>/extended/<cat>.md` — agent-written
  V2 categories
- `<HERMES_HOME>/cards/<name>_<timestamp>/extended/alternate_greetings/, lore/` —
  CLI-written per-entry payloads

By default the loader **refuses to overwrite** existing `SOUL.md` /
`HERMES.md`. Pass `--overwrite` to replace them. `finalize` overwrites
by default (since it's the natural completion of a staged import); pass
`--no-overwrite` to refuse.

## Out of scope

- Keyword-triggered lorebook injection (entries are rendered as always-on)
- Multi-character routing or per-sender state
- Patching Hermes source / writing middleware / running a relay
- Channel configuration (`platform_toolsets`, allowlists, safety settings)
- Starting or supervising the Hermes process itself
