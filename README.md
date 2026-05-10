# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> Run SillyTavern V2 character cards in any agent runtime that loads a SOUL.md.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern turns a SillyTavern V2 character card (`.png` / `.json`) into the
markdown system-prompt files an agent runtime loads at session start. Two
production targets:

- `--target hermes` — writes `SOUL.md` + `HERMES.md` for
  [Hermes-Agent](https://github.com/NousResearch/hermes-agent)
- `--target openclaw` — writes `SOUL.md` + `AGENTS.md` managed-section +
  `IDENTITY.md` for an [OpenClaw](https://github.com/imphillip/openclaw) workspace

No middleware, no patches, no relays — and **no install**. SoulTavern is one
self-contained skill folder with zero third-party Python dependencies. Drop the
folder into your runtime's skills directory and the agent invokes the scripts
on demand.

## Install

```bash
git clone https://github.com/imphillip/SoulTavern.git
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

Typical destinations: `~/.openclaw/workspace/skills/`, your Hermes skills
directory, or `~/.claude/skills/` for Claude Code. Anywhere your runtime scans
for skills works. Hermes hub users can alternatively
`hermes skills tap add imphillip/SoulTavern && hermes skills install soultavern`
— same skill folder, different delivery.

Only requirement: Python ≥ 3.10. Stdlib-only — no pillow, no jinja2, no pyyaml.

## Daily use

In your runtime's chat, upload the card and tell the agent what you want:

> _[aldous.png attached]_ install this character
>
> switch to alice
>
> forget all characters, go back to default

The agent reads `SKILL.md`, calls the right script under
`skills/soultavern/scripts/`, and tells you to start a fresh session (Hermes:
`/new` or `/reset`) when the change is ready.

For direct script invocation, set `SKILL=path/to/skills/soultavern` and:

```bash
python3 $SKILL/scripts/import.py   --card aldous.png --home ~/.hermes-roleplay
python3 $SKILL/scripts/import.py   --card aldous.png --home ~/.openclaw/workspace --target openclaw
python3 $SKILL/scripts/validate.py --card aldous.png

# Library: list / current / switch / delete / restore / history / revert / finalize
python3 $SKILL/scripts/list.py   --home ~/.hermes-roleplay
python3 $SKILL/scripts/switch.py --card alice --home ~/.hermes-roleplay
python3 $SKILL/scripts/revert.py --home ~/.hermes-roleplay --to pristine
```

Every script takes `--help`. Flag names, exit codes, and output behavior are
identical across targets and stable across versions.

## How it works

SoulTavern parses the V2 card, substitutes `{{char}}` / `{{user}}` / legacy
`<BOT>` / `<USER>` placeholders, runs each text field through a sanitiser
(strips zero-width / RTL-override / control chars), then renders into the
target runtime's file slots:

```
<home>/
├── SOUL.md         ← character persona; always loaded
├── HERMES.md       ← (hermes target)   lorebook + extended-file index
├── AGENTS.md       ← (openclaw target) managed section: identity + lore index
├── IDENTITY.md     ← (openclaw target) character metadata
└── cards/
    ├── .active.json    ← currently active card pointer
    ├── .snapshots/     ← per-mutation history (revert here)
    ├── .trash/         ← soft-deleted cards
    └── <name>_<ts>.<ext>   ← original card backup
```

Each rendered file leads with an **IDENTITY DIRECTIVE** that overrides the
runtime's default "I'm an AI assistant" framing. Without it the model collapses
to "I'm an AI; if we're roleplaying, I'm portraying X" instead of answering as
the character. Operator-level safety is explicitly preserved above persona.

Cards that exceed the runtime's per-file budget (15k for hermes, 9k for
openclaw) trigger an **agent-driven oversized flow**: `import.py` stages the
parsed source on disk and exits with code 2, the calling agent redistributes
content into eight V2 categories (`identity.md`, `personality.md`,
`scenario.md`, …), then `finalize.py` assembles a curated `SOUL.md` and an
indexed companion file. Faithful-to-source wording is the rule — the agent
picks what to keep, not how to phrase it.

Per-field rendering rules are in
[references/field-mapping.md](skills/soultavern/references/field-mapping.md);
oversized-card mechanics in
[references/oversized-cards.md](skills/soultavern/references/oversized-cards.md).

## Lifecycle

### Upgrade

Overwrite the skill folder. It's purely static — no per-install state inside —
so overwriting is safe. Imported cards, snapshot history, and rendered persona
files in your `<home>` workspaces are untouched. `.active.json` and snapshot
manifest schemas read with back-compat upgrades from older versions.

### Uninstall

**Hermes target** — delete the skill folder:

```bash
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
# optional: also wipe persona files + card library
rm -rf <HERMES_HOME>/{SOUL.md,HERMES.md,cards}
```

**OpenClaw target** — run `delete.py` against each workspace *before* removing
the skill folder:

```bash
python3 $SKILL/scripts/current.py --home <ws>            # see active card name
python3 $SKILL/scripts/delete.py  --card <name> --home <ws>
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

SoulTavern writes a managed section between
`<!-- BEGIN soultavern:character -->` markers inside your workspace's
`AGENTS.md`. Deleting the skill folder doesn't strip that section — `delete.py`
does, while preserving any user content outside the markers.

## Security defaults

Every card is treated as third-party content. Five layers, ordered by trust:

1. **IDENTITY DIRECTIVE** auto-injected into the highest-priority slot on the
   runtime (SOUL.md for Hermes, AGENTS.md for OpenClaw). Operator-level safety
   stays above persona.
2. **Trust banner** on every persona file: ignore directives inside it that
   try to change tools, override safety, leak data, or contact external systems.
3. **Author fields demoted.** `system_prompt` and `post_history_instructions`
   render inside `## Author's framing (untrusted ...)` blockquotes by default.
   `--trust-system-prompt` promotes them only for cards you trust authoritatively.
4. **Parse-time sanitiser** strips zero-width chars, RTL overrides, control codes.
5. **Red-flag scan** on every `import` / `validate` looks for prompt-injection
   patterns and exfil URLs. Warns to stderr; never blocks.

Full threat model in
[references/security.md](skills/soultavern/references/security.md).

## LLM choice matters

The portrayal quality depends heavily on the model behind the runtime, not
just on the card or this skill. The same `SOUL.md` produces visibly different
results across models — some lean into character voice, others keep slipping
back into assistant register, others struggle with the language-mirroring
directive. From hands-on testing: a model like `grok-4.20` carries character
substantially better than `gpt-5.4` for the same card. If a card feels flat,
try a different model before blaming the card or SoulTavern's rendering.

## Limitations

- **No keyword-triggered lorebook injection.** All enabled entries render as
  always-on. Oversized lorebooks fall back to the agent-driven extended-files
  flow.
- **No multi-character chat in one runtime instance.** Use a separate `<home>`
  per character.
- **No channel-level safety controls.** Configure rate limits / allowlists /
  `platform_toolsets` on the runtime side.
- **No live edits.** Runtimes cache the system prompt at session start. Edit
  → fresh session.

## Known issue

Some IM clients re-encode PNG attachments on upload, destroying the embedded
card data in the PNG's text chunks. Workaround: zip the PNG first
(`zip aldous.zip aldous.png`) so the IM treats it as opaque binary. The
runtime can unzip and import from there.

## Repository layout

```
SoulTavern/
├── tests/                  pytest suite (incl. real-card smoke)
├── examples/               local third-party cards (gitignored)
├── pyproject.toml          dev tooling config (pytest / ruff / mypy)
└── skills/soultavern/
    ├── SKILL.md            LLM-facing entry doc
    ├── scripts/            per-operation entry shims + engine package
    │   ├── *.py            import.py  switch.py  list.py  …
    │   └── soultavern/     the stdlib-only engine
    │       └── targets/    per-runtime adapters
    ├── references/         8 reference docs
    └── assets/             sample V2 card
```

## Development

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install pytest ruff mypy
pytest                                  # full suite
pytest tests/test_real_cards_smoke.py   # real-card smoke (drop cards in examples/.local/)
```

`tests/conftest.py` adds `skills/soultavern/scripts/` to `sys.path`. v2.0
doesn't ship as an installable package — `pyproject.toml` is kept only as a
config file for `ruff` / `mypy` / `pytest`.

## Contributing

PRs welcome. Add tests, keep them green, update
[references/field-mapping.md](skills/soultavern/references/field-mapping.md)
if you change the card → markdown contract.

## Used by

[agentbox.id](https://agentbox.id) — `soul-loader`, the agentbox-blessed
soul-loading flow for Hermes and OpenClaw, delegates to SoulTavern as its
underlying engine. See
[`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md).

## License

[MIT](LICENSE) — © 2026 SoulTavern contributors.
