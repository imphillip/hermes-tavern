---
name: soultavern
description: "Import and manage SillyTavern V2 character cards (.png/.json) for any agent runtime with a SOUL.md-style persona file. Pure-stdlib skill folder — no install. v2.0 supports --target hermes (Hermes-Agent) and --target openclaw (OpenClaw workspaces). Channel-agnostic — affects every gateway."
version: 2.0.0
author: SoulTavern contributors
license: MIT
metadata:
  hermes:
    tags: [Roleplay, CharacterCard, SillyTavern, SOUL, Persona, Library, TavernAI, OpenClaw]
    homepage: https://github.com/imphillip/SoulTavern
prerequisites:
  commands: [python3]
  python:
    version: ">=3.10"
---

# SoulTavern

> _Lineage:_ TavernAI → SillyTavern → HermesTavern → **SoulTavern**

v2.0 is **skill-folder only**. There is no `soultavern` binary on PATH,
no wheel to install, no third-party Python deps. The skill is one
folder; you invoke it by running scripts in `scripts/` directly. Drop
the folder anywhere your runtime reads skills from and it works.

## When to use

Trigger this skill whenever the user wants to **bring a SillyTavern
character into the runtime** *or* **manage characters already imported**.
Concrete signals:

**Import / load:**
- "import character card", "load SillyTavern card", "set up roleplay persona",
  "TavernAI character", "chub.ai card", "soul.agentbox.id"
- the user provides a `.png` or `.json` character card path
- the user asks the runtime to "be" / "play" a character whose card they have on disk

**Library management:**
- "switch character to X", "play X instead", "be Alice now"
- "what character am I running right now?", "who is loaded?"
- "list my characters", "show all imported cards"
- "delete the X card", "remove the Bob persona"
- "bring back the card I deleted", "undelete X", "restore the previous one"
- "go back to before I loaded any card", "revert to the previous SOUL",
  "show me the snapshot history"

This skill is **channel-agnostic**. The persona it writes is loaded by
the runtime itself at session start, so it applies uniformly across
every channel the user has configured (CLI, email, Telegram, Discord,
Slack, …). Do not touch channel configuration here.

## What it does

```
   .png/.json card                    <home>/
   ┌──────────────────┐    parse +     ├── SOUL.md       ← persona
   │ chara_card_v2    │    render +    ├── <companion>   ← lorebook (per target)
   │ {data: {...}}    │    write   →   └── cards/
   └──────────────────┘                    ├── .active.json
                                            └── <name>_<ts>.<ext>   (backup)
```

One pass: read the card, substitute `{{char}}` / `{{user}}` placeholders,
render the V2 fields into markdown files, copy the source card into
`<home>/cards/` for safekeeping, and record it as the active character.
The runtime loads `SOUL.md` plus its companion file at session start.

## How to invoke

Every operation is a script in `scripts/`. Substitute `$SKILL_DIR` with
the absolute path to this skill folder.

```bash
SKILL_DIR=<absolute path to this skills/soultavern folder>

# Import a card
python3 "$SKILL_DIR/scripts/import.py" --card aldous.png --home ~/.hermes-roleplay

# Same, targeting OpenClaw
python3 "$SKILL_DIR/scripts/import.py" \
    --card aldous.png --home ~/.openclaw/workspace --target openclaw

# Library management — see "Library management" section
python3 "$SKILL_DIR/scripts/list.py"    --home ~/.hermes-roleplay
python3 "$SKILL_DIR/scripts/current.py" --home ~/.hermes-roleplay
python3 "$SKILL_DIR/scripts/switch.py"  --card alice --home ~/.hermes-roleplay
```

Run any script with `--help` to see its full flag list. The flag
surface is identical across targets — `--target` selects the runtime.

## Quick start (Hermes target — default)

```bash
python3 "$SKILL_DIR/scripts/import.py" --card aldous.png --home ~/.hermes-roleplay
cd ~/.hermes-roleplay && HERMES_HOME=~/.hermes-roleplay hermes
```

**Hermes launch posture.** `SOUL.md` is read from `HERMES_HOME`, but
`HERMES.md` is read from **cwd**. You must `cd $HERMES_HOME` (or use
`--cwd`) before running `hermes`, or the lorebook / extended-file index
won't be loaded.

Useful flags (all on `import.py`):

```bash
# Preview without writing
... --dry-run

# Replace existing files
... --overwrite

# Custom address term for {{user}}
... --user-noun "the operator"

# Skip lorebook even if the card has one
... --soul-only

# Sanity-check a card without writing (also runs the red-flag scan)
python3 "$SKILL_DIR/scripts/validate.py" --card aldous.png

# Render system_prompt / post_history_instructions in their high-trust V2 slots
# instead of inside untrusted blockquotes. Only for trusted card authors.
... --trust-system-prompt

# Target a different agent runtime (default is hermes)
... --target openclaw
```

## Targets (multi-runtime support)

