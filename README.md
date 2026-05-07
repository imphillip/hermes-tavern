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

**Lineage:** `TavernAI` → `SillyTavern` → **`HermesTavern`** → **`SoulTavern`** *(in progress)*

---

## Vision: from HermesTavern to SoulTavern

HermesTavern is the first concrete instance of a broader direction:
let any agent runtime that loads a persistent persona file at session
start pick up the entire SillyTavern card ecosystem.

We're generalizing this into **SoulTavern** — a multi-target adapter
starting with `--target hermes` (this project, unchanged) and adding
`--target openclaw` plus a generic SOUL.md fallback. The rename
happens at v1.0; until then, `hermes-tavern` keeps working as today.

### Three principles

1. **Soul portability over feature parity.** SillyTavern and RisuAI
   exist for hardcore RP. SoulTavern's job is one-way porting — take
   the thousands of community-made V2 cards and make them loadable in
   agent runtimes that don't natively speak SillyTavern. The 30-40%
   that doesn't survive (token streaming, swipe / regen / branch,
   keyword-triggered lore injection) is channel/UI machinery we
   explicitly don't chase. The 70-80% that does port covers most
   casual-to-mid RP usage.

2. **File-level adaptation is the universal interface.** Any agent
   runtime that loads markdown system-prompt files at session start
   is a candidate. Adaptation has two layers: (a) render V2 fields
   into that runtime's specific files (`SOUL.md` + `HERMES.md` for
   Hermes; `SOUL.md` + `IDENTITY.md` + `AGENTS.md` for OpenClaw), and
   (b) inject an **IDENTITY DIRECTIVE** that suppresses the runtime's
   default "I'm an AI assistant" framing. (b) is the linchpin:
   without it, the agent stays itself wearing a costume.

3. **Deterministic CLI, agent-driven LLM work.** The Python tool
   never shells out to a separate LLM (a v0.4.0 mistake corrected in
   v0.4.5). When a card overflows always-on context, the CLI stages
   `source.md` and exits with code 2; the calling agent does the V2
   categorization in its own context using its own file tools. This
   keeps the tool durable across LLM CLI evolution and gives the
   agent the same trust posture it applies to any third-party file —
   including the ability to decline policy-conflicting categories
   (their absence becomes visible in the index, an honest signal
   rather than a silent rewrite).

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

