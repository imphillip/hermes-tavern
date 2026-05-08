# `<HERMES_HOME>/cards/` library layout

The library is created the first time `hermes-tavern import` runs.
All `list` / `current` / `switch` / `delete` / `restore` / `history` /
`revert` commands operate inside this directory.

**Small cards** (rendered output ≤ 15k per slot):

```
<HERMES_HOME>/
├── SOUL.md                        # rendered persona (active character)
├── HERMES.md                      # rendered lorebook (optional)
└── cards/
    ├── .active.json               # pointer to currently active card
    ├── .trash/                    # soft-deleted card payloads
    │   └── <name>_<ts>.<ext>
    ├── <name>_<ts>.json           # imported card backups
    ├── <name>_<ts>.png
    └── <name>_<ts>.yaml
```

**Oversized cards** (triggered when rendered SOUL or HERMES > 15k —
import stages source material on disk and the calling agent writes the
V2-category files; `hermes-tavern finalize` then assembles the curated
SOUL.md and indexed HERMES.md):

```
<HERMES_HOME>/
├── SOUL.md                        # curated persona (identity + personality + roleplay_guides)
├── HERMES.md                      # index pointing into extended/
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>          # original card backup
    └── <name>_<ts>/
        ├── source.md              # CLI-staged input for the agent
        └── extended/
            ├── identity.md ... examples.md   # agent-written V2 categories
            ├── alternate_greetings/01.md ... # CLI-staged at import time
            └── lore/<entry>.md ...           # CLI-staged at import time
```

`AGENTS.md` is intentionally never written — Hermes loads it only when
HERMES.md is absent, so the references would never reach the model.
The oversized-card flow merges the index into `HERMES.md`. See
`oversized-cards.md` for the full rationale, the agent procedure, and
failure modes.

## Launch posture

`HERMES.md` is read relative to **cwd** at hermes startup, not
`HERMES_HOME`. Users must `cd $HERMES_HOME` before running `hermes` or
the lorebook / extended-file index won't be loaded. `SOUL.md` is the
exception — it's anchored to `HERMES_HOME` regardless of cwd.

If `hermes` is already running in a channel when SOUL.md / HERMES.md
are updated, the model's system prompt is cached at session start —
the new files don't apply automatically. The user can either:

- run `/new` in the channel to start a fresh session, or
- run `/reset` in the channel to clear and reload

Both pick up the updated files. HermesTavern prints this reminder to
stderr after every `import` / `switch` / `revert`.

## `.snapshots/` — SOUL.md / HERMES.md history

Every `import` / `switch` / `revert` captures the resulting on-disk
state into `cards/.snapshots/<NNNN>_<ts>_<name>/`. Before the very
first mutation, a special `pristine` snapshot records the
pre-HermesTavern state (which may legitimately be "no SOUL.md or
HERMES.md existed"):

```
<HERMES_HOME>/cards/.snapshots/
├── 0001_pristine/
│   ├── manifest.json
│   └── (SOUL.md / HERMES.md if they existed pre-HermesTavern)
├── 0002_20260502T130000_Aldous/
│   ├── manifest.json
│   ├── SOUL.md
│   └── HERMES.md
└── ...
```

`hermes-tavern history --home <home>` lists snapshots chronologically.
`hermes-tavern revert --home <home> --to <id|name|pristine|previous>`
restores any of them — correctly removing the live SOUL.md / HERMES.md
when the target snapshot didn't have them (this is what makes "revert
to pristine when nothing existed before" work). The active record is
restored from the snapshot's manifest, or cleared if the target had
none.

The revert action is itself recorded as a new snapshot for traceability.

## `.active.json`

```json
{
  "name": "Aldous",
  "card_file": "Aldous_20260501T120000.png",
  "imported_at": "2026-05-01T12:00:00+00:00",
  "user_noun": "the visitor",
  "soul_only": false,
  "has_hermes_md": true
}
```

- `name` — `data.name` from the card at import time.
- `card_file` — basename inside `cards/` (no path).
- `imported_at` — ISO-8601 UTC timestamp of the *most recent* activation
  (import or switch).
- `user_noun` — the `--user-noun` value used when rendering. `switch`
  reuses this unless `--user-noun` is passed explicitly.
- `soul_only` — whether `--soul-only` was used. Same reuse rule on
  `switch`.
- `has_hermes_md` — whether HERMES.md was actually written this round.

The file is overwritten by every `import` and every `switch`. It is
removed by `delete` when the deleted card was active.

## `.trash/`

`hermes-tavern delete` moves the card payload into `.trash/`, preserving
the filename. `restore` moves it back. Nothing in `.trash/` is ever
unlinked by HermesTavern; permanent deletion is a host-shell operation.

If a deleted card was active, `SOUL.md` and `HERMES.md` are left in
place — only the `.active.json` pointer is cleared. To wipe the persona
entirely, switch to another card or remove the rendered files manually.

## Card filenames

Filenames follow `{safe_name}_{YYYYMMDDTHHMMSS}{suffix}` where
`{safe_name}` is `data.name` with anything outside
`[A-Za-z0-9_.-]` collapsed to `_`. Collisions are rare because of the
timestamp; if one occurs (same name imported twice in the same second),
the second import overwrites the first inside `cards/` but the active
pointer still tracks it correctly.

## `--card` query resolution

For `switch` / `delete` / `restore`, the `--card` argument is matched in
this order:

1. Exact filename in `cards/` (or `cards/.trash/` for `restore`).
2. Case-insensitive equality with the filename stem.
3. Case-insensitive equality with the parsed `data.name`.
4. Case-insensitive prefix match against either of (2) or (3).

If multiple cards match at step (4), the command refuses and lists the
candidates. Disambiguate by passing the full filename.
