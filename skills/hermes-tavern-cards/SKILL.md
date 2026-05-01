---
name: hermes-tavern-cards
description: "Manage SillyTavern character cards already imported into HERMES_HOME — list, show current, switch active, soft-delete, restore."
version: 0.3.0
author: HermesTavern contributors
license: MIT
metadata:
  hermes:
    tags: [Roleplay, CharacterCard, SillyTavern, Persona, Library, TavernAI]
    homepage: https://github.com/hermes-tavern/hermes-tavern
    related_skills: [hermes-tavern]
prerequisites:
  commands: [python]
  python:
    version: ">=3.10"
    packages: [pillow, pyyaml, jinja2]
---

# HermesTavern (cards manager)

## When to use

Trigger this skill when the user wants to **manage characters that have
already been imported** with the `hermes-tavern` loader skill. Concrete
signals:

- "switch character to X", "play X instead", "be Alice now"
- "what character am I running right now?", "who is loaded?"
- "list my characters", "show all imported cards"
- "delete the X card", "remove the Bob persona"
- "bring back the card I deleted", "undelete X", "restore the previous one"
- "go back to before I loaded any card", "revert to the previous SOUL", "show me the snapshot history"

For the **first-time import** of a fresh `.png` / `.json` / `.yaml` card,
use the sibling skill `hermes-tavern` instead.

## What it does

```
   <HERMES_HOME>/
   ├── SOUL.md              ← active persona  ──┐
   ├── HERMES.md            ← active lorebook ──┤  switch / delete /
   └── cards/                                   │  restore commands
       ├── .active.json     ← which card is on  │  rewrite these from
       ├── .trash/          ← soft-deleted      │  files in cards/
       │   └── bob_…json                        │
       ├── alice_…json                          │
       └── carol_…png    ──────────────────────-┘
```

The card library lives in `<HERMES_HOME>/cards/`. Each command operates on
that library — none of them parse a fresh card from outside the library.
Soft-deletes go to `cards/.trash/`; nothing is permanently removed by
default, so users can `restore` if they change their mind.

## Prerequisites

- Python 3.10+
- The `hermes-tavern` CLI on PATH — run `bash scripts/install.sh` once
  (see Install below; or skip if the sibling `hermes-tavern` skill has
  already installed it on this machine)
- A `HERMES_HOME` that already has at least one card imported via
  `hermes-tavern import` (the sibling loader skill)

## Install

```bash
bash scripts/install.sh
```

Idempotent — exits early if the CLI is already on PATH. The installer
is identical to the one in the sibling `hermes-tavern` skill; running
it from either skill installs the same CLI for both.

## Quick start

```bash
# What's loaded right now?
hermes-tavern current --home ~/.hermes-roleplay

# What cards do I have?
hermes-tavern list --home ~/.hermes-roleplay
hermes-tavern list --home ~/.hermes-roleplay --all     # include trash

# Switch active persona
hermes-tavern switch --card alice --home ~/.hermes-roleplay

# Soft-delete a card (moves it to cards/.trash/)
hermes-tavern delete --card bob --home ~/.hermes-roleplay

# Bring it back
hermes-tavern restore --card bob --home ~/.hermes-roleplay

# See SOUL.md / HERMES.md snapshot history
hermes-tavern history --home ~/.hermes-roleplay

# Revert SOUL.md / HERMES.md to a snapshot
hermes-tavern revert --home ~/.hermes-roleplay --to pristine    # back to before any card
hermes-tavern revert --home ~/.hermes-roleplay --to alice       # back to when alice was active
hermes-tavern revert --home ~/.hermes-roleplay --to 0003        # back to snapshot 0003
hermes-tavern revert --home ~/.hermes-roleplay --previous       # one snapshot back
```

The `--card` argument accepts:

- the card's filename in `cards/` (e.g. `alice_20260501T120000.json`)
- the character's name (case-insensitive prefix match against the parsed
  `name` field or filename stem)

If a query is ambiguous, the command refuses and lists the candidates.

## References

- `references/library-layout.md` — `<HERMES_HOME>/cards/` layout, `.active.json` schema, `--card` query resolution
- `../hermes-tavern/references/usage-recipes.md` — switching / deleting / restoring recipes (shared with the loader skill)
- `../hermes-tavern/references/field-mapping.md` — V2 → markdown rendering rules (used when re-rendering on switch)
- `../hermes-tavern/references/security.md` — threat model and how `--trust-system-prompt` interacts with `switch`
- `../hermes-tavern/references/distillation.md` — when `switch` triggers re-distillation; `--no-distill` / `--distill-cmd` flags

## Files this skill writes

- `<HERMES_HOME>/SOUL.md`, `<HERMES_HOME>/HERMES.md` — rewritten by
  `switch` (always with overwrite)
- `<HERMES_HOME>/cards/.active.json` — updated by `switch`; cleared by
  `delete` if the deleted card was active
- `<HERMES_HOME>/cards/.trash/<file>` — created/removed by `delete` /
  `restore`

`switch` always overwrites `SOUL.md` / `HERMES.md` (that is its whole
point). `delete` never touches `SOUL.md` itself — if the user deletes the
active card and wants the persona gone too, they should `switch` to a
different card or remove the files manually.

## Out of scope

- Importing fresh cards from outside `<HERMES_HOME>/cards/` (use the
  `hermes-tavern` loader skill)
- Permanent deletion (use the host shell to empty `cards/.trash/`)
- Multi-character routing inside a single Hermes instance (run a separate
  `HERMES_HOME` per character instead)
- Channel-level configuration