**Easiest** — download the pre-built zip from the
[latest Release](https://github.com/imphillip/hermes-tavern/releases/latest):

```bash
curl -LO https://github.com/imphillip/hermes-tavern/releases/latest/download/hermes-tavern-skills.zip
```

(Or grab it via your browser from the Releases page.)

Then in your Hermes chat, upload `hermes-tavern-skills.zip` and say
**"install this skill"**. The bundled wheel inside puts the
`hermes-tavern` CLI on PATH automatically.

From here on, every interaction is just upload-and-talk as shown above.

### Or build from HEAD

If you want unreleased changes (e.g. tracking `main`):

```bash
git clone https://github.com/imphillip/hermes-tavern.git
cd hermes-tavern && zip -r hermes-tavern-skills.zip skills/
```

Zip the whole `skills/` directory, not individual sub-skills —
Hermes expects the `skills/<name>/SKILL.md` layout. Then upload in
your Hermes chat as above.

### Or via Hermes hub

If your Hermes is set up with the hub `tap` system:

```bash
hermes skills tap add imphillip/hermes-tavern
hermes skills install hermes-tavern
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

### Uninstall

Two layers — the skill (prompt files) and the CLI (system binary). The
hub command only handles the first:

```bash
bash skills/hermes-tavern/scripts/uninstall.sh   # removes the CLI; --dry-run to preview
hermes skills uninstall hermes-tavern            # removes the skill
```

The uninstaller auto-detects pipx / uv tool / dedicated venv, refuses
to nuke arbitrary paths, and never touches your `<HERMES_HOME>/`
data (cards, SOUL.md, snapshots — those are personal content, not
install artifacts).

### Requirements

- Python ≥ 3.10
- For oversized cards, the calling agent (Hermes itself, or whichever
  agent is driving the import) reads the staged `source.md` and writes
  per-category files. No separate LLM CLI is shelled out to — the agent
  uses its own file tools.

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
- **Agent-driven oversized-card flow** — when a card overflows 75% of
  the Hermes 20k slot, `import` stages source material on disk and the
  calling agent redistributes it into V2 categories in its own context
  (no subprocess LLM call). `hermes-tavern finalize` then assembles the
  curated SOUL.md and the indexed HERMES.md.
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

# After the agent has populated extended/<category>.md for an oversized card
hermes-tavern finalize --card aldous --home ~/.hermes-roleplay
```

`switch` / `delete` / `restore` accept either a filename or the
character name (case-insensitive prefix match against the parsed `name`
or filename stem).

## Operating modes

HermesTavern picks one of two modes per card based on the rendered
size. The threshold is 75% of the Hermes 20k slot — i.e. 15,000 chars
— for **either** SOUL.md or HERMES.md.

### Small cards (rendered output ≤ 15k per slot)

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

### Oversized cards (rendered SOUL or HERMES > 15k) — agent-driven

HermesTavern does **not** shell out to a separate LLM. Instead `import`
stages the source material on disk, exits with code 2, and asks the
calling agent to redistribute that material into eight V2-aligned
categories — faithful to original wording, declining gracefully when
content conflicts with policy. After the agent writes the category
files, `hermes-tavern finalize` assembles the final SOUL.md (from a
small set of always-on picks) and HERMES.md (the category index).

```
<HERMES_HOME>/
├── SOUL.md                          ← curated picks: identity + personality + roleplay_guides
├── HERMES.md                        ← Director's notes + V2-category index
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← original card backup
    └── <name>_<ts>/
        ├── source.md                ← CLI-staged input for the agent
        └── extended/                ← V2-aligned categories
            ├── identity.md          ← name, age, ethnicity, basic facts          (agent-written)
            ├── appearance.md        ← physical description, voice                 (agent-written)
            ├── personality.md       ← traits, mannerisms, speech style            (agent-written)
            ├── backstory.md         ← past events, history, relationships         (agent-written)
            ├── scenario.md          ← the opening situation                       (agent-written)
            ├── kinks.md             ← preferences (only if present)               (agent-written)
            ├── roleplay_guides.md   ← explicit portrayal instructions             (agent-written)
            ├── examples.md          ← sample dialogue patterns                    (agent-written)
            ├── alternate_greetings/01.md, 02.md, ...                              (CLI-written)
            └── lore/<entry-slug>.md ← per character_book entry                    (CLI-written)
```

Empty categories are simply omitted (the agent either had nothing to
put in that bucket, or declined — both are observable signals via the
HERMES.md index where missing files are visible by their absence).

The model reads SOUL.md and HERMES.md statically at session start, then
opens specific `extended/...md` files only when the conversation calls
for those details — that's why `cd $HERMES_HOME` matters even more
here (HERMES.md is the index that points at the per-category files).

Full procedure, including failure modes and the `finalize` step, lives
in [`skills/hermes-tavern/references/oversized-cards.md`](skills/hermes-tavern/references/oversized-cards.md).

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

The skill is self-documenting; its `SKILL.md` and `references/`
directory contain the full operator-facing docs.

- [`skills/hermes-tavern/SKILL.md`](skills/hermes-tavern/SKILL.md) —
  import + library management (list / current / switch / delete /
  restore / history / revert) in one place

**Reference docs**

- [`v2-spec-summary.md`](skills/hermes-tavern/references/v2-spec-summary.md) — V2 card field cheat sheet
- [`field-mapping.md`](skills/hermes-tavern/references/field-mapping.md) — exact V2 → markdown rules
- [`usage-recipes.md`](skills/hermes-tavern/references/usage-recipes.md) — common workflows and gotchas
- [`security.md`](skills/hermes-tavern/references/security.md) — threat model + sanitiser layers
- [`oversized-cards.md`](skills/hermes-tavern/references/oversized-cards.md) — agent-driven categorization flow for oversized cards
- [`library-layout.md`](skills/hermes-tavern/references/library-layout.md) — `<HERMES_HOME>/cards/` schema, snapshot history, `--card` resolution

## Repository layout

```
hermes-tavern/
├── src/hermes_tavern/             Python package (the engine; bundled wheel until PyPI)
├── tests/                         pytest suite (incl. real-card smoke)
├── examples/                      local third-party cards (gitignored)
└── skills/                        Hermes-hub-discoverable skills tree
    └── hermes-tavern/             one skill: import + library management
        ├── SKILL.md
        ├── references/            6 reference docs
        ├── scripts/               skill entry wrappers + install.sh
        └── assets/                bundled wheel + sample V2 card
```

> **v0.5.0 note.** Earlier versions shipped a separate
> `hermes-tavern-cards` skill for management. It's been merged into
> `hermes-tavern` so users only install one skill and Hermes only has
> one trigger surface to route. If your `hermes skills list` still
> shows `hermes-tavern-cards`, run `hermes skills uninstall
> hermes-tavern-cards`.

The `skills/` subdirectory matches the `path: "skills/"` convention
used by `openai/skills` and `anthropics/skills`, so
`hermes skills tap add imphillip/hermes-tavern` works without any
extra configuration. Each skill folder uses the standard
`references/` / `scripts/` / `assets/` layout — only
categories with content are populated.

## Limitations

- **No keyword-triggered lorebook injection.** All entries are rendered
  as always-on. This trades faithfulness for simplicity and works fine
  with long-context models; oversized lorebooks are handled by the
  agent-driven extended-files flow, not gating.
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
- **Oversized cards on policy-restricted agents may end up with
  partial categorization.** When a card overflows the 15k threshold
  HermesTavern stages source material and asks the calling agent to
  categorize it. A policy-restricted agent may decline some categories
  (e.g. `kinks.md`) — those will be absent from the assembled
  HERMES.md index. The character will still load, but with whatever
  the agent was willing to keep. If you want a fuller pass, re-run
  the agent step against `source.md` with a different model and then
  re-run `hermes-tavern finalize`.

## Development

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                    # run the full suite
pytest -k staging         # run a subset
pytest tests/test_real_cards_smoke.py   # real-card smoke (auto-skipped without cards)
```

To run the real-card smoke against your own cards, drop them into
`examples/.local/`. That directory is gitignored — license / size /
content of community cards are too varied to redistribute, so they
stay local.

The `tests/` suite covers parse, render, substitute, sanitize, scan,
classify, staging, extended, finalize, library, CLI, and end-to-end
pipeline. Aim for green.

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
