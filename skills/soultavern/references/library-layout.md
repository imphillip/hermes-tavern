# `<home>/cards/` library layout

The library is created the first time `import.py` runs. All `list` /
`current` / `switch` / `delete` / `restore` / `history` / `revert`
scripts operate inside this directory. `<home>` is the runtime home
directory: `HERMES_HOME` for `--target hermes`, the OpenClaw workspace
dir for `--target openclaw`.

**Small cards** (rendered output below the per-runtime threshold —
15k for hermes, 9k for openclaw):

```
<home>/
├── SOUL.md                        # rendered persona (active character)
├── <companion>                    # rendered lorebook (optional)
│                                  #   HERMES.md (hermes target) or
│                                  #   AGENTS.md managed section (openclaw target)
├── IDENTITY.md                    # openclaw target only — character metadata
└── cards/
    ├── .active.json               # pointer to currently active card
    ├── .trash/                    # soft-deleted card payloads
    │   └── <name>_<ts>.<ext>
    ├── <name>_<ts>.json           # imported card backups
    └── <name>_<ts>.png
```

**Oversized cards** (triggered when the rendered SOUL or companion
file would exceed the per-runtime threshold — `import.py` stages
source material on disk and the calling agent writes the V2-category
files; `finalize.py` then assembles the curated SOUL.md and indexed
companion file):

```
<home>/
├── SOUL.md                        # curated persona (identity + personality + roleplay_guides)
├── <companion>                    # index pointing into extended/
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>          # original card backup
    └── <name>_<ts>/
        ├── source.md              # script-staged input for the agent
        └── extended/
            ├── identity.md ... examples.md   # agent-written V2 categories
            ├── alternate_greetings/01.md ... # script-staged at import time
            └── lore/<entry>.md ...           # script-staged at import time
```

For `--target hermes`, `AGENTS.md` is intentionally never written —
Hermes loads `AGENTS.md` only when `HERMES.md` is absent, so any
references inside `AGENTS.md` would never reach the model. The
oversized-card flow merges the index into `HERMES.md`.

For `--target openclaw`, the equivalent index lands in the AGENTS.md
managed section (the segment between `<!-- BEGIN soultavern:character -->`
markers); user content outside the markers is preserved on every
import / switch / delete / revert.

See `oversized-cards.md` for the full rationale, the agent procedure,
and failure modes.

## Launch posture

For `--target hermes`: `HERMES.md` is read relative to **cwd** at
hermes startup, not `HERMES_HOME`. Users must `cd $HERMES_HOME` before
running `hermes` or the lorebook / extended-file index won't be loaded.
`SOUL.md` is the exception — it's anchored to `HERMES_HOME` regardless
of cwd.

For `--target openclaw`: all three files (`SOUL.md`, `AGENTS.md`,
`IDENTITY.md`) are read from the workspace root that the runtime is
launched against — there's no separate cwd vs. home split.

If the runtime is already running when persona files are updated, the
model's system prompt is cached at session start — the new files don't
apply automatically. The user starts a fresh session (Hermes: `/new`
or `/reset`). SoulTavern prints this reminder to stderr after every
`import` / `switch` / `revert`.

## `.snapshots/` — persona-file history

Every `import` / `switch` / `revert` captures the resulting on-disk
state into `cards/.snapshots/<NNNN>_<ts>_<name>/`. Before the very
first mutation, a special `pristine` snapshot records the
pre-SoulTavern state (which may legitimately be "no SOUL.md or
companion file existed"):

```
<home>/cards/.snapshots/
├── 0001_pristine/
│   ├── manifest.json
│   └── (SOUL.md / companion file if they existed pre-SoulTavern)
├── 0002_20260502T130000_Aldous/
│   ├── manifest.json
│   ├── SOUL.md
│   └── (companion file)
└── ...
```

`history.py --home <home>` lists snapshots chronologically.
`revert.py --home <home> --to <id|name|pristine|previous>` restores
any of them — correctly removing the live persona files when the
target snapshot didn't have them (this is what makes "revert to
pristine when nothing existed before" work). The active record is
restored from the snapshot's manifest, or cleared if the target had
none.

The revert action is itself recorded as a new snapshot for
traceability.

## `.active.json`

```json
{
  "name": "Aldous",
  "card_file": "Aldous_20260501T120000.png",
  "imported_at": "2026-05-01T12:00:00+00:00",
  "user_noun": "the visitor",
  "soul_only": false,
  "has_hermes_md": true,
  "target": "hermes"
}
```

- `name` — `data.name` from the card at import time.
- `card_file` — basename inside `cards/` (no path).
- `imported_at` — ISO-8601 UTC timestamp of the *most recent*
  activation (import or switch).
- `user_noun` — the `--user-noun` value used when rendering. `switch`
  reuses this unless `--user-noun` is passed explicitly.
- `soul_only` — whether `--soul-only` was used. Same reuse rule on
  `switch`.
- `has_hermes_md` — whether the companion file was actually written
  this round.
- `target` — which `--target` produced this record (`hermes` /
  `openclaw` / `generic`). Records written by pre-v0.6 versions
  default to `"hermes"` on read.

The file is overwritten by every `import` and every `switch`. It is
removed by `delete` when the deleted card was active.

## `.trash/`

`delete.py` moves the card payload into `.trash/`, preserving the
filename. `restore.py` moves it back. Nothing in `.trash/` is ever
unlinked by SoulTavern; permanent deletion is a host-shell operation.

If a deleted card was active, the persona files are left in place —
only the `.active.json` pointer is cleared. To wipe the persona
entirely, switch to another card or remove the rendered files
manually.

## Card filenames

Filenames follow `{safe_name}_{YYYYMMDDTHHMMSS}{suffix}` where
`{safe_name}` is `data.name` with anything outside
`[A-Za-z0-9_.-]` collapsed to `_`. Collisions are rare because of the
timestamp; if one occurs (same name imported twice in the same second),
the second import overwrites the first inside `cards/` but the active
pointer still tracks it correctly.

## `--card` query resolution

For `switch` / `delete` / `restore`, the `--card` argument is matched
in this order:

1. Exact filename in `cards/` (or `cards/.trash/` for `restore`).
2. Case-insensitive equality with the filename stem.
3. Case-insensitive equality with the parsed `data.name`.
4. Case-insensitive prefix match against either of (2) or (3).

If multiple cards match at step (4), the command refuses and lists the
candidates. Disambiguate by passing the full filename.
