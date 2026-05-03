# HermesTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> Run your SillyTavern characters in a Hermes agent.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

HermesTavern is a one-shot importer that turns SillyTavern V2 character
cards (`.png` / `.json` / `.yaml`) into the two markdown files that
[Hermes-Agent](https://github.com/NousResearch/hermes-agent) loads at
startup as identity and project-context: `SOUL.md` and `HERMES.md`.

No middleware, no patches, no relays. Drop a card in, get the markdown
out, point Hermes at it, and your agent is in character — across every
gateway you've already configured (CLI, email, Telegram, Discord,
Slack, …).

**Lineage:** `TavernAI` → `SillyTavern` → **`HermesTavern`**

---

## Using it

Hermes is a competent AI agent — it understands intent, downloads
attachments, runs the right tool. Once HermesTavern is installed,
the entire UX is conversational. No commands to memorize.

In your Hermes chat (Telegram, Discord, QQ, email — any channel
Hermes already speaks on), upload the card file and say what you want:

> _[aldous.png attached]_ install this character

> switch to alice

> forget all characters, go back to default Hermes

That's the whole surface area. Hermes parses what you mean, calls
`hermes-tavern` under the hood, and tells you to run `/new` or
`/reset` when the change is ready to load. Anything ambiguous, just
clarify in plain language — Hermes handles the rest.

## Install

One file upload. No terminal once Hermes is running:

```bash
git clone https://github.com/imphillip/hermes-tavern.git
cd hermes-tavern && zip -r hermes-tavern-skills.zip skills/
```

In your Hermes chat, upload `hermes-tavern-skills.zip` and say
**"install this skill"**. Zip the whole `skills/` directory, not
individual sub-skills — Hermes expects the `skills/<name>/SKILL.md`
layout and uses the bundled wheel under
`skills/hermes-tavern/assets/` to put the `hermes-tavern` CLI on PATH.

From here on, every interaction is just upload-and-talk as shown above.

### Or via Hermes hub

If your Hermes is set up with the hub `tap` system:

```bash
hermes skills tap add imphillip/hermes-tavern
hermes skills install hermes-tavern hermes-tavern-cards
```

### Bootstrap: installing the CLI on the host

Only needed when Hermes itself isn't around to do the install for you
(setting up a fresh Hermes machine, or installing the CLI on a
different host):

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
bash skills/hermes-tavern/scripts/install.sh
```

Idempotent — tries `pipx` → `uv tool` → a dedicated venv at
`~/.local/share/hermes-tavern-venv` with a shim in `~/.local/bin`.
Override with `HERMES_TAVERN_VENV` / `HERMES_TAVERN_BIN`. When
`hermes-tavern` lands on PyPI, this collapses to
`pipx install hermes-tavern` and the bundled wheels go away.

### Requirements

- Python ≥ 3.10
- A working [`hermes`](https://github.com/NousResearch/hermes-agent) CLI
  if you want distillation for oversized cards (default
  `--distill-cmd "hermes -q"`; override with `--distill-cmd` or skip
  with `--no-distill`)

---

## Why

Hermes already auto-loads `SOUL.md` (independent identity slot) and
`HERMES.md` (cwd-relative project context slot) into its system prompt
on every session start. The only thing missing is a converter that
respects the SillyTavern V2 schema, the placeholder grammar
(`{{char}}`, `{{user}}`, `<BOT>`, `<USER>`), and the lorebook layout.
That's HermesTavern.

What we deliberately don't do:

- patch Hermes
- write a middleware / relay
- touch channel configuration (`platform_toolsets`, allowlists, …)
- start or supervise the Hermes process
- write to `AGENTS.md`, `MEMORY.md`, `USER.md`, or `CLAUDE.md`

## Features

- **V2 + V1 + PNG + YAML parsing** — every container shape SillyTavern
  emits in the wild
- **Placeholder substitution** — `{{char}}` / `{{user}}` plus the
  legacy `<BOT>` / `<USER>`, case-insensitive, non-recursive
- **Lorebook → HERMES.md rendering** — entries sorted by
  `insertion_order`, disabled entries skipped, oversize tail-truncated
- **Identity directive** — auto-injected at the top of every SOUL.md to
  override hermes's hard-coded "you are an AI assistant" framing, so
  the model just answers as the character instead of "I'm an AI; if
  we're roleplaying, I'm portraying X"
- **Three security layers** — visible trust banner, parse-time
  sanitiser (zero-width / RTL-override / control-char strip), red-flag
  pattern scan with prompt-injection categories
- **Distillation pipeline** — when a card overflows 75% of the Hermes
  20k slot, shells out to `hermes -q` to compress the prompt-loaded
  portion and lays out the full original content for runtime retrieval
- **Card library** — list / current / switch / delete / restore over
  the cards imported into a `HERMES_HOME`
- **Snapshot history** — every `import` / `switch` / `revert` is
  captured under `cards/.snapshots/`, with a special `pristine`
  snapshot of the pre-HermesTavern state. `revert --to pristine` /
  `--previous` / `--to <id|name>` walks the history
- **Channel-agnostic** — produces the persona files Hermes loads at
  startup; everything Hermes can talk on is automatically in character

## Common workflows

```bash
# Sanity-check a card (parse + render + scan, no writes)
hermes-tavern validate --card aldous.png

