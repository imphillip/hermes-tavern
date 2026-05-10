# Usage recipes

Channel-agnostic by design — these recipes apply equally whether the
user talks to the runtime through CLI, email, Telegram, Discord, Slack,
or any other configured gateway. Channel configuration lives entirely
on the runtime side; SoulTavern only writes the persona files.

All examples use the hermes target. Set `SKILL=path/to/skills/soultavern`
first; for the openclaw target swap `--target openclaw` and use your
OpenClaw workspace dir instead of `$HERMES_HOME`.

## 1. First-time import

```bash
python3 $SKILL/scripts/import.py --card aldous.png --home $HERMES_HOME
cd $HERMES_HOME && hermes
```

The import copies `aldous.png` into `$HERMES_HOME/cards/` for
safekeeping, renders `SOUL.md` (and `HERMES.md` if the card has a
lorebook) into `$HERMES_HOME/`, and records the new card as active.

## 2. Preview before committing

```bash
python3 $SKILL/scripts/import.py --card aldous.png --home $HERMES_HOME --dry-run
```

Renders to stdout in fenced markdown blocks. No files are touched, no
backup is made, no active record is updated.

## 3. Replace an existing persona

The import script refuses to overwrite by default. Two ways to switch:

```bash
# (a) Re-import the same or a new card
python3 $SKILL/scripts/import.py --card alice.png --home $HERMES_HOME --overwrite

# (b) Switch to a card already in the library
python3 $SKILL/scripts/switch.py --card alice --home $HERMES_HOME
```

Prefer (b) when the card is already imported — it does not duplicate the
backup and reuses the previous `--user-noun` setting.

## 4. Rotating between several characters

Import each card once:

```bash
python3 $SKILL/scripts/import.py --card alice.png --home $HERMES_HOME
python3 $SKILL/scripts/import.py --card bob.json  --home $HERMES_HOME --overwrite
python3 $SKILL/scripts/import.py --card carol.png --home $HERMES_HOME --overwrite
```

Then switch on demand:

```bash
python3 $SKILL/scripts/list.py   --home $HERMES_HOME
python3 $SKILL/scripts/switch.py --card alice --home $HERMES_HOME
```

For *concurrent* multi-character setups (e.g. one runtime instance for
Alice on Telegram, another for Bob on Discord), use **separate `<home>`
directories** rather than trying to multiplex one instance.

## 5. Custom address term

```bash
python3 $SKILL/scripts/import.py --card alice.png \
        --home $HERMES_HOME \
        --user-noun "the operator"
```

Every `{{user}}` / `<USER>` token in the card is replaced with
"the operator" instead of the default "the visitor". The choice is
recorded in `.active.json` so subsequent `switch.py` calls reuse it
unless overridden.

## 6. Skip the lorebook

```bash
python3 $SKILL/scripts/import.py --card alice.png --home $HERMES_HOME --soul-only
```

Useful when (a) the lorebook would push you over the runtime's per-file
budget, or (b) you want a leaner persona without world-building context.
If a previous run wrote a companion file (`HERMES.md` for hermes target,
`AGENTS.md` managed section for openclaw), it is removed.

## 7. Delete and restore

```bash
# Send a card to the trash
python3 $SKILL/scripts/delete.py --card bob --home $HERMES_HOME

# Inspect what's in the trash
python3 $SKILL/scripts/list.py --home $HERMES_HOME --all

# Pull it back out
python3 $SKILL/scripts/restore.py --card bob --home $HERMES_HOME
```

Notes:

- `delete` is always soft — files move to `cards/.trash/`, never
  unlinked. Empty the trash from the host shell when you are sure
  (`rm $HERMES_HOME/cards/.trash/*`).
- If you delete the *active* card, the persona files (`SOUL.md` plus
  the target's companion files) stay in place — the active record is
  just cleared. Switch to another card if you want the persona gone too.
- `restore` puts the card back into `cards/` but does **not** make it
  active. Run `switch.py` afterwards to load it.

## 8. Sanity-check a card before importing

```bash
python3 $SKILL/scripts/validate.py --card aldous.png
```

Reports which fields are populated and the projected SOUL.md / companion
sizes against the budget. Exit code is non-zero if rendering would fail.

## 9. Where channel safety lives

SoulTavern intentionally does not configure:

- per-channel allowlists / blocklists
- `platform_toolsets`
- rate limits or cost caps
- LLM model selection

All of that is set on the runtime side (Hermes config, OpenClaw config,
etc.). SoulTavern only writes the persona files — the loaded persona
is then visible to whichever channels the runtime is already talking on.

## 10. Backups

Every import copies the original card to
`<home>/cards/<name>_<timestamp>.<ext>`. Treat this directory as
your character library — back it up like any other dotfile dir.
