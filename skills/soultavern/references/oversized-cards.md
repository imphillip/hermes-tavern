# Oversized cards (agent-driven flow)

Some SillyTavern cards are too detailed to fit a runtime's static
context budget. Hermes's 20k-char-per-slot cap is generous for most
cards but breaks on chub.ai exports that combine a 15k description
with five alternate openings and a thick lorebook; OpenClaw's 12k
per-file cap is even tighter. SoulTavern handles those by **handing
the categorization work to the calling agent** rather than shelling
out to a separate LLM.

This is the v0.4.5 architecture. Earlier versions (≤ v0.4.0) tried
to shell out to `hermes -q "<prompt>"`; that coupled the tool to a
specific Hermes CLI shape and broke as soon as the subcommand layout
changed. The agent-driven flow has the same end-state — curated
SOUL.md, indexed companion file, full original on disk — but the LLM
call happens inside the agent's own context with whatever tools it
already has.

## Trigger

The agent flow is invoked whenever the rendered SOUL.md or companion
file would exceed the runtime's per-target threshold:

| target | threshold (per file) |
| --- | --- |
| `hermes` | 15,000 chars (75% of the 20k slot) |
| `openclaw` | 9,000 chars (75% of the 12k per-file budget) |

The check happens after the normal render — including placeholder
substitution and security sanitization — so what gets staged is what
would have shipped, not the raw card.

## Phase 1 — staging (script, deterministic)

`python3 SKILL_DIR/scripts/import.py --card <oversized.png> --home <home>`
does the following before exiting with code 2:

1. Copies the card into `<home>/cards/<name>_<ts>.<ext>` (same as for
   small cards).
2. Writes `<home>/cards/<name>_<ts>/source.md`. This is a
   self-describing markdown view of the parsed card:
   - One `## <field>` block per V2 prose field (description,
     personality, scenario, first_mes, mes_example, system_prompt,
     post_history_instructions).
   - Description fields with `Header:` style sub-headers (a common
     chub.ai pattern, e.g. `Full Name: ...`, `Appearance: ...`) are
     pre-flagged as `### Header` blocks so the agent gets cleaner
     input.
   - One `## alternate_greeting #N` block per opening.
   - One `### <label>` block per character_book entry, with keys
     preserved in an HTML comment.