# Preview the rendered markdown
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --dry-run

# Replace an existing persona
hermes-tavern import --card alice.png --home ~/.hermes-roleplay --overwrite

# Library management
hermes-tavern list    --home ~/.hermes-roleplay [--all]
hermes-tavern current --home ~/.hermes-roleplay
hermes-tavern switch  --card alice --home ~/.hermes-roleplay
hermes-tavern delete  --card bob   --home ~/.hermes-roleplay
hermes-tavern restore --card bob   --home ~/.hermes-roleplay

# SOUL.md / HERMES.md snapshot history (every import/switch is captured)
hermes-tavern history --home ~/.hermes-roleplay
hermes-tavern revert  --home ~/.hermes-roleplay --to pristine     # back to pre-card state
hermes-tavern revert  --home ~/.hermes-roleplay --previous        # one back
hermes-tavern revert  --home ~/.hermes-roleplay --to 0003

# Trust the card author's system_prompt / post_history_instructions
# (default is to render them inside untrusted blockquotes)
hermes-tavern import ... --trust-system-prompt

# Disable distillation for oversized cards (surface the budget error)
hermes-tavern import ... --no-distill

# Use a different distillation command
hermes-tavern import ... --distill-cmd "claude -p"
```

`switch` / `delete` / `restore` accept either a filename or the
character name (case-insensitive prefix match against the parsed `name`
or filename stem).

## Operating modes

HermesTavern picks one of two modes per card based on the rendered
size. The threshold is 75% of the Hermes 20k slot — i.e. 15,000 chars
— for **either** SOUL.md or HERMES.md.

### Normal mode (rendered output ≤ 15k per slot)

```
<HERMES_HOME>/
├── SOUL.md                          ← rendered persona
├── HERMES.md                        ← rendered lorebook (only if the
│                                       card has a character_book)
└── cards/
    ├── .active.json                 ← currently active card pointer
    ├── .snapshots/<NNNN>_…/         ← SOUL.md / HERMES.md history
    ├── .trash/                      ← soft-deleted cards (delete/restore)
    └── <name>_<ts>.<ext>            ← original card backup
```

### Distillation mode (rendered SOUL or HERMES > 15k)

HermesTavern shells out to your already-configured Hermes CLI (default
`hermes -q`) for a one-shot LLM compression of the rendered output,
then lays the **full original** content per-field on disk for runtime
retrieval by the model.

```
<HERMES_HOME>/
├── SOUL.md                          ← LLM-distilled persona (compact)
├── HERMES.md                        ← distilled lore + extended-file index
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← original card backup
    └── <name>_<ts>/
        └── extended/                ← full original content, per-field
            ├── description.md
            ├── personality.md
            ├── scenario.md
            ├── first_mes.md
            ├── mes_example.md
            ├── system_prompt.md
            ├── post_history_instructions.md
            ├── alternate_greetings/01.md, 02.md, ...
            └── lore/<entry-slug>.md