`--target` selects which agent runtime the import is shaped for:

| target | files written | notes |
|---|---|---|
| `hermes` (default) | `SOUL.md` + `HERMES.md` | Full lorebook in `HERMES.md`. Hermes loads `SOUL.md` from `HERMES_HOME` and `HERMES.md` from cwd. |
| `openclaw` | `SOUL.md` + `AGENTS.md` (managed-section append) + `IDENTITY.md` | `AGENTS.md` outranks `SOUL.md` in OpenClaw's loader, so the IDENTITY DIRECTIVE goes there. Existing user content in `AGENTS.md` is preserved — only the section between `<!-- BEGIN soultavern:character -->` markers is touched. |
| `generic` | *(skeleton — lands in a later release)* | Single `SOUL.md` + companion index for unspecified runtimes. |

Per-target details:

- `references/openclaw-target.md` — file layout, write strategy, and budget constants for OpenClaw
- `references/openclaw-identity-directive.md` — the IDENTITY DIRECTIVE wording for OpenClaw, with iteration playbook

The `--home` argument is the runtime's home directory (`HERMES_HOME` for
hermes, the OpenClaw workspace dir for openclaw).

## Library management

Once cards are imported, the same scripts handle list / current / switch
/ delete / restore over `<home>/cards/`. None reach outside that
directory; switching writes a fresh SOUL.md + companion file from a
card already in the library.

```bash
python3 "$SKILL_DIR/scripts/current.py" --home ~/.hermes-roleplay
python3 "$SKILL_DIR/scripts/list.py"    --home ~/.hermes-roleplay
python3 "$SKILL_DIR/scripts/list.py"    --home ~/.hermes-roleplay --all     # include trash

# Switch active persona
python3 "$SKILL_DIR/scripts/switch.py"  --card alice --home ~/.hermes-roleplay

# Soft-delete a card (moves to cards/.trash/)
python3 "$SKILL_DIR/scripts/delete.py"  --card bob --home ~/.hermes-roleplay

# Bring it back
python3 "$SKILL_DIR/scripts/restore.py" --card bob --home ~/.hermes-roleplay

# Snapshot history (every import/switch is captured)
python3 "$SKILL_DIR/scripts/history.py" --home ~/.hermes-roleplay

# Revert to a snapshot
python3 "$SKILL_DIR/scripts/revert.py"  --home ~/.hermes-roleplay --to pristine
python3 "$SKILL_DIR/scripts/revert.py"  --home ~/.hermes-roleplay --to alice
python3 "$SKILL_DIR/scripts/revert.py"  --home ~/.hermes-roleplay --previous
```

For `switch` / `delete` / `restore`, the `--card` argument is matched in
this order: exact filename → case-insensitive filename stem →
case-insensitive parsed `data.name` → case-insensitive prefix on either.
Ambiguous queries refuse and list the candidates.

`switch` always overwrites the persona files (that is its whole point).
`delete` never touches `SOUL.md` itself — if the user deletes the active
card and wants the persona gone too, they should `switch` to a different
card or `revert` to a snapshot.

`switch` to an oversized card whose `extended/` is already populated
from a prior `finalize` reuses those files — no agent re-engagement
needed. If `extended/` was deleted, `switch` falls back to the staging
path and prompts for the agent procedure again.

Full library layout (`.active.json` schema, snapshot directory, trash
behavior, `--card` resolution rules) is in
`references/library-layout.md`.

## Oversized card procedure

When the rendered SOUL.md or companion file would exceed 75% of the
target's per-file budget, `import.py` does **not** shell out to any
LLM. Instead it stages the source material on disk and asks the agent
(you) to redistribute it into V2 categories.

### Step 1 — `import.py` runs and exits with code 2

```text
soultavern: Veranna is oversized (16842 chars over the 15000-char threshold).

Source material has been staged for the agent at:
  /Users/me/.hermes-roleplay/cards/Veranna_20260502T010101/source.md

Next step: read that file, redistribute its content into per-category
files under the sibling extended/ directory ...
```

The script has already written:

- `cards/<stem>/source.md` — the parsed, sanitized, placeholder-substituted
  source. Description fields with `Header:` style sub-headers are
  pre-flagged as `### Header` blocks.
- `cards/<stem>/extended/alternate_greetings/01.md, 02.md, ...` — one per
  alternate opening (script-written; no agent work needed on these).
- `cards/<stem>/extended/lore/<entry>.md` — one per lorebook entry
  (script-written; no agent work needed on these either).

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
  absence in the companion-file index.
- **One H1 per file.** Open each file with `# <Category title>` (e.g.
  `# Identity`, `# Roleplay Guidelines`) — `finalize` strips the H1 when
  re-rendering and uses it for the index title.
- **Don't touch `alternate_greetings/` or `lore/`.** Those are already
  written by `import.py` and have their own structure.

### Step 3 — run `finalize.py`

```bash
python3 "$SKILL_DIR/scripts/finalize.py" --card <name> --home <home>
```