3. Writes the per-entry payloads directly (no LLM judgement needed —
   they're already structured per-entry):
   ```
   <home>/cards/<name>_<ts>/extended/
   ├── alternate_greetings/
   │   ├── 01.md
   │   └── 02.md
   └── lore/
       ├── Mirror_Lake.md
       └── Old_Council.md
   ```
4. Raises `NeedsAgentCategorizationError`, which the script converts
   to exit code 2 with a structured message pointing the agent at the
   `source.md` path and the SKILL.md procedure.

## Phase 2 — agent categorization (in your context, no subprocess)

The agent reads `cards/<stem>/source.md` and writes up to eight files
into the sibling `extended/` directory:

```
extended/
├── identity.md          # name, age, ethnicity, height, basic facts
├── appearance.md        # physical description, body, voice
├── personality.md       # traits, archetype, mannerisms, speech style
├── backstory.md         # past events, history, formative context
├── scenario.md          # the opening situation
├── kinks.md             # sexual preferences, fetishes (if present)
├── roleplay_guides.md   # explicit "how to portray" instructions
└── examples.md          # sample dialogue / interaction patterns
```

Rules (also stated in SKILL.md):

- **Faithful to source wording.** Reuse sentences verbatim. The voice
  belongs to the source.
- **Skip empty categories.** Don't fabricate content for categories
  the source doesn't speak to. Missing files are a signal, not a bug.
- **Decline gracefully.** If part of the source conflicts with the
  agent's operating policy, leave the affected category absent and
  move on. Don't silently rewrite — the user will see the absence.
- **One H1 per file**, e.g. `# Identity`. `finalize.py` strips the H1
  when re-rendering and uses it for the index title.

The agent should not touch `alternate_greetings/` or `lore/` — those
are already on disk from phase 1.

## Phase 3 — finalize (script, deterministic)

```bash
python3 SKILL_DIR/scripts/finalize.py --card <name> --home <home>
```

This:

1. Loads `extended/<cat>.md` for each V2 category (missing/empty
   files become empty strings — visible in the resulting index by
   absence).
2. Renders the **curated SOUL.md** from a small subset of categories:
   `identity`, `personality`, `roleplay_guides`. These are the
   always-on essentials; everything else is reachable on demand.
3. Walks `extended/` and builds an `ExtendedFile` index covering V2
   categories + alternate greetings + lorebook entries.
4. Renders the **indexed companion file** with director's notes and
   the index entries. For `--target hermes` that's `HERMES.md`; for
   `--target openclaw` it's the AGENTS.md managed section.
5. Writes both files into `<home>/`, updates `.active.json` with
   `finalized: true`, and takes a snapshot.

## Why HERMES.md and not AGENTS.md (hermes target)

Hermes's context loader picks up files in priority order:

1. `SOUL.md` — independent identity slot (always loaded from `HERMES_HOME`)
2. `HERMES.md` / `.hermes.md` — project context, **loaded from cwd**
3. `AGENTS.md` — fallback for the same slot, **only when HERMES.md is absent**
4. `CLAUDE.md` / `.cursorrules` — lower priority still

If SoulTavern wrote both `HERMES.md` and `AGENTS.md`, the loader would
use HERMES.md and silently ignore AGENTS.md — and our extended-file
references would never reach the model. So `--target hermes` always
merges the index into `HERMES.md` and never writes `AGENTS.md`.

OpenClaw's loader inverts this: `AGENTS.md` outranks `SOUL.md`, and
there's no separate "HERMES.md" slot — so `--target openclaw` uses
the AGENTS.md managed section as the index home and SOUL.md as the
persona body. Existing user content in AGENTS.md outside the
`<!-- BEGIN soultavern:character -->` markers is preserved on every
import / switch / delete / revert.

## Launch posture

`SOUL.md` is read from `<home>` regardless of cwd. `HERMES.md`
(hermes target) is read relative to **cwd at hermes startup** —
if you run `hermes` from your home directory while `HERMES_HOME`
points at `~/.hermes-roleplay`, the SOUL.md will load but the
HERMES.md (and therefore the persona's extended-file index) will not.

The required posture for `--target hermes` is:

```bash
cd $HERMES_HOME && hermes
```

For `--target openclaw`, all three persona files (`SOUL.md`,
`AGENTS.md`, `IDENTITY.md`) are read from the workspace root the
runtime is launched against — no separate cwd-vs-home split.

SoulTavern prints the activation reminder to stderr after every
`import` / `finalize` / `switch` so it's hard to miss.

## Final layout

```
<home>/
├── SOUL.md                  # curated identity (compact, from SOUL_PICKS)
├── <companion>              # index over extended/ files
│                              (HERMES.md or AGENTS.md managed section)
├── IDENTITY.md              # openclaw target only — character metadata
└── cards/
    ├── .active.json
    ├── <stem>.<ext>         # original card backup
    └── <stem>/
        ├── source.md        # agent's input, kept for reference / re-finalize
        └── extended/
            ├── identity.md ... examples.md
            ├── alternate_greetings/01.md ...
            └── lore/<entry>.md
```

`source.md` is preserved on disk after finalize for two reasons:
re-running `finalize.py` after editing a category file should never
require a re-import, and the user occasionally wants to see what was
fed to the agent.

## Switching back to a finalized card

`switch.py --card <name> --home <home>` on an already-finalized
oversized card detects the populated `extended/` and skips straight
to `finalize` semantics — no agent intervention needed. The agent
only re-engages if `extended/` is missing or empty (e.g. the user
deleted the directory).

## Files SoulTavern intentionally never writes

- **AGENTS.md** (hermes target) — shadowed by HERMES.md, would never
  load. (The openclaw target *does* write a managed section into
  `AGENTS.md`, but only the marker-bounded segment.)
- **MEMORY.md / USER.md** — owned by the running agent; the agent
  rewrites them via its memory tool, so anything SoulTavern wrote
  would be clobbered on the next session.
- **CLAUDE.md / .cursorrules** — lower-priority context files used
  by other tools; out of scope.

## Failure modes

- **Agent skipped phase 2 and ran `finalize.py` immediately** →
  `LibraryError` with the message `no agent categorization found in
  <extended_dir>`. Read `source.md`, write the category files, retry.
- **Agent declined to categorize a sensitive section** → finalize
  succeeds, the category is absent from the index, and that material
  stays only in `source.md`. The user can either re-engage a
  different agent on `source.md` or accept the gap.
- **One category file is over-stuffed and pushes curated SOUL.md
  past the budget** → `BudgetExceededError` from `finalize.py`. The
  picks (identity + personality + roleplay_guides) need to be
  trimmed. Re-edit the offending file and re-run.
- **Editing persona files after the runtime is already running** →
  no effect. The system prompt is cached at session start. Start a
  fresh session (Hermes: `/reset` or `/new`).

## Design rationale

Three reasons we chose agent-driven categorization over the obvious
alternatives:

1. **No CLI/LLM coupling.** v0.4.0 shelled out to `hermes -q
   "<prompt>"` and broke the moment Hermes changed its subcommand
   parser. The agent already has tools for reading and writing files
   in its own context; reusing those is more durable than maintaining
   a subprocess shim.
2. **Same trust posture.** When the agent reads `source.md` it
   applies the same third-party-content posture it would apply to any
   file handed to it from outside — including the option to decline.
   A subprocess LLM has no such contextual awareness.
3. **Compatible with retrieval.** Modern agents retrieve over
   stuffing. SOUL.md carries the always-on essentials; everything
   else is one tool-call away. The agent that did the categorization
   is the same kind of agent that will later read those files at
   runtime.

The trade-off is that the agent must perform an extra step. We think
that's the right call: the agent is already in the loop, it has the
context, and the resulting layout is a much cleaner separation of
"identity" from "reference."
