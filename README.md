# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> Run your SillyTavern characters in any agent runtime that loads a SOUL.md.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern is a one-shot importer that turns SillyTavern V2 character
cards (`.png` / `.json`) into the markdown system-prompt files an
agent runtime loads at startup. v2.0 ships with two functional
targets: `--target hermes` (writes `SOUL.md` + `HERMES.md` for
[Hermes-Agent](https://github.com/NousResearch/hermes-agent)) and
`--target openclaw` (writes `SOUL.md` + `AGENTS.md` managed-section +
`IDENTITY.md` for an [OpenClaw](https://github.com/imphillip/openclaw)
workspace).

No middleware, no patches, no relays, and **no install.** SoulTavern is
a single self-contained skill folder with zero third-party Python
dependencies. Drop the folder where your runtime reads skills from,
invoke the scripts directly — done.

**Lineage:** `TavernAI` → `SillyTavern` → `HermesTavern` → **`SoulTavern`**

> SoulTavern v2.0 collapses to skill-folder-only distribution. The
> `soultavern` CLI on PATH (and the `hermes-tavern` backward-compat
> alias) are gone — every operation is a script under
> `skills/soultavern/scripts/`. Output for `--target hermes` and
> `--target openclaw` matches v1.0 byte-for-byte; only the way you
> invoke it changed. See [CHANGELOG.md](CHANGELOG.md#200) for migration.

---

## Vision: from HermesTavern to SoulTavern

HermesTavern is the first concrete instance of a broader direction:
let any agent runtime that loads a persistent persona file at session
start pick up the entire SillyTavern card ecosystem.

**SoulTavern** is the multi-target generalization. Two production
targets ship today: `--target hermes` (default; writes `SOUL.md` +
`HERMES.md`) and `--target openclaw` (writes `SOUL.md` + `AGENTS.md`
managed-section + `IDENTITY.md`). A `--target generic` fallback for
unspecified runtimes is registered as a skeleton and lands in a later
release.

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

3. **Deterministic tool, agent-driven LLM work.** The Python scripts
   never shell out to a separate LLM (a v0.4.0 mistake corrected in
   v0.4.5). When a card overflows always-on context, `import.py`
   stages `source.md` and exits with code 2; the calling agent does
   the V2 categorization in its own context using its own file tools.
   This keeps the tool durable across LLM CLI evolution and gives the
   agent the same trust posture it applies to any third-party file —
   including the ability to decline policy-conflicting categories
   (their absence becomes visible in the index, an honest signal
   rather than a silent rewrite).

---

## Using it

Once your runtime knows where the SoulTavern skill folder is, the
entire UX is conversational. In your runtime's chat, upload the card
file and say what you want:

> _[aldous.png attached]_ install this character

> switch to alice

> forget all characters, go back to default

That's the whole surface area. The runtime parses what you mean, calls
the right SoulTavern script under the hood, and tells you to start a
fresh session (`/new` or `/reset` for Hermes) when the change is ready
to load. Anything ambiguous — just clarify in plain language.

## Install

**There is no install step.** SoulTavern is a skill folder with no
runtime dependencies beyond Python ≥ 3.10. Drop the folder where your
runtime reads skills from and you're done.

```bash
git clone https://github.com/imphillip/SoulTavern.git
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

That's it. The runtime's agent reads `skills/soultavern/SKILL.md` and
invokes `python3 .../scripts/import.py` (etc.) on demand. No PATH
manipulation, no wheel build, no `pipx`, no global state.

`<YOUR_RUNTIME_SKILLS_DIR>` depends on the runtime: typical examples
are `~/.openclaw/workspace/skills/`, your Hermes skills directory, or
`~/.claude/skills/` for Claude Code. Anywhere the runtime scans for
skills works.

### Or via runtime skill hub

If your runtime supports a hub-style "tap" system (e.g. Hermes):

```bash
hermes skills tap add imphillip/SoulTavern
hermes skills install soultavern
```

The hub installer drops the same skill folder; nothing else happens.

### Uninstall

Delete the skill folder (or run your runtime's `skills uninstall`).
The skill never writes outside its own folder during install — your
imported cards, SOUL.md, and snapshots live in your `<home>/`
workspace and are unaffected.

### Requirements

- Python ≥ 3.10 (stdlib only — no pillow, no jinja2, no pyyaml, no
  third-party deps).
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
That's SoulTavern's `--target hermes`.

OpenClaw has the analogous setup — `SOUL.md` + `AGENTS.md` +
`IDENTITY.md` are read into the bootstrap budget at session start —
with a different loader-priority order (AGENTS.md outranks SOUL.md, so
the IDENTITY DIRECTIVE has to live there). That's `--target openclaw`.

What we deliberately don't do:

- patch the runtime
- write a middleware / relay
- touch channel configuration (`platform_toolsets`, allowlists, …)
- start or supervise the runtime process
- write to `MEMORY.md`, `USER.md`, or `CLAUDE.md`
- write to `AGENTS.md` outside of the openclaw target's marker-bounded
  managed section

## Features

- **V2 + V1 + PNG parsing** — every JSON / PNG container shape
  SillyTavern emits in the wild (YAML support dropped in v2.0;
  ecosystem usage was negligible)
- **Placeholder substitution** — `{{char}}` / `{{user}}` plus the
  legacy `<BOT>` / `<USER>`, case-insensitive, non-recursive
- **Lorebook rendering** — entries sorted by `insertion_order`,
  disabled entries skipped, oversize tail-truncated. Lands in
  `HERMES.md` (hermes target) or the `AGENTS.md` managed section
  (openclaw target).
- **Identity directive** — auto-injected into whichever file has the
  highest loader priority on the runtime (SOUL.md for Hermes, AGENTS.md
  for OpenClaw). Overrides the runtime's hard-coded "you are an AI
  assistant" framing so the model just answers as the character
  instead of "I'm an AI; if we're roleplaying, I'm portraying X".
- **Three security layers** — visible trust banner, parse-time
  sanitiser (zero-width / RTL-override / control-char strip), red-flag
  pattern scan with prompt-injection categories
- **Agent-driven oversized-card flow** — when a card overflows the
  runtime's per-file budget, `import.py` stages source material on
  disk and the calling agent redistributes it into V2 categories in
  its own context (no subprocess LLM call). `finalize.py` then
  assembles the curated SOUL.md and the indexed companion file.
- **Card library** — list / current / switch / delete / restore over
  the cards imported into a `<home>` directory (`HERMES_HOME` for
  hermes, OpenClaw workspace dir for openclaw)
- **Snapshot history** — every `import` / `switch` / `revert` is
  captured under `cards/.snapshots/`, with a special `pristine`
  snapshot of the pre-import state. `revert --to pristine` /
  `--previous` / `--to <id|name>` walks the history
- **Channel-agnostic** — produces the persona files the runtime
  loads at session start; everything the runtime can talk on is
  automatically in character

## Common workflows

Set `SKILL=path/to/skills/soultavern` first, then:

```bash
# Sanity-check a card (parse + render + scan, no writes)
python3 $SKILL/scripts/validate.py --card aldous.png

# Preview the rendered markdown
python3 $SKILL/scripts/import.py --card aldous.png --home ~/.hermes-roleplay --dry-run

# Replace an existing persona
python3 $SKILL/scripts/import.py --card alice.png --home ~/.hermes-roleplay --overwrite

# Library management
python3 $SKILL/scripts/list.py    --home ~/.hermes-roleplay [--all]
python3 $SKILL/scripts/current.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/switch.py  --card alice --home ~/.hermes-roleplay
python3 $SKILL/scripts/delete.py  --card bob   --home ~/.hermes-roleplay
python3 $SKILL/scripts/restore.py --card bob   --home ~/.hermes-roleplay

# Snapshot history (every import/switch is captured)
python3 $SKILL/scripts/history.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to pristine
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --previous
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to 0003

# Trust the card author's system_prompt / post_history_instructions
# (default is to render them inside untrusted blockquotes)
python3 $SKILL/scripts/import.py ... --trust-system-prompt

# After the agent has populated extended/<category>.md for an oversized card
python3 $SKILL/scripts/finalize.py --card aldous --home ~/.hermes-roleplay
```

`switch` / `delete` / `restore` accept either a filename or the
character name (case-insensitive prefix match against the parsed `name`
or filename stem).

## Operating modes

SoulTavern picks one of two modes per card based on the rendered
size. The threshold is 75% of the runtime's per-file slot — 15,000
chars for `--target hermes`, 9,000 for `--target openclaw` (see
`references/openclaw-target.md`).

### Small cards (rendered output below the threshold)

`--target hermes` layout:

```
<home>/
├── SOUL.md                          ← rendered persona
├── HERMES.md                        ← rendered lorebook (only if the
│                                       card has a character_book)
└── cards/
    ├── .active.json                 ← currently active card pointer
    ├── .snapshots/<NNNN>_…/         ← persona-file history
    ├── .trash/                      ← soft-deleted cards (delete/restore)
    └── <name>_<ts>.<ext>            ← original card backup
```

`--target openclaw` adds `IDENTITY.md` (character metadata) and writes
the lorebook as a managed section inside `AGENTS.md` instead of a
separate `HERMES.md`. See `references/openclaw-target.md` for the
file-by-file breakdown.

### Oversized cards — agent-driven

SoulTavern does **not** shell out to a separate LLM. Instead
`import.py` stages the source material on disk, exits with code 2,
and asks the calling agent to redistribute that material into eight
V2-aligned categories — faithful to original wording, declining
gracefully when content conflicts with policy. After the agent writes
the category files, `finalize.py` assembles the final SOUL.md (from a
small set of always-on picks) and the companion file (the category
index).

```
<home>/
├── SOUL.md                          ← curated picks: identity + personality + roleplay_guides
├── <companion>                      ← Director's notes + V2-category index
│                                       (HERMES.md or AGENTS.md managed section)
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← original card backup
    └── <name>_<ts>/
        ├── source.md                ← script-staged input for the agent
        └── extended/                ← V2-aligned categories
            ├── identity.md          ← name, age, ethnicity, basic facts          (agent-written)
            ├── appearance.md        ← physical description, voice                 (agent-written)
            ├── personality.md       ← traits, mannerisms, speech style            (agent-written)
            ├── backstory.md         ← past events, history, relationships         (agent-written)
            ├── scenario.md          ← the opening situation                       (agent-written)
            ├── kinks.md             ← preferences (only if present)               (agent-written)
            ├── roleplay_guides.md   ← explicit portrayal instructions             (agent-written)
            ├── examples.md          ← sample dialogue patterns                    (agent-written)
            ├── alternate_greetings/01.md, 02.md, ...                              (script-written)
            └── lore/<entry-slug>.md ← per character_book entry                    (script-written)
```

Empty categories are simply omitted (the agent either had nothing to
put in that bucket, or declined — both are observable signals via the
companion-file index where missing files are visible by their absence).

The model reads SOUL.md and the companion file statically at session
start, then opens specific `extended/...md` files only when the
conversation calls for those details. For Hermes that means launching
from inside `$HERMES_HOME` (HERMES.md is read from cwd, not from
HERMES_HOME — the index that points at the per-category files needs
to be visible).

Full procedure, including failure modes and the `finalize` step, lives
in [`skills/soultavern/references/oversized-cards.md`](skills/soultavern/references/oversized-cards.md).

## Files SoulTavern writes — and never writes

**Writes (only inside `<home>`):** the layout above. That's the
entire blast radius.

**Never writes (`--target hermes`):**

- `AGENTS.md` — shadowed by HERMES.md per Hermes's loader priority.
- `MEMORY.md`, `USER.md` — owned by the running agent's memory tool.
- `CLAUDE.md`, `.cursorrules` — other tools' territory.
- Any file outside `<home>` at runtime.
- Any runtime config / channel allowlist / `platform_toolsets` entry.

**Writes (`--target openclaw`):** SOUL.md (full replace), AGENTS.md
(only the section between `<!-- BEGIN soultavern:character -->`
markers — existing user content outside the markers is preserved),
IDENTITY.md (full replace).

To clean a `<home>` completely: `rm -rf <home>/{SOUL.md,HERMES.md,IDENTITY.md,cards}`,
plus strip the soultavern managed section from any AGENTS.md.
Nothing leaks elsewhere.

## Documentation

The skill is self-documenting; its `SKILL.md` and `references/`
directory contain the full operator-facing docs.

- [`skills/soultavern/SKILL.md`](skills/soultavern/SKILL.md) —
  import + library management (list / current / switch / delete /
  restore / history / revert) in one place

**Reference docs**

- [`v2-spec-summary.md`](skills/soultavern/references/v2-spec-summary.md) — V2 card field cheat sheet
- [`field-mapping.md`](skills/soultavern/references/field-mapping.md) — exact V2 → markdown rules
- [`usage-recipes.md`](skills/soultavern/references/usage-recipes.md) — common workflows and gotchas
- [`security.md`](skills/soultavern/references/security.md) — threat model + sanitiser layers
- [`oversized-cards.md`](skills/soultavern/references/oversized-cards.md) — agent-driven categorization flow for oversized cards
- [`library-layout.md`](skills/soultavern/references/library-layout.md) — `<home>/cards/` schema, snapshot history, `--card` resolution
- [`openclaw-target.md`](skills/soultavern/references/openclaw-target.md) — OpenClaw target file layout, write strategy, budget constants
- [`openclaw-identity-directive.md`](skills/soultavern/references/openclaw-identity-directive.md) — OpenClaw IDENTITY DIRECTIVE wording + iteration playbook

## Repository layout

```
SoulTavern/
├── tests/                         pytest suite (incl. real-card smoke)
├── examples/                      local third-party cards (gitignored)
├── pyproject.toml                 dev tooling config (pytest / ruff / mypy)
└── skills/                        skills tree
    └── soultavern/                one skill: import + library management
        ├── SKILL.md               LLM-facing entry doc
        ├── scripts/               per-operation entry points + the engine package
        │   ├── import.py  switch.py  list.py  …    thin shims the LLM invokes
        │   └── soultavern/        the Python package (stdlib only)
        │       └── targets/       per-runtime adapters (hermes / openclaw / generic)
        ├── references/            8 reference docs
        └── assets/                sample V2 card
```

> **v2.0.0 break.** The `soultavern` CLI is gone. Operations are now
> scripts under `skills/soultavern/scripts/`. The Python package moved
> from `src/soultavern/` to `skills/soultavern/scripts/soultavern/`. Wheel
> distribution, install.sh, and the `hermes-tavern` backward-compat
> alias are all removed. See [CHANGELOG.md](CHANGELOG.md#200) for the
> full migration.

> **v1.0.0 rename.** Pre-v1.0 the project was named **HermesTavern**
> (single-target, Hermes-Agent only). v1.0 rebranded as **SoulTavern**
> with multi-target support.

> **v0.5.0 note.** Earlier versions shipped a separate
> `hermes-tavern-cards` skill for management. It was merged into the
> main skill in v0.5.0.

The `skills/` subdirectory matches the `path: "skills/"` convention
used by `openai/skills` and `anthropics/skills`, so a runtime that
supports tap-style skill discovery works without any extra configuration.
Each skill folder uses the standard `references/` / `scripts/` /
`assets/` layout — only categories with content are populated.

## Limitations

- **No keyword-triggered lorebook injection.** All entries are rendered
  as always-on. This trades faithfulness for simplicity and works fine
  with long-context models; oversized lorebooks are handled by the
  agent-driven extended-files flow, not gating.
- **No multi-character chat in one runtime instance.** Run a separate
  `<home>` per character.
- **No channel-level safety controls.** Configure these on the runtime
  side (Hermes's `platform_toolsets`, allowlists, rate limits, etc.).
  SoulTavern only writes the persona files.
- **No live edits.** Runtimes cache the system prompt at session start.
  Edits to the persona files take effect on the next session (or after
  `/reset` inside Hermes).

## Known issues

- **Some IM clients re-encode PNG attachments on upload, destroying
  the embedded card data.** SillyTavern V2 cards keep the actual
  payload inside a PNG `tEXt` chunk; when an IM rewrites the image
  (resizing, stripping metadata, converting to a JPEG thumbnail, …),
  the chunk is gone and SoulTavern can't parse the file.
  **Workaround:** zip the PNG before uploading
  (`zip aldous.zip aldous.png`) so the IM treats it as an opaque
  binary blob and leaves the bytes untouched. The runtime can unzip
  and import from there.
- **Oversized cards on policy-restricted agents may end up with
  partial categorization.** When a card overflows the per-runtime
  threshold (15k for hermes, 9k for openclaw), SoulTavern stages
  source material and asks the calling agent to categorize it. A
  policy-restricted agent may decline some categories (e.g.
  `kinks.md`) — those will be absent from the assembled companion
  index. The character will still load, but with whatever the agent
  was willing to keep. If you want a fuller pass, re-run the agent
  step against `source.md` with a different model and then re-run
  `finalize.py`.

## Development

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"      # only pytest / ruff / mypy — no runtime deps

pytest                    # run the full suite
pytest -k staging         # run a subset
pytest tests/test_real_cards_smoke.py   # real-card smoke (auto-skipped without cards)
```

`tests/conftest.py` adds `skills/soultavern/scripts/` to `sys.path`, so
imports like `from soultavern.parse import load_card` work without any
`pip install -e .` step. The runtime package itself has zero third-party
dependencies — `[dev]` is only the test/lint toolchain.

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
   `skills/soultavern/references/field-mapping.md` so the spec
   matches the code.
4. If you add a new flag to one of the `scripts/*.py` entry points,
   mention it in the relevant `SKILL.md` and the README's "Common
   workflows" block.

Issues for design discussion, bug reports, and feature requests are
also welcome.

## Used by

[agentbox.id](https://agentbox.id) — `soul-loader`, the agentbox-blessed
soul-loading flow for Hermes and OpenClaw, delegates to SoulTavern as
its underlying engine. See
[`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md).

## License

[MIT](LICENSE) — © 2026 SoulTavern contributors.
