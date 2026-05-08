# Usage recipes

Channel-agnostic by design — these recipes apply equally whether the user
talks to Hermes through CLI, email, Telegram, Discord, Slack, or any other
configured gateway. Channel configuration lives entirely on the Hermes
side; HermesTavern only writes the persona files.

## 1. First-time import

```bash
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay
HERMES_HOME=~/.hermes-roleplay hermes
```

The import copies `aldous.png` into `~/.hermes-roleplay/cards/` for
safekeeping, renders `SOUL.md` (and `HERMES.md` if the card has a
lorebook) into `~/.hermes-roleplay/`, and records the new card as active.

## 2. Preview before committing

```bash
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --dry-run
```

Renders to stdout in fenced markdown blocks. No files are touched, no
backup is made, no active record is updated.

## 3. Replace an existing persona

The import command refuses to overwrite by default. Two ways to switch:

```bash
# (a) Re-import the same or a new card
hermes-tavern import --card alice.png --home ~/.hermes-roleplay --overwrite

# (b) Switch to a card already in the library
hermes-tavern switch --card alice --home ~/.hermes-roleplay
```

Prefer (b) when the card is already imported — it does not duplicate the
backup and reuses the previous `--user-noun` setting.

## 4. Rotating between several characters

Import each card once:

```bash
hermes-tavern import --card alice.png --home ~/.hermes-roleplay
hermes-tavern import --card bob.json  --home ~/.hermes-roleplay --overwrite
hermes-tavern import --card carol.png --home ~/.hermes-roleplay --overwrite
```

Then switch on demand:

```bash
hermes-tavern list   --home ~/.hermes-roleplay
hermes-tavern switch --card alice --home ~/.hermes-roleplay
```

For *concurrent* multi-character setups (e.g. one Hermes for Alice on
Telegram, another for Bob on Discord), use **separate `HERMES_HOME`
directories** rather than trying to multiplex one instance.

## 5. Custom address term

```bash
hermes-tavern import --card alice.png \
                     --home ~/.hermes-roleplay \
                     --user-noun "the operator"
```

Every `{{user}}` / `<USER>` token in the card is replaced with
"the operator" instead of the default "the visitor". The choice is
recorded in `.active.json` so subsequent `switch` calls reuse it unless
overridden.

## 6. Skip the lorebook

```bash
hermes-tavern import --card alice.png --home ~/.hermes-roleplay --soul-only
```

Useful when (a) the lorebook would push you over the 20k-char Hermes cap,
or (b) you want a leaner persona without world-building context. If a
previous run wrote `HERMES.md`, it is removed.

## 7. Delete and restore

```bash
# Send a card to the trash
hermes-tavern delete --card bob --home ~/.hermes-roleplay

# Inspect what's in the trash
hermes-tavern list --home ~/.hermes-roleplay --all

# Pull it back out
hermes-tavern restore --card bob --home ~/.hermes-roleplay
```

Notes:

- `delete` is always soft — files move to `cards/.trash/`, never
  unlinked. Empty the trash from the host shell when you are sure
  (`rm ~/.hermes-roleplay/cards/.trash/*`).
- If you delete the *active* card, `SOUL.md` and `HERMES.md` stay in
  place — the active record is just cleared. Switch to another card if
  you want the persona gone too.
- `restore` puts the card back into `cards/` but does **not** make it
  active. Run `hermes-tavern switch` afterwards to load it.

## 8. Sanity-check a card before importing

```bash
hermes-tavern validate --card aldous.png
```

Reports which fields are populated and the projected SOUL.md / HERMES.md
sizes against the 19k budget. Exit code is non-zero if rendering would
fail.

## 9. Where channel safety lives

HermesTavern intentionally does not configure:

- per-channel allowlists / blocklists
- `platform_toolsets`
- rate limits or cost caps
- LLM model selection

All of that is set on the Hermes side (typically in the user's hermes
config). HermesTavern only writes `SOUL.md` and `HERMES.md` — the loaded
persona is then visible to whichever channels Hermes is already talking
on.

## 10. Backups

Every import copies the original card to
`<HERMES_HOME>/cards/<name>_<timestamp>.<ext>`. Treat this directory as
your character library — back it up like any other dotfile dir.