```

The model reads SOUL.md and HERMES.md statically at session start, then
opens specific `extended/...md` files only when the conversation calls
for those details — that's why `cd $HERMES_HOME` matters even more
here (HERMES.md is the index that points at the per-field files).

Opt out of distillation with `--no-distill` (surfaces the original
budget error). Override the distillation command with
`--distill-cmd "<command>"`. Full pipeline lives in
[`skills/hermes-tavern/references/distillation.md`](skills/hermes-tavern/references/distillation.md).

## Files HermesTavern writes — and never writes

**Writes (only inside `<HERMES_HOME>`):** the layout above. That's the
entire blast radius.

**Never writes:**

- `AGENTS.md` — shadowed by HERMES.md per Hermes's loader priority.
- `MEMORY.md`, `USER.md` — owned by the running agent's memory tool.
- `CLAUDE.md`, `.cursorrules` — other tools' territory.
- Any file outside `<HERMES_HOME>` at runtime.
- Any Hermes config / channel allowlist / `platform_toolsets` entry.

To clean a `HERMES_HOME` completely: `rm -rf <home>/{SOUL.md,HERMES.md,cards}` —
nothing leaks elsewhere.

## Documentation

The two skills are self-documenting; their `SKILL.md` and
`references/` directories contain the full operator-facing docs.

**Skills**

- [`skills/hermes-tavern/SKILL.md`](skills/hermes-tavern/SKILL.md) —
  import & validate
- [`skills/hermes-tavern-cards/SKILL.md`](skills/hermes-tavern-cards/SKILL.md) —
  list / current / switch / delete / restore

**Reference docs (loader skill)**

- [`v2-spec-summary.md`](skills/hermes-tavern/references/v2-spec-summary.md) — V2 card field cheat sheet
- [`field-mapping.md`](skills/hermes-tavern/references/field-mapping.md) — exact V2 → markdown rules
- [`usage-recipes.md`](skills/hermes-tavern/references/usage-recipes.md) — common workflows and gotchas
- [`security.md`](skills/hermes-tavern/references/security.md) — threat model + sanitiser layers
- [`distillation.md`](skills/hermes-tavern/references/distillation.md) — oversized-card pipeline

**Reference docs (cards skill)**

- [`library-layout.md`](skills/hermes-tavern-cards/references/library-layout.md) — `<HERMES_HOME>/cards/` schema, `--card` resolution

## Repository layout

```
hermes-tavern/
├── src/hermes_tavern/             Python package (the engine; bundled wheel until PyPI)
├── tests/                         pytest suite (incl. real-card smoke)
├── examples/                      local third-party cards (gitignored)
└── skills/                        Hermes-hub-discoverable skills tree
    ├── hermes-tavern/             Skill 1: import & validate
    │   ├── SKILL.md
    │   ├── references/            5 reference docs
    │   ├── scripts/               skill entry wrappers + install.sh
    │   └── assets/                bundled wheel + sample V2 card
    └── hermes-tavern-cards/       Skill 2: library management
        ├── SKILL.md
        ├── references/            library-layout doc
        ├── scripts/               skill entry wrappers + install.sh
        └── assets/                bundled wheel
```

The `skills/` subdirectory matches the `path: "skills/"` convention
used by `openai/skills` and `anthropics/skills`, so
`hermes skills tap add imphillip/hermes-tavern` works without any
extra configuration. Each skill folder uses the standard
`references/` / `scripts/` / `assets/` layout — only
categories with content are populated.

## Limitations

- **No keyword-triggered lorebook injection.** All entries are rendered
  as always-on. This trades faithfulness for simplicity and works fine
  with long-context models; oversized lorebooks are handled by
  distillation, not gating.
- **No multi-character chat in one Hermes instance.** Run a separate
  `HERMES_HOME` per character.
- **No channel-level safety controls.** Configure these on the Hermes
  side (`platform_toolsets`, allowlists, rate limits). HermesTavern
  only writes the persona files.
- **No live edits.** Hermes caches the system prompt at session start.
  Edits to `SOUL.md` / `HERMES.md` take effect on the next session or
  after `/reset` inside hermes.

## Known issues

- **Some IM clients re-encode PNG attachments on upload, destroying
  the embedded card data.** SillyTavern V2 cards keep the actual
  payload inside a PNG `tEXt` chunk; when an IM rewrites the image
  (resizing, stripping metadata, converting to a JPEG thumbnail, …),
  the chunk is gone and HermesTavern can't parse the file.
  **Workaround:** zip the PNG before uploading
  (`zip aldous.zip aldous.png`) so the IM treats it as an opaque
  binary blob and leaves the bytes untouched. Hermes can unzip and
  import from there.
- **Distillation of oversized cards can stall on safety-restricted
  models.** When a card overflows the 15k threshold HermesTavern
  shells out to `hermes -q` for an LLM compression pass. If the card
  carries adult or otherwise content-policy-touching material and
  the underlying model is heavily moderated, the call can take
  noticeably longer (retries, slow streaming, hard refusals) —
  sometimes long enough to look frozen. There's no clean fix on the
  HermesTavern side: point Hermes at a less restrictive model for
  these cards.

## Development

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                    # run the full suite
pytest -k distill         # run a subset
pytest tests/test_real_cards_smoke.py   # real-card smoke (auto-skipped without cards)
```

To run the real-card smoke against your own cards, drop them into
`examples/.local/`. That directory is gitignored — license / size /
content of community cards are too varied to redistribute, so they
stay local.

The `tests/` suite covers parse, render, substitute, sanitize, scan,
extended, distill (mocked LLM), library, CLI, and end-to-end pipeline.
Aim for green; unmocked subprocess tests use a small fake `hermes`
shell script written into a tempdir.

## Contributing

PRs welcome. Before opening one:

1. Add or update tests under `tests/` for whatever you change.
2. Run `pytest` and confirm it stays green.
3. If you change the card → markdown contract, update
   `skills/hermes-tavern/references/field-mapping.md` so the spec
   matches the code.
4. If you add a new CLI flag, mention it in the relevant `SKILL.md`
   and the README's "Common workflows" block.

Issues for design discussion, bug reports, and feature requests are
also welcome.

## Used by

[agentbox.id](https://agentbox.id) — `soul-loader`, the agentbox-blessed
soul-loading flow, installs HermesTavern under the hood. See
[`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md).

## License

[MIT](LICENSE) — © 2026 HermesTavern contributors.
