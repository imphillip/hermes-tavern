# Distillation mode

Some SillyTavern cards are simply too detailed to fit in Hermes's static
context budget. The Hermes 20k char-per-slot cap is generous for most
cards but breaks on chub.ai exports that combine a 15k description with
five alternate openings and a thick lorebook. HermesTavern handles this
with a **distillation pipeline**: when the rendered output would exceed
75% of either slot, we ship the card to your Hermes CLI for compression
and lay out the full original content for runtime retrieval.

## Trigger

Distillation runs whenever:

- the rendered `SOUL.md` would exceed 15,000 characters, **or**
- the rendered `HERMES.md` would exceed 15,000 characters

(15k = 75% of the 20k Hermes slot, leaving ~5k of headroom for the trust
banner, headings, and any future Hermes-side prompt scaffolding.)

The check happens after the normal render — including placeholder
substitution and security sanitisation — so what gets distilled is what
would have shipped, not the raw card.

You can opt out with `--no-distill`, in which case the original
`BudgetExceededError` surfaces and you get to trim the card by hand.
You can also point HermesTavern at a different distillation command
with `--distill-cmd "<your command>"` (default: `hermes -q`).

## Pipeline

When distillation triggers, HermesTavern:

1. Writes the **full original content** to
   `<HERMES_HOME>/cards/<card_stem>/extended/`, one file per field:
   ```
   extended/
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
2. Builds a single distillation prompt containing the rendered
   SOUL.md and HERMES.md plus tight character-count limits.
3. Shells out to the configured command (default `hermes -q`),
   appending the prompt as a final argument. This reuses your Hermes
   instance's already-configured model and API key — HermesTavern
   never bundles its own LLM SDK.
4. Parses the response, expecting:
   ```
   <soul>
   ...compressed identity...
   </soul>
   <lore>
   ...compressed always-on lore, or NONE if not worth keeping...
   </lore>
   ```
5. Writes the compressed `<soul>` content to `SOUL.md`.
6. Writes `HERMES.md` containing (a) the compressed `<lore>` block, if
   any, and (b) an index of the extended files in step (1) with
   one-line "read me when …" hints.

## Why HERMES.md and not AGENTS.md

Hermes's context loader picks up files in priority order:

1. `SOUL.md` — independent identity slot (always loaded from `HERMES_HOME`)
2. `HERMES.md` / `.hermes.md` — project context, **loaded from cwd**
3. `AGENTS.md` — fallback for the same slot, **only when HERMES.md is absent**
4. `CLAUDE.md` / `.cursorrules` — lower priority still

If we wrote both `HERMES.md` and `AGENTS.md`, the loader would use
HERMES.md and silently ignore AGENTS.md — and our extended-file
references would never reach the model. So HermesTavern always merges
the index into `HERMES.md` and never writes `AGENTS.md`.

## Launch posture

`SOUL.md` is read from `HERMES_HOME`, but `HERMES.md` is read relative
to **cwd at hermes startup**. If you run `hermes` from your home
directory while `HERMES_HOME` points at `~/.hermes-roleplay`, the
SOUL.md will load but the HERMES.md (and therefore the persona's
extended-file index) will not.

The required posture is:

```bash
cd $HERMES_HOME && hermes
```

HermesTavern prints this reminder to stderr after every `import` /
`switch` so it's hard to miss. The README and SKILL.md call it out at
the top.

## Final layout

```
<HERMES_HOME>/
├── SOUL.md                  # distilled identity (compact)
├── HERMES.md                # distilled lore + extended-file index
└── cards/
    ├── .active.json
    ├── <card_stem>.<ext>    # original card backup
    └── <card_stem>/
        └── extended/
            ├── description.md
            ├── alternate_greetings/01.md ...
            └── lore/<entry>.md
```

## Runtime retrieval

`HERMES.md` carries an index of the form:

```markdown
## Extended material on disk

The following files contain the **full original** card content. Read
them with your file tools when the conversation calls for specifics
about Aldous that aren't already in this file or SOUL.md.

- `cards/Aldous_…/extended/description.md` — Full description: long-form identity of Aldous; read for biographical detail
- `cards/Aldous_…/extended/lore/Mirror_Lake.md` — Mirror Lake: lorebook entry; relevant when conversation touches lake
- ...
```

This is loaded statically by Hermes at startup. The model sees the
index and uses its own file-reading tools to pull a specific extended
file when the conversation calls for it. HermesTavern does not implement
the retrieval mechanism itself — that lives entirely in Hermes (and
ultimately in the model's tool-use). What we provide is a layout the
model can navigate.

## Files HermesTavern intentionally never writes

- **AGENTS.md** — shadowed by HERMES.md, would never load.
- **MEMORY.md / USER.md** — owned by the running agent; the agent
  rewrites them via its memory tool, so anything HermesTavern wrote
  would be clobbered on the next session.
- **CLAUDE.md / .cursorrules** — lower-priority context files used by
  other tools; out of scope.

## Failure modes

- **Distillation command not on PATH** → `DistillationError`; pass
  `--no-distill` to fall back, or install `hermes-agent`, or override
  `--distill-cmd` to point at your actual binary.
- **Distillation command exits non-zero** → `DistillationError` with
  the last few stderr lines.
- **Response missing `<soul>` block** → `DistillationError`; the model
  drifted from the requested output format. Re-run; consider a stronger
  model.
- **Distilled output still over 19k hard cap** → currently no hard
  guard; the SOUL.md is written as-is. We rely on the LLM honouring
  the 12k target stated in the prompt. If this becomes a recurring
  issue, add a post-distillation re-render that re-applies the budget
  check.
- **Switching back to a previously-distilled card** → re-runs
  distillation. Cached compression is not implemented in v1.
- **Editing SOUL.md / HERMES.md after `hermes` is already running** →
  no effect. The system prompt is cached at session start. Run `/reset`
  in the hermes session, or start a new session.

## Cost / latency notes

Distillation adds one LLM call per `import` or `switch`. For the
default `hermes -q` invocation that is whatever Hermes is configured
with — typically Claude Sonnet/Opus or your local model. A 40k-char
input + 24k-char output prompt costs roughly the same as a 20-message
chat turn, depending on model.

Cards under the 75% threshold pay zero distillation cost; the path is
entirely skipped. If you're rotating between several large cards
frequently and want to avoid repeated distillation calls, the cleanest
workaround for v1 is to keep separate `HERMES_HOME` directories per
card so the active SOUL.md / HERMES.md persist between sessions.

## Design rationale

Three reasons we chose this architecture over the obvious alternative
(field-level "spillover" from SOUL.md to HERMES.md):

1. **Spillover just splits one big always-on prompt into two big
   always-on prompts.** Tokens still get burned on every conversation
   turn even when the user never asks about the obscure third
   alternate greeting.
2. **Distillation produces a tight identity prompt that captures
   essence**, not blob. A good summary of a 20-page character bible
   reads better than a tail-truncated dump of it.
3. **Dynamic loading aligns with how Hermes-style agents work** —
   retrieval over stuffing. The model only spends tokens on detail
   when the conversation actually calls for it.

The trade-off is the upfront LLM call, the dependency on a working
`hermes -q` (or equivalent) at import time, and the model's good
judgement about which extended file to pull. We think it's the right
call; opt out with `--no-distill` if you disagree.