This:

1. Loads `cards/<stem>/extended/<cat>.md` for each V2 category.
2. Renders the **curated SOUL.md** from a small subset (identity +
   personality + roleplay_guides) — these are the always-on essentials.
3. Walks `extended/` and renders an **indexed companion file** pointing
   at every category file, every alternate greeting, and every lorebook
   entry, with one-line "read me when …" hints.
4. Writes both files into `<home>/`, updates `.active.json`, and
   takes a snapshot for `revert`.

After this, the card behaves exactly like a small card from the user's
perspective: start the runtime from `<home>` and the persona loads.

See `references/oversized-cards.md` for the design rationale, full file
layout, security considerations, and failure modes.

## Files this skill never touches

- **AGENTS.md (Hermes target)** — shadowed by HERMES.md; we put references in HERMES.md instead.
- **AGENTS.md outside the managed section (OpenClaw target)** — only the section between `<!-- BEGIN soultavern:character -->` markers is touched; everything else is preserved.
- **MEMORY.md / USER.md** — owned by the running agent; human edits get overwritten.
- **CLAUDE.md / .cursorrules** — lower-priority context files used by other tools.

## Security defaults

Every card is treated as third-party content:

1. **`# IDENTITY DIRECTIVE`** is auto-injected (in SOUL.md for Hermes,
   in the AGENTS.md managed section for OpenClaw — whichever has higher
   loader priority on that runtime) to override the runtime's
   hard-coded "you are an AI assistant" framing. Without it the model
   collapses back to "I'm an AI assistant. If we're roleplaying, I'm
   currently portraying X" instead of just answering as the character.
   Operator safety is explicitly preserved.
2. SOUL.md / companion files include a **trust-boundary banner**
   marking everything below as third-party content. Banner is
   security-only — it tells the model to ignore directives that try to
   change tools / override safety / leak data, without calling the
   persona "roleplay material" (that would undercut the IDENTITY
   DIRECTIVE).
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
*not* covered (channel-level safety lives on the runtime side).

## Skill folder layout

```
skills/soultavern/
  SKILL.md                ← you are here
  scripts/                ← everything the agent ever runs
    import.py  switch.py  list.py  current.py  delete.py  restore.py
    revert.py  history.py  finalize.py  validate.py
                          ↑ thin entry shims the LLM invokes
    soultavern/           ← the importable engine package; pure stdlib
      parse.py  render.py  text.py  sanitize.py  substitute.py
      classify.py  scan.py  staging.py  snapshots.py  library.py
      extended.py  cli.py
      targets/            ← per-runtime adapters
        hermes.py  openclaw.py  generic.py  base.py  openclaw_writers.py
  assets/                 ← demo card
    aldous_v2.json
  references/             ← deeper docs (read on demand)
```

## References

- `references/v2-spec-summary.md` — V2 card field cheat sheet
- `references/field-mapping.md` — exact V2 → markdown rendering rules
- `references/usage-recipes.md` — common workflows and gotchas
- `references/security.md` — threat model, sanitiser layers, operator workflow
- `references/oversized-cards.md` — agent-driven categorization flow, file layout, failure modes
- `references/library-layout.md` — `<home>/cards/` schema, snapshots, `--card` resolution
- `references/openclaw-target.md` — OpenClaw target spike findings + design baseline
- `references/openclaw-identity-directive.md` — OpenClaw IDENTITY DIRECTIVE wording + iteration playbook

## Files this skill writes

Small cards (rendered output below the target's oversize threshold):

- `<home>/SOUL.md` — character identity (always written)
- `<home>/<companion>` — companion file (`HERMES.md` for hermes target,
  `AGENTS.md` managed section for openclaw target)
- `<home>/IDENTITY.md` — *(openclaw target only)* character metadata
- `<home>/cards/<name>_<timestamp>.<ext>` — copy of the source card
- `<home>/cards/.active.json` — pointer to the currently active card

Oversized cards (after the agent flow + `finalize.py`):

- `<home>/SOUL.md` — curated identity (identity + personality +
  roleplay_guides picks)
- `<home>/<companion>` — index over the extended/ files
- `<home>/cards/<name>_<timestamp>/source.md` — staging input
- `<home>/cards/<name>_<timestamp>/extended/<cat>.md` — agent-written
  V2 categories
- `<home>/cards/<name>_<timestamp>/extended/alternate_greetings/, lore/` —
  script-written per-entry payloads

By default `import.py` **refuses to overwrite** existing persona files.
Pass `--overwrite` to replace them. `finalize.py` overwrites by default
(since it's the natural completion of a staged import); pass
`--no-overwrite` to refuse.

## Out of scope

- Keyword-triggered lorebook injection (entries are rendered as always-on)
- Multi-character routing or per-sender state
- Patching runtime source / writing middleware / running a relay
- Channel configuration (`platform_toolsets`, allowlists, safety settings)
- Starting or supervising the runtime process itself
