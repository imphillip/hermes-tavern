# HermesTavern

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
- **Three security layers** — visible trust banner, parse-time
  sanitiser (zero-width / RTL-override / control-char strip), red-flag
  pattern scan with prompt-injection categories
- **Distillation pipeline** — when a card overflows 75% of the Hermes
  20k slot, shells out to `hermes -q` to compress the prompt-loaded
  portion and lays out the full original content for runtime retrieval
- **Card library** — list / current / switch / delete / restore over
  the cards imported into a `HERMES_HOME`
- **Channel-agnostic** — produces the persona files Hermes loads at
  startup; everything Hermes can talk on is automatically in character

## Requirements

- Python ≥ 3.10
- A working [`hermes`](https://github.com/NousResearch/hermes-agent) CLI
  if you want distillation for oversized cards (default
  `--distill-cmd "hermes -q"`; override with `--distill-cmd` or skip
  with `--no-distill`)

## Install

`hermes-tavern` is **not yet published to PyPI**. The CLI ships as a
wheel bundled inside each skill's `assets/` and is installed via the
skill's `scripts/install.sh`:

```bash
# Install from a checked-out skill folder:
bash hermes-tavern/scripts/install.sh
# (Idempotent. The installer tries pipx → uv tool → dedicated venv +
# shim. Set HERMES_TAVERN_VENV / HERMES_TAVERN_BIN to override paths.)
```

For local development of the engine itself:

```bash
git clone <this-repo> hermes-tavern && cd hermes-tavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

When publishing to PyPI lands, `pipx install hermes-tavern` will be the
preferred path; the bundled-wheel approach will remain as a fallback for
air-gapped installs.

## Quick start

```bash
# 1. import a card
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay

# 2. launch hermes from inside HERMES_HOME
cd ~/.hermes-roleplay && HERMES_HOME=~/.hermes-roleplay hermes
```

The `cd` matters. `SOUL.md` is read from `HERMES_HOME`, but `HERMES.md`
is read from **cwd** at hermes startup. Launching hermes from anywhere
else loads the persona but not the world / lorebook / extended-file
index. HermesTavern prints this reminder after every import.

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

## Documentation

The two skills are self-documenting; their `SKILL.md` and
`references/` directories contain the full operator-facing docs.

**Skills**

- [`hermes-tavern/SKILL.md`](hermes-tavern/SKILL.md) —
  import & validate
- [`hermes-tavern-cards/SKILL.md`](hermes-tavern-cards/SKILL.md) —
  list / current / switch / delete / restore

**Reference docs (loader skill)**

- [`v2-spec-summary.md`](hermes-tavern/references/v2-spec-summary.md) — V2 card field cheat sheet
- [`field-mapping.md`](hermes-tavern/references/field-mapping.md) — exact V2 → markdown rules
- [`usage-recipes.md`](hermes-tavern/references/usage-recipes.md) — common workflows and gotchas
- [`security.md`](hermes-tavern/references/security.md) — threat model + sanitiser layers
- [`distillation.md`](hermes-tavern/references/distillation.md) — oversized-card pipeline

**Reference docs (cards skill)**

- [`library-layout.md`](hermes-tavern-cards/references/library-layout.md) — `<HERMES_HOME>/cards/` schema, `--card` resolution

## Repository layout

```
hermes-tavern/
├── src/hermes_tavern/         Python package (the engine; pip-installable)
├── tests/                     pytest suite (incl. real-card smoke)
├── examples/                  local third-party cards (gitignored)
├── hermes-tavern/             Skill 1: import & validate
│   ├── SKILL.md
│   ├── references/            5 reference docs
│   ├── scripts/               skill entry wrappers
│   └── assets/aldous_v2.json  sample V2 card
└── hermes-tavern-cards/       Skill 2: library management
    ├── SKILL.md
    ├── references/            library-layout doc
    └── scripts/               skill entry wrappers
```

Each skill folder uses the standard `references/` / `scripts/` /
`assets/` layout — only categories with content are populated.

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

## Development

```bash
git clone <this-repo> hermes-tavern && cd hermes-tavern
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

## Roadmap

- [ ] PNG export — write back into a card after editing the markdown
- [ ] Distilled-output cache so switching back to a previously-distilled card doesn't re-spend an LLM call
- [ ] Web UI for live preview
- [ ] Batch import a card library
- [ ] `revert` / `undo` to roll back to the previously-active card

## Contributing

PRs welcome. Before opening one:

1. Add or update tests under `tests/` for whatever you change.
2. Run `pytest` and confirm it stays green.
3. If you change the card → markdown contract, update
   `hermes-tavern/references/field-mapping.md` so the spec
   matches the code.
4. If you add a new CLI flag, mention it in the relevant `SKILL.md`
   and the README's "Common workflows" block.

Issues for design discussion, bug reports, and feature requests are
also welcome.

## License

[MIT](LICENSE) — © 2026 HermesTavern contributors.
